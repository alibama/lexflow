# lexflow question catalogue: next candidates

**How citations are marked.** "Verified (repo)" means the section already appears in `curated/{va,dc,md}/*.json`. Those files record that their quotes were checked against open-us-law v2026.09.1. That check covers only the quoted text, not the subsection details given here. Everything else comes from memory and is marked **unverified**. Check it against law.lis.virginia.gov, code.dccouncil.gov and mgaleg.maryland.gov before ingesting. Two case citations are well known but were not checked this session, and they are marked that way.

**What lexflow already covers.** It has two questions: "start a business" (an LLC filing path in VA, DC and MD) and "request public records" (VA § 2.2-3704; DC §§ 2-532 and 2-537; MD GP §§ 4-202, 4-203 and 4-206). Several questions below reuse those models instead of starting from nothing.

**Local overlay note for the three test areas:**
- Charlottesville is an independent city with its own assessor, permit office and development code.
- Baltimore City is outside any county. It writes its own building and zoning codes, but the state (SDAT) assesses its property.
- DC is state and city at once. "State" law and "local" law there are both the DC Code and the DCMR.

---

## A. General public

### A1. Do I need a building permit for this project (deck, fence, shed, finished basement, water heater, roof), and how do I get one?
- **Who it helps:** Homeowners, DIYers, small landlords, handymen and small contractors. Unpermitted work causes trouble when you sell, with insurance claims, and with code enforcement.
- **Governing law:**
  - VA: the Uniform Statewide Building Code. The enabling statute is Va. Code § 36-97 et seq. and the regulations are 13VAC5-63. The list of work exempt from permits is in USBC § 108.2 in recent editions. Localities enforce the code and set fees, but they may not change the technical provisions. Charlottesville permits go through Neighborhood Development Services. (All unverified.)
  - DC: the DC Construction Codes, 12 DCMR (12A Building, 12B Residential), administered by the Department of Buildings, which took this over from DCRA in 2022. (Unverified.)
  - MD: the Maryland Building Performance Standards, Public Safety Art. § 12-501 et seq. Local governments may amend them. Baltimore City adopts its own Building, Fire, and Related Codes, administered by DHCD. (Unverified.)
- **Process and decision shape:**
  - DMN `permit_required`. Inputs: jurisdiction, project type, size (square feet and height), attached to the house or not, structural or not, historic district or not, floodplain or not, owner-occupied or not. Outputs: whether a permit is needed and for which trades, walk-through or plan review, other approvals needed (zoning, historic), and whether the owner may pull the permit or a licensed contractor must.
  - BPMN: decide whether a permit is needed → zoning check → apply with plans → plan review, with a loop for corrections → pay fees → permit issued → inspections (footing, framing, final) as milestone events → certificate of completion.
  - Local overlay: permit portal, fee schedule, inspection request line, historic district map.
- **State or local:** Both. The state adopts the code; the locality runs it and sets fees.
- **Feasibility:** High. The exemption list works as a clean decision table, and the three test areas run permits three different ways, which is a good test of per-locality search.
- **Main caveat:** The exemption list changes with each code edition (VA readopts about every three years), so lexflow must quote the current edition. It should answer "do I need a permit and what is the process", not technical code questions such as joist spans.

### A2. My property assessment went up a lot. How do I appeal it, and what is the deadline?
- **Who it helps:** Every property owner, every reassessment cycle.
- **Governing law:**
  - VA: Board of Equalization, Va. Code § 58.1-3370 et seq. Corrections by the assessor or commissioner, §§ 58.1-3980 and 3981. Circuit court, § 58.1-3984. Charlottesville has its own City Assessor and Board of Equalization. (All unverified.)
  - DC: OTR first-level review, then the Real Property Tax Appeals Commission, D.C. Code § 47-825.01a. (Unverified.)
  - MD: an appeal to the SDAT supervisor, then the PTAAB, then the Maryland Tax Court, under Tax-Property Art. § 14-502 et seq. Baltimore City follows this state process directly. (Unverified.)
- **Process and decision shape:**
  - BPMN: notice received → optional informal review → first-level appeal, with a deadline counted from the notice date → hearing → decision → second-level appeal → court. Each deadline is a timer event.
  - DMN `appeal_route`. Inputs: jurisdiction, property class, appeal tier, days since notice. Outputs: where to file, the form, the deadline, whether there is a hearing, and the burden of proof (the assessment is presumed correct).
  - A second DMN, `evidence_checklist`, suggests evidence such as comparable sales, an appraisal or photos of the property's condition.
- **State or local:** Both. State procedure, local calendars and forms.
- **Feasibility:** High.
- **Main caveat:** Notice dates move with the cycle (MD reassesses each area every three years; VA localities vary). The current year's date has to come from the local overlay, not the statute. Keep homestead and other tax credits as a separate question.

### A3. My landlord won't make repairs (no heat, leaks, mold, pests). What can I do, and can I withhold rent?
- **Who it helps:** Tenants, and small landlords who want to know what they owe.
- **Governing law:**
  - VA: the Residential Landlord and Tenant Act, Va. Code § 55.1-1200 et seq. The landlord's duty to maintain is § 55.1-1220. A tenant can pay rent into court escrow under a tenant's assertion, § 55.1-1244. (All unverified.)
  - DC: the Housing Code at 14 DCMR, plus the implied warranty of habitability from *Javins v. First National Realty Corp.*, 428 F.2d 1071 (D.C. Cir. 1970). The housing code is unverified; *Javins* is well known but was not checked this session.
  - MD: rent escrow under Real Property Art. § 8-211. Baltimore City has its own local rent escrow provisions in the Public Local Laws, § 9-9 et seq. (Unverified.)
- **Process and decision shape:**
  - BPMN: written notice to the landlord → statutory waiting period (timer) → three branches: a code-enforcement complaint, a rent escrow filing with rent paid into court on time, or ending the lease where the law allows it → hearing → order.
  - DMN `repair_remedy`. Inputs: condition type, whether it threatens health or safety, whether written notice was given, days since notice, whether the tenant is current on rent. Outputs: remedies available, where to file, whether rent must go into court, and a fixed warning: do not simply stop paying rent.
  - A small second DMN covers the presumption of retaliation.
  - Nuisance and noise complaints fit here as the code-enforcement branch.
- **State or local:** Mostly state, with local code enforcement and, in Baltimore City, a local escrow scheme.
- **Feasibility:** High.
- **Main caveat:** Getting this wrong can get someone evicted. The output must say that rent withholding outside the statutory procedure is risky, and it must send people to legal aid. Public and subsidized housing adds federal rules that this model does not cover.

### A4. I'm in prison or just got out. Can I realistically start my own business, and what will my record block?
- **Who it helps:** People getting ready for release, people recently released, and their families.
- **Why this one, honestly:** Self-employment is often the most reachable route to income. A general business license, a trade name filing and the business tax registration do not ask about criminal history. Employers screen, and many will not hire. The real barriers are narrower and easy to predict:
  - licensed trades (barbering, HVAC, electrical, contracting);
  - conditions of probation or parole (the supervising officer may need to approve self-employment, and contact or travel limits can rule out some work);
  - debts that block licenses or bank accounts (child support arrears, unpaid fines, ChexSystems records).

  A sole proprietorship is the cheapest start, so this question is a direct use of the sole-proprietorship branch the business DMN is being extended to cover.
- **Governing law:**
  - Formation: VA trade name certificate, § 59.1-69; VA local BPOL license, § 58.1-3703; DC basic business license, §§ 47-2851.02 and 47-2855.02. (All verified (repo).)
  - Criminal history and licensing:
    - VA: § 54.1-204 says a prior conviction alone does not disqualify someone from a license unless the conviction directly relates to the occupation. (Unverified.)
    - MD: fair-chance licensing provisions exist, including a pre-application determination. The section number is not confirmed. (Unverified.)
    - DC: occupational licensing boards apply a criminal-record review standard. The section is not confirmed. (Unverified.)
  - Supervision conditions come from the court order or the parole board, not from statute.
- **Process and decision shape:**
  - Reuse the business BPMN with a gate in front of it.
  - DMN `reentry_business_gate`. Inputs: jurisdiction, intended work (unlicensed / licensed trade / regulated by a federal agency), offense category, years since conviction, on supervision or not, child support arrears or not, banking status. Outputs:
    - which entity path fits (usually a sole proprietorship with a trade name);
    - whether a license board review applies and whether a pre-application determination exists;
    - "ask your PO before you start" when the person is on supervision;
    - "open a second-chance bank account" when banking is blocked.
- **State or local:** Both. State formation and licensing law, local business license.
- **Feasibility:** High for the formation part, since it is mostly verified sections already in the repo. Medium for the licensing gate.
- **Main caveat:** Fair-chance licensing laws promise an individual review, not a license. Some fields stay closed for some offenses, either by statute or because of federal rules (for example, a CDL hazmat endorsement or work in childcare). The DMN has to say "likely barred" plainly where that is the answer.

### A5. Can I get my record sealed or expunged, and if not now, when?
- **Who it helps:** Released people and their families. This is the most-asked reentry question.
- **Governing law:**
  - VA: petition-based sealing under Va. Code § 19.2-392.12, and automatic sealing under §§ 19.2-392.6, 392.7 and 392.11, effective July 1, 2026. The section numbers and the effective date were confirmed by web search in an earlier pass; the eligibility details were not.
  - MD: expungement under Crim. Proc. §§ 10-101 to 10-110, and shielding under §§ 10-301 to 10-306. Shielding is granted once per lifetime, and the prosecutor has 30 days to object. The structure was confirmed by web search in an earlier pass; the waiting periods were not.
  - DC: the Second Chance Amendment Act of 2022, D.C. Code § 16-801 et seq., with automatic sealing in § 16-805 and sealing by motion in § 16-806. (The mapping of sections to topics is partly unverified.)
- **Process and decision shape:**
  - BPMN: get your record → classify each charge → check whether relief is automatic → if not, petition the court → serve the prosecutor → objection window (timer) → ruling → order sent to the agencies.
  - DMN inputs: disposition, offense class, excluded-offense flags, date the sentence was completed, new convictions since, earlier grants. Outputs: remedy type (auto-seal / petition / expunge / shield / not eligible), earliest eligible date, which court, and fee or fee waiver.
- **State or local:** Mostly state.
- **Feasibility:** High for the statutory table. The hard part is a lookup table from each state's offense codes to statutes.
- **Main caveat:** For many people the honest output is "not eligible until a given date" or "not eligible". Automatic sealing depends on agencies carrying it out, so lexflow should show implementation status separately from legal eligibility. Sealed records stay in private background-check databases that already copied them.

---

## B. A FOIA-request and redaction legal services business

These build on the existing records question, which models only the requester's first step.

### B1. They withheld or redacted records. Which exemption did they claim, does it actually apply, and did they have to release the rest?
- **Who it helps:** The service's analysts reviewing a production, and requesters who got heavily redacted pages.
- **Governing law:**
  - VA: the exemptions are in Va. Code §§ 2.2-3705.1 to 2.2-3705.7, and § 2.2-3704.01 says that if part of a record is exempt, the rest must be released with the exempt part redacted. (Unverified.) A denial must cite the specific Code section, § 2.2-3704(B). (The section is verified (repo); the subsection detail is unverified.)
  - DC: the exemptions are in D.C. Code § 2-534, and § 2-534(b) requires release of any reasonably segregable part of a record. (Unverified.)
  - MD: the denial provisions are GP § 4-301 et seq., which separates mandatory denials from discretionary ones; § 4-343 makes discretionary denials subject to a public-interest test. (Unverified.) The denial must be in writing and give reasons, § 4-203. (The section is verified (repo); the subsection detail is unverified.)
- **Process and decision shape:**
  - DMN `exemption_check`. Inputs: jurisdiction, record category (personnel, criminal investigative, legal advice, trade secret, personal identifiers, and so on), the exemption cited, and whether the agency gave a written reason. Outputs:
    - whether the exemption exists and fits the category;
    - whether withholding is mandatory or discretionary;
    - whether the agency had to redact and release the rest instead of withholding the whole record;
    - a challenge flag.
  - A per-page review loop records each redaction and the exemption cited for it.
- **State or local:** State law. It applies the same way to cities and counties.
- **Feasibility:** Medium. There are many exemptions (VA has well over a hundred), so ingest by category in stages.
- **Main caveat:** Whether an exemption fits a particular record is a judgment call, and courts weigh it. The DMN can flag a mismatch or a blanket withholding, but it cannot settle the dispute.

### B2. What can they charge for records, and can the fees be waived or challenged?
- **Who it helps:** Requesters facing large estimates, and the service when it prices engagements.
- **Governing law:**
  - VA: § 2.2-3704(F) allows reasonable charges that do not exceed actual cost. The requester may ask for a cost estimate in advance, and a deposit may be required above a set amount. (The section is verified (repo); the subsection letters and dollar amounts are unverified.)
  - DC: fees under § 2-532(b) (the section is verified (repo)), with a public-interest fee waiver in 1 DCMR § 408 (unverified).
  - MD: fees under GP § 4-206 (verified (repo)). The first two hours of search are free, and there is a waiver for indigence or public interest. (Those details are unverified.)
- **Process and decision shape:**
  - DMN `fee_check`. Inputs: jurisdiction, the estimate amount, labor hours, requester type (media / nonprofit / individual / commercial), any waiver request. Outputs: whether the estimate is lawful, whether a deposit can be required, whether a waiver can be requested and its standard, and whether the response clock stops while the deposit is unpaid.
  - BPMN: request an estimate → receive it → negotiate or narrow the request → pay the deposit or ask for a waiver → appeal a waiver denial.
- **State or local:** State law, with local fee schedules.
- **Feasibility:** High.
- **Main caveat:** What counts as "actual cost" in practice comes from advisory opinions, not from statute. Note which parts of an answer rest on those opinions.

### B3. The deadline passed or they denied my request. What is the appeal path, how fast is it, and can I recover attorney's fees?
- **Who it helps:** The service's escalation work, and the outside lawyer it refers litigation to.
- **Governing law:**
  - VA: a petition for mandamus or an injunction under § 2.2-3713, which must be heard within 7 days, with fees if the petitioner substantially prevails. The FOIA Council also issues free advisory opinions under § 2.2-3700 et seq. (Both unverified.) Missing the response deadline counts as a denial, § 2.2-3704(E). (The section is verified (repo); the subsection is unverified.)
  - DC: an administrative appeal to the Mayor under § 2-537 (verified (repo)), then Superior Court, with fees under § 2-537(c) (subsection unverified).
  - MD: the Public Access Ombudsman (mediation), the State Public Information Act Compliance Board (fee and some other disputes), and circuit court. The fee-shifting rules are not confirmed. (All unverified.)
- **Process and decision shape:**
  - BPMN, an extension of the existing records BPMN: deadline-missed event or denial → choose a route (VA: FOIA Council opinion or court; DC: Mayor's appeal, then court; MD: ombudsman, then board, then court) → each route with its own timer → outcome → fee petition.
  - DMN `escalation_route`. Inputs: jurisdiction, type of failure (no response / denial / fee / redaction), amount in dispute. Outputs: the next forum, its deadline, whether a lawyer is needed, and whether fees can be recovered.
- **State or local:** State.
- **Feasibility:** High. It mostly extends sections already ingested.
- **Main caveat:** Going to court requires a licensed attorney. The service should model this step as "hand off to counsel".

### B4. Who may make a records request, and may a paid service make one for a client?
- **Who it helps:** Anyone deciding how to structure a FOIA business.
- **Governing law:**
  - VA: rights belong to "citizens of the Commonwealth", § 2.2-3704(A) (verified (repo) quote). The Supreme Court upheld that restriction in *McBurney v. Young*, 569 U.S. 221 (2013) (well known; not checked this session). In practice a VA-based requester or a VA client has to be the named requester.
  - DC (§ 2-532) and MD (GP § 4-201 et seq.) let any person request. (DC is verified (repo); the MD wording is unverified.)
  - Unauthorized practice of law: VA Supreme Court Rules, Part 6, § I; DC Court of Appeals Rule 49; MD Business Occupations & Professions § 10-601 et seq. (All unverified.)
- **Process and decision shape:**
  - DMN `requester_eligibility`. Inputs: jurisdiction, the requester's residence or media status, whether a paid agent is filing, and the task (drafting / filing / negotiating / appealing / litigating). Outputs: who must be the named requester, and whether the task is likely the practice of law.
- **State or local:** State.
- **Feasibility:** Medium. Whether a task is the practice of law is a fuzzy line set by case law.
- **Main caveat:** Drafting and filing requests is generally fine for non-lawyers. Giving advice on exemptions, or appealing for someone else, may cross the line. This question should flag that question for review, not answer it.

### B5. What personal information must be redacted before a document is filed in court or published?
- **Who it helps:** The redaction side of the business, small law firms, and people representing themselves.
- **Governing law:**
  - VA: Va. Code § 8.01-420.8 limits SSNs and similar identifiers in court filings. (Unverified.)
  - Federal: Fed. R. Civ. P. 5.2 (well known; not checked this session).
  - DC: Superior Court Civil Rule 5.2. (Unverified.)
  - MD: Maryland Rules Title 20 and Rule 1-322.1 on excluding personal identifier information from filings. (Unverified.)
  - Data that cannot be published regardless: student records (FERPA, 20 U.S.C. § 1232g), health information (HIPAA, 45 CFR Part 164). Both are well known; not checked this session.
- **Process and decision shape:**
  - DMN `redaction_required`. Inputs: jurisdiction, destination (state court / federal court / public posting / production to an agency), data type (SSN, account number, minor's name, date of birth, medical, financial). Outputs: redact fully / partially (for example, last four digits only) / file under seal / no redaction, with the rule cited.
  - BPMN: classify the document → detect sensitive fields → apply redactions → produce a redaction log → second-person QA → file or produce.
- **State or local:** State court rules plus federal statutes.
- **Feasibility:** High for the rules table. Detecting the fields is a separate engineering problem.
- **Main caveat:** Rules differ between state and federal courts and by case type (family, criminal). The destination input matters more than anything else.

---

## C. City and county staff

### C1. We received a records request. What is our response clock, what must the response say, and when can we extend?
- **Who it helps:** Clerks, records officers and department FOIA contacts.
- **Governing law:**
  - VA: § 2.2-3704(B), five working days with a 7-day extension (section verified (repo); deadline details unverified).
  - DC: § 2-532(c), 15 business days plus 10 more (section verified (repo); deadlines unverified).
  - MD: GP § 4-203, 10 working days to notify and 30 days to respond, with extensions by agreement (section verified (repo); deadlines unverified).
- **Process and decision shape:**
  - The custodian's side of the existing records BPMN: request received (timer starts) → classify → search → apply exemptions and redact (a call to B1) → estimate fees (a call to B2) → one of the lawful responses (provide / withhold / redact / not found / extend).
  - DMN `response_type` picks which statutory response applies and lists the elements the response must contain.
- **State or local:** State law, plus local policy on who handles requests.
- **Feasibility:** High. It reuses sections already ingested.
- **Main caveat:** Counting working days depends on local holidays and closures. Make the calendar part of the local overlay.

### C2. Can this board meet or go into closed session, and what notice and minutes are required?
- **Who it helps:** Clerks, board staff and city or county attorneys.
- **Governing law:**
  - VA: meeting notice, § 2.2-3707; permitted reasons for closed meetings, § 2.2-3711; the motion and certification steps, § 2.2-3712; electronic meetings, § 2.2-3708.3. (All unverified.)
  - DC: the Open Meetings Act, D.C. Code § 2-571 et seq., with closed meetings in § 2-575. (Unverified.)
  - MD: the Open Meetings Act, GP § 3-301 et seq., with closed sessions in § 3-305 and an Open Meetings Compliance Board. (Unverified.)
- **Process and decision shape:**
  - DMN `closed_session_allowed`. Inputs: jurisdiction, body type, topic (personnel, legal advice, real estate, procurement, and so on). Outputs: allowed or not, the statutory purpose to cite, and the required motion wording.
  - BPMN: post notice (timer measured back from the meeting date) → open session → motion to close → closed session → reconvene → certification vote → minutes.
- **State or local:** State.
- **Feasibility:** High. The list of permitted purposes is a crisp decision table.
- **Main caveat:** Electronic and hybrid meeting rules changed a lot after 2020 and may change again. Pin the effective date.

### C3. For this purchase, do we need a small-purchase process, quotes, or a formal bid?
- **Who it helps:** Procurement officers and department heads.
- **Governing law:**
  - VA: the Virginia Public Procurement Act, Va. Code § 2.2-4300 et seq. Small-purchase procedures are under § 2.2-4303, with dollar ceilings that change. Localities may adopt their own procurement ordinances. (All unverified.)
  - DC: the Procurement Practices Reform Act, D.C. Code § 2-351.01 et seq. (Unverified.)
  - MD: state agencies follow the State Finance & Procurement Article. Baltimore City purchasing runs through the Board of Estimates under the City Charter. (Unverified.)
- **Process and decision shape:**
  - DMN `procurement_method`. Inputs: jurisdiction, estimated value, whether it is goods, services or construction, emergency or sole source, cooperative contract available. Outputs: the method required, the minimum number of quotes, posting requirements and the approving authority.
  - BPMN: requisition → choose the method → solicit → evaluate → award → protest window (timer).
- **State or local:** Mostly local, inside a state frame.
- **Feasibility:** Medium. The local ordinance and internal policy carry most of the detail, and those are less likely to be in the open-law corpus.
- **Main caveat:** Thresholds change often and are sometimes set by policy rather than ordinance. Confidence should drop when the source is a policy manual.

### C4. A land-use application came in. What review deadlines and public-notice rules bind us, and what happens if we miss them?
- **Who it helps:** Planners and zoning administrators. It is the staff side of a zoning or variance question for the public.
- **Governing law:**
  - VA: published and mailed notice, § 15.2-2204; deadlines for subdivision plat review, § 15.2-2259; some deadlines can result in a plat being deemed approved. The Charlottesville Development Code (2023) sets local steps. (All unverified.)
  - DC: 11 DCMR Subtitles Y and Z (BZA and Zoning Commission procedures), with ANC notice under D.C. Code § 1-309.10. (Unverified.)
  - MD: the Land Use Article. Baltimore City's Zoning Code is City Code Art. 32. (Unverified.)
- **Process and decision shape:**
  - BPMN with a timer for each statutory deadline: application accepted → completeness review → notice (mailing, posting and newspaper, each counted back from the hearing) → staff report → hearing → decision → appeal window.
  - DMN `review_clock`. Inputs: application type and jurisdiction. Outputs: the review deadline, the notice deadlines, and what happens on a miss (deemed approved / right to sue / none).
- **State or local:** Both.
- **Feasibility:** Medium.
- **Main caveat:** Missing a statutory deadline or a notice requirement can void a decision. The tool has to be precise here, so every timer should carry its quoted source.

### C5. Do I have a conflict of interest on this vote or contract, and what must I disclose?
- **Who it helps:** Council members, board and commission members, and staff who influence contracts.
- **Governing law:**
  - VA: the State and Local Government Conflict of Interests Act, Va. Code § 2.2-3100 et seq., with transaction disclosure in § 2.2-3115. (Unverified.)
  - DC: the Code of Conduct and the Board of Ethics and Government Accountability, D.C. Code § 1-1161.01 et seq. (Unverified.)
  - MD: the Public Ethics Law, GP § 5-101 et seq., which requires local ethics ordinances at least as strict. Baltimore City has its own Ethics Code, City Code Art. 8. (Unverified.)
- **Process and decision shape:**
  - DMN `conflict_check`. Inputs: jurisdiction, the official's role, the interest (personal, family, business), dollar size, and whether the matter is a contract, a vote or a gift. Outputs: may participate / must disclose and may participate / must recuse, the disclosure form, and who to ask for an advisory opinion.
  - BPMN: identify the interest → disclose → recuse or participate → record it in the minutes.
- **State or local:** Both. State floor, local ethics codes.
- **Feasibility:** High for the statutory tests.
- **Main caveat:** Outcomes often turn on advisory opinions. The DMN should route borderline cases to the ethics counsel or board instead of deciding them.

---

## Recommendation: build these two next

1. **A4, reentry self-employment.** It sits on top of the business model and the sole-proprietorship branch already being added to the entity-type DMN. Its core formation sections (VA §§ 59.1-69 and 58.1-3703, DC §§ 47-2851.02 and 47-2855.02) are already quote-checked in the repo, so most of the new work is one gate DMN. It is also the most useful honest answer for people coming out of prison: employers screen, but a business license mostly does not.
2. **A1, building permits.** The user named building codes, and this is the best real test of per-city search. Charlottesville (the USBC run locally), DC (12 DCMR under DOB) and Baltimore City (its own adopted codes) handle the same question three different ways. The exemption list is a crisp table that is easy to compare between Claude and Ollama.

Runner-up: **B3 (records appeals)**. It is cheap because it extends the existing records BPMN and sections already ingested, and it is the first piece a FOIA services business would need.

Every citation above that is not marked verified (repo) is unverified and needs checking before ingestion. The repo files checked against are `curated/{va,dc,md}/{records,business}.json`.