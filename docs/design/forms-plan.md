# Forms on process steps: plan and prototype

_10 October 2026. Scope: how the official forms researched in `docs/design/forms-research.md`
(`fixtures/forms/forms.json`) attach to the steps of lexflow's process models; how they show on the dashboard and
on Lexipedia; how the official forms are re-checked for new versions; and the rules for the drafts lexflow makes
from the statute when a step has no official form._

_Revised the same day after the adversarial check in `docs/design/verify-forms.md`, and again after each of its
two re-checks. §10 lists each finding of the check and what changed; §11 and §12 do the same for the re-checks._

_Method. Code facts come from reading this repository on this date. Statute text came from lexflow's local
open-us-law copy (v2026.09.1). For Virginia that is the copy in `fixtures/statutes/va_sections.json`. For
California it is the search index, read with `lexflow.municipal.statutes.section_texts`, because
`fixtures/statutes/ca_sections.json` does not hold Bus. & Prof. Code §§ 476, 480-482 and 485-487. The practice-act
sections the California scope names (§§ 1687, 1958.1, 2660.5, 4202.6, 4989.10, 4989.24, 5100.2, 26001, 26057 and
26059) were read in the same store. The California text has not been compared with leginfo.legislature.ca.gov,
which answers automated clients with a bot challenge. No web page was fetched for this plan or its revisions, and
nothing was written to any wiki, Wikibase or other service._

_Privacy and credit. This document names organisations, official offices and statutes only. Forms are linked at
their publishers' URLs and not copied. Nobody is named as a partner, advisor or endorser of lexflow. This is
information, not legal advice._

## Summary

- **The prototype works and is tested.** `lexflow/forms/registry.py` loads the fixture and answers "which forms
  serve step X of state Y's process Z" for curated files, model rows and compiled models.
  `lexflow/forms/draft.py` builds an HTML form and a printable letter from a statute. Every element cites its
  section and quotes the words it rests on. The build refuses any draft whose quotes are not in the text or not
  under the cited subsection, or that breaks another rule in §6. Two worked examples are in `out/forms/`.
  `tests/test_forms.py` has 108 tests. In the app container 104 pass and 4 skip by default, because those 4
  tests read `out/forms/` (2 rebuild the worked examples, 2 compare their snapshot texts with the store text by
  text) and the container does not mount `out/`. With `LEXFLOW_FORMS_OUT` pointing at a copy of `out/forms/` in
  the container, all 108 pass. The check that the statute texts are the ones
  the worked examples were built from (by SHA-256) runs by default wherever the texts load: Virginia's from the
  fixture, California's from the local store, which the app container has (§9).
- **No form step compiles to a `userTask` today.** Of the fixture's 74 form-to-step references, 58 are steps
  taken by someone outside the public body: 57 by a private party, 1 by a court. The compiler turns those into
  message catch events in the public body's pool, and the person's own pool stays a black box
  (`lexflow/extract/compile.py:103`). The other 16 are public-body steps: 8 `receiveTask` (collecting a fee), 5
  `task`, 2 `sendTask` and 1 `businessRuleTask`. So the proposed `forms` field goes on any step node and on the
  message flow that carries the filing, not only on user tasks. User tasks appear when the process lab opens the
  person's own pool (§2.4).
- **Following the user's instruction, forms are referenced from the Setup page, where they tie in.** The
  fixture already describes a `forms` checklist step. `Registry.setup_entry()` and `Registry.setup_status()`
  serve it, so wiring it in takes one `Step(...)` line in `lexflow/pipeline/steps.py` (§3.1). Model pages,
  answers and the wiki then show "Forms for this step" and link back to that Setup step. There is no separate
  top-level page.
- **Sections 480 and 482 of the California Business and Professions Code do not, by themselves, support a
  request.** They set the rules a board follows before it denies a licence for a conviction. The request the law
  provides is the **written request for a hearing under § 485(b)**, due within 60 days after the notice of denial
  is served. In it, the applicant can rely on § 480(b)-(d) and § 482(b) and send rehabilitation evidence under §
  481(c). The California example is that request. Its page also lists the official record-clearing forms:
  CR-180 and CR-181 for the § 1203.4 dismissal that § 480(c) names, and CR-409 and CR-410. It also lists BCIA
  8016RR, the Department of Justice's request for a copy of one's own criminal record. The page shows BCIA 8016RR
  as a related form, not an evidence form. The draft does not apply to State Bar, alcoholic-beverage or gambling
  licences, which § 476(a) puts outside the division, and the page says so.
- **Drafts follow strict rules (§6).** A draft is made only for a step with no official paper form. Each page
  shows the banner *"Draft made by lexflow from the statute; not an official form and not legal advice; use the
  official form if the agency has one"*. Printed, each part of the letter page starts a new sheet with the banner
  on top. Both the form page and the printable letter list the official alternatives before anything else. Every
  field belongs to an element that cites and quotes the statute. No field is filled in or ticked in advance. A few
  optional fields only address and date the letter: the custodian's or board's address, the application number
  and the date of the notice. The statute does not ask for them, and the form marks them optional. The Virginia
  draft has no phone number, purpose or signature field, because § 2.2-3704 asks for none. The form runs offline
  and sends and stores nothing. Code checks the rules, but the checks work on words, so both specs still need a
  lawyer's review.

## 1. What this change adds

| File | What it is |
|---|---|
| `lexflow/forms/__init__.py` | Package marker |
| `lexflow/forms/registry.py` | `Registry`: `forms_for_step(state, question, step)`, `no_form_for_step`, `has_official_form`, `forms_for_state`, `unlinked_forms`, `forms_for_model(model)`, `check_steps()`, `setup_entry()`, `setup_status(states, today)`; `registry()` loads the fixture once |
| `lexflow/forms/draft.py` | `Spec`/`Element`/`Field`/`FormLink`, the two specs, `check()` (with `locate()` and `bearer()`), `build()`, `render_form()`, `render_letter()`, CLI `python -m lexflow.forms.draft [--sources FILE] [--out DIR]` |
| `out/forms/va-foia-request.{form.html,letter.html,json}` | Virginia records request, Va. Code § 2.2-3704 |
| `out/forms/ca-bpc-485-hearing-request.{form.html,letter.html,json}` | California hearing request after a licence denial, Bus. & Prof. Code §§ 476, 480, 481, 482, 485, 486, 487 |
| `out/forms/index.html` | Links to both |
| `tests/test_forms.py` | 108 tests. The 4 tests that read `out/forms/` skip where it is absent, as in the app container. Set `LEXFLOW_FORMS_OUT` to a copy to run them there. Tests that need California's text read it from `out/forms/` or the local store and skip where neither is present; the California provenance, hash and practice-act tests need the store |

The state and question of a form-to-step link come from the step's curated file:
`curated/<state>/<question>.json` or `curated_ask/<question>/<state>.json`. They do not come from the form's
`process`. For example, the Department of Justice's BCIA 8016RR (a request for a copy of one's own criminal
record) is filed under record sealing. It is also linked, as `related` only, to `submit_rehab_evidence` in
`curated_ask/license_conviction/ca.json`. `check_steps()` confirms that every step id
in the fixture exists and that its `step_action` still matches the curated file. All 94 references pass: 74 to
forms and 20 in `no_form` notes.

## 2. Forms in the IR

### 2.1 Where the form steps sit today

`compile_facts` maps steps to BPMN by actor and kind (`TASK_FOR_KIND`, `lexflow/extract/compile.py:25`). Applied
to the fixture's references:

| Step actor | Becomes | Form references | `no_form` references |
|---|---|---|---|
| Private party (requester, applicant, petitioner) | message catch event in the public body's pool, from a black-box pool | 57 | 18 |
| Court (an outside pool) | message catch event | 1 | 0 |
| Public body: fee collection | `receiveTask` | 8 | 0 |
| Public body / official: other acts | `task` | 5 | 0 |
| Public body: notice to the person | `sendTask` | 2 | 2 |
| Public body: decision with a table | `businessRuleTask` | 1 | 0 |

The step id survives as the node id in every case: the catch event is `Node(id=s.id, ...)`. A lookup by
`(state, question, node id)` therefore works on compiled models, and `forms_for_model` accepts a
`LegalProcessModel`; `test_forms_for_a_compiled_model` compiles `curated/va/records.json` to check this.

### 2.2 Proposed `forms` field

A form is a reference with its own provenance, not free text. The proposal is for `lexflow/ir.py`, which this
change does not edit:

```python
class FormRef(BaseModel):
    """An official form, portal or sample letter for a step, or lexflow's draft where there is none."""
    id: str                                   # fixtures/forms/forms.json id, or "draft:<spec id>"
    kind: Literal["official", "draft"]
    match: Literal["exact", "partial", "related"] = "exact"
    title: str
    url: Optional[str] = None                 # publisher's URL; for a draft, the local page
    publisher: Optional[str] = None
    form_number: Optional[str] = None
    revision: Optional[str] = None
    fillable: Optional[str] = None            # "acroform", "flat", "online", None
    fee: Optional[str] = None
    checked: Optional[str] = None             # date of the last read-only link check
    status: Optional[str] = None              # verification.status: ok, blocked, not_fetched, changed, http_404 ...
    sources: list[Source] = Field(default_factory=list)   # the law that requires or authorises the form

class Node(BaseModel):
    ...
    forms: list[FormRef] = Field(default_factory=list)    # any activity, or a message catch event

class MessageFlow(BaseModel):
    ...
    forms: list[FormRef] = Field(default_factory=list)    # the filing the message carries
```

* `sources` holds the statute that makes the form official where there is one. Examples: Tex. Gov't Code §
  552.235, which requires the Attorney General's request form; Va. Code § 19.2-354.1, whose financial statement
  is "on a form developed by the Executive Secretary"; and Tex. Gov't Code § 411.0745(c)-(d) for the OCA
  nondisclosure petitions. A form without one is a convenience, which the page says.
* A draft's `FormRef` carries `kind="draft"`. Its `sources` are the elements' quotes, so the existing quote
  checker (`metrics.quotes_checked`) covers drafts too.
* `review.gaps` gets a line for each step with no form and no draft. This matches how the models already record
  what the text leaves open.

### 2.3 In BPMN XML

BPMN 2.0 has no form element. In `schemas/bpmn/Semantic.xsd`, `tUserTask` allows `rendering` children of type
`tRendering` (a bare `tBaseElement`), and `tMessage` has an `itemRef` to an `itemDefinition`. The proposal is to
keep lexflow's data in its own namespace, as `<lex:grounding>` and `<lex:deadline>` already do
(`lexflow/bpmn_xml.py`):

```xml
<bpmn:intermediateCatchEvent id="submit_request" name="Request records with reasonable specificity">
  <bpmn:extensionElements>
    <lex:grounding>...</lex:grounding>
    <lex:forms>
      <lex:form ref="va-foia-request-letter" kind="official" match="exact" checked="2026-10-10" status="ok"
                href="https://foiacouncil.dls.virginia.gov/sample%20letters/request%20letter%202021.doc"
                publisher="Virginia Freedom of Information Advisory Council"/>
      <lex:form ref="draft:va-foia-request" kind="draft"/>
    </lex:forms>
  </bpmn:extensionElements>
  ...
</bpmn:intermediateCatchEvent>
```

* The same `<lex:forms>` block goes on the message flow and on any activity. Schema validation is unaffected,
  because `extensionElements` accepts any foreign element.
* The message can also carry the form's identity through `bpmn:message itemRef` pointing to a
  `bpmn:itemDefinition` whose `structureRef` names the form id. That is the standard way to say what a message
  contains, and bpmn-js keeps it on import and export.
* When the lab gives the person's pool a process (§2.4), the step becomes a `userTask`. A `bpmn:rendering` child
  can then point at the draft page. For an engine run, the form's JSON Schema can be referenced through the
  engine's own extension: SpiffWorkflow's spiff-arena uses user-task properties for a JSON Schema form. Check
  the property names against spiff-arena before relying on them.

### 2.4 Who fills in the form

A form belongs to the step's actor, which is usually the person. The person's side of the process is where the
lab (`docs/design/lab-research.md`) adds a case. The proposal is that, when a case opens, the lab expands the
black-box pool into a small process. Each outside step becomes a `userTask` in that pool, linked by the existing
message flow to the public body's catch event. The `forms` of the catch event are copied to the user task. Steps
inside the public body that take a form from the person (the 8 fee `receiveTask`s, for example) show the form
from the person's side as "what you hand over", and the public body's node keeps the reference.

### 2.5 Changes elsewhere (not made here)

| Where | Change |
|---|---|
| `lexflow/extract/compile.py` | After building nodes, attach `registry().forms_for_step(state, question, node.id)` to each step node and its incoming message flow; a draft spec adds a `kind="draft"` ref |
| `lexflow/bpmn_xml.py` | Write `<lex:forms>` in `extensionElements`; optional `itemDefinition` for messages |
| `lexflow/municipal/stats.py:193` `steps_of` | Return the step `id` and its `forms`, `no_form` and `draft`, so the dashboard, the wiki and the browser plugin share one list |
| `lexflow/validate.py` | Count `FormRef` quotes like other sources; warn when an `exact` form's link status is not ok or blocked |

## 3. On the dashboard

### 3.1 Setup: the one place forms are wired in

The fixture's `setup` block is the checklist entry, and the registry serves it:

```python
# lexflow/pipeline/steps.py (proposed)
from ..forms import registry as FR

def st_forms(con):
    return FR.registry().setup_status(states=_gov_states(con) or None)

Step(**FR.registry().setup_entry(), status=st_forms, run=run_forms,
     credits=[], credits_note="No outside dataset: each form is linked at its publisher's own URL and not "
                              "copied; statute text is credited on the statutes step.")
```

* `setup_status` applies the fixture's `status_rule`. The result is `done` when every form with a URL for the
  chosen states was checked within 90 days with status ok, blocked or not_fetched (robots.txt). It is `partial`
  when some checks are older or failed, `todo` when nothing was ever checked, and `optional` when no forms were
  researched for those states.
* The row shows `detail_template`. Today it reads "82 forms for 64 steps in 10 states; 48 fillable PDFs; 1 link to
  recheck; 1 with no official URL". The status is `partial` because ilsos.gov timed out. The Texas Statement of
  Inability has no official URL.
* If `run_forms` uses `pdftotext` for the revision check (§5), the PDF text tool is credited in the
  `credits.py` format, with its licence checked against the maker's page first, as that module requires.

### 3.2 Model pages

* **Under each step** in "Steps and the words they come from" (`dashboard/app.js:631`): a line "Official
  form" with the title, form number, publisher, a fillable badge, the fee and "link checked on …", exact matches
  first and partial or related ones marked. For a step with none: the `no_form` statute line and, where a spec
  exists, "Draft from the statute" opening the local draft page.
* **"Other forms for this process"**: `unlinked_forms(state, question)`. Examples are Virginia's DC-495 (the
  requester's enforcement petition) and Maryland's ombudsman and Compliance Board forms, which serve paths not yet
  modelled.
* A muted footer, "Forms: Setup → Link official forms to process steps", links to the Setup row. There is no forms
  page of its own.
* API: `GET /api/models/{mid}` adds `forms` to each step through `steps_of`. `GET /api/forms?state=&question=`
  returns the registry rows. `GET /api/forms/drafts/{id}` returns the draft JSON. The draft pages can be rendered
  on request from `draft.build`, so no generated HTML has to be shipped.

### 3.3 Answers

Ask answers whose `out_of_corpus` lists a court rule or agency form (the CA, DC, MD, TX and VA sealing files do)
get the forms of the matching model's steps. An answer's own steps are not curated steps, so these are linked "for
the related process", never as the step's form.

## 4. On the wiki

Publishing stays in the existing "Publish to Lexipedia" step. This change publishes nothing.

* **Process pages** (`lexflow/publish/lexipedia.py:145`): after the steps list, a section "===== Forms for each
  step =====" with one DokuWiki table row per step: the step, its official form (an external link with the form
  number), the publisher, fillable or not, the fee, and the date of the last check. Only official URLs are
  linked.
* **Steps with a draft**: a static rendering of the draft. It shows the banner first, the official alternatives,
  then each element with its level, citation and quote. It has no input fields, because a wiki page cannot keep a
  private person's answers. The fillable version comes with the lab's thin `lexflowlab` plugin
  (`docs/design/lab-research.md` §1.6). That plugin runs in the reader's browser and posts nothing.
* **Place pages** keep local portals and offices in `curated/places`. Where a place runs its own request portal,
  it is listed above the statewide draft, following the banner's rule.

## 5. Re-checking official forms for new versions

The Setup step's `run_forms` is the checker described in the fixture (`checker`). It uses the User-Agent
`lexflow-research/0.1 (https://github.com/alibama/lexflow)`, reads robots.txt once per host, makes at most 1
request per second per host (1.2 s spacing) and times out at 15 s. It keeps no downloads.

1. **Conditional fetch.** Send `If-None-Match` and `If-Modified-Since` when the last check recorded an ETag or
   Last-Modified. A 304 refreshes `checked` and nothing else.
2. **Fingerprint.** On a 200, hash the bytes in memory (SHA-256). For a PDF, read AcroForm and XFA presence, the
   field count, the page count and the PDF title, and read the printed form number and revision from the text.
   A proposed `verification.fingerprint` block holds `sha256`, `bytes`, `etag`, `last_modified`, `fields`,
   `pages` and `revision`. The fixture has none yet, so the first run only records them.
3. **Classify.**
   * *unchanged*: same hash. Update `checked`.
   * *new version*: the revision string or field count changed. Set status `changed`, keep the previous
     fingerprint under `previous`, and list the steps it serves.
   * *edited*: the hash changed but the revision is the same. Record it, flag nothing.
   * *moved*: a new `final_url`. Record it in `verification.final_url`, and keep `url` as the publisher's entry
     point. The four Judicial Council forms already redirect (301, 301) to
     `courts.ca.gov/sites/default/files/courts/default/2024-11/`. The fixture records that, and `summary()` passes
     `final_url` on to pages.
   * *gone*: 404 or 410 becomes `http_404`. The step shows "link broken; see the publisher's forms index"
     (`index_url`).
   * *blocked* or *robots*: stays `blocked` or `not_fetched`. No retries and no bypass. A person checks it in a
     browser.
4. **Index pages.** Where an entry has an `index_url` (vacourts.gov, txcourts.gov, mdcourts.gov and others), the
   checker lists the form links on that page and reports any number it does not know as "possible new form".
   It does not add the form. A person matches it to a step, as `match` requires.
5. **Effects downstream.**
   * A `changed` exact form puts "new version since <date>" on its steps, and the Setup row goes `partial` until
     someone confirms the step match.
   * When an exact paper form appears for a step that has a draft, `draft.check` refuses that draft
     (`has_official_form`). The page then shows the form only.
   * A new statute release re-runs `build()` on every spec. A quote that no longer appears blocks the draft until
     the spec is updated.
6. **Cadence.** The 90-day window in `status_rule`. The fixture records the revisions courts print on their
   forms, for example "Rev. January 1, 2024" on CR-180, CR-181 and CR-409, and "07/26" on CC-1201. For three
   entries the re-check could not find the recorded revision in the file's text: CC-DC-CR-072A, Texas Form 205
   and the New York DOCCS certificate application. Each has a `revision_note` saying so, and pages mark the
   revision as not confirmed on the form itself.

## 6. Rules for generated drafts

`check()` in `lexflow/forms/draft.py` enforces rules 1 to 7, and the page renderers implement rules 8 to 11.
`tests/test_forms.py` tests each of rules 1 to 11, including every invented-content case in
`docs/design/verify-forms.md` and its two re-checks, and all of these tests run by default in the app container.
Rule 10 is tested on the referrer policy and on every outbound link; rule 11 on each source's text, URL, origin and
SHA-256, the date made and the review status. A test also checks that this section quotes the review status the
code writes, names every word after which rule 3 lets a party head a subject, and lists the words rule 4 allows in
an exempt field's label. Rules 12 and 13 are about how a spec is written; review checks them, not code.

1. **Only where there is no official form.** A step with an `exact` PDF or Word form gets no draft. Portals,
   sample letters and guides do not block a draft, because the step can still be done by letter. They are listed
   first under "Official form first".
2. **Every element cites and quotes.** Each element names its section and subsection and quotes the words it
   rests on. The quote must appear in the stored section text, with only whitespace and curly quotation marks
   normalised. It must fall under the cited subsection to the depth cited: "f.3.D" means (f)(3)(D). Subsection
   letters count only in sequence, so a nested "(i)" is not taken for subsection (i).
   * In a section lettered (a), (b) ..., an unlettered paragraph before the first subdivision or after the last is
     the section's own text, not part of a subdivision. So § 485's "Service by mail is complete on the date of
     mailing." is cited to § 485, not § 485(b). An unlettered paragraph between two subdivisions could be either
     the section's text or the end of the subdivision above, so no citation is accepted for it. None of the eight
     sections the drafts quote has such a paragraph.
   * In a section lettered A., B. ..., such a paragraph continues the subsection above it, as the second
     paragraph of Va. Code § 2.2-3704(G) does.
   * An element with no subsection must quote the section's unlettered text.
3. **Levels say how strong each element is, and code checks the quote against the level.** The levels are
   `required` (the statute requires it of the person), `if_asked` (the other side may require it), `right` (the
   person's choice), `context` (who, what, when), `duty` (what the other side must do) and `notice` (what happens
   next). Each spec lists the statute's words for each side, such as "requester" and "request", or "applicant" and
   "request" (the person's request stands for the person). A spec that lists none is refused.

   The *bearer* of "shall", "must" or "may require" is the last party before it, in its clause, that heads a
   subject. A party heads a subject when it is not possessive ("the applicant's decision") and nothing but words
   such as "a", "the" or "written" stands between it and the start of the clause, a comma, semicolon or colon, a
   paragraph mark, or "and", "or", "but" or "then". So a party after a preposition ("to a request", "by the
   applicant"), after a verb ("may request") or inside a subordinate clause ("unless the applicant shall request")
   is passed over. There is no bearer at all in three cases:
   * The party right before the mandatory word is passed over. In "A request for public records that the public
     body shall answer ... is valid", the "shall" is the public body's, in a relative clause, so it does not fall
     to "request".
   * The party found has a verb of its own right after it, and the mandatory word is not a second verb of it
     after "and", "or", "nor" or "but". In § 480(f)(2), "a board may request mitigating information ..., provided
     that ... the applicant's decision not to disclose any information shall not be a factor ...", the "shall
     not" is not the board's, because its subject is "decision". In Va. Code § 2.2-3704(F), "a public body may
     make reasonable charges ... and shall make all reasonable efforts ...", the "shall" is the public body's.
   * The party found is joined to a party of the other side. "The public body or the requester shall decide"
     binds both sides, so it is neither side's duty alone.

   The levels then use the bearer as follows.
   * A `required` element must quote "shall", "must", "unless" or "only if".
     * For "shall" or "must", the bearer is the person, inside the quote. "Shall not", "shall have" and "shall
       constitute" do not count. Nor do benefits: "shall receive", "shall obtain", "shall get" and the like. A
       passive "shall be ..." counts only for the person's own acts ("shall be made", "filed", "signed", "in
       writing" ...), and not when the other side is named after "by".
     * For "unless" or "only if", the person is the condition's subject. The consequence must name the person,
       not the other side, and must be a loss ("waived", "withdrawn", "denied" ...) that is not negated.
       § 485(b), "Unless written request for hearing is made within the 60-day period, the applicant's right to a
       hearing is deemed waived", passes. § 487's "the board shall conduct such hearing ... unless the applicant
       shall request ..." does not. Nor does "Unless the requester agrees, the request shall not be denied",
       whose consequence is no loss.
   * An `if_asked` element must quote "may require", with the other side as bearer and the person as the first
     party after it. "May request" does not count, because a request is not a requirement.
   * A `duty` element must quote "shall" or "must", with the other side as bearer. "Shall have", "shall
     constitute" and "shall be deemed" (or "tolled", "granted" and the like) do not count: they are grants or
     legal consequences. Exemptions do not count either: "shall not be required", "shall not be obliged", "shall
     be exempt" and the like. Otherwise "shall not" counts, as a duty not to act. § 481(b) is a `notice`, not a
     `duty`, for another reason: its subject is "Criteria", which is not a party, so its "shall include" has no
     bearer.
   * A `required` or `if_asked` element may not quote words saying the act is voluntary or optional ("voluntary",
     "need not", "at the option of" ...).
   * **A requirement is shown as one.** An element at any level other than `required` is refused when its quote
     passes the `required` test. So § 485(b)'s hearing request, § 480(c)'s proof of dismissal and Va. Code
     § 2.2-3704(B)'s identification of the records cannot be shown as a choice, a context line, a note or a duty
     of the other side. A `right` or `context` element whose quote passes the `if_asked` test is refused too,
     because what the other side may require is not the person's choice. Every `required` and `if_asked` element
     must be in the letter's layout.
   * A `notice` or `duty` element may rest on "may require". This is a judgement call. Neither carries a field
     for the person to fill in, and a notice is never in the letter. Va. Code § 2.2-3704(I), earlier unpaid
     bills, is a demand the public body may make before it processes a request, not something the request
     contains, so it stays a note. Its help states no obligation.

   Each counterexample in `docs/design/verify-forms.md` and its two re-checks is refused, and a test pins each
   one. They include § 480(f)(2) ("disclosure is voluntary"), § 487 (the board's duty), Va. Code § 2.2-3704(E) (a
   deemed denial) and (F) (a deemed withdrawal) as `required`, § 2.2-3704(B)(4)'s extra days as a `duty`, the
   three real requirements as `right`, `context` or `notice`, and the second re-check's made-up sentences above.
   The rules work on words, not meaning, and do not parse the sentence. Known gaps remain:
   * a party the spec does not list, or a pronoun ("he", "it"), is invisible to them;
   * a benefit verb that is not on the list ("shall acquire") passes as a duty of the person;
   * a mandatory word whose real subject is a noun that is not a party can still be given to a party that heads
     an earlier subject and has no verb of its own right after it.

   So review still checks each level.
4. **No element rests on an unrelated sentence, and notes add no fields.** The label of every `required`,
   `if_asked`, `duty` and `right` element must share a content word with the element's quote. So must each of its
   fields: the field's name, and its label with any options. The parties' own words do not count. A "purpose"
   field resting on "shall take all necessary precautions for their preservation" is refused.
   * Each field of a `context` element must share a word with its quote too, name and label alike. Here the other
     side's words count, because a context field may name who the letter goes to ("custodian", "board"), but the
     person's words do not. A "Phone number" or "Purpose of the request" field resting on "within five working
     days of receiving a request" is refused. A context field whose label names the other side ("the public
     body's ...") passes this rule, so review still reads each context field.
   * The only exceptions are the letter's own date (`date_sent`, a date field) and the sender's name (`name`, a
     text field). Each is exempt only with that name and type, with no placeholder and no options, and with a
     label that holds "date" or "name" and no word outside its list. For `date_sent` the list is "date", "it",
     "letter", "of", "send", "sent", "the", "this", "you". For `name` it is "full", "name", "your". So "Your
     name" and "Date you send it" are exempt, while "Your name and phone number", "Name, phone and date of birth"
     and "Date you send it and your date of birth" are not, and are refused.
   * `duty` and `notice` elements carry no fields, and a `notice` element is never part of the letter.
5. **No invented requirements.** No text of an element may use an obligation word that its own quote does not use.
   The words are matched by stem, so "requir" covers "required", "requires" and "requiring", and "oblig" covers
   "obliged", "obliges", "obligate" and "obligation". The list includes "must", "shall", "should", "ought",
   "require", "requisite", "req.", "need", "needful", "necessary", "necessity", "essential", "compulsory",
   "compelled", "obligatory", "mandatory", "mandated", "expected", "responsible", "have to", "please", "kindly",
   "make sure", "is to be" and "to be given" (the full list is `_OBLIGATION` in `draft.py`). That covers labels,
   help, conditions, letter sentences outside the quotation, field labels, placeholders, options and the
   description of a linked form. The `right`, `context` and `notice` elements use no obligation word at all.
   Neither do the spec's own texts: the title, summary and scope, the headings of related forms, the fixture's
   no-form note shown in the official box, and the letter's fixed parts (subject, salutation, closing). A field
   labelled "Phone number (required)", "Medium (compulsory)" or "Medium (should)", the placeholder "you have to
   give one", the help "You need a medium ...", and a summary "You must give your phone number" are all refused.
   * Texts are read after Unicode folding (NFKC), with invisible format characters removed. So a full-width
     "ｍｕｓｔ", "required" with a soft hyphen (U+00AD) inside it and "need" with a zero-width space
     (U+200B) inside it are all caught.
   * No text may use an asterisk-like mark, which reads as "required": "*", "＊", "∗", "✱", "⁎" or any other
     character whose Unicode name says asterisk.
   * No text may use a letter outside the Latin script. A Cyrillic "e" (U+0435) in "required" would otherwise
     hide the word from the check.

   The letter is assembled from the elements alone, in the spec's layout, and each paragraph carries
   `data-element`. Because "please" counts, the Virginia cost-estimate sentence now reads "I ask for a cost
   estimate in advance of the supplying of the records", after the wording of § 2.2-3704(F).
6. **Nothing chosen for the person.** No field has a default value: no box is ticked and no option is chosen.
   For example, ticking "Ask for a cost estimate first" in Virginia pauses the response time under
   § 2.2-3704(F), so the person makes that choice.
7. **Linked forms say what they are.** An official form linked from an element carries its match, `partial` or
   `related` (never `exact`), and a description of what the form is. A form the fixture links to no step of the
   same process is at most `related`. CR-180, linked only under record sealing, cannot be `partial` on the
   licence-conviction draft. Otherwise the match may not be stronger than the fixture gives the form for a step of
   the same process. Pages show it as "Related official form", not "Official form".
8. **The banner on every page,** word for word. On screen it is at the top of each page and of the letter. When
   printed, each part of the letter page (the scope and official forms, the letter, the notes) starts a new sheet
   with the banner at its top. The form page prints only the letter, which carries the banner. A CSS page-margin
   box (`@page { @top-center }`) also repeats the banner at the top of every sheet in browsers that support margin
   boxes. In a browser that does not, a part that runs onto a second sheet has the banner on its first sheet only.
9. **Official alternatives first.** The form page shows the step's official forms, the `no_form` note and related
   official forms before any field. The printable letter shows the scope and the same box before the letter. When
   printed, they take the first page, and the letter starts on the next.
10. **Private by construction.** The form has no action URL and no network calls. It uses no cookies,
    localStorage or IndexedDB. Every page sets the `no-referrer` policy, and every outbound link is
    `noopener noreferrer`. Nothing typed leaves the page. Printing is its only output. Any later saving is the
    lab's opt-in local case store.
11. **Provenance.** The draft JSON records each section's text, URL, origin (fixture or open-us-law row) and
    SHA-256, the date made, and the review status "draft, machine-checked (quotes and rules); not reviewed by a
    lawyer". The pages show the same words.
12. **Plain words, no advice.** Help text explains its own quote in plain words. It does not predict outcomes or
    recommend arguments. Where the person's facts decide a point, such as the § 480(a)(1) seven-year condition,
    the letter quotes the rule and leaves the facts to the person.
13. **No computed deadlines.** The drafts state deadline rules in the statute's words ("within five working days
    of receiving a request"; "within 60 days after service"). They compute no dates until the lab's calendar work
    fixes the business-day handling (`docs/design/lab-research.md` §3.4).

**What the checks cannot do.** They match words, not meaning. They refuse each misquote, mis-cited subsection,
invented requirement and wrong level that the verification and its two re-checks found, and a test pins each case.
A sentence worded differently from those cases can still pass (rule 3 lists the known gaps). So can a
deliberately misleading spec whose labels reuse its quote's words. The fields that only address or date the letter are `context` elements, and the optional
ones are marked so, but no code proves that the statute does not need them. Lawyer review of each spec stays a
condition for release (§9).

## 7. The worked examples

### 7.1 Virginia: request for public records (Va. Code § 2.2-3704)

The fixture lists the FOIA Council's sample letter (Word) as the official help, and its `no_form` note says the
statute sets no form. Of the draft's 20 elements, 10 make up the letter and 10 are notes for the requester.

| Element | Level | Cites | In the letter |
|---|---|---|---|
| `records`: identify the records | required | § 2.2-3704(B) "shall identify the requested records with reasonable specificity" | yes |
| `name_address` | if asked | (A) "may require the requester to provide his name and legal address" | yes, when given |
| `access`: inspect or copies | right | (A) "at the option of the requester" | yes; neither option is preset |
| `cost_estimate` | right | (F) "shall provide the requester with a cost estimate if requested" | when ticked; not ticked in advance, because asking tolls the response period |
| `medium`, `email` | right | (G) a medium "identified by the requester"; email delivery "where the public body has the capability", for records kept in an electronic database | when given; both sentences say they are about database records |
| `reference`: naming the law | right | (B) "need not make reference to this chapter" | when ticked; not ticked in advance |
| `response_duty` | duty | (B) "within five working days of receiving a request" | yes, quoted |
| `date`, `custodian` | context | (B) | yes; the custodian's address is optional, and the statute does not ask for it |
| `search_notice` | duty | (F) before a search, written notice that charges may apply, and an offer of a cost estimate | no |
| notes | notice | (B)(4) seven more work days, or 60 for criminal investigative files; (C) a court petition for more time; (D) no new record; (E) deemed denial; (F) charges, tolling, 30-day withdrawal; (H) a deposit when charges are likely to exceed $200, capped at the advance determination; (I) unpaid bills, which the public body "may require" the requester to pay before it processes a request (a note, not an `if_asked` element, because it is not part of the request; rule 3) | no |

Left out on purpose: phone number, purpose of the request, signature and a citizenship statement. Section
2.2-3704 asks for none of them. (Subsection A says who may request; it does not ask the request to say so.)

### 7.2 California: hearing request after a licence denial (Bus. & Prof. Code §§ 485, 480, 482)

The fixture's `no_form` note for `request_hearing` says no statewide form exists: each board has its own
application and criteria. The law supports a request here, but it is the § 485(b) hearing request, not a request
under § 480 or § 482. Of the draft's 26 elements, 13 make up the letter and 13 are notes.

| Element | Level | Cites |
|---|---|---|
| `hearing_request` | required | § 485(b) "Unless written request for hearing is made within the 60-day period, the applicant's right to a hearing is deemed waived." |
| `dismissal_proof` (only for §§ 1203.4-1203.42 dismissals missing from the DOJ report) | required | § 480(c) "shall provide proof of the dismissal if it is not reflected on the report furnished by the Department of Justice" |
| `dismissed`, `rehabilitated`, `arrest_only` | right | § 480(c), (b), (d) |
| `seven_years` | right | § 480(a)(1). The letter quotes both branches of the condition: a conviction within seven years, or a conviction for which the applicant is incarcerated now or was released within seven years. It names the (A) and (B) exceptions and asks for the person's own facts. It does not say whether the condition is met. |
| `sentence_completed` | right | § 482(b)(1) |
| `evidence` | right | § 481(c). BCIA 8016RR is linked as a related form, described as a request for a copy of one's own criminal record and not an evidence form |
| `date`, `applicant`, `board`, `application`, `service_date` | context | § 485. "Service by mail is complete on the date of mailing." is the section's closing text, so it is cited to § 485, not (b). The board's address, the application number and the notice date are optional |
| `notice_contents`, `hearing_within`, `rehab_criteria` | duty | § 480(f)(3), the notice contents; § 487, a hearing within 90 days of the request, with the postponement and extension rules; § 486's closing paragraph, the § 482 rehabilitation criteria served with the decision or notice |
| notes | notice | § 476(a), State Bar, alcoholic-beverage and gambling licences outside the division (so outside this draft); § 480(i), three bodies with their own rules; § 485(a), statement of issues; § 480(a), "only if", whose help summarises both conditions and both qualifiers of (a)(2); § 480(a)(1)(A)-(B), the exceptions, quoted in full with the licences in (i)-(v); § 480(a)(2), formal discipline, quoted in full (discipline based on a dismissed conviction is no basis for denial; discipline older than seven years counts only for the sexual-misconduct conduct the paragraph names); § 481(b), the three factors in the substantial-relationship criteria; § 480(f)(3)(D), the record copy, with BCIA 8016RR; § 486(a), reapplying; § 486(b), evidence considered on reapplication |

The page's scope says where the draft does not apply, or where other rules come in:

* licences under § 476(a);
* the three bodies of § 480(i);
* practice acts and divisions with conviction rules of their own, from the curated file's notes:
  * The Board of Pharmacy may deny "Notwithstanding Section 480" (§ 4202.6).
  * The Board of Accountancy has grounds "In addition to" those of § 480, with no seven-year limit for some
    financial felonies (§ 5100.2).
  * Three sections direct a board to deny a licence to a person subject to sex-offender registration under
    Penal Code § 290, with exceptions (§§ 1687, 1958.1, 2660.5).
  * Section 4989.24, in the Educational Psychologist Practice Act, bars a licence for a conviction, in
    California, in another state or in a territory of the United States, of a crime involving sexual abuse of
    children, or for a person subject to that registration "or the equivalent in another state or territory".
    Its subdivision (b) says such a denial "shall comply with the conditions for denial specified in Section 480".
    So the scope does not list it as a departure from § 480; the earlier scope did. The second re-check noted
    that the scope had left out the other states and territories; it now names them.
  * For a state cannabis licence under Division 10, § 26057(b)(2) lets the Department of Cannabis Control
    (§ 26001(w)) deny for "Conduct that constitutes grounds for denial of licensure under Chapter 2 (commencing
    with Section 480) of Division 1.5, except as otherwise specified in this section and Section 26059". The
    earlier scope left this out.

Those practice-act texts were read in the local open-us-law store to confirm the wording.
`test_the_california_scope_follows_the_practice_act_texts` checks each phrase the scope relies on against the
store, where the store is present. They are not among the spec's sections, so `check()` does not quote-check the
scope note.

The page's official list comes from the registry. CR-180 Petition for Dismissal and CR-181 Order for Dismissal
(Judicial Council, "Rev. January 1, 2024") are the official path to the § 1203.4 dismissal that § 480(c) names.
The list also has CR-409 ("Rev. January 1, 2024") and CR-410 ("New January 1, 2019") for arrest sealing (Pen. Code
§ 851.91). And it has BCIA 8016RR (Department of Justice record review, "Rev. 03/2024", $25 plus the Live Scan
site's fee). Every link was checked on 2026-10-10 with status ok.

## 8. Privacy

* Users of the lab are private people, so the forms collect nothing by default. The draft page keeps what is
  typed in memory only, and closing the page clears it.
* Any later local save (a case in the lab) stays on the user's machine. Sharing an outcome is explicit opt-in and
  anonymised, as `docs/design/lab-research.md` §4 describes. Form answers are never part of an outcome report.
* The fixture and the drafts hold organisations and official offices only. A draft has blanks for the person's
  details and never a default value; `check()` refuses a field with one (§6.6).

## 9. Open questions and next steps

* `fixtures/statutes/ca_sections.json` lacks Bus. & Prof. Code §§ 476, 480-482 and 485-487. The tests read the
  California text from the worked example's snapshot (`out/forms/*.json`, `sources`) or, failing that, from the
  local store. `tests/test_forms.py` records the SHA-256 of every section text the worked examples were built
  from. Wherever the texts load, a test that runs by default compares them with those hashes: in the app
  container for California (from the store) and everywhere for Virginia (from the fixture). Where `out/forms/` is
  present, the test also compares the snapshot's hashes with them. This passed on 2026-10-10. The text-by-text
  comparison of snapshot and store (after `strip_history`) still runs only with `LEXFLOW_FORMS_OUT` set in the
  container. Adding the seven sections to the fixture would let every test run from fixtures alone. This change
  could not edit fixtures/statutes.
* The California text has not been compared with leginfo.legislature.ca.gov, which answers automated clients with
  a bot challenge. A person should compare §§ 476, 480-482 and 485-487 in a browser before anyone uses the draft.
* The `forms` step needs wiring into `lexflow/pipeline/steps.py`, and `steps_of` needs to return step ids (§3,
  §2.5). The `FormRef` field is proposed for `lexflow/ir.py`. All three are outside this change's write scope.
* Both specs need a lawyer's review before any user sees them. Until then they stay "machine-checked". The checks
  in §6 work on words and cannot prove that an element states the law correctly.
* More specs. The `no_form` list has 24 entries. Good next candidates are the public-records requests of the
  other nine states (most have a short statutory content rule; Florida's sets none) and the DC licence petition
  (§ 47-2853.12(n)).
* An official form that changes its revision under an existing draft's step needs a person to confirm the match
  (§5.5). That review needs a place on the Setup row.

## 10. Findings of the verification and what changed

`docs/design/verify-forms.md` checked this change on 2026-10-10. Its findings, and the answer to each:

| Finding | What changed |
|---|---|
| The printable letter listed the official alternatives last | `render_letter` puts the scope and the "Official form first" box before the letter, on a page of their own when printed. Tests check both pages |
| CA `seven_years` quoted only the first branch of § 480(a)(1) and said "That condition is not met" | The quote is the whole condition, with both branches. The letter names the (A) and (B) exceptions, asks for the person's facts and makes no claim about them. The exceptions note quotes (A), (B) and (i)-(v) in full |
| The CA scope ignored § 476(a) | § 476 is now a source, and a note quotes § 476(a). The scope and the note say the draft does not apply to State Bar, alcoholic-beverage or gambling licences. The scope also lists the practice-act rules from the curated notes (corrected after the re-check for § 4989.24, and extended to § 26057(b)(2); §11) |
| BCIA 8016RR was shown as the "Official form" for evidence, and element links dropped the match | Element links carry their match and what the form is. BCIA 8016RR shows as a "Related official form", described as a request for a copy of your own criminal record and not a form for sending evidence. `check()` refuses an exact element link or one stronger than the fixture's |
| `check()` missed invented content: a field label and placeholder, an unrelated sentence, and § 485's closing paragraph taken as (b) | Field labels, placeholders and options are scanned. Obligation words must come from the quote. Mandatory words must fall on the right party. The labels and fields of `required`, `if_asked`, `duty` and `right` elements must share a word with the quote (after the re-check, `context` fields too; see §11). `locate()` treats unlettered closing text as the section's own and checks subsections to the cited depth. Each case is a test |
| "Fields the statute does not ask for are left out" was neither enforced nor true | The claim is replaced (Summary, §6): the address, number and date fields are optional context fields and are marked so. The relevance rule (§6.4) is enforced |
| Defaults with a legal effect (`cost_estimate`, `cite_law`, `access`) | No defaults remain, and `check()` refuses one |
| Wording: "Deposits over $200"; the 60 work days of (B)(4); the scope of email delivery under (G) | The deposit note follows (H), with its cap and tolling. The extension note cites (B)(4) with the 60 work days. The email sentence and help are limited to database records, where the body has the capability |
| "All 31 tests pass in the container" was true only with `out/forms` copied in | The test counts above say what runs where. `LEXFLOW_FORMS_OUT` points the tests at a copy. The worked-example test now also checks that every file is byte for byte what a rebuild gives |
| Missing notes: CA § 487, § 486(b) and the § 482 criteria, § 481(b) and § 476; VA (F) notice before a search and (C) court petition | Added, each quoted and checked |
| Missing fixture revisions and `final_url` | Revisions added for CC-1201, A406-01PREDET, CR-180, CR-181, CR-409 and CR-410. The redirect targets of the four Judicial Council forms were already in `verification.final_url` (the verification looked for a top-level field); `summary()` now passes them on. Unconfirmed revisions carry a `revision_note` |
| Not done here | CA statute text in `fixtures/statutes/ca_sections.json`; a comparison with leginfo; lawyer review; wiring in `steps.py`, `steps_of` and `ir.py` (§9) |

## 11. Findings of the re-check and what changed

The re-check in `docs/design/verify-forms.md` ("Re-check, 10 October 2026") confirmed the fixes in §10 and listed
what was not fixed, or only partly. Its findings, and the answer to each:

| Finding | What changed |
|---|---|
| W5: `required` elements could rest on § 480(f)(2) ("disclosure is voluntary"), § 487 (the board's duty), Va. (E) (deemed denial) and Va. (F) (deemed withdrawal). "Request" counted as the person wherever it stood, and any "unless the applicant" or "applicant's ... shall not" satisfied the check | The bearer is now the last party, before the mandatory word, that heads a subject. Possessives and parties after a preposition, a verb or a subordinating word are passed over. "Shall not", "shall have" and "shall constitute" are not duties of the person, and a passive counts only for the person's own acts. An "unless" or "only if" counts only when the person is the condition's subject and the consequence is a loss for the person alone. A quote saying the act is voluntary or optional cannot be `required` or `if_asked`. All four cases are refused. The same rules, applied to `if_asked` ("may require" only) and `duty` (no grants or deemed effects), also refuse the level-shifted variants: § 480(f)(2) as `if_asked`, § 2.2-3704(B)(4)'s extra days as `duty`, and a requester's duty put as a `duty` of the public body. § 481(b), whose subject is "Criteria", became a `notice`. A clause-boundary bug also went: a sentence starting with "Unless" was given the previous sentence as its clause |
| W5: `context` and `notice` elements were exempt from the relevance rule, so a context "Phone number" or "Purpose of the request" field, or a notice with a phone field in the letter, passed | Each context field must share a word with its quote. The other side's words count and the person's do not, and only the letter's date and the sender's name are exempt (by name, type and label; after the second re-check, by the whole label, §12). `duty` and `notice` elements carry no fields, and a notice is never in the letter. The CA field `license` became `application_licence`, and the VA address label names the public body, so that both rest on their quotes |
| W5: "need", "needed", "necessary", "compulsory", "obligatory", "mandated", "expected to" and a "*" marker were not caught, and the summary, scope and related headings were not scanned | All are in `_OBLIGATION`, and "*" is refused everywhere. The title, summary, scope, related headings, the fixture's no-form note and the letter's fixed parts are scanned and may use no obligation word. Three texts were reworded as a result: the VA summary ("what a request must do"), the CA summary ("must follow") and the CA scope ("required to register"). So was the VA `response_duty` help ("more time needed"), which now lists the four responses of (B) |
| WRONG (docs): §6.3 claimed that a public body's duty "cannot be presented as a requirement of the requester, and the reverse"; the `draft.py` docstring said the checks catch "the kinds of invented content" in the note; §10 said every label and field must share a word with its quote; §6 said the tests cover rules 1-11 | §6.3 now states the rules and their limit, and the docstring says each listed case is refused and pinned but other wordings can pass. §10 names the levels the relevance rule covers. Rule 10 is now tested (referrer policy, `noopener noreferrer` on every outbound link). So is rule 11 (text, URL, origin, SHA-256, date, review status), by default |
| W4 follow-on: CR-180 as `partial` on `dismissed` passed, because the fixture links CR-180 to no step of the licence-conviction process | A form the fixture links to no step of the same process is at most `related` |
| The snapshot-vs-store comparison never ran by default | The test file records each source's SHA-256, and a test compares the loaded texts with them by default (§9). The full text comparison still needs `LEXFLOW_FORMS_OUT` |
| The printed letter's first sheet and the notes sheets had no banner | Each printed part starts with the banner, and a page-margin box repeats it on every sheet where the browser supports one (rule 8) |
| The `only_if` help summarised § 480(a)(2) without its two qualifiers | The help now gives both: discipline based on a dismissed conviction is no basis for denial, and discipline older than seven years counts only for the conduct of §§ 726 and 729(a). A new note, `formal_discipline`, quotes § 480(a)(2) in full |
| The CA scope listed § 4989.24 among sections that "depart from § 480", and omitted § 26057(b)(2) | Checked against the store text (§7.2). § 4989.24 is now described with its subdivision (b), which applies § 480's conditions. § 26057(b)(2) is added in its own words. The scope no longer says "depart". It also no longer says that licences under other codes "have their own rules"; it says only that the draft is not for them |
| `locate()` accepted, with no subsection, an unlettered paragraph between two subdivisions, although the docstring spoke only of paragraphs after the last | Such a paragraph is now ambiguous and no citation is accepted for it. None of the eight sections quoted has one. The docstrings say so |

The official box's sentence "The statute sets what the request contains" was not true of the CA note, which also
cites the board's notice duty in § 480(f)(3). It now reads "The law for this step: ...". The worked examples in
`out/forms/` were rebuilt from the same statute texts (the hashes are unchanged), and the worked-example test checks
that they are byte for byte what a rebuild gives.

## 12. Findings of the second re-check and what changed

The second re-check in `docs/design/verify-forms.md` ("Re-check 2, 10 October 2026") confirmed the fixes in §11
and listed what was still wrong. Its findings, and the answer to each:

| Finding | What changed |
|---|---|
| DEFECT and OVERSTATED: a requirement of the person could be shown as `right` ("Your choice under the statute"), `context` or `notice`: § 485(b) `hearing_request`, § 480(c) `dismissal_proof` and Va. (B) `records`, each with its real quote. A `required` element could also be left out of the letter. Rule 3 said the quote bears out every level | An element at any level other than `required` is refused when its quote passes the `required` test (`passes()` in `draft.py`). A `right` or `context` element whose quote passes the `if_asked` test is refused too. Every `required` and `if_asked` element must be in the layout. The re-check called the `notice` case a judgement call. The conservative choice was taken: a notice resting on a requirement is refused, and so is a duty. A notice may still rest on "may require", as Va. (I) on earlier unpaid bills does, because that demand is not part of the request. Rule 3 says so. No current element is refused. A spec that names no parties is now refused as a whole, because none of these tests can run without them. Rule 3's heading now says that code checks the quote against the level |
| DEFECT (minor): the letter-field exemption checked only that the label held "name" or "date", so "Your name and phone number", "Name, phone and date of birth" and "Date you send it and your date of birth" passed | An exempt field's label may hold only the words listed for it in `LETTER_FIELDS` (rule 4), and an exempt field may have no placeholder and no options |
| DEFECT (minor): "should", "ought to", "requiring", "essential", "compelled", "obliges", "obligate", "necessity", "needful", "req.", "please provide", "is to be given", "＊" and "∗" passed | Obligation words are matched by stem, and the list is longer (rule 5). Texts are read after NFKC folding, with invisible format characters removed. Any character whose Unicode name says asterisk is refused, and so is any letter outside the Latin script. Because "please" counts, the VA cost-estimate sentence was reworded |
| OVERSTATED (minor): rule 3's limit named only hidden bearers and unlisted party words. Made-up sentences with a benefit verb, a negated consequence, a relative clause, a joint subject, or an exemption put as a duty passed | The code now refuses all of them. "Shall receive", "shall obtain" and the like are not duties of the person. A negated consequence is no loss. A mandatory word right after a passed-over party has no bearer, and neither has one whose subject joins both sides. "Shall not be required", "shall not be obliged" and "shall be exempt" are not duties. Rule 3 names these cases and lists the gaps that remain |
| WRONG (minor, docs): rule 11 quoted the review status without "(quotes and rules)" | Rule 11 quotes the status the code writes, and a test compares the two |
| Nit: the docstring and rule 3 named only "a comma, a paragraph mark or and/or", but the code also accepts ";", ":", "but" and "then" | Both now name them all. A test checks that they name every word in `_JOINERS` |
| Nit: rule 3 said "For this reason" about § 481(b) right after the sentence about "shall not" | Rule 3 now gives the real reason: "Criteria" is not a party |
| Nit: § 480(f)(2)'s "shall not be a factor" passed as a `duty`, with "a board may request" as its bearer | A party with a verb of its own right after it does not bear a later mandatory word, unless that word is a second verb of the same party after "and", "or", "nor" or "but". So § 480(f)(2) is refused as a `duty`, while Va. (F) "may ... and shall" and Va. (G) "may ... but shall" stay duties of the public body. Every sentence of the eight stored sections was tried at each mandatory level with the old code and the new. This is the only change: `required` still accepts 3 sentences and `if_asked` 2, and `duty` accepts 27 instead of 28 |
| Nit: the scope's "that registration" for § 4989.24 left out "or the equivalent in another state or territory" | The scope now names convictions in California, another state or a territory, and "the equivalent in another state or territory". A store test checks both phrases in § 4989.24 |
| Unchanged and documented: the text-by-text snapshot test needs `LEXFLOW_FORMS_OUT`; `ca_sections.json` lacks the sections; the CA text has not been compared with leginfo; both specs need a lawyer's review; the wiring is outside this area | Still open (§9). The fix report's figure of 23 refused false accepts was not recounted, and this plan does not use it |

The worked examples in `out/forms/` were rebuilt from their saved sources. Two texts changed: the VA cost-estimate
sentence and the CA scope. The statute texts and their hashes are unchanged, and the worked-example test checks
that the files are byte for byte what a rebuild gives.
