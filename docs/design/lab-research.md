# Process lab: research on letting people start and follow their own process

_10 October 2026. Scope: what lexflow needs so that a person can start a legal process from one of its models (for
example a public-records request in Virginia), see the next step, the deadline, who to contact and what to send,
and keep track of it until it ends. The four questions are (1) how a Lexipedia (DokuWiki) plugin should carry this,
(2) what guided self-help tools already do and what users need to see, (3) how to compute statutory deadlines, and
(4) how people could share, by explicit opt-in and anonymised, how long a step actually took, so that those outcomes
can test the models._

_Method. Code facts come from reading this repository; line numbers refer to the tree on this date. Statute text
was read from lexflow's local open-us-law copy (v2026.09.1) through `lexflow.municipal.statutes.section_texts`. The
link given for each statute is the official publisher page, and each was opened (HTTP 200) unless the entry says
otherwise. Other web sources were opened at 1 request per second or slower, with lexflow's research User-Agent. DOIs
were checked against Crossref and resolve at doi.org. Some pages were not machine-readable, and they are marked
**not opened**: dokuwiki.org serves a "human check" page to scripts, the Texas Attorney General's site answered
402, and the New York Senate and California leginfo sites answered 403. Those pages were not worked around. For
DokuWiki, the source code on GitHub was read instead. GitHub file links were checked through the GitHub API,
because github.com's HTML pages answer 503 to scripted requests. Nothing was written to any wiki, Wikibase or other
service._

_Privacy and credit. This document names organisations, official offices and statutes only. No person-level
contact is stored or reproduced. Papers are cited with their authors as bibliographic credit; nobody cited here is
a partner, advisor or endorser of lexflow. This is information, not legal advice._

## Summary

- **The models already hold most of what a user needs to see.** The 22 curated models have 53 deadlines. Each has
  an amount, a unit (29 in business days, 23 in calendar days, 1 in years), an anchor in the law's words, a
  consequence (11 deemed denials, 17 rights that lapse, 1 invalid act, 24 unstated) and, in 36 cases, an `on_miss` step that says
  what happens next. Steps carry actors, recipients and verbatim quotes. What is missing is a *case*: one person's
  instance of a model, with dates.
- **One bug matters before any deadline is shown to a user.** The compiler maps `business_days` to ISO `D`
  (`lexflow/extract/compile.py:24`). Virginia's "five working days" therefore becomes `P5D` in `Timer.value`, in
  `<lex:deadline>` and in the BPMN `timeDuration`, and the business-day meaning survives only in the event's
  display name. For a request received on a weekday, a 5-business-day timer written as `P5D` fires two days early
  when there is no holiday, and four days early over Thanksgiving week (worked example in §3.4).
- **Calendars should come from the statutes, not from a generic library.** "Business day" and "working day" mean
  different things in different states. Texas defines "business day" in § 552.0031, with optional holidays, Friday
  or Monday observance and up to 10 nonbusiness days a body may designate. Virginia leaves "working days"
  undefined, and the FOIA Council counts by excluding weekends and legal holidays. Maryland has two different
  holiday lists. In its current source (read, not run), the widely used Python `holidays` package (MIT) leaves
  Election Day and the Friday after Thanksgiving out of Virginia's calendar, although Va. Code § 2.2-3300 makes
  both legal holidays. It also treats
  Good Friday and César Chávez Day as Texas holidays, where § 552.0031 counts them as business days unless the
  body observes Good Friday. lexflow already stores every one of these sections, so each calendar day can carry its
  source quote.
- **Guided self-help tools stop at the first document.** Docassemble, A2J Author, LawHelp Interactive, the
  Document Assembly Line and the SPLC letter generator all help a person *produce* a form or letter. None of the
  ones reviewed follows the process afterwards: counting the agency's clock, noticing a deemed denial, or starting
  the remedy and its own deadline. MuckRock tracks requests, but in public and in calendar days. The lab's
  distinctive job is the follow-up, computed from quoted law.
- **On Lexipedia: a native plugin that stays thin, not an iframe.** There is no public lexflow server to call.
  lexflow runs on the user's machine, and since Chrome's Local Network Access change a public page cannot quietly
  `fetch` `localhost`. The plugin should therefore be a small DokuWiki syntax plugin plus `script.js`, on the model
  of the bpmnio plugin the wiki already runs. lexflow publishes the model and calendar data inline. The same widget
  code runs in the dashboard. The plugin needs no server-side storage, AJAX endpoint or outside call.
- **Local-first by default.** A case lives in the browser (IndexedDB), or in the local lexflow SQLite when used
  from the dashboard. It can be exported as a file and as an `.ics` calendar. Safari deletes script-written storage
  after 7 days of use without a visit to the site, so export and `navigator.storage.persist()` are required, not
  extras.
- **Outcome sharing needs coarsening because the agency is the adversary.** An agency knows who asked and when. A
  report like "City X, received 3 Oct, answered on working day 9" names the requester to the agency that received
  it. Reports should carry the model step, the outcome, the elapsed time in the model's own units (bucketed) and
  the quarter, with no dates, no free text and no identifiers. Agency-level figures should be published only above
  a minimum count. Outcomes then measure two different things, which must be kept apart: whether bodies meet the
  statutory time (law in action), and whether the model's structure explains what happened (model error).
- **Following the user's instruction, the lab is referenced from the Setup page.** It ties in there through a
  "holiday calendars" step with its credits, and a "sharing: off" card. It does not get a separate top-level page
  (§5).

## 0. What lexflow has today (local survey)

| Area | What exists | Where |
|---|---|---|
| IR timer | `Timer(kind: duration\|date\|cycle, value: ISO 8601, anchor, strict)`. `strict=False` marks a directory (soft) deadline. There is no day-count, calendar, tolling or extension field. | `lexflow/ir.py:59-63` |
| Facts deadline | `FDeadline(amount, unit ∈ {hours, days, business_days, weeks, months, years}, anchor, consequence ∈ {right-lapses, action-invalid, directory-only, deemed-denial, unstated}, on_miss, source)` | `lexflow/extract/schema.py:31-40` |
| Unit detection | "working", "business", "work" and "(except Saturdays, Sundays …)" are all read as `business_days` | `lexflow/extract/segment.py:189-193` |
| Compile | `UNIT = {"business_days": "D", …}`, so business days become a calendar ISO duration. A deadline on an agency step becomes an interrupting boundary timer. A deadline on a requester step becomes an event-based gateway that races a timer. `on_miss` wires the timer to a step or outcome. | `lexflow/extract/compile.py:24, 85-118` |
| BPMN | `<lex:deadline kind value anchor strict/>` plus a standard `timeDuration`. Example: Virginia `respond` is written as `P5D`, and `respond_extended` as `P7D`. | `lexflow/bpmn_xml.py:339-342, 382-386`; `docs/wiki/lexflow__va__records.txt:174-221` |
| Simulation | SpiffWorkflow runs the models. `prepare(..., timer_override)` can replace timer values per run. | `lexflow/simulate.py:71-74` |
| Petri nets | Each process is turned into a workflow net (pm4py) and checked for soundness | `lexflow/petri.py:245, 340` |
| As-done vs as-written | Legistar matter histories become an event log with XES-style columns (`case:concept:name`, `concept:name`, `time:timestamp`, `org:resource`) and a conformance summary | `lexflow/sources/legistar.py:104-157` |
| Contacts | General website for 16,228 governments and postal address for 38,640. Records-specific contacts (office, page, email) exist for 3 researched places only (aggregate counts; no values read out). | `contacts` table |
| API | FastAPI with no CORS middleware. `robots.txt` disallows everything. The app is meant to run on the user's machine. | `lexflow/api/app.py:43, 560` |
| Setup | Steps with `why`, `needs`, `cost` and `credits` (dicts with name, by, licence, url, use, cite, note), plus service cards. The credits note says "Credit is not endorsement". | `lexflow/pipeline/steps.py:30-44, 492-577`; `lexflow/pipeline/credits.py:1-10`; `dashboard/app.js:450-544` |
| Lexipedia | `lexipedia.xyz` serves DokuWiki with the bpmnio plugin. `lexflow:va:records` is live with an embedded diagram. The HEAD response carried no Content-Security-Policy or X-Frame-Options header, and the session cookie is `HttpOnly; SameSite=Lax`. | observed 10 Oct 2026; `lexflow/publish/lexipedia.py` |

What the records models do when a deadline passes (from `curated/*/records.json`):

| State | Deadlines | Missed deadline leads to |
|---|---|---|
| VA | 5 working days; 7 more work days (B.4) | Outcome "deemed denied; violation of the chapter". The requester's remedy (mandamus or injunction, § 2.2-3713) is listed in the gaps, not modelled. |
| DC | 15 business days; 25 with extension; 10 for the Mayor | `deemed_denied`, then a petition to the Mayor or suit (both modelled) |
| IL | 5 business days; 5 more; Public Access Counselor (PAC) review steps of 7 business days; 60 days to seek review | Outcome "PAC review or Section 11 suit open". Review steps are modelled. |
| NY | 5 business days; an agency-stated "approximate date" (stored as `amount: 0`); 30 days to appeal; 10 business days to decide the appeal | Appeal step, then forwarding to the Committee on Open Government |
| TX | 10 and 15 business days for the Attorney General route; 60 days for the requester to pay or inspect | Information presumed public; request considered withdrawn |
| MD | 10 working days; 30 days | Partial inspection; deemed denial outcome |
| WA | 5 business days; 2 business days for internal review; 1 year to sue | Motion in superior court |
| OH | 5 business days (video estimate); 3 business days to cure | Complaint, then suit |
| CA | 10 days; at most 14 more | Own end event; consequence unstated |
| NC | 25 business days; 30 days to start mediation | No jurisdiction if mediation is late |
| FL | none in the model | (none) |

So in 8 of the 11 states the model already says what follows a missed deadline. Virginia's model stops at deemed
denial, so the lab must show the gap note (remedy not modelled) instead of a dead end.

## 1. DokuWiki plugins, and whether the Lexipedia plugin should be an embed or native

### 1.1 Plugin types (read from the DokuWiki source)

The current release is DokuWiki 2026-07-14c "Mort" ([release](https://github.com/dokuwiki/dokuwiki/releases/tag/release-2026-07-14c)).
The base classes are in `inc/Extension/` ([source](https://github.com/dokuwiki/dokuwiki/tree/master/inc/Extension)).

| Type | Base class | What a plugin implements | Use in the lab |
|---|---|---|---|
| Syntax | [`SyntaxPlugin`](https://github.com/dokuwiki/dokuwiki/blob/master/inc/Extension/SyntaxPlugin.php) | `getType()`, `getPType()`, `getSort()`, `connectTo($mode)` (lexer patterns such as `addEntryPattern`/`addSpecialPattern`), `handle()` (parse time; its return value is cached as instructions) and `render($format, $renderer, $data)` (must check the format) | The `<lexflow-lab …>` block that puts the widget's mount point and data on the page |
| Action | [`ActionPlugin`](https://github.com/dokuwiki/dokuwiki/blob/master/inc/Extension/ActionPlugin.php) | `register(EventHandler)` hooks events: `TPL_METAHEADER_OUTPUT` (add `<script>`/`<link>` to the head, [template.php](https://github.com/dokuwiki/dokuwiki/blob/master/inc/template.php)), `AJAX_CALL_UNKNOWN` (custom endpoints on `lib/exe/ajax.php?call=…`, [Ajax.php](https://github.com/dokuwiki/dokuwiki/blob/master/inc/Ajax.php)), `JS_SCRIPT_LIST` | Not needed. An AJAX endpoint would mean server-side state, which the lab avoids. |
| Admin | [`AdminPlugin`](https://github.com/dokuwiki/dokuwiki/blob/master/inc/Extension/AdminPlugin.php) | `handle()`, `html()`; `forAdminOnly()` returns true by default | At most a settings page (where calendar pages live). Configuration Manager settings (`conf/default.php`, `conf/metadata.php`) are enough. |
| Helper | `Plugin` with `loadHelper()` ([PluginTrait](https://github.com/dokuwiki/dokuwiki/blob/master/inc/Extension/PluginTrait.php)) | Shared PHP functions | Not needed |
| Remote | [`RemotePlugin`](https://github.com/dokuwiki/dokuwiki/blob/master/inc/Extension/RemotePlugin.php) | Public methods become JSON-RPC calls | Not needed. lexflow publishes through the core API. |
| Renderer, Auth, CLI | in the same folder | Output formats, user back ends, command-line tools | Not needed |

### 1.2 Embedding a JavaScript widget

- **Bundling.** `lib/exe/js.php` concatenates `lib/plugins/<name>/script.js` from *every* enabled plugin into one
  script that is served on every page (`js_pluginscripts()`). It expands `/* DOKUWIKI:include file.js */` and
  `include_once` directives, so a plugin can bundle vendor code
  ([js.php](https://github.com/dokuwiki/dokuwiki/blob/master/lib/exe/js.php), lines 183 and 217). The bpmnio plugin
  uses these directives to bundle bpmn-js and dmn-js into `script.js`
  ([script.js](https://github.com/Color-Of-Code/dokuwiki-plugin-bpmnio/blob/main/script.js)). Because the bundle loads
  on every page, the lab's `script.js` should be a small loader. It should fetch the widget bundle from
  `lib/plugins/lexflowlab/` only when a lab block is on the page.
- **Passing data.** bpmnio's `render()` writes the diagram XML base64-encoded into a hidden `div`, and its script
  reads it ([syntax/bpmnio.php](https://github.com/Color-Of-Code/dokuwiki-plugin-bpmnio/blob/main/syntax/bpmnio.php),
  lines 12-17 and 200-228). The same pattern fits the lab: lexflow publishes the model's facts JSON (steps,
  deadlines, sources, `on_miss`) and the calendar JSON inside the block. The widget then needs no request at all.
  Site-wide values can go in `JSINFO`, which is printed in the page head (`tpl_metaheaders()`).
- **Media files.** DokuWiki's default `conf/mime.conf` does not allow `.json` uploads
  ([mime.conf](https://github.com/dokuwiki/dokuwiki/blob/master/conf/mime.conf)). lexflow's own snippet already adds
  `bpmn`, `dmn` and `pnml` through `mime.local.conf` (`docker/dokuwiki/local.php.snippet`). Inline data avoids
  another MIME change.
- **Render cache.** Rendered pages are cached (`$conf['cachetime']` defaults to one day,
  [conf/dokuwiki.php](https://github.com/dokuwiki/dokuwiki/blob/master/conf/dokuwiki.php), line 87; a `Nocache`
  parser mode exists). Server-rendered HTML is the same for every visitor, so anything about *this* user's case has
  to be drawn in the browser. That fits local-first anyway.

### 1.3 Calling an outside API, and CORS

- **From the browser.** A `fetch` from `https://lexipedia.xyz` to another origin needs that origin to answer with
  `Access-Control-Allow-Origin: https://lexipedia.xyz`. JSON requests are preflighted (`OPTIONS`), and credentialed
  requests cannot use `*` ([MDN, CORS](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/CORS)). FastAPI would
  need `CORSMiddleware` with an explicit origin list. Its documentation notes that wildcards cannot be combined with
  `allow_credentials=True` ([FastAPI, CORS](https://fastapi.tiangolo.com/tutorial/cors/)). lexflow has no such
  middleware today, and more to the point it has no public server.
- **To the user's own lexflow.** A public page that `fetch`es `http://localhost:…` now meets Chrome's Local Network
  Access permission prompt. The prompt covers `fetch()`, subresources and subframe navigation from a public site to
  loopback or local-network addresses ([Chrome for Developers, June 2025](https://developer.chrome.com/blog/local-network-access)).
  A plain top-level link ("Open this case in my lexflow") is not among the request types that post lists. A file
  export and import moves a case without any cross-origin call.
- **From the wiki server.** PHP can call out with `DokuHTTPClient`, which honours the wiki's proxy settings
  ([DokuHTTPClient.php](https://github.com/dokuwiki/dokuwiki/blob/master/inc/HTTP/DokuHTTPClient.php)). That avoids
  CORS, but the user's case data would then pass through the wiki server, which breaks the local-first rule.
- **DokuWiki's own API.** It is off by default (`remote = 0`, `remoteuser = '!!not set!!'`, `remotecors = ''`
  meaning deny, [conf/dokuwiki.php](https://github.com/dokuwiki/dokuwiki/blob/master/conf/dokuwiki.php), lines
  69-71). lexflow's snippet turns it on for `@bots` only, for publishing. The lab must not need it.

### 1.4 Storing data

Server-side, a plugin can write page metadata (`p_set_metadata`), files under the data directory (`io_saveFile`,
`metaFN`), or media, or use a plugin such as sqlite. All of these would put private case data on a server, and
anonymous visitors' writes would have no CSRF protection (§1.5). Client-side, the widget can use IndexedDB in the
wiki's origin. That storage is shared with every other plugin's script on lexipedia.xyz, which is acceptable only
because the wiki owner controls which plugins run. It is also subject to browser eviction (§4.1).

### 1.5 Security model

- **Plugins are fully trusted code.** A plugin is PHP that runs with the wiki's full privileges. Installing one
  means trusting it. Its `script.js` runs on every page, in the wiki's origin.
- **Output escaping is the plugin's job.** DokuWiki provides `hsc()`
  ([common.php](https://github.com/dokuwiki/dokuwiki/blob/master/inc/common.php), line 38). Raw HTML and PHP in
  pages are no longer core features: they now live in the separate htmlok plugin
  ([saggi-dw/dokuwiki-plugin-htmlok](https://github.com/saggi-dw/dokuwiki-plugin-htmlok), created April 2023).
  Pasting a `<script>` into a page is therefore not a supported way to embed a widget. A plugin is.
- **CSRF.** `checkSecurityToken()` returns true when no user is logged in. The token (`sectok`) protects logged-in
  users only ([common.php](https://github.com/dokuwiki/dokuwiki/blob/master/inc/common.php), lines 112-145). Any
  state-changing endpoint open to anonymous visitors is unprotected by design. This is another reason the lab has
  none.
- **ACL.** `auth_quickaclcheck($id)` returns the permission level: `AUTH_READ` 1, `AUTH_EDIT` 2, `AUTH_CREATE` 4,
  `AUTH_UPLOAD` 8, `AUTH_DELETE` 16, `AUTH_ADMIN` 255
  ([auth.php](https://github.com/dokuwiki/dokuwiki/blob/master/inc/auth.php), line 700;
  [defines.php](https://github.com/dokuwiki/dokuwiki/blob/master/inc/defines.php)). Admin plugins are admin-only
  unless `forAdminOnly()` is overridden.
- **Upload filter.** `iexssprotect` checks uploads for HTML and JavaScript (on by default).
- **Not opened.** dokuwiki.org's developer pages (`devel:plugins`, `devel:security`, `devel:javascript`,
  `devel:event:*`) sit behind a human check. A person should read them before the plugin is written.

### 1.6 Thin embed or native plugin?

| | Thin embed (iframe of a page served by lexflow) | Native plugin, kept thin (syntax plugin + loader `script.js` + shared widget bundle) |
|---|---|---|
| Needs a public lexflow host | Yes. None exists, and the user's own lexflow is on `localhost`. | No. Data is published inline by lexflow. |
| Cross-origin issues | CORS for any data calls; Local Network Access if it points at `localhost`; third-party storage is partitioned by top-level site (MDN describes Firefox's scheme: [state partitioning](https://developer.mozilla.org/en-US/docs/Web/Privacy/Guides/State_Partitioning)) | None. Everything is same-origin. |
| Sandboxing | A sandboxed iframe isolates the widget from wiki scripts, unless it is same-origin with both `allow-scripts` and `allow-same-origin` ([MDN, iframe](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/iframe)) | Shares the origin with the other plugins the wiki owner installed |
| Looks like the wiki, prints, works without the app | Partly | Yes |
| Code reuse with the dashboard | The whole page | The same widget module, mounted by the dashboard and by the plugin |
| Maintenance | lexflow hosting, uptime, CORS lists | One small PHP class; the widget is versioned with lexflow |

**Recommendation: a native plugin that stays thin.** Call it `lexflowlab`.

- **Syntax.** `<lexflow-lab model="va-records" calendar="va" />`, or a block that wraps a base64 JSON payload.
- **PHP.** It only validates attributes and escapes output with `hsc()`.
- **JavaScript.** `script.js` lazy-loads the widget, which keeps the case in IndexedDB.
- **Not included.** No AJAX endpoint, no admin page, no outbound requests and no cookies of its own.

lexflow's publisher, `lexflow/publish/lexipedia.py`, would add the block to each process page and to each place
page (where local contacts live). An "Open in my lexflow" link and file export give the durable local route. If the
lab ever shows the diagram, the bpmn.io watermark must stay visible, as lexflow's own credit for bpmn-js records.

## 2. Guided legal self-help: the state of the art and what users need to see

### 2.1 What exists

| Tool | Maker | What it does | Follows the process after the first document? | Data handling |
|---|---|---|---|---|
| [California Courts Self-Help Guide](https://selfhelp.courts.ca.gov/) | Judicial Council of California | Guides by case type ("take the next step"), form finder, self-help centres | Gives information on next steps; does not track a case | Information site |
| [Docassemble](https://docassemble.org/) | Open-source project (MIT) | Guided interviews in YAML + Python that assemble PDF/DOCX/RTF | No built-in follow-up. Its date helpers (`date_interval`, `date_difference`) have no business-day or holiday calendar ([dates.py](https://github.com/jhpyle/docassemble/blob/master/docassemble_base/docassemble/base/dates.py)). | Answers are stored encrypted on the server, keyed by the user's password, unless `multi_user` is on. Sessions are deleted after 90 days without activity by default ([security docs](https://docassemble.org/docs/security.html)). |
| [A2J Author](https://www.cali.org/faq/15690) | CALI and IIT Chicago-Kent's Center for Access to Justice & Technology | "A2J Guided Interviews" in plain language. Graphics walk the user along a path to the courthouse. The output is a form to print and file. | No | Cloud-based authoring; interviews run on LawHelp Interactive or another server ([a2jauthor.org](https://www.a2jauthor.org/)) |
| [LawHelp Interactive](https://www.lawhelpinteractive.org/) | Site credits Scale Justice | Fills legal documents for free; hosts interviews | Save and resume with an account | Account-based |
| [Document Assembly Line](https://assemblyline.suffolklitlab.org/) and Court Forms Online | Suffolk LIT Lab (MIT) | Docassemble-based court-form interviews, with e-filing (certified for Tyler eFile & Serve) | Ends at filing | Server-hosted |
| [SPLC Public Records Letter Generator](https://splc.org/foiletter.asp) | Student Press Law Center | Writes a state records request with the statute citation and the response time | No. It "will NOT send the letter" and only returns text. | No account |
| [RCFP Open Government Guide](https://www.rcfp.org/open-government-guide/) | Reporters Committee for Freedom of the Press | State-by-state guide to open records and meetings laws, all 50 states and DC | Reference work | Copyright RCFP; no reuse terms stated |
| [MuckRock](https://www.muckrock.com/about/) | MuckRock Foundation (nonprofit) | Files and tracks records requests in public. A 2017 analysis of more than 30,000 requests to over 6,000 agencies found a median of the agencies' average response times of 31 days and a 43% success rate ([MuckRock, 14 Mar 2017](https://www.muckrock.com/news/archives/2017/mar/14/muckrock-foia-response-data/)). | Yes, in public. Response times are counted in calendar days from filing. | Requests are published |

The pattern: the mature tools assemble the *first* document and stop. The one tool that tracks the process does so
in public and counts calendar days, without the statute's units, tolling or extensions. None of the tools reviewed
counts business days from a calendar sourced in statute.

### 2.2 Evidence on what helps

- **Clear forms and reminders.** In a field study, redesigning a criminal summons to put the key information first,
  and sending text-message reminders, raised court appearance and cut warrants for failure to appear (Fishbane,
  Ouss, Shah 2020, *Science* 370(6517), [doi:10.1126/science.abb6591](https://doi.org/10.1126/science.abb6591)).
  Deadline reminders are therefore a core feature, not a nicety.
- **Scale of unmet need.** Low-income Americans got no or not enough legal help for 92% of their civil legal
  problems (LSC, [The Justice Gap, 2022](https://justicegap.lsc.gov/)).
- **Design for people without lawyers.** IAALS's report on self-represented litigants asks courts and service
  providers to share responsibility for guiding people through the process
  ([IAALS 2016](https://iaals.du.edu/publications/cases-without-counsel-our-recommendations-after-listening-litigants)).
  The federal plain-language guides cover writing, designing and testing for understanding
  ([Digital.gov](https://digital.gov/guides/plain-language)).

### 2.3 What the lab shows for a case, and where each item comes from

| User need | Shown as | Source in the model today | Gap |
|---|---|---|---|
| Where am I? | The path so far, with dates | Steps and `after`; the user's own events | Case state (new) |
| What happens next, and who acts? | "Next: the public body must answer (you wait)" or "Next: you may appeal" | `actor`, `modality`, `recipient`, `kind` | None |
| By when? | A date, plus *how it was counted*: unit, calendar, first day, holidays skipped, rule quoted | `deadline.amount/unit/anchor/source` | Calendar, count rules, tolling and extensions (§3) |
| Who to contact | The office or role channel (e.g. the FOIA officer every Virginia public body must designate and publish, Va. Code [§ 2.2-3704.2](https://law.lis.virginia.gov/vacode/2.2-3704.2/)), linked to the official page; oversight bodies where they exist (Virginia FOIA Council advisory opinions, [§ 30-179](https://law.lis.virginia.gov/vacode/30-179/); Illinois PAC; DC Mayor) | `contacts` (website, postal; records office for 3 places), actors | Records-office contacts for most places. Role channels only, never names (link to the official page instead). |
| What to send | What the law says the request or reply must contain (VA: "reasonable specificity"; TX § 552.2615(b): answer the itemized estimate in writing within 10 business days) and an optional local draft letter | Step quotes, decision tables (response types) | Draft letters (local only, like the SPLC generator: text, never sent by lexflow) |
| What if the deadline passes? | The consequence in the law's words, the next step and *its* deadline (e.g. NY appeal within 30 days; IL PAC review within 60 days; WA suit within 1 year; VA mandamus or injunction, § 2.2-3713) | `consequence`, `on_miss`, outcomes, gap notes | VA, CA and FL need remedy links (the VA remedy is a gap note today) |
| Reminders | `.ics` file with `VALARM` reminders ([RFC 5545](https://www.rfc-editor.org/rfc/rfc5545)) | New | New |
| Evidence | "What I sent, when, how" log, kept locally | New | New |
| How sure is this? | Review status (draft / checked), gaps, "information, not legal advice", and where to check (the official FOIA officer, the oversight body) | `review`, `lex:gap` | None |
| Optional feedback channels | Official ones only, at the user's choice. Example: the Virginia FOIA Council must provide an online form to comment on the assistance a public body gave (§ 30-179(6)). The lab links to it and never submits anything. | New | New |

## 3. Computing statutory deadlines

### 3.1 Units and definitions, by state

| Jurisdiction | Records-law wording (curated model) | Is "business/working day" defined? | Holiday source | When a calendar-day period ends on a weekend or holiday |
|---|---|---|---|---|
| Virginia | "within five working days of receiving a request"; "an additional seven work days" ([§ 2.2-3704(B), (B)(4)](https://law.lis.virginia.gov/vacode/2.2-3704/)) | No. FOIA Council: weekends and legal holidays are excluded, and day 1 is the first working day after receipt ([AO-02-08](https://foiacouncil.dls.virginia.gov/ops/08/AO_02_08.htm)). | [§ 2.2-3300](https://law.lis.virginia.gov/vacode/2.2-3300/): 13 days, including Election Day and the Friday after Thanksgiving. Saturday moves to Friday, Sunday to Monday. Days appointed by the Governor or President count. | [§ 1-210](https://law.lis.virginia.gov/vacode/1-210/): the event day is not counted. Rolling forward is stated only for judicial proceedings and limitation periods. |
| District of Columbia | "15 days (except Saturdays, Sundays, and legal public holidays)"; extensions of 10 or 15 such days ([§ 2-532](https://code.dccouncil.gov/us/dc/council/code/sections/2-532)) | The exclusion is written into the deadline itself | [§ 1-612.02](https://code.dccouncil.gov/us/dc/council/code/sections/1-612.02), including DC Emancipation Day (16 April) and days the Mayor designates | (not checked) |
| Maryland | "10 working days"; "not more than 30 days" ([GP § 4-203](https://mgaleg.maryland.gov/mgawebsite/Laws/StatuteText?article=ggp&section=4-203&enactments=false)) | No. The PIA definitions in GP § 4-101 have none. | Two lists: "legal holiday" in [GP § 1-111](https://mgaleg.maryland.gov/mgawebsite/Laws/StatuteText?article=ggp&section=1-111&enactments=false) (Lincoln's birthday, Maryland Day, Good Friday, general election day …; Sunday moves to Monday only) and "employee holiday" in [SPP § 9-201](https://mgaleg.maryland.gov/mgawebsite/Laws/StatuteText?article=gsp&section=9-201&enactments=false). Which one makes a "working day" is open. | (not checked) |
| Texas | "not later than the 10th business day after the date …" ([Gov't Code ch. 552](https://tcss.legis.texas.gov/resources/GV/htm/GV.552.htm#552.0031)) | Yes, § 552.0031. Not Saturday or Sunday, and not a national or state holiday under § 662.003(a)-(b). An optional holiday counts only if the officer for public information observes it. The Friday or Monday counts only if the body observes the holiday then. Remote work does not change a business day. A body may designate up to 10 nonbusiness days a year. | [§ 662.003](https://tcss.legis.texas.gov/resources/GV/htm/GV.662.htm#662.003): Confederate Heroes Day, Texas Independence Day, San Jacinto Day, Emancipation Day in Texas, LBJ Day, the Friday after Thanksgiving, 24 and 26 December. Optional holidays: Rosh Hashanah, Yom Kippur, Good Friday. | Mail receipt: if the actual date cannot be established, receipt is the 3rd business day after the postmark (§ 552.301(a-1)) |
| Illinois | "within 5 business days after its receipt" ([5 ILCS 140/3(d)](https://www.ilga.gov/ftp/ILCS/Ch%200005/Act%200140/000501400K3.html)) | Not among the definitions in [§ 2](https://www.ilga.gov/ftp/ILCS/Ch%200005/Act%200140/000501400K2.html) as read | (not looked up) | (not looked up) |
| New York | "within five business days of the receipt" (POL § 89(3)(a), as quoted in the model) | (not checked) | GCL § 24 (public holidays, plus the Saturday half-holiday) | GCL § 25-a: to the next business day. Text read locally; the [publisher page](https://www.nysenate.gov/legislation/laws/GCN/25-A) answered 403, **not opened**. |
| Washington | "within five business days" (RCW 42.56.520) | (not checked) | [RCW 1.16.050](https://apps.leg.wa.gov/rcw/default.aspx?cite=1.16.050) (Sunday is listed; Saturday moves to Friday, Sunday to Monday) | [RCW 1.12.040](https://apps.leg.wa.gov/rcw/default.aspx?cite=1.12.040): exclude the first day; include the last unless it is a holiday, Saturday or Sunday |
| Ohio | "within five business days of receipt"; "three business days to cure" ([R.C. 149.43](https://codes.ohio.gov/ohio-revised-code/section-149.43)) | (not checked; R.C. 1.14 is not in the local copy) | (not in the local copy) | (not in the local copy) |
| California | "within 10 days from receipt"; extension of at most 14 days by written notice (Gov § 7922.535) | No business days | Gov § 6700: every Sunday and listed days. Some days do not bind a city, county or district unless it adopts them. | Gov § 6800 and CCP § 12: exclude the first day, include the last unless it is a holiday. CCP § 12a: a last day falling on a holiday (which includes Saturdays) moves to the next non-holiday. Text read locally; [leginfo](https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=CCP&sectionNum=12a.) answered 403, **not opened**. |
| North Carolina | "within 25 business days" (§ 132-6(d)) | (not checked) | [§ 103-4](https://www.ncleg.gov/EnactedLegislation/Statutes/HTML/BySection/Chapter_103/GS_103-4.html): legal public holidays, including Greek Independence Day, Halifax Resolves, Good Friday, Yom Kippur, and election day in general-election years. More days than offices close for. | [§ 103-5](https://www.ncleg.gov/EnactedLegislation/Statutes/HTML/BySection/Chapter_103/GS_103-5.html): to the next day the office is open |
| Florida | no fixed deadline in the model | (none) | [§ 683.01](http://www.leg.state.fl.us/statutes/index.cfm?App_mode=Display_Statute&Search_String=&URL=0600-0699/0683/Sections/0683.01.html): legal holidays include every Sunday and many commemorative days | (not checked) |
| Federal FOIA | "within 20 days (excepting Saturdays, Sundays, and legal public holidays)" ([5 U.S.C. § 552(a)(6)(A)(i)](https://www.law.cornell.edu/uscode/text/5/552)) | The exclusion is written into the deadline | [5 U.S.C. § 6103](https://www.law.cornell.edu/uscode/text/5/6103); OPM lists observed dates for 2024-2030 and offers an `.ics` file ([OPM](https://www.opm.gov/policy-data-oversight/pay-leave/federal-holidays/)) | Courts: [FRCP 6(a)](https://www.law.cornell.edu/rules/frcp/rule_6). Exclude the trigger day, count every day, and if the last day is a weekend or legal holiday run to the next day that is not. "Legal holiday" includes state holidays where the court sits. |

Four lessons:

1. **A legal holiday is not the same as an office closure.** Florida's and North Carolina's lists include days that
   offices do not close for. Texas instead defines "business day" for the records law itself, and lets a body
   designate its own nonbusiness days.
2. **The calendar belongs to the deadline's statute and to the body.** It is not a property of the state alone.
3. **"Working day" left undefined needs an interpretive source.** For Virginia that is the FOIA Council's opinion,
   and the lab should show it as such.
4. **Calendar-day deadlines need a roll-forward rule.** That rule comes from the state's general time-computation
   statute, and its scope varies (Virginia's § 1-210 roll-forward is limited to judicial proceedings and
   limitation periods).

### 3.2 Holiday data: statute first, libraries as a cross-check

lexflow already holds every holiday section listed above, with publisher URLs. A calendar should be generated from
these sections. Each holiday carries its rule ("the fourth Thursday in November and the Friday next following"),
its observance shift and its source quote, so a user can see *why* a day was skipped.

The Python [`holidays`](https://pypi.org/project/holidays/) package (v0.106, MIT, [source](https://github.com/vacanza/holidays))
is useful as a cross-check, with two differences found by reading its US calendar at commit
[`6486576`](https://github.com/vacanza/holidays/blob/6486576f8a6f3135d9ae4e27a130250758c8de10/holidays/countries/united_states.py)
(29 Aug 2026). The library was read, not run, because it is not installed in lexflow's container.

- **Virginia.** The subdivision calendar has no Election Day and no Friday after Thanksgiving, although § 2.2-3300
  lists both. It names the second Monday in October "Indigenous Peoples' Day", where the statute says "Columbus Day
  and Yorktown Victory Day". The date is the same, so counting is unaffected.
- **Texas.** The public calendar includes Good Friday and César Chávez Day. Under § 552.0031, Good Friday is a
  nonbusiness day only if the officer for public information observes it. César Chávez Day is not a § 662.003
  holiday at all (§ 662.013 says state agencies "shall remain open"), so it is a business day unless the body
  designates it under § 552.0031(f). The library has no notion of optional holidays observed by the body, or of
  designated nonbusiness days.

Both differences move a deadline by one day in a typical case. They would be worth reporting upstream, but that is
the user's decision, and nothing was filed. Local overlays (a city's own holiday schedule, weather closures, a
Texas body's designated days) need a per-body source. Today that means the official page, or the user marking
"office closed" in their own case.

### 3.3 Counting rules the engine needs

- **First day.** The trigger day is excluded (Va. § 1-210(A); Cal. Gov § 6800; RCW 1.12.040; FRCP 6(a)(1)(A)). The
  Virginia FOIA Council counts day 1 as the first working day after receipt.
- **Last day.** Some statutes roll forward to the next business or open day (CA, NY, NC, WA, FRCP), and some do not
  say. A business-day count never ends on a non-business day.
- **Months and years.** These are calendar arithmetic with edge cases. California defines "year" as 365 days and
  "month" as a calendar month (Gov §§ 6803, 6804). Formal work on date arithmetic for law shows that adding months
  or years is ambiguous at month ends, and that the ambiguities can be detected statically (Monat, Fromherz,
  Merigoux 2024, ESOP, [doi:10.1007/978-3-031-57267-8_16](https://doi.org/10.1007/978-3-031-57267-8_16); Catala:
  Merigoux, Chataing, Protzenko 2021, [doi:10.1145/3473582](https://doi.org/10.1145/3473582)). Washington's
  one-year suit limit is the only year-unit deadline in the models.
- **Receipt.** "Receipt" is a legal event with its own rules. Texas deems a mailed request received on the 3rd
  business day after the postmark when the date cannot be established. Rules for after-hours email were not
  verified for any state, so the lab should ask the user for the date the body received it and show the rule
  where one exists.
- **End of day and time zone.** FRCP 6(a)(4) ends electronic filing at midnight in the court's time zone. Agency
  deadlines usually speak in days. The lab should compute dates in the body's time zone and display whole dates.

### 3.4 Worked example: Virginia's five working days

The calendar is § 2.2-3300 as of 2026. It was computed in the container with a 40-line script, so it is not
production code.

| Request received | `P5D` (today's timer) | 5 working days, § 2.2-3300 | Same, with the library's Virginia calendar | B.4: 7 more work days, counted from day 5 |
|---|---|---|---|---|
| Fri 18 Jan 2008 (FOIA Council AO-02-08) | Wed 23 Jan | **Mon 28 Jan**, which matches the opinion | (2008 calendar not compared) | (none) |
| Fri 30 Oct 2026 | Wed 4 Nov | **Mon 9 Nov** (Election Day, 3 Nov, skipped) | Fri 6 Nov | Thu 19 Nov |
| Wed 25 Nov 2026 | Mon 30 Nov | **Fri 4 Dec** (26 and 27 Nov skipped) | Thu 3 Dec | Tue 15 Dec |

The model's gap note says it is unclear whether the 7 work days run from the end of the 5-day period or from the
B.4 response. The difference is real. If a B.4 response is sent on Wed 4 Nov 2026, counting from the response
gives Mon 16 Nov, while counting from day 5 gives Thu 19 Nov. The lab should show both dates and the ambiguity,
not pick one silently. The 2008 case should become a unit test.

### 3.5 Tolling, extensions and suspensions

| Kind | Example in law | What the engine must do |
|---|---|---|
| Tolling by a requester exchange | Va. § 2.2-3704(F): the response period "shall be tolled" between notice of a cost estimate and the requester's answer; the request is deemed withdrawn if there is no answer within 30 days. Federal FOIA: one request to the requester for information, and fee clarification, toll the 20 days ([§ 552(a)(6)(A)(ii)](https://www.law.cornell.edu/uscode/text/5/552)). | Pause the clock between two user-recorded events. Start the requester's own 30-day clock. (Virginia's tolling is a gap note in the model today.) |
| Deemed withdrawal | Tex. § 552.2615(b): withdrawn if the requester does not answer an itemized estimate within 10 business days; § 552.221(e): 60 days to inspect or pay | A requester-side deadline with a lapse consequence (already modelled for the 60-day rule) |
| Extension by notice | Va. B.4 (7 work days); D.C. § 2-532(d) (10 or 15 days, Saturdays, Sundays and holidays excepted); Cal. Gov § 7922.535(b) (at most 14 days); federal unusual circumstances (at most 10 working days) | A conditional second deadline, valid only if notice is given within the first period. Its anchor must be explicit. |
| Extension by court | Va. § 2.2-3704(C): the body may petition the court for more time | Clock replaced by a court date (user-entered) |
| Agency-set date | N.Y. POL § 89(3)(a): an "approximate date … reasonable under the circumstances" (`amount: 0` in the model) | The user enters the date stated in the acknowledgement; the lab flags that only reasonableness is reviewable |
| Suspension | Tex. § [552.2325](https://tcss.legis.texas.gov/resources/GV/htm/GV.552.htm#552.2325): after a catastrophe, a body may suspend the chapter for at most 7 days, extended once by up to 7 more (14 days in all), on notice to the Attorney General. Pending deadlines are tolled until the first business day after the suspension. The Attorney General must post each notice for a year. | Calendar overlay per body and period. The AG's notice page was **not opened** (402), so its format is unknown. |

### 3.6 Proposed additions to the deadline record (no code changed here)

The IR and the facts schema need to say *how* to count, not only how much. A sketch:

```json
"deadline": {
  "amount": 5, "unit": "business_days",
  "count": {"calendar": "va", "first_day": "next", "roll": "none",
            "business_day_source": "undefined in § 2.2-3704; FOIA Council AO-02-08 excludes weekends and legal holidays"},
  "anchor": "receiving a request", "anchor_event": "request_received",
  "tolls": [{"from": "cost_estimate_sent", "until": "requester_answered_estimate",
             "source": {"section": "2.2-3704", "subsection": "F", "quote": "shall be tolled"}}],
  "extensions": [{"amount": 7, "unit": "business_days", "requires": "written B.4 response within the first period",
                  "runs_from": ["end_of_first_period", "b4_response"], "ambiguous": true}],
  "set_by_body": false,
  "consequence": "deemed-denial", "on_miss": "deemed_denied"
}
```

- **`Timer`** (`lexflow/ir.py`) gains `day_count: "calendar" | "business"`, `calendar: str | None` and
  `roll: "none" | "next_business_day" | "next_open_day"`.
- **The compiler** stops writing `P5D` for 5 business days. It keeps `unit` and writes `<lex:deadline value="P5D"
  dayCount="business" calendar="va" …>`. Engine timers then get a per-case `timeDate` computed by the lab, which
  `simulate.prepare(timer_override=…)` can already accept.
- **Precedent.** Flowable's timer events take a `flowable:businessCalendarName` that points to a calendar in the
  engine configuration ([Flowable BPMN constructs](https://www.flowable.com/open-source/docs/bpmn/ch07b-BPMN-Constructs)).
  BPMN 2.0.2 itself has only ISO 8601 durations, dates and cycles
  ([OMG, formal/13-12-09](https://www.omg.org/spec/BPMN/2.0.2/About-BPMN)).
- **Which files.** These changes belong to `lexflow/extract/*`, `lexflow/ir.py` and `lexflow/bpmn_xml.py`, which
  other workflows own. They are proposals only.

### 3.7 Calendar data

A calendar is a versioned list of days. Each day has a reason and a source: "statute holiday", "observed shift",
"designated nonbusiness day (body)", "closure (user-marked)" or "suspension (TX § 552.2325)". It is keyed by
jurisdiction and, optionally, by body (`gov_id`). Publish the statute layer to Lexipedia with the model, for
example inline in the lab block or as a `lexflow:calendars:<state>` page. Keep the user's closures in the case
only. Every computed date should list the days it skipped and why.

## 4. Privacy-preserving outcome sharing, and how outcomes can measure the models

### 4.1 Local-first storage

Local-first software keeps the primary copy on the user's device, works offline and lets the user own their data
(Kleppmann, Wiggins, van Hardenberg, McGranaghan 2019, Onward!, [doi:10.1145/3359591.3359737](https://doi.org/10.1145/3359591.3359737);
[Ink & Switch essay](https://www.inkandswitch.com/local-first/)).

- **In the dashboard.** The case goes in the local SQLite store, on the user's machine, next to the models. It is
  never pushed by Turso sync unless the user opts in per table.
- **On Lexipedia.** The case goes in IndexedDB in the wiki origin. Browser storage is "best-effort" by default and
  can be evicted. `navigator.storage.persist()` asks for persistence: Firefox prompts, while Chrome and Safari
  decide from the user's history with the site
  ([MDN, storage quotas and eviction](https://developer.mozilla.org/en-US/docs/Web/API/Storage_API/Storage_quotas_and_eviction_criteria)).
  Safari deletes all script-written storage (IndexedDB, localStorage and others) after 7 days of Safari use without
  interaction with the site. Home-screen web apps keep their own counter
  ([WebKit, March 2020](https://webkit.org/blog/10218/full-third-party-cookie-blocking-and-more/)). A records
  request can easily run longer than 7 days. Remedies:
  - export and import of the case as a JSON file;
  - an `.ics` export of the deadlines (the user's calendar keeps them);
  - a prominent "open in my lexflow" route.
- **Never on a server by default.** No account, no server copy, no analytics. Free-text notes and documents never
  leave the device.

### 4.2 What an opt-in outcome report contains

The user must take an explicit action each time. The full report is shown before anything is shared, and it can
be saved as a file instead of being sent.

| Field | Example | Why | Privacy treatment |
|---|---|---|---|
| Model and version | `va-records`, content hash | Attach the evidence to the model that made the prediction | Public information |
| Step and outcome | `respond` and one of `answered_in_time`, `answered_late`, `extension_notice`, `no_answer` (deemed denial), `estimate_tolled`, `withdrawn`, `still_open` | The measurement | Closed vocabulary; no free text |
| Elapsed time | Business days by the model's calendar, in buckets aligned to the deadline (≤5, 6-7, 8-12, 13-20, >20) | Compare with the statute | Bucketed |
| Period | Quarter of the trigger (`2026-Q4`) | Trends | No dates |
| Where | State, plus body *type* (city, county, state agency). The body itself is named only if the user chooses, and is published only above a minimum count. | Agency-level accountability | Coarsened by default |
| Calendar version | `va:2.2-3300@2026-09` | Reproducible counting | (none needed) |
| Never | Names, addresses, request text, dates, documents, notes, device or account IDs, IP addresses (the collector keeps no logs) | (none) | (none) |

**Threat model.** The body that answered knows who asked and on which day. Any report with exact dates and the
body's identity can be linked back by that body, and small bodies receive few requests. Hence the defaults:

- quarters instead of dates, and buckets instead of exact counts;
- body type unless the user opts into naming the body;
- publication only for cells with at least *k* reports (k = 10 is suggested; an open question);
- reports batched and sent with a random delay, so the time a report arrives does not reveal the event.

k-anonymity gives the vocabulary for such thresholds (Sweeney 2002,
[doi:10.1142/S0218488502001648](https://doi.org/10.1142/S0218488502001648)). If the lab grows beyond a handful of
users, two stronger options exist:

- *Local differential privacy*: randomised response on each answer, as in RAPPOR (Erlingsson, Pihur, Korolova 2014,
  [doi:10.1145/2660267.2660348](https://doi.org/10.1145/2660267.2660348); for the underlying definitions, Dwork,
  McSherry, Nissim, Smith 2006, [doi:10.1007/11681878_14](https://doi.org/10.1007/11681878_14)).
- *Secret-shared aggregation*: Prio (Corrigan-Gibbs, Boneh, [NSDI 2017](https://www.usenix.org/conference/nsdi17/technical-sessions/presentation/corrigan-gibbs)),
  now being standardised as the IETF Distributed Aggregation Protocol. In DAP, clients split each measurement
  between two aggregators, and the collector sees only totals
  ([draft-ietf-ppm-dap-19](https://datatracker.ietf.org/doc/draft-ietf-ppm-dap/), an Internet-Draft, not an RFC).

Both cost accuracy or infrastructure. Thresholds and coarsening come first.

**"Pull, don't push."** Users can compare their own case with *published* aggregates without sharing anything. The
widget downloads the aggregate table with the model. Most of the lab's value needs no upload at all.

### 4.3 How outcomes measure the models

Keep two questions apart.

1. **Did the body answer within the statutory time? (law in action)** This is an on-time rate per step in the
   model's own units, with a time-to-response curve. Cases still open are right-censored, not dropped, which is
   what the Kaplan-Meier estimator is for (Kaplan, Meier 1958, *JASA* 53(282),
   [doi:10.1080/01621459.1958.10501452](https://doi.org/10.1080/01621459.1958.10501452)). Also measure the share of
   deemed denials, the use of extensions and the time to a remedy. A late answer is evidence about the body, not an
   error in the model.
2. **Does the model explain what happened? (model error)**
   - *Path conformance.* Replay each case's events on the model's workflow net. lexflow already builds the net
     with pm4py (`lexflow/petri.py`), and the Legistar module shows the event-log format. Events the model cannot
     replay point to missing structure. Example: Virginia cost estimates that toll the clock, now only a gap note.
     Logs can be exported in XES ([IEEE 1849-2016](https://doi.org/10.1109/IEEESTD.2016.7740858)); for the method,
     see van der Aalst, *Process Mining* (2016), [doi:10.1007/978-3-662-49851-4](https://doi.org/10.1007/978-3-662-49851-4).
   - *Unit and anchor checks.* If "late" answers cluster exactly at the weekend count, the unit (calendar or
     business) or the anchor is probably wrong.
   - *Calendar checks.* Agencies often state their own due date in the acknowledgement. Recording that date next
     to the lab's date measures calendar errors directly: local closures, designated days, a library's missing
     holiday.

**Bias.** Self-reported cases are not a sample. People with problems report more, and lexflow users are not typical
requesters. Field experiments control the request instead. Two examples: Worthy, John, Vannoni (JPART, published
online 2016, [doi:10.1093/jopart/muw063](https://doi.org/10.1093/jopart/muw063)), and the Dutch replication by
Grimmelikhuijsen, John, Meijer, Worthy (2019, *JBPA*, [doi:10.30636/jbpa.12.34](https://doi.org/10.30636/jbpa.12.34)),
which sent 390 requests and found a 76% response rate, higher for requests framed as FOI requests. Published
figures should say "self-reported, n = …, period …, counted in <unit> by <calendar>". MuckRock's figures are a
useful comparison, but they are calendar days from filing.

**Where aggregates go.** Lexipedia process pages could show observed figures under the model, with method, n and
period. Wikibase statements should come only after review, in line with the existing rule that only reviewed
content is published. Nothing is published automatically.

## 5. How the lab ties into Setup

Following the user's instruction to "keep it referenced in the setup", the lab gets no separate top-level page at
first. It appears on the Setup page in three places, each with credits in the existing `credits.py` format next to
the step that uses them:

1. **A step "Build holiday calendars".** It generates the per-state calendars from the holiday and
   time-computation sections already in the statute store, and compares them with the `holidays` package.
   Proposed credits:
   - `used_for(OPEN_US_LAW, "Holiday and time-computation sections, with their official publisher URLs")`;
   - a new `PY_HOLIDAYS = credit("holidays", "The vacanza/holidays project", "MIT", "https://github.com/vacanza/holidays", "Cross-check only; differences are shown, the statute wins")`;
   - a new `OPM_HOLIDAYS = credit("Federal holidays", "U.S. Office of Personnel Management", "Public domain (US government work)", "https://www.opm.gov/policy-data-oversight/pay-leave/federal-holidays/", "Observed dates for federal deadlines")`.

   Each licence string must be checked against the maker's page before it is added, as the module's header
   requires.
2. **A service card "Process lab: local only".** It shows where cases are stored (the data folder), that sharing is
   **off**, and what a report would contain.
3. **"Start this process"** on model and answer pages. Each opens the case card and links back to the Setup step
   whose data it uses.

The Lexipedia plugin is a publishing concern. It belongs with the existing "Publish to Lexipedia" step, which
already credits DokuWiki and bpmnio.

## 6. Recommendations

1. **Fix the unit loss first.** Carry `business_days` through `Timer` and `<lex:deadline>`, and stop emitting
   `P5D` for 5 business days. Until that lands, the lab must compute dates from the facts (`deadline.unit`), not
   from `Timer.value`.
2. **Generate calendars from statutes.** Cover VA, DC, MD (with the two-list question flagged), TX (§ 552.0031
   rules), NY, CA, WA, NC, FL and federal, with source quotes per day. Add the AO-02-08 case and the 2026 examples
   above as tests. Keep `holidays` as a cross-check and show its differences.
3. **Extend the deadline record.** Add count rules, tolling events, conditional extensions (with an ambiguity
   flag), agency-set dates and suspensions (§3.6). Fill these for the 29 business-day deadlines first.
4. **Model a case as an event log.** Use the XES-style columns already used for Legistar, so cases replay on the
   workflow net and export to process-mining tools.
5. **Build one widget for two hosts.** The dashboard (local SQLite) and Lexipedia (IndexedDB) should run the same
   module. The case card shows the items in §2.3, with every date explained and every rule quoted.
6. **On Lexipedia, ship a native, thin `lexflowlab` plugin.** It has a syntax component and a loader
   `script.js`, with data published inline by lexflow. It has no AJAX endpoint, no server storage and no outbound
   calls. It escapes everything with `hsc()`, and keeps the bpmn.io watermark if the diagram is shown.
7. **Make export a first-class feature.** Offer a JSON case file and an `.ics` file with `VALARM` reminders, and
   ask for persistent storage. Warn Safari users about the 7-day rule.
8. **Contacts are roles, not people.** Show the office channel (the FOIA officer's office mailbox or portal, the
   oversight body), with a link to the official page for anything person-level. Fill records contacts for more
   places from official pages, and keep provenance.
9. **Sharing stays off until the user turns it on.** Each report is previewed. Defaults: quarter, buckets, body
   type, a k threshold, no free text and no logs. "Pull" aggregates need no sharing at all.
10. **Report two kinds of numbers, separately.** On-time rates (bodies) and conformance or calendar diagnostics
    (models), each labelled self-reported, with n, period and calendar version.

## 7. Open questions

- **The Setup reading.** This document reads "keep it referenced in the setup" as: the lab is reached and
  configured from the Setup page (calendar step, sharing card, credits), not given its own navigation entry.
  Confirm, or say whether the instruction meant only the lab's credits.
- **Collection.** Who, if anyone, would operate a report collector, under what terms, and with what retention?
  Alternatively, should the lab only ever *publish* aggregates the user computes from their own cases?
- **Thresholds and buckets.** What value of k, and which buckets, for agency-level publication? Small bodies may
  never reach k.
- **Unresolved law.** The Virginia B.4 extension anchor (end of day 5 or the B.4 response). Maryland's "working
  day" (legal holiday, GP § 1-111, or employee holiday, SPP § 9-201). Whether Virginia counts closure days (local
  policies say so; the FOIA Council text on this was not verified). After-hours email receipt rules in every state.
- **Unchecked statutes.** Illinois and Ohio holiday statutes (R.C. 1.14 is not in the local copy), and New York
  POL § 89 itself (not found under the tried citation forms).
- **Pages not opened.** dokuwiki.org developer pages (human check), the Texas Attorney General's catastrophe-notice
  list (402), and the NY Senate and CA leginfo pages (403). A person should read these.
- **Installation.** Installing a plugin on lexipedia.xyz is an admin action for the wiki owner.
- **Upstream reports.** Whether to report the `holidays` differences upstream (no network write was made).

## Sources

**DokuWiki (source code, read on GitHub)**

- DokuWiki release [2026-07-14c](https://github.com/dokuwiki/dokuwiki/releases/tag/release-2026-07-14c).
- Plugin base classes: [`inc/Extension/`](https://github.com/dokuwiki/dokuwiki/tree/master/inc/Extension).
- Core files:
  - [`lib/exe/js.php`](https://github.com/dokuwiki/dokuwiki/blob/master/lib/exe/js.php)
  - [`inc/Ajax.php`](https://github.com/dokuwiki/dokuwiki/blob/master/inc/Ajax.php)
  - [`inc/template.php`](https://github.com/dokuwiki/dokuwiki/blob/master/inc/template.php)
  - [`inc/common.php`](https://github.com/dokuwiki/dokuwiki/blob/master/inc/common.php)
  - [`inc/auth.php`](https://github.com/dokuwiki/dokuwiki/blob/master/inc/auth.php)
  - [`inc/defines.php`](https://github.com/dokuwiki/dokuwiki/blob/master/inc/defines.php)
  - [`conf/dokuwiki.php`](https://github.com/dokuwiki/dokuwiki/blob/master/conf/dokuwiki.php)
  - [`conf/mime.conf`](https://github.com/dokuwiki/dokuwiki/blob/master/conf/mime.conf)
  - [`inc/HTTP/DokuHTTPClient.php`](https://github.com/dokuwiki/dokuwiki/blob/master/inc/HTTP/DokuHTTPClient.php)
- Plugins: [bpmnio](https://github.com/Color-Of-Code/dokuwiki-plugin-bpmnio) (Color-Of-Code) and
  [htmlok](https://github.com/saggi-dw/dokuwiki-plugin-htmlok).
- dokuwiki.org developer documentation: **not opened** (human check).

**Web platform**

- MDN: [CORS](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/CORS),
  [iframe](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/iframe),
  [state partitioning](https://developer.mozilla.org/en-US/docs/Web/Privacy/Guides/State_Partitioning) and
  [storage quotas and eviction](https://developer.mozilla.org/en-US/docs/Web/API/Storage_API/Storage_quotas_and_eviction_criteria).
- [FastAPI CORS](https://fastapi.tiangolo.com/tutorial/cors/).
- [Chrome Local Network Access](https://developer.chrome.com/blog/local-network-access).
- [WebKit tracking-prevention post](https://webkit.org/blog/10218/full-third-party-cookie-blocking-and-more/).
- [RFC 5545](https://www.rfc-editor.org/rfc/rfc5545).

**Self-help tools and evidence**

- Tools: [California Courts Self-Help Guide](https://selfhelp.courts.ca.gov/), [Docassemble](https://docassemble.org/)
  ([security](https://docassemble.org/docs/security.html),
  [dates.py](https://github.com/jhpyle/docassemble/blob/master/docassemble_base/docassemble/base/dates.py)),
  [A2J Author (CALI FAQ)](https://www.cali.org/faq/15690), [LawHelp Interactive](https://www.lawhelpinteractive.org/),
  [Document Assembly Line](https://assemblyline.suffolklitlab.org/), [SPLC letter generator](https://splc.org/foiletter.asp),
  [RCFP Open Government Guide](https://www.rcfp.org/open-government-guide/), [MuckRock about](https://www.muckrock.com/about/)
  and [MuckRock 2017 data post](https://www.muckrock.com/news/archives/2017/mar/14/muckrock-foia-response-data/).
- Evidence and guidance: [LSC Justice Gap 2022](https://justicegap.lsc.gov/),
  [IAALS Cases Without Counsel](https://iaals.du.edu/publications/cases-without-counsel-our-recommendations-after-listening-litigants),
  [Digital.gov plain language](https://digital.gov/guides/plain-language) and Fishbane et al. 2020
  ([doi](https://doi.org/10.1126/science.abb6591)).

**Law (text read from the local open-us-law copy; links are the official publishers)**

- Virginia: [§ 1-210](https://law.lis.virginia.gov/vacode/1-210/), [§ 2.2-3300](https://law.lis.virginia.gov/vacode/2.2-3300/),
  [§ 2.2-3704](https://law.lis.virginia.gov/vacode/2.2-3704/), [§ 2.2-3704.2](https://law.lis.virginia.gov/vacode/2.2-3704.2/),
  [§ 2.2-3713](https://law.lis.virginia.gov/vacode/2.2-3713/), [§ 30-179](https://law.lis.virginia.gov/vacode/30-179/)
  and [FOIA Council AO-02-08](https://foiacouncil.dls.virginia.gov/ops/08/AO_02_08.htm).
- District of Columbia: [§ 1-612.02](https://code.dccouncil.gov/us/dc/council/code/sections/1-612.02) and
  [§ 2-532](https://code.dccouncil.gov/us/dc/council/code/sections/2-532).
- Maryland: [GP § 1-111](https://mgaleg.maryland.gov/mgawebsite/Laws/StatuteText?article=ggp&section=1-111&enactments=false),
  [GP § 4-203](https://mgaleg.maryland.gov/mgawebsite/Laws/StatuteText?article=ggp&section=4-203&enactments=false) and
  [SPP § 9-201](https://mgaleg.maryland.gov/mgawebsite/Laws/StatuteText?article=gsp&section=9-201&enactments=false).
- Texas: [Gov't Code ch. 552](https://tcss.legis.texas.gov/resources/GV/htm/GV.552.htm#552.0031) (§§ 552.0031,
  552.221, 552.2325, 552.2615, 552.301) and [ch. 662](https://tcss.legis.texas.gov/resources/GV/htm/GV.662.htm#662.003)
  (§§ 662.003, 662.013).
- Illinois: [5 ILCS 140/2](https://www.ilga.gov/ftp/ILCS/Ch%200005/Act%200140/000501400K2.html) and
  [5 ILCS 140/3](https://www.ilga.gov/ftp/ILCS/Ch%200005/Act%200140/000501400K3.html).
- Washington: [RCW 1.16.050](https://apps.leg.wa.gov/rcw/default.aspx?cite=1.16.050) and
  [RCW 1.12.040](https://apps.leg.wa.gov/rcw/default.aspx?cite=1.12.040).
- North Carolina: [§ 103-4](https://www.ncleg.gov/EnactedLegislation/Statutes/HTML/BySection/Chapter_103/GS_103-4.html)
  and [§ 103-5](https://www.ncleg.gov/EnactedLegislation/Statutes/HTML/BySection/Chapter_103/GS_103-5.html).
- Florida: [§ 683.01](http://www.leg.state.fl.us/statutes/index.cfm?App_mode=Display_Statute&Search_String=&URL=0600-0699/0683/Sections/0683.01.html).
- Ohio: [R.C. 149.43](https://codes.ohio.gov/ohio-revised-code/section-149.43).
- New York GCL §§ 24 and 25-a, and California Gov §§ 6700, 6800, 6803, 6804, 7922.535 and CCP §§ 12, 12a: read
  locally; publisher pages answered 403.
- Federal: [5 U.S.C. § 552](https://www.law.cornell.edu/uscode/text/5/552), [5 U.S.C. § 6103](https://www.law.cornell.edu/uscode/text/5/6103),
  [FRCP 6](https://www.law.cornell.edu/rules/frcp/rule_6) and [OPM federal holidays](https://www.opm.gov/policy-data-oversight/pay-leave/federal-holidays/).

**Libraries and standards**

- [`holidays` on PyPI](https://pypi.org/project/holidays/) and its
  [US calendar at commit 6486576](https://github.com/vacanza/holidays/blob/6486576f8a6f3135d9ae4e27a130250758c8de10/holidays/countries/united_states.py).
- [Flowable BPMN constructs](https://www.flowable.com/open-source/docs/bpmn/ch07b-BPMN-Constructs) and
  [OMG BPMN 2.0.2](https://www.omg.org/spec/BPMN/2.0.2/About-BPMN).
- [IETF DAP draft](https://datatracker.ietf.org/doc/draft-ietf-ppm-dap/) and
  [Prio (NSDI 2017)](https://www.usenix.org/conference/nsdi17/technical-sessions/presentation/corrigan-gibbs).

**Papers (DOIs checked on Crossref and doi.org)**

- Kleppmann et al. 2019, [10.1145/3359591.3359737](https://doi.org/10.1145/3359591.3359737).
- Erlingsson et al. 2014, [10.1145/2660267.2660348](https://doi.org/10.1145/2660267.2660348).
- Sweeney 2002, [10.1142/S0218488502001648](https://doi.org/10.1142/S0218488502001648).
- Dwork et al. 2006, [10.1007/11681878_14](https://doi.org/10.1007/11681878_14).
- Kaplan & Meier 1958, [10.1080/01621459.1958.10501452](https://doi.org/10.1080/01621459.1958.10501452).
- IEEE 1849-2016 (XES), [10.1109/IEEESTD.2016.7740858](https://doi.org/10.1109/IEEESTD.2016.7740858).
- van der Aalst 2016, [10.1007/978-3-662-49851-4](https://doi.org/10.1007/978-3-662-49851-4).
- Fishbane et al. 2020, [10.1126/science.abb6591](https://doi.org/10.1126/science.abb6591).
- Merigoux et al. 2021, [10.1145/3473582](https://doi.org/10.1145/3473582).
- Monat et al. 2024, [10.1007/978-3-031-57267-8_16](https://doi.org/10.1007/978-3-031-57267-8_16).
- Worthy et al. 2016, [10.1093/jopart/muw063](https://doi.org/10.1093/jopart/muw063).
- Grimmelikhuijsen et al. 2019, [10.30636/jbpa.12.34](https://doi.org/10.30636/jbpa.12.34).
