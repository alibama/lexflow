# Official forms for lexflow's processes

Which official forms, portals and sample letters people need for lexflow's five processes in Virginia, DC,
Maryland, Texas, California, Florida, New York, Illinois, Washington and North Carolina, which process step each
one serves, whether it is a fillable PDF, and what it costs. The data is in `fixtures/forms/forms.json`.

* Researched 2026-10-10. Every URL was fetched read-only by a client that sent the User-Agent
  `lexflow-research/0.1 (https://github.com/alibama/lexflow)`, read `robots.txt` first, waited at least 1.2 seconds
  between requests to a host and gave up after 15 seconds. Nothing was submitted, filled in or kept: PDFs were
  parsed in memory, and a temporary copy for text extraction was deleted at once.
* Statute text comes from the local open-us-law store (read-only), the same text the curated models quote.
* Organisations and official office channels only. The fixture holds no person-level data, no email addresses and no
  phone numbers; sample letters are linked, not copied.
* Nothing outside `fixtures/forms/forms.json` and this file was changed.

## 1. The short version

82 forms, portals, sample letters and guides; 72 answered HTTP 200 to the checker. They are tied to
74 step references in 29 curated files, and every step id was
checked against the file. 24 notes cover cases where no official form exists and the statute says what a
request must contain.

| State | Public records | Business formation | Sealing / expungement | Licence denial (conviction) | Court debt / fee waiver |
|---|---|---|---|---|---|
| Virginia | 2, 1 fillable; statute | 1 (1 unverified) | 4, 4 fillable | 3, 1 fillable | 1, 1 fillable |
| District of Columbia | 2; statute | 2, 1 fillable | 2 (1 unverified) | no form | 1 (1 unverified); statute |
| Maryland | 3, 2 fillable; statute | 2, 1 fillable | 5, 5 fillable | no form | 3, 3 fillable |
| Texas | 2, 1 fillable; statute | 3, 3 fillable | 2, 1 fillable; statute | 1, 1 fillable | 2 (1 unverified), 1 fillable; statute |
| California | no form | 4, 3 fillable | 5, 5 fillable | no form | 3, 3 fillable |
| Florida | no form | 3, 3 fillable | 1; statute | no form | no form |
| New York | 3; statute | 2, 1 fillable | 1 (1 unverified) | 1, 1 fillable; statute | no form |
| Illinois | 1; statute | 1 (1 unverified) | 1, 1 fillable | 1, 1 fillable; statute | 1, 1 fillable |
| Washington | 1; statute | 1, 1 fillable | 2 | 1; statute | 2 |
| North Carolina | no form | 2, 2 fillable | 1 (1 unverified) | 1 (1 unverified); statute | 2 (2 unverified) |

Cells count the entries in the fixture. "unverified" means the publisher's server refused or ignored the
checker (section 3); "statute" means a `no_form` note explains what the law requires instead; "no form" means no
official form exists and only the statute applies.

What stands out:

* **Public records.** Only Texas has an official statewide request form (the Attorney General's, which
  Gov't Code § 552.235 requires and which is optional to use). Illinois forbids requiring one: "A public body may
  not require that a request be submitted on a standard form" (5 ILCS 140/3(c)). Everywhere else the statute
  sets the content (a written request that reasonably describes the records, or none at all in Florida), and
  the official help is a sample letter (Virginia FOIA Council, Maryland Attorney General, New York Committee on
  Open Government) or a portal (DC, New York state agencies).
* **Business formation.** Every jurisdiction publishes articles of organization. Fees read from the form text:
  Texas $300, New York $200, Washington $180 (paper; online adds a processing fee), North Carolina $125,
  Florida $125 for an LLC and $70 for a profit corporation (Fla. Stat. §§ 607.0201-0202, form CR2E010),
  Maryland $100 (expedited $150), DC $99 (DLCP fee page). California ($70), Virginia ($100) and Illinois ($150)
  come from the statutes the curated models already quote: Virginia's SCC disallows automated clients in
  `robots.txt`, and ilsos.gov did not answer within 15 seconds.
* **Sealing and expungement.** California (CR-180/181, CR-409/410), Virginia (CC-1201, CC-1203, CC-1473),
  Maryland (CC-DC-CR-072A/B/C, 078, 148) and Illinois (the statewide EXP-AD suite) have fillable statewide
  forms. Texas has OCA model petitions for nondisclosure (Gov't Code § 411.0745(c) requires them) but none for
  expunction. New York's courts publish a CPL 160.59 application, as § 160.59(1-a) requires (their site
  blocked the checker). Washington's pattern
  forms are flat PDFs or Word files. DC has a court guide but no fillable motion. Florida starts online at FDLE
  ($75 certificate of eligibility); the court petition forms are set out in Fla. R. Crim. P. 3.989, and no
  official fillable copy was verified.
* **Licence denials.** Only Virginia's DPOR (predetermination request, IFF supplemental form) and Texas
  licensing agencies (criminal history evaluation letters; TDLR's costs $10) publish forms for the licensing
  step itself, and each covers only its own licences.
  California (Bus. & Prof. Code § 485: a written hearing request within 60 days), DC (§ 47-2853.12(n) petition,
  90-day decision), North Carolina (§ 93B-8.1(b6), a petition to each board, fee capped at $45) and Washington
  (RCW 18.400.020 preliminary application, two-month decision) define the request in statute but publish no
  statewide form. New York, Illinois, North Carolina and Washington also have certificate routes with forms
  (DOCCS certificates, Certificate of Good Conduct, Certificate of Relief, CROP).
* **Court debt.** Statewide forms exist in California (TR-320/CR-320), Virginia (DC-211, which carries the
  financial statement § 19.2-354.1 requires), Maryland (DCA-131, CC-088, CC-DC-089), Illinois (FW-CRM),
  Washington (GR 39 petition and order) and North Carolina (AOC-CR-415, AOC-G-106). Texas's OCA form covers only
  community supervision; Florida leaves payment plans to each clerk (Fla. Stat. § 28.246(4)); none was found for
  New York or for DC criminal fines.
* **Fillable.** 48 of the 58 PDFs that could be fetched have AcroForm fields;
  10 are flat. 7 carry permission encryption (they open without a password) and 9
  hold XFA alongside the AcroForm, so a filler must decrypt object streams and should fill the AcroForm layer.

Findings for the curated models, which this task did not change:

* Maryland: petition expungement (Crim. Proc. § 10-105) is missing from the downloaded statutes, so
  `curated_ask/record_sealing/md.json` has no petition step although CC-DC-CR-072A/B exist. The downloaded
  Crim. Proc. § 1-209 predates the 2026 predetermination amendment (HB 557, effective July 1, 2026, per the
  Office of Financial Regulation).
* Texas Code Crim. Proc. art. 42A.655(h) requires OCA's ability-to-pay reconsideration form, but the TX
  court-debt model covers only arts. 42.15 and 43.03-43.05, so the form has no exact step.
* Several forms serve paths the models leave out: the requester's FOIA enforcement petition in Virginia (DC-495,
  § 2.2-3713), California arrest sealing (CR-409, § 851.91), Virginia expungement (CC-1473), and the corporation
  paths in every state (the business models follow the LLC path).
* Florida's LLC form charges $125, the $100 filing fee the model quotes from § 605.0213(2) plus the
  registered-agent designation.
* The corpus marks Va. Code § 19.2-392.2 "effective until December 1, 2026".

## 2. Where this ties in: the Setup checklist

Forms are reference data of the same kind as `curated/places/<state>/<place>.json`, which the Setup page loads in
its optional `local` step. They fit best as one more optional box on that checklist, after `build`, so a fresh
install picks them up with everything else and each model page can list the forms for its steps. The fixture
carries the proposed checklist entry under `setup`, in the shape of the `Step` dataclass in
`lexflow/pipeline/steps.py`. That file is outside this task's write scope, so it is not wired in yet. A sketch:

```python
Step("forms", "Link official forms to process steps",
     "Official forms, portals and sample letters for each state's processes (fixtures/forms/forms.json), each "
     "tied to the curated step it serves, with its publisher, fee and whether it is fillable. Links are "
     "re-checked read-only; nothing is filled in or submitted.",
     "optional", st_forms, run_forms, needs=["build"], params=["states", "force"],
     cost="one polite request per form URL (about 100 URLs, 2 minutes); no downloads kept")
```

* `st_forms` reads the fixture and reports `done` when every form for the loaded states was checked within 90
  days, `partial` when some checks are older or failed, and `todo` otherwise. The detail line could read
  "82 forms for 74 steps in 10 states; 48 fillable PDFs; 10 links to recheck".
* `run_forms` re-runs the link check with the same User-Agent, robots.txt and rate rules, and writes only the
  `verification` blocks. Hosts that answer 403 to automated clients (section 3) stay marked `blocked`, not
  failed, so they do not keep the box unticked.
* The model page can join on `steps[].file` and `steps[].step` to show "Forms for this step" under each step,
  and the ask answers can link a form wherever their `out_of_corpus` list names "court rule" or "agency
  policy" forms (the CA, DC, MD, TX and VA sealing files already do).
* Users of the lab are private people. The step should check links only. If form filling is ever added, it should
  run on the user's machine, keep their answers there, and share nothing unless they opt in.

## 3. Method and limits

1. Candidates came from web searches and from each publisher's own forms index (Judicial Council, vacourts.gov,
   mdcourts.gov, txcourts.gov, sunbiz.org, sosnc.gov, the WA Secretary of State, illinoiscourts.gov and others).
   Commercial form sites were used only as leads and are never cited.
2. Each URL was fetched by the checker (a few were fetched again after a timeout or a parser fix). For PDFs it
   looked for `/AcroForm`, `/XFA` and field dictionaries,
   decrypting permission-only encryption with the standard empty user password where needed (the Judicial Council
   forms use AES-256), and read the form number, revision and fee from the text with `pdftotext`.
3. Fees are recorded only when the form, the publisher's page or a statute states them, with the source named in
   `fee_source`. Local add-ons (county filing fees, Live Scan operator fees) are noted, not totalled.
4. Step matches were made by hand against `curated/<state>/<question>.json` and
   `curated_ask/<question>/<state>.json`; `match` says whether the form *is* the step (`exact`), does part of it
   (`partial`), or supports it (`related`). The licence, sealing and court-debt step models exist only for CA,
   DC, MD, TX and VA, so forms for the other five states have no step yet.

Hosts that could not be checked automatically:

| Host | Result | Effect |
|---|---|---|
| scc.virginia.gov, cis.scc.virginia.gov | `robots.txt` disallows all but named search engines | LLC-1011 not fetched; URL from a search index |
| nccourts.gov | HTTP 403 (CloudFront) | AOC-CR-281, CR-415, G-106, CR-273 unverified |
| nycourts.gov | HTTP 403 (managed bot challenge) | CPL 160.59 application unverified; the challenge was not attempted |
| dccourts.gov | HTTP 403 | Sealing guide and fee-waiver form unverified |
| ilsos.gov | no answer within 15 s, three tries | LLC-5.5 unverified |
| myfloridalegal.com, ncdoj.gov | HTTP 403 | Not used |

Bot challenges were left alone. These links should be checked by a person in a browser before anyone relies
on them.

## 4. Forms by state

Columns: the step ids are in the curated file named after them (`ask/...` is `curated_ask/...`). "Check" is the
HTTP result on 2026-10-10.

### Virginia

| Process | Form | Publisher | Steps | Fillable | Fee | Check |
|---|---|---|---|---|---|---|
| Public records | [Sample request letter (Virginia Freedom of Information Act)](https://foiacouncil.dls.virginia.gov/sample%20letters/request%20letter%202021.doc) | Virginia Freedom of Information Advisory Council | `submit_request` in `curated/va/records` | template (Word) | none stated | 200 |
| Public records | [Petition for Injunction or Mandamus - Freedom of Information Act (and Affidavit for Good Cause)](https://www.vacourts.gov/forms/district/dc495.pdf) (DC-495) | Office of the Executive Secretary, Supreme Court of Virginia | none modelled | yes, 33 fields | none stated | 200 |
| Business formation | [Articles of Organization (Virginia limited liability company): form and instructions](https://scc.virginia.gov/getdoc/83cdc393-e6cf-455c-807f-7be9a54c5876/llc1011-(1).pdf) (LLC-1011) | State Corporation Commission, Clerk's Office | `deliver_articles`, `collect_fee` in `curated/va/business` | unknown | $100 | robots |
| Sealing / expungement | [Petition for Sealing Pursuant to Va. Code § 19.2-392.12](https://www.vacourts.gov/static/forms/circuit/crim_sealing/cc1201.pdf) (CC-1201) | Office of the Executive Secretary, Supreme Court of Virginia | `file_petition` in `curated_ask/record_sealing/va` | yes, 104 fields | No court fees or costs | 200 |
| Sealing / expungement | [Addendum to Petition for Sealing Pursuant to Va. Code § 19.2-392.12](https://www.vacourts.gov/static/forms/circuit/crim_sealing/cc1201a.pdf) (CC-1201(A)) | Office of the Executive Secretary, Supreme Court of Virginia | `file_petition` (partial) in `curated_ask/record_sealing/va` | yes, 97 fields | No court fees or costs | 200 |
| Sealing / expungement | [Petition for Sealing Pursuant to Va. Code § 19.2-392.12:1(A) and/or (B)](https://www.vacourts.gov/static/forms/circuit/crim_sealing/cc1203.pdf) (CC-1203) | Office of the Executive Secretary, Supreme Court of Virginia | `file_petition` (related) in `curated_ask/record_sealing/va` | yes, 192 fields | No cost | 200 |
| Sealing / expungement | [Petition for Expungement Filed in a Circuit Court - Acquittal/Dismissal](https://www.vacourts.gov/forms/circuit/cc1473.pdf) (CC-1473) | Office of the Executive Secretary, Supreme Court of Virginia | none modelled | yes, 40 fields | No court fees | 200 |
| Licence denial (conviction) | [Request for Predetermination of Criminal History](https://www.dpor.virginia.gov/sites/default/files/FormsAndApplications/A406-01PREDET.pdf) (A406-01PREDET) | Department of Professional and Occupational Regulation | `request_predetermination` in `curated_ask/license_conviction/va` | yes, 171 fields (XFA + AcroForm) | none stated | 200 |
| Licence denial (conviction) | [Criminal Conviction Reporting Form](https://www.dpor.virginia.gov/sites/default/files/FormsAndApplications/A406-01CCR_pdf.pdf) (A406-01CCR) | Department of Professional and Occupational Regulation | `apply` (partial) in `curated_ask/license_conviction/va` | no (flat PDF) | none stated | 200 |
| Licence denial (conviction) | [Criminal Conviction - Supplemental Form: Requesting an Informal Fact Finding (IFF) Conference](https://www.dpor.virginia.gov/sites/default/files/FormsAndApplications/A713-01IFF_pdf.pdf) (A713-01IFF) | Department of Professional and Occupational Regulation | `present_case` (partial), `informal_conference` (related) in `curated_ask/license_conviction/va` | no (flat PDF) | none stated | 200 |
| Court debt / fee waiver | [Petition for Payment Agreement for Fines and Costs or Request to Modify Existing Agreement](https://www.vacourts.gov/forms/district/dc211.pdf) (DC-211) | Office of the Executive Secretary, Supreme Court of Virginia | `set_terms`, `establish_agreement` (related) in `curated_ask/court_debt/va` | yes, 100 fields | none stated | 200 |

* **Sample request letter (Virginia Freedom of Information Act)**: Optional template (Word .doc). The statute sets no form: a request must identify the records with reasonable specificity and need not cite the Act; the custodian may ask for the requester's name and legal address.
* **DC-495**: The requester's enforcement petition. curated/va/records.json models only the public body's own petition for more time (petition_court), so no step matches yet.
* **LLC-1011**: The search index describes this file as the SCC's LLC-1011 instructions (fee $100; file online in the Clerk's Information System at cis.scc.virginia.gov, by mail or by hand). Not opened here.
* **CC-1201**: Addendum CC-1201(A) lists further charges from the same incident. The instructions also say the petitioner asks the Central Criminal Records Exchange, through a Virginia State Police online portal, to send the record to the court (step request_record); no paper form for that.
* **CC-1203**: A second sealing petition for the listed misdemeanors; the modelled process follows § 19.2-392.12.
* **CC-1473**: Expungement of acquitted or dismissed charges, a separate path from the modelled sealing petition. The corpus marks § 19.2-392.2 'effective until December 1, 2026'.
* **A406-01PREDET**: DPOR boards only; Department of Health Professions boards are not covered by § 54.1-204.1.
* **A406-01CCR**: Filed with a licence application that reports a conviction.
* **DC-211**: Carries the written financial statement that § 19.2-354.1 says the court uses to set installments ('on a form developed by the Executive Secretary').

### District of Columbia

| Process | Form | Publisher | Steps | Fillable | Fee | Check |
|---|---|---|---|---|---|---|
| Public records | [DC Government Public FOIA Portal](https://myfoia.dc.gov/) | District of Columbia Government | `submit_request` in `curated/dc/records` | online | none stated | 200 |
| Public records | [Freedom of Information Act (FOIA) - Appeals](https://dc.gov/page/freedom-information-act-foia-appeals) | Mayor's Office of Legal Counsel (DC Government) | `petition_mayor` in `curated/dc/records` | n/a (web page) | none stated | 200 |
| Business formation | [Articles of Organization for Domestic Limited Liability Company](https://dlcp.dc.gov/sites/default/files/dc/sites/DLCP/publication/attachments/DLC-1%20Articles%20of%20Organization%20for%20Domestic%20Limited%20Liability%20Company.pdf) (DLC-1, Ver. 8, October 2022) | Department of Licensing and Consumer Protection, Corporations Division | `deliver_filing`, `pay_fee` (partial) in `curated/dc/business` | yes, 9 fields | $99 | 200 |
| Business formation | [DLCP License & Corporate Filing Fees](https://dlcp.dc.gov/page/dlcp-license-corporate-filing-fees) | Department of Licensing and Consumer Protection | `pay_fee` in `curated/dc/business` | n/a (web page) | $99 (domestic for-profit initial registration) | 200 |
| Sealing / expungement | [Police Clearances (Arrest and Criminal History Section)](https://mpdc.dc.gov/service/police-clearances-arrest-and-criminal-history-section) | Metropolitan Police Department | `request_arrest_record`, `charge_fee` in `curated_ask/record_sealing/dc` | n/a (web page) | $7 | 200 |
| Sealing / expungement | [How to file a motion to seal](https://www.dccourts.gov/sites/default/files/pdf-forms/How_to_file_a_motion_to_seal.pdf) | Superior Court of the District of Columbia, Criminal Division | `file_motion`, `serve_prosecutor` (related) in `curated_ask/record_sealing/dc` | unknown | none stated | 403 |
| Court debt / fee waiver | [Application to Proceed Without Prepayment of Costs, Fees, or Security (Civil Division)](https://www.dccourts.gov/sites/default/files/pdf-forms/Civil_IFP_Application.pdf) | Superior Court of the District of Columbia | none modelled | unknown | none stated | 403 |

* **DC Government Public FOIA Portal**: Requests may also go by mail, fax or email to the agency FOIA officer. The Office of the Chief Financial Officer uses its own portal, linked from dc.gov/foia.
* **Freedom of Information Act (FOIA) - Appeals**: How to petition the Mayor to review a denial; no numbered form.
* **DLC-1**: The form itself refers to the fee schedule posted online. Online filing is through BOSS (formerly CorpOnline), linked from the DLCP page.
* **Police Clearances (Arrest and Criminal History Section)**: The arrest-record request used to check sealing eligibility.
* **How to file a motion to seal**: A guide, not a fillable motion. No statewide fillable motion-to-seal form was found; § 16-806 requires a written motion and service on the prosecutor.
* **Application to Proceed Without Prepayment of Costs, Fees, or Security (Civil Division)**: Waives filing costs in civil and family matters; it is not a payment plan for criminal fines, assessments or restitution, for which no form was found (see no_form).

### Maryland

| Process | Form | Publisher | Steps | Fillable | Fee | Check |
|---|---|---|---|---|---|---|
| Public records | [Sample Request Letter (Public Information Act Manual, Appendix A)](https://oag.maryland.gov/resources-info/Documents/pdfs/PIA%20Manual/Appendix_A.pdf) (Appendix A) | Office of the Attorney General of Maryland | `submit_application` in `curated/md/records` | template | none stated | 200 |
| Public records | [Request for Assistance - Maryland Public Information Act Disputes](https://piaombuds.maryland.gov/Documents/Ombuds_Request_Form%20-%20fillable.pdf) | Office of the Public Access Ombudsman | none modelled | yes, 23 fields | none stated | 200 |
| Public records | [Public Information Act Compliance Board Complaint Form](https://oag.maryland.gov/resources-info/Documents/pdfs/PIACB/PIACB_Intake_form.pdf) | State Public Information Act Compliance Board (Office of the Attorney General) | none modelled | yes, 29 fields | none stated | 200 |
| Business formation | [Articles of Organization (Maryland limited liability company)](https://dat.maryland.gov/Documents/Accessible%20Documents/Charter%20-%20Create%20or%20Start%20a%20Business/Articles%20of%20Organization%20for%20a%20Limited%20Liability%20Company_0526-A.pdf) (rev. 05/2026) | State Department of Assessments and Taxation, Charter Division | `deliver_articles`, `collect_fee` in `curated/md/business` | yes, 13 fields | $100 standard; $150 expedited; same-day $425 online or $525 on paper | 200 |
| Business formation | [Maryland Business Express](https://businessexpress.maryland.gov/) | State of Maryland (SDAT) | `deliver_articles` in `curated/md/business` | online | $100 standard | 200 |
| Sealing / expungement | [Petition for Expungement of Records (Acquittal, Dismissal, PBJ, Nolle Prosequi, Stet, NCR, No Finding, Transfer)](https://www.mdcourts.gov/sites/default/files/court-forms/courtforms/joint/ccdccr072A.pdf/ccdccr072A.pdf) (CC-DC-CR-072A, rev. 10/01/2026) | Maryland Judiciary | none modelled | yes, 48 fields | No fee | 200 |
| Sealing / expungement | [Petition for Expungement of Records (Non-Marijuana/Cannabis Related Offenses) - Guilty Disposition](https://www.mdcourts.gov/sites/default/files/court-forms/courtforms/joint/ccdccr072B.pdf/ccdccr072B.pdf) (CC-DC-CR-072B, rev. 10/01/2025-2) | Maryland Judiciary | none modelled | yes, 48 fields | $30 per case, nonrefundable; a fee waiver may be requested | 200 |
| Sealing / expungement | [Petition for Expungement of Records (Less Than 3 Years Has Passed Since Disposition)](https://www.mdcourts.gov/sites/default/files/court-forms/ccdccr072c.pdf) (CC-DC-CR-072C, rev. 01/2025) | Maryland Judiciary | `auto_expunge` (related) in `curated_ask/record_sealing/md` | yes, 52 fields | none stated | 200 |
| Sealing / expungement | [General Waiver and Release](https://www.mdcourts.gov/sites/default/files/court-forms/courtforms/joint/ccdccr078.pdf/ccdccr078.pdf) (CC-DC-CR-078, rev. 01/2025) | Maryland Judiciary | none modelled | yes, 21 fields | none stated | 200 |
| Sealing / expungement | [Petition for Shielding Under MD Second Chance Act](https://www.mdcourts.gov/sites/default/files/court-forms/courtforms/joint/ccdccr148.pdf/ccdccr148.pdf) (CC-DC-CR-148, rev. 07/2026) | Maryland Judiciary | `petition_shield` in `curated_ask/record_sealing/md` | yes, 56 fields | none stated | 200 |
| Court debt / fee waiver | [Request for Traffic Violation(s) Payment Plan (District Court)](https://www.mdcourts.gov/sites/default/files/court-forms/dca131.pdf) (DCA-131, rev. 10/2022) | District Court of Maryland | `apply_clerk_plan`, `approve_plan` (related) in `curated_ask/court_debt/md` | yes, 103 fields | none stated | 200 |
| Court debt / fee waiver | [Request for Traffic Violation(s) Payment Plan (Circuit Court)](https://www.mdcourts.gov/sites/default/files/court-forms/cc088.pdf) (CC-088, rev. 10/2022) | Maryland Circuit Courts | `apply_clerk_plan` in `curated_ask/court_debt/md` | yes, 93 fields | none stated | 200 |
| Court debt / fee waiver | [Request for Waiver of Costs](https://www.mdcourts.gov/sites/default/files/court-forms/courtforms/joint/ccdc089.pdf/ccdc089.pdf) (CC-DC-089, rev. 11/2025) | Maryland Judiciary | none modelled | yes, 100 fields | none stated | 200 |

* **Appendix A**: Template only. The statute requires a written application to the custodian unless the record is on the custodian's list of records available without one, or the custodian waives the requirement.
* **Request for Assistance - Maryland Public Information Act Disputes**: Optional form for mediation of a dispute; mediation is not in curated/md/records.json.
* **Public Information Act Compliance Board Complaint Form**: Use is optional. The Board's page says a complaint must be signed and filed within 30 days after the Ombudsman's final determination.
* **CC-DC-CR-072A**: Petition-based expungement (§ 10-105) is missing from the downloaded statutes, so the MD model (curated_ask/record_sealing/md.json) has no petition step; see its out_of_corpus list.
* **CC-DC-CR-072B**: Same corpus gap as CC-DC-CR-072A.
* **CC-DC-CR-072C**: Asks for expungement before the automatic three-year expungement under § 10-105.1.
* **CC-DC-CR-078**: Filed with CC-DC-CR-072A for some dispositions (release of tort claims to file early).
* **CC-DC-CR-148**: Must be filed with a Notice Regarding Restricted Information (MDJ-008) under Md. Rule 20-201.1.
* **DCA-131**: Eligible when the outstanding fines total at least $150 (form text and § 7-504.1(c)). Covers fines owed to the District Court only.
* **CC-088**: Fines owed to the circuit court where it is filed only.
* **CC-DC-089**: Waiver of prepaid court costs (for example the $30 fee on CC-DC-CR-072B); not a plan for fines.

### Texas

| Process | Form | Publisher | Steps | Fillable | Fee | Check |
|---|---|---|---|---|---|---|
| Public records | [Texas Public Information Act Information Request Form](https://www.texasattorneygeneral.gov/sites/default/files/files/divisions/open-government/Public-Information-Request-Form-10-01-19.pdf) (10-01-19) | Office of the Attorney General of Texas | `submit_request` in `curated/tx/records` | yes, 17 fields | none stated | 200 |
| Public records | [Open Records complaint portal](https://oag.my.site.com/OpenRecords) | Office of the Attorney General of Texas | none modelled | online | none stated | 200 |
| Business formation | [Certificate of Formation - Limited Liability Company](https://www.sos.state.tx.us/corp/forms/205_boc.pdf) (Form 205, revised 09/26) | Texas Secretary of State | `sign_certificate`, `deliver_certificate`, `collect_fee` in `curated/tx/business` | yes, 128 fields | $300 | 200 |
| Business formation | [Certificate of Formation - For-Profit Corporation](https://www.sos.state.tx.us/corp/forms/201_boc.pdf) (Form 201, revised 09/26) | Texas Secretary of State | none modelled | yes, 185 fields | $300 | 200 |
| Business formation | [Assumed Name Certificate](https://www.sos.state.tx.us/corp/forms/503_boc.pdf) (Form 503, revised 09/26) | Texas Secretary of State | `file_assumed_name`, `collect_assumed_name_fee` in `curated/tx/business` | yes, 68 fields | $25 | 200 |
| Sealing / expungement | [Petition for Order of Nondisclosure Under Section 411.0725 (model petition)](https://txcourts.gov/media/1454243/petition-for-nondisclosure-under-section-411-0725-2022.pdf) (2022) | Office of Court Administration of the Texas Judicial System | `file_nondisclosure` in `curated_ask/record_sealing/tx` | yes, 26 fields | The civil-case filing fee (§ 411.0745(b)); amount set by county; a Statement of Inability may be filed | 200 |
| Sealing / expungement | [An Overview of Orders of Nondisclosure](https://txcourts.gov/media/1438062/overview-of-orders-of-nondisclosure.pdf) | Office of Court Administration of the Texas Judicial System | `file_nondisclosure` (related) in `curated_ask/record_sealing/tx` | n/a (guide) | $28 for the section 411.072 letter (no petition needed) | 200 |
| Licence denial (conviction) | [Request for Criminal History Evaluation Letter](https://www.tdlr.texas.gov/misc/evaluation/Criminal%20History%20Evaluation%20Letter.pdf) (ENF001) | Texas Department of Licensing and Regulation | `request_letter` in `curated_ask/license_conviction/tx` | yes, 33 fields | $10 | 200 |
| Court debt / fee waiver | [Ability to Pay Reconsideration Request (standardized form and instructions)](https://www.txcourts.gov/media/1453404/reconsideration-of-ability-to-pay-form.pdf) | Office of Court Administration of the Texas Judicial System | `report_difficulty` (related) in `curated_ask/court_debt/tx` | yes, 60 fields | none stated | 200 |
| Court debt / fee waiver | Statement of Inability to Afford Payment of Court Costs or an Appeal Bond (Misc. Docket No. 22-9090) | Supreme Court of Texas | none modelled | unknown | none stated | no URL |

* **Texas Public Information Act Information Request Form**: The Attorney General must create the form (§ 552.235); a request must be in writing and sent by mail, email, hand delivery or another method the body approves (§ 552.234).
* **Open Records complaint portal**: Where a requester complains of an overcharge (§ 552.269); not a step in curated/tx/records.json.
* **Form 201**: Corporation path; curated/tx/business.json models the LLC path.
* **Petition for Order of Nondisclosure Under Section 411.0725 (model petition)**: One of several OCA model petitions (sections 411.0726 to 411.0736 each have their own petition, order and instructions on the index page). OCA must prescribe them (§ 411.0745(c)-(d)).
* **ENF001**: TDLR programmes only. Each licensing authority adopts its own request process and cost-based fee (§ 53.105).
* **Ability to Pay Reconsideration Request (standardized form and instructions)**: Art. 42A.655(h) requires OCA to adopt this standardized form. It is for people on community supervision and does not cover restitution. The modelled county and district court process (arts. 42.15, 43.035) has no form.
* **Misc. Docket No. 22-9090**: The OCA nondisclosure instructions point petitioners who cannot pay filing fees to this statement.

### California

| Process | Form | Publisher | Steps | Fillable | Fee | Check |
|---|---|---|---|---|---|---|
| Business formation | [Articles of Organization (Form LLC-1)](https://bpd.cdn.sos.ca.gov/llc/forms/llc-1.pdf) (LLC-1) | California Secretary of State | `deliver_articles`, `pay_fee` in `curated/ca/business` | yes, 32 fields | $70 | 200 |
| Business formation | [Statement of Information (Limited Liability Company)](https://bpd.cdn.sos.ca.gov/llc/forms/llc-12.pdf) (LLC-12) | California Secretary of State | `file_soi`, `pay_soi_fee`, `refile_soi` (related) in `curated/ca/business` | yes, 54 fields | $20 | 200 |
| Business formation | [Articles of Incorporation of a General Stock Corporation](https://bpd.cdn.sos.ca.gov/corp/pdf/articles/arts-gs.pdf) (ARTS-GS) | California Secretary of State | none modelled | yes, 92 fields | none stated | 200 |
| Business formation | [bizfile Online](https://bizfileonline.sos.ca.gov/) | California Secretary of State | `deliver_articles`, `file_soi` in `curated/ca/business` | online | none stated | 200 |
| Sealing / expungement | [Petition for Dismissal](https://www.courts.ca.gov/documents/cr180.pdf) (CR-180) | Judicial Council of California | `file_petition`, `serve_prosecutor` (related) in `curated_ask/record_sealing/ca` | yes, 81 fields (XFA + AcroForm) | none stated | 200 |
| Sealing / expungement | [Order for Dismissal](https://www.courts.ca.gov/documents/cr181.pdf) (CR-181) | Judicial Council of California | `dismiss_case`, `decide_petition` (related) in `curated_ask/record_sealing/ca` | yes, 58 fields (XFA + AcroForm) | none stated | 200 |
| Sealing / expungement | [Petition to Seal Arrest and Related Records (Pen. Code, § 851.91)](https://www.courts.ca.gov/documents/cr409.pdf) (CR-409) | Judicial Council of California | none modelled | yes, 39 fields (XFA + AcroForm) | none stated | 200 |
| Sealing / expungement | [Order to Seal Arrest and Related Records (Pen. Code, §§ 851.91, 851.92)](https://www.courts.ca.gov/documents/cr410.pdf) (CR-410) | Judicial Council of California | none modelled | yes, 26 fields (XFA + AcroForm) | none stated | 200 |
| Sealing / expungement | [Request for Live Scan Service (Record Review)](https://oag.ca.gov/system/files/media/BCIA-8016RR.pdf) (BCIA 8016RR, rev. 03/2024) | California Department of Justice | `withhold_record` (related), `submit_rehab_evidence` (related) in `curated_ask/license_conviction/ca`, `curated_ask/record_sealing/ca` | yes, 48 fields (XFA + AcroForm) | $25 DOJ processing fee plus the Live Scan site's own fee; DOJ fee waiver available | 200 |
| Court debt / fee waiver | [Can't Afford to Pay Fine: Traffic and Other Infractions](https://www.courts.ca.gov/documents/tr320.pdf) (TR-320/CR-320) | Judicial Council of California | `request_atp` in `curated_ask/court_debt/ca` | yes, 79 fields (XFA + AcroForm) | none stated | 200 |
| Court debt / fee waiver | [Agreement to Pay and Forfeit Bail in Installments](https://www.courts.ca.gov/documents/tr300.pdf) (TR-300) | Judicial Council of California | `pay_due` (related) in `curated_ask/court_debt/ca` | yes, 37 fields (XFA + AcroForm) | none stated | 200 |
| Court debt / fee waiver | [Request to Waive Court Fees](https://www.courts.ca.gov/documents/fw001.pdf) (FW-001) | Judicial Council of California | none modelled | yes, 132 fields (XFA + AcroForm) | none stated | 200 |

* **ARTS-GS**: Corporation path; the model follows the LLC path.
* **CR-180**: Relief needs 15 days' notice to the prosecuting attorney (§ 1203.4(d)). No fee is stated on the form.
* **CR-181**: Proposed order submitted with CR-180.
* **CR-409**: Arrest sealing is in the CA gold sections but not in the step model, which follows § 1203.4.
* **BCIA 8016RR**: How a person gets their own state record to confirm relief, and the copy a licensing board's denial notice must tell the applicant how to request.
* **FW-001**: Waives civil filing fees; it does not reduce a criminal or infraction fine (use TR-320/CR-320).

### Florida

| Process | Form | Publisher | Steps | Fillable | Fee | Check |
|---|---|---|---|---|---|---|
| Business formation | [Articles of Organization for Florida Limited Liability Company (with instructions)](https://form.sunbiz.org/pdf/cr2e047.pdf) (CR2E047) | Florida Department of State, Division of Corporations | `deliver_articles`, `pay_fee` in `curated/fl/business` | yes, 46 fields | $125 (articles of organization and designation of registered agent) | 200 |
| Business formation | [Articles of Incorporation (Florida profit corporation, with instructions)](https://form.sunbiz.org/pdf/cr2e010.pdf) (CR2E010) | Florida Department of State, Division of Corporations | none modelled | yes, 68 fields | $70 ($35 filing + $35 registered-agent designation) | 200 |
| Business formation | [Application for Registration of Fictitious Name](https://form.sunbiz.org/pdf/cr4e001.pdf) (CR4E001) | Florida Department of State, Division of Corporations | `register_name`, `collect_name_fee` in `curated/fl/business` | yes, 50 fields | $50 nonrefundable processing fee | 200 |
| Sealing / expungement | [Seal and Expunge Application (certificate of eligibility)](https://web.fdle.state.fl.us/intakeweb/formrenderer.xhtml?pageId=se) | Florida Department of Law Enforcement | none modelled | online | $75 nonrefundable processing fee, unless the executive director waives it | 200 |

* **CR2E047**: curated/fl/business.json models the $100 filing fee of § 605.0213(2); the form's $125 adds the registered-agent designation.
* **CR2E010**: The Fla. Stat. §§ 607.0201-0202 path. The FL model lists § 607.0201 among its sections but has no corporation steps.
* **Seal and Expunge Application (certificate of eligibility)**: The certificate must be obtained before petitioning the court. Florida has no record-sealing step model yet (curated_ask covers ca, dc, md, tx, va).

### New York

| Process | Form | Publisher | Steps | Fillable | Fee | Check |
|---|---|---|---|---|---|---|
| Public records | [Freedom of Information Law Sample Letters](https://opengovernment.ny.gov/system/files/documents/2020/09/freedom-information-law-sample-letters.pdf) | New York State Committee on Open Government | `submit_request`, `appeal` (related) in `curated/ny/records` | template | none stated | 200 |
| Public records | [Appeal a Written Denial (Sample Letter)](https://opengovernment.ny.gov/appeal-written-denial-sample-letter) | New York State Committee on Open Government | `appeal` in `curated/ny/records` | template | none stated | 200 |
| Public records | [FOIL NY (request portal for state agencies)](https://www.ny.gov/foil-ny) | State of New York | `submit_request` in `curated/ny/records` | online | none stated | 200 |
| Business formation | [Articles of Organization (Section 203 of the Limited Liability Company Law)](https://dos.ny.gov/system/files/documents/2023/01/1336-f.pdf) (DOS-1336-f, rev. 12/22) | New York Department of State, Division of Corporations | `deliver_articles`, `collect_fee` in `curated/ny/business` | yes, 29 fields | $200 | 200 |
| Business formation | [Certificate of Incorporation for Domestic Business Corporation](https://dos.ny.gov/certificate-incorporation-domestic-business-corporation) (DOS-1239-f) | New York Department of State, Division of Corporations | none modelled | n/a (web page) | $125 | 200 |
| Sealing / expungement | [Application to Seal a Conviction after 10 Years (CPL 160.59)](https://ww2.nycourts.gov/FORMS/cpl_160.59_sealing_application/pdfs/CPL_160.59_Sealing_Application.pdf) | New York State Unified Court System | none modelled | unknown | none stated | 403 |
| Licence denial (conviction) | [Certificate of Relief from Disabilities - Certificate of Good Conduct Application and Instructions](https://doccs.ny.gov/system/files/documents/2026/01/certificate-application-revised-1-8-2026.pdf) (revised 1-8-2026) | New York State Department of Corrections and Community Supervision | none modelled | yes, 251 fields | none stated | 200 |

* **Freedom of Information Law Sample Letters**: Templates for a request (post or email) and follow-ups; the statute requires a written request for a record reasonably described.
* **Appeal a Written Denial (Sample Letter)**: An appeal must be in writing within 30 days of the denial, to the head of the entity or its designee.
* **FOIL NY (request portal for state agencies)**: State agencies; local governments take requests directly.
* **DOS-1336-f**: Publication within 120 days (§ 206) is a separate filing with its own $50 fee (modelled).
* **DOS-1239-f**: Corporation path; the NY model follows the LLC path.
* **Application to Seal a Conviction after 10 Years (CPL 160.59)**: The chief administrator must prescribe a form application (§ 160.59(1-a)); a copy must be served on the district attorney. Automatic sealing under CPL 160.57 needs no form.
* **Certificate of Relief from Disabilities - Certificate of Good Conduct Application and Instructions**: DOCCS issues certificates to people it supervised or committed, and to people with federal or out-of-state convictions (Correction Law § 703); everyone else applies to the sentencing court, which after sentencing acts only 'upon verified application to the court' (§ 702(3)) on its own form.

### Illinois

| Process | Form | Publisher | Steps | Fillable | Fee | Check |
|---|---|---|---|---|---|---|
| Public records | [FOIA - Request for Review by Public Access Counselor (PAC)](https://www.illinoisattorneygeneral.gov/Page-Attachments/FOIAPAC/Request%20for%20Review%20Form%20FOIA.pdf) | Office of the Illinois Attorney General, Public Access Counselor | `request_review` in `curated/il/records` | no (flat PDF) | none stated | 200 |
| Business formation | [Articles of Organization (Limited Liability Company Act)](https://www.ilsos.gov/publications/pdf_publications/llc55.pdf) (LLC-5.5) | Illinois Secretary of State, Department of Business Services | `deliver_articles`, `collect_fee` in `curated/il/business` | unknown | $150 | timeout |
| Sealing / expungement | [Request to Expunge and/or Seal Criminal Records](https://ilcourtsaudio.blob.core.windows.net/antilles-resources/resources/62dae17d-e95a-4185-9242-a8cce2bcffde/EXP-AD%20Request.pdf) (EXP-AD, approved 09/2026) | Illinois Supreme Court Commission on Access to Justice (statewide standardized forms) | none modelled | yes, 151 fields | County filing fee in each county, unless waived | 200 |
| Licence denial (conviction) | [Request for Certificate of Good Conduct](https://osad.illinois.gov/content/dam/soi/en/web/osad/expungement/documents/certs-of-good-conduct-relief-from-disab/certif-good-conduct-request-approved.pdf) | Illinois Supreme Court (statewide standardized form) | none modelled | yes, 157 fields | none stated | 200 |
| Court debt / fee waiver | [Application for Waiver of Criminal Court Assessments](https://ilcourtsaudio.blob.core.windows.net/antilles-resources/resources/da298661-6e2a-4f5e-9a87-84f80072c1a8/FW-CRM%20Application.pdf) (FW-CRM) | Illinois Supreme Court Commission on Access to Justice (statewide standardized forms) | none modelled | yes, 120 fields | none stated | 200 |

* **FOIA - Request for Review by Public Access Counselor (PAC)**: Sample form, not required; a Request for Review must be filed within 60 days of the denial.
* **EXP-AD**: Part of a suite (case list, additional cases, orders, certificate of service) that all Illinois circuit courts must accept. Illinois has no record-sealing step model yet.
* **Request for Certificate of Good Conduct**: Required to be accepted in all Illinois circuit courts. Hosted on the State Appellate Defender's site.
* **FW-CRM**: Filed no later than 30 days after sentencing (§ 124A-20(b)). Cook County has its own variant.

### Washington

| Process | Form | Publisher | Steps | Fillable | Fee | Check |
|---|---|---|---|---|---|---|
| Public records | [Obtaining Records (how to request public records; Model Rules)](https://www.atg.wa.gov/obtaining-records) | Washington State Office of the Attorney General | `submit_request` in `curated/wa/records` | n/a (web page) | none stated | 200 |
| Business formation | [Certificate of Formation - Limited Liability Company (fillable)](https://www.sos.wa.gov/sites/default/files/2025-12/6.2025%20-%20Certificate%20of%20Formation%20-%20LLC%20%28Fillable%20Form%29.pdf) (6.2025) | Washington Secretary of State, Corporations & Charities Division | `execute_certificate`, `deliver_certificate`, `pay_filing_fee` in `curated/wa/business` | yes, 72 fields | $180; +$100 to expedite; $10 if the initial report is filed later | 200 |
| Sealing / expungement | [Petition and Declaration for Order Vacating Conviction (misdemeanor)](https://www.courts.wa.gov/FORMS/documents/CrRLJ%2009.0100%20Petition%20to%20Vacate%20Conviction_(f)(U).pdf) (CrRLJ 09.0100, 11/2024) | Washington Administrative Office of the Courts (pattern form) | none modelled | no (flat PDF) | none stated | 200 |
| Sealing / expungement | [Motion and Declaration for Order Vacating Record of Felony Conviction](https://www.courts.wa.gov/forms/documents/CR08.0900_Mt%20and%20Decl%20for%20Or%20Vacating%20Record%20of%20Felony_2025%2007.docx) (CR 08.0900, 2025 07) | Washington Administrative Office of the Courts (pattern form) | none modelled | no (Word file) | none stated | 200 |
| Licence denial (conviction) | [Instructions for a Certificate of Restoration of Opportunity (petition form CRO 01.0100)](https://www.courts.wa.gov/forms/documents/CROP%20instructions%20English%202020%2001.pdf) (CRO 01.0100) | Washington Administrative Office of the Courts | none modelled | n/a (guide) | A superior court filing fee applies (amount not stated); GR 34 fee waiver available | 200 |
| Court debt / fee waiver | [Petition re: Legal Financial Obligations](https://www.courts.wa.gov/forms/documents/CR%2008.0800%20Petition%20re%20LFO%202022%2001.pdf) (CR 08.0800, GR 39 mandatory, 01/2022) | Washington Administrative Office of the Courts | none modelled | no (flat PDF) | none stated | 200 |
| Court debt / fee waiver | [Order re: Legal Financial Obligations](https://www.courts.wa.gov/forms/documents/CR%2008.0810%20Order%20re%20LFO%202022%2001.pdf) (CR 08.0810, 01/2022) | Washington Administrative Office of the Courts | none modelled | no (flat PDF) | none stated | 200 |

* **Obtaining Records (how to request public records; Model Rules)**: Guidance and the advisory Model Rules (chapter 44-14 WAC); no statewide request form. Each agency publishes its own records-request page.
* **Certificate of Formation - Limited Liability Company (fillable)**: Online filing in CCFS costs $180 plus an online processing fee (SOS online instructions).
* **CrRLJ 09.0100**: Proposed order is CrRLJ 09.0200.
* **CRO 01.0100**: The English petition file was not located on courts.wa.gov (translations are posted).
* **CR 08.0800**: Waive, reduce or convert LFOs, or change a payment plan. Washington has no court-debt step model yet.

### North Carolina

| Process | Form | Publisher | Steps | Fillable | Fee | Check |
|---|---|---|---|---|---|---|
| Business formation | [Limited Liability Company Articles of Organization](https://www.sosnc.gov/webfiles/documents/forms/Business_Registration/limited_liability_companies/articles_of_organization.pdf) (L-01, revised August 2017) | North Carolina Department of the Secretary of State, Business Registration Division | `deliver_articles`, `collect_fee` in `curated/nc/business` | yes, 59 fields | $125 | 200 |
| Business formation | [Articles of Incorporation (business corporation)](https://www.sosnc.gov/webfiles/documents/forms/Business_Registration/business_Corporations/articles_of_incorporation_for_business.pdf) (B-01, revised July 2017) | North Carolina Department of the Secretary of State, Business Registration Division | none modelled | yes, 47 fields | $125 | 200 |
| Sealing / expungement | [Petition and Order of Expunction Under G.S. 15A-145.5 (Nonviolent Felony or Nonviolent Misdemeanor)](https://www.nccourts.gov/assets/documents/forms/cr281_1.pdf) (AOC-CR-281) | North Carolina Administrative Office of the Courts | none modelled | unknown | $175 unless the petitioner is indigent | 403 |
| Licence denial (conviction) | [Certificate of Relief Petition and Order](https://www.nccourts.gov/assets/documents/forms/cr273_0.pdf) (AOC-CR-273) | North Carolina Administrative Office of the Courts | none modelled | unknown | none stated | 403 |
| Court debt / fee waiver | [Request for Relief from Fines, Fees and Other Monetary Obligations, and Order on Request](https://www.nccourts.gov/assets/documents/forms/cr415_2.pdf) (AOC-CR-415) | North Carolina Administrative Office of the Courts | none modelled | unknown | none stated | 403 |
| Court debt / fee waiver | [Petition to Proceed as an Indigent](https://www.nccourts.gov/assets/documents/forms/g106.pdf) (AOC-G-106) | North Carolina Administrative Office of the Courts | none modelled | unknown | none stated | 403 |

* **B-01**: Corporation path; the NC model follows the LLC path.
* **AOC-G-106**: Waives costs of filing claims, appeals and motions (used, for example, for expunction fees).
* **AOC-CR-273**: A board weighs a certificate of relief under § 93B-8.1.

## 5. Where no official form exists

The statute (or rule) says what the request must contain or how to send it.

| State | Process | Law | What the request needs | Steps |
|---|---|---|---|---|
| Virginia | Public records | Va. Code § 2.2-3704(A)-(B) | Records identified with reasonable specificity; No need to cite the Act; Name and legal address, if the custodian asks | `submit_request` |
| District of Columbia | Public records | D.C. Code § 2-532 | A request that reasonably describes the record (as modelled); Format of the copy, if wanted (§ 2-532(a-1)). An online portal exists; no numbered form. | `submit_request` |
| Maryland | Public records | Md. Code, Gen. Prov. § 4-202 | A written application to the custodian; None needed for records on the custodian's list under § 4-201(c)(2), or when the custodian waives it | `submit_application` |
| Texas | Public records | Tex. Gov't Code § 552.234 | A written request; Delivered by U.S. mail, email, hand delivery, or another method the governmental body approves (fax, its website). The OAG form exists but its use is optional. | `submit_request` |
| California | Public records | Cal. Gov. Code § 7922.530(a) | A request that reasonably describes an identifiable record or records. No statewide form; agencies may run their own portals. | `submit_request` |
| Florida | Public records | Fla. Stat. § 119.07(1) | Chapter 119 sets no form or writing requirement for the request; The custodian must acknowledge it promptly; the requester may ask for written reasons for any exemption | `submit_request` |
| New York | Public records | N.Y. Pub. Off. Law § 89(3)(a) | A written request for a record reasonably described | `submit_request` |
| Illinois | Public records | 5 ILCS 140/3(c) | A written request to the public body (personal delivery, mail, fax or other means it accepts); No standard form and no purpose may be required, except to check commercial purpose or a fee waiver | `submit_request` |
| Washington | Public records | RCW 42.56.080 | A request for identifiable records; No purpose required except to apply listed exemptions | `submit_request` |
| North Carolina | Public records | N.C. Gen. Stat. §§ 132-6(b), 132-6.2(b)-(c) | No purpose or motive need be given; Requests for copies of computer databases may be required in writing; A fee dispute may be taken to the State Chief Information Officer for mediation (no form found) | `submit_request`, `write_database_request`, `request_fee_mediation` |
| California | Licence denial (conviction) | Cal. Bus. & Prof. Code §§ 485(b), 480(f)(3) | A written request for hearing within 60 days after service of the notice of denial; The board's denial notice must state the challenge procedure, the right to appeal, and how to request a copy of one's conviction history (Pen. Code §§ 11122-11127). Each board has its own application and criteria; no statewide form. | `request_hearing`, `notify_denial` |
| District of Columbia | Licence denial (conviction) | D.C. Code § 47-2853.12(n) | A petition to the board, at any time (including before education or training); The board decides within 90 days of receipt. No DLCP or DC Health petition form was found. | `file_petition`, `rule_on_petition` |
| Maryland | Licence denial (conviction) | Md. Code, Crim. Proc. § 1-209 (as amended by 2026 Md. Laws ch. 302, HB 557) | A predetermination request to the department (effective July 1, 2026, per the Office of Financial Regulation advisory); the downloaded § 1-209 predates it. No department form found; check each board. | `submit_evidence` |
| Florida | Licence denial (conviction) | Fla. Stat. § 455.213(3)(b) | No pre-application request process found; a conviction more than 5 years before the application may not be grounds for denial of the licences listed in § 455.213(3)(a) | none modelled |
| Washington | Licence denial (conviction) | RCW 18.400.020 | A preliminary application to the licensing authority, at any time, including before education or paying a fee; Only Department of Licensing licences and boards it supports; Written determination within two months. No statewide preliminary-application form found. | none modelled |
| North Carolina | Licence denial (conviction) | N.C. Gen. Stat. § 93B-8.1(b6) | A petition to the board for a predetermination, at any time; A criminal history record report with the petition; Board decides within 45 days; fee capped at $45. Each board publishes its own petition. | none modelled |
| New York | Licence denial (conviction) | N.Y. Correction Law § 702(3) | After sentencing, a court certificate of relief from disabilities is issued only on a verified application to the sentencing court. The court's application form is on nycourts.gov, which blocked the checker. | none modelled |
| Illinois | Licence denial (conviction) | 20 ILCS 2105 | No IDFPR pre-application form found | none modelled |
| Texas | Sealing / expungement | Tex. Code Crim. Proc. art. 55A.253 | A verified ex parte petition with the person's full name, sex, race, date of birth, driver's licence and social security numbers and address at arrest (or why any is missing); The offense charged, offense and arrest dates, county (and city) of arrest, arresting agency, case number and court; A list, with physical and email addresses, of every agency and private entity believed to hold the records, each state or local agency listed once. No OCA model expunction form was found; each district clerk posts the agency list (art. 55A.253(c)). | `file_expunction` |
| Florida | Sealing / expungement | Fla. R. Crim. P. 3.692, 3.989 | Petition, sworn statement and certificate of eligibility, served on the prosecuting attorney and arresting authority (forms are printed in Rule 3.989). No statewide fillable PDF from an official host was verified. | none modelled |
| Florida | Court debt / fee waiver | Fla. Stat. §§ 28.246(4), 27.52(1) | Payment plans are developed by each clerk (no statewide form); Application for Criminal Indigent Status: form developed by the Florida Clerks of Court Operations Corporation; $50 application fee | none modelled |
| New York | Court debt / fee waiver | N.Y. Crim. Proc. Law § 420.10(5) | An application to the sentencing court for resentence, at any time, if unable to pay. No statewide form found. | none modelled |
| District of Columbia | Court debt / fee waiver | D.C. Code § 16-711 | No payment-plan or fine-relief form found; requests go by motion in the criminal case | `request_plan_hearing` |
| Texas | Court debt / fee waiver | Tex. Code Crim. Proc. art. 43.035 | The defendant tells the court of difficulty paying; no form for the county and district court process | `report_difficulty` |

Statutory wording quoted in the fixture (`no_form[].quote`) is copied from the open-us-law text of the section.

## 6. Gaps and next steps

* Virginia State Corporation Commission: robots.txt disallows automated clients, so LLC-1011 and the assumed-name certificate were not fetched.
* nccourts.gov, nycourts.gov and dccourts.gov answered HTTP 403 (bot protection) to the research client; their forms are listed from the publishers' own URLs as indexed by a search engine, unverified.
* ilsos.gov did not answer within the 15-second timeout (three tries), so LLC-5.5 is unverified.
* myfloridalegal.com (Florida Attorney General) and ncdoj.gov answered HTTP 403.
* Not found: a DC fillable motion to seal; a DC criminal-fine payment-plan form; DC, Florida, Illinois, North Carolina (statewide) and Washington pre-application licensing forms; a Texas OCA expunction form; a txcourts.gov copy of the Statement of Inability; the English CRO 01.0100 file; a North Carolina fee-mediation form.

Suggested follow-ups, none of them done here:

* Wire the `forms` step into the Setup checklist (section 2) and show forms on model pages.
* Re-check the blocked hosts by hand and record the result in the fixture.
* Add the missing Maryland expungement sections (Crim. Proc. §§ 10-101, 10-105, 10-106, 10-110) so the model
  can carry the petition step the CC-DC-CR-072 forms serve.
* Model the requester-side enforcement steps (Va. Code § 2.2-3713) and the corporation paths, which already have
  forms.
* When licence, sealing and court-debt models are built for FL, NY, IL, WA and NC, attach the forms listed here.

## 7. Fixture format

`fixtures/forms/forms.json` (`schema: lexflow-forms/1`):

* `forms[]`: `id`, `state`, `process`, `title`, `form_number`, `publisher`, `kind` (pdf_form, word_form,
  online_portal, sample_letter, instructions, web_page), `url`, optional `index_url`, `steps[]` (`file`, `step`,
  `match`, and the step's `step_action` copied from the curated file), `statutes[]`, `fillable`, `file` (format,
  AcroForm, field count, XFA, pages, PDF title), `fee` and `fee_source`, `verification` (status, HTTP status,
  final URL after redirects, date) and `notes`.
* `no_form[]`: `state`, `process`, `steps[]`, `statute`, `must_contain[]`, optional `quote`, `see[]` (form ids),
  `note`.
* `setup`: the proposed checklist step (section 2). `checker`: how links were checked. `coverage`: counts per
  state and process. `gaps[]`: what could not be found or verified.
