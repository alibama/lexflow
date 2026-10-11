# Process lab: prototype and plan

_10 October 2026, revised the same day after [verify-lab.md](verify-lab.md), again after its re-check (the
part-day default, the summary's small groups, the office-channel checks, the outcome-table migration and the page
text), and again after its second re-check (text after a number in office values, phone values, encoded and
non-http links, two-letter initials, the page's Setup sentence). This note follows
[lab-research.md](lab-research.md). It describes the prototype now in the tree, how it would be mounted in the
dashboard (referenced from Setup, as the user asked), how a Lexipedia DokuWiki plugin would embed it, what is shared
and what never leaves the browser, and how shared outcomes would feed back into the benchmark. Nothing is mounted,
published or installed by this work. `lexflow/api/app.py`, `dashboard/app.js`, `lexflow/pipeline/steps.py`,
`lexflow/publish/*` and the wiki are unchanged. The snippets below are proposals for the owners of those files._

_Privacy and credit. Organisations, official offices and statutes only. Users of the lab are private people: nothing
about them is collected by default. Works are cited for credit only; nobody cited is a partner, advisor or endorser
of lexflow. This is information, not legal advice._

## 0. What exists now

| File | What it does |
|---|---|
| `lexflow/lab/deadlines.py` | Business-day and calendar-day arithmetic. Holiday tables for 10 states, D.C. and the federal government, each from the jurisdiction's own statute (cited in comments, with the publisher URL). It applies each table's weekend-shift rule, its roll-forward rule for a last day that falls on a weekend or holiday, and short-period rules (Md. Gen. Prov. § 1-302(c); N.Y. GCL § 20). Two tables also carry a published schedule for 2026 and 2027: California's court holidays (Cal. Rules of Court, rule 1.11, and the Judicial Council's schedule, which moves Farmworkers Day 2027 to Fri 9 Apr) and Virginia's executive days off (DHRM's Pay and Holiday Calendars: the full-day closing of Thu 24 Dec 2026, and part days off on 25 Nov 2026, 24 Nov 2027 and 23 Dec 2027). Variants give another reading where the law is open (Maryland's two holiday lists; Texas optional holidays and Friday/Monday observance; Florida's § 683.01; for Virginia, the § 1-210(E) reading of a part day off and a reading without the executive days off). A Virginia part day off is not counted as a working day by default (§5). It also has a parser for deadline rules ("5 working days", "within 10 business days of receipt", "not later than the 15th business day after …", "an additional seven work days", "15 days (except Saturdays, Sundays, and legal public holidays)"). |
| `lexflow/lab/instances.py` | The case (a JSON document the user keeps). It loads a model from the store, or from the curated file compiled in memory when the store lacks it. The steps come from the model's BPMN: flow order, lanes, boundary timers, event-gateway timers, and where a missed timer leads. They are joined by id to the facts, which keep the deadline's unit. The timeline gives the step the case is on, each deadline with its due date, how it was counted, the days skipped and why, the section, subsection and quote, other readings (each calendar reading that gives a different date, the default one included), and the status. A body's deadline is counted with the calendar's default reading; a deadline of the requester's own takes the calendar's earlier reading where it names one (Virginia: without the executive days off), with the default shown beside it. A case's status is *on time*, *overdue* or *closed*. A deadline's status is *on time*, *overdue*, *met*, *late*, *open* or *lapsed* (the user's own steps), *may apply*, or *not started*. A deemed denial is inferred when a deemed-denial deadline passes, and it starts later clocks (New York's 30-day appeal, for example). |
| `lexflow/lab/api.py` | `APIRouter(prefix="/api/lab")`, not mounted. Endpoints: `GET /models`, `GET /models/{id}/steps`, `GET /calendars/{key}`, `POST /timeline` (stateless), `GET /states/{state}/places` (every government of one state with the office channels that pass `lexflow.privacy`, so the page never sends a place; an office mailbox only once a check found it on the office's own page, which today means none), `POST /outcomes` (opt-in; exactly six fields, any other field or any query-string parameter is a 422, a cross-site request is a 403, a global rate limit gives 429; the table's creation or rebuild and the report are one `BEGIN IMMEDIATE` transaction), `GET /outcomes/summary` (cells of 10 or more reports; inside a cell, outcomes shared by fewer than 10 are pooled as "other", and if the pool itself holds fewer than 10 the smallest named outcome joins it until it holds 10 or more, so no group under 10 is shown or can be worked out; it creates nothing). The earlier `GET /places?q=` and `GET /places/{gov_id}/channels` are gone: they sent the place, and every keystroke of the search, to the server. |
| `lexflow/privacy.py` | The office-channel rules of [entities-contacts.md](entities-contacts.md) §5.2, as shape checks that keep only text they can account for: `is_office_mailbox` (the whole-token rule, with the owner's initials and name words; a label gives initials only when it starts with an office name, never when it is a person's name; an initialism needs three letters or more, since two letters are also a person's initials), `is_office_phone` (every word of the label office vocabulary or the owner's name or initials; an upper-case word is never let through on its shape; a label of line words only, such as "Phone", is refused), `office_phone_value` (the phone's value itself: shown only when nothing but office or line words stands beside the number; "434-555-0100 Jane Doe" is refused whole), `office_label` (the label of any row, dropped unless it is office or page vocabulary), `office_value` (drops every piece of an office value whose words it cannot account for, before or after a number: an "Attn:" or "c/o" piece naming a person, and a staff name anywhere else, such as after a room number, P.O. box or phone number; kept unchecked are only a street's name between a house number and a street type such as "St", and the short piece before a state and ZIP code, as the city), `is_office_url` (decodes the link first, so `%40` and `%7E` count; refuses any scheme but http and https, such as `vbscript:` and `file:`, links with an e-mail address or `~`, and staff, people or directory pages), `office_source` and `is_office_channel`. The lab's channel filter uses it; it replaces a substring regex that let personal mailboxes through. Rule 5 (a mailbox shown only once found on the office's own page) needs the check state, so the API applies it. A name made only of office or address words ("Page Law") cannot be caught by any shape check. |
| `dashboard/lab.html`, `dashboard/lab.js` | A standalone page that links `styles.css`. The user chooses a state and a process, optionally a place, starts a case, records events, and sees the current step, the deadlines, the timeline and where to send things. Choosing a state, or opening any case of that state, loads that state's list of governments and office channels once per page load (the page says so); it is loaded whether or not the case has a place, so the request does not say whether it has one. The place search and "where to send" run on that list in the browser. The holiday card lets a case set its own days: holidays the office was open, optional holidays the body observes, days it was closed, and a variant reading. They are kept in the case, in its export and import, and sent with the timeline. Cases are exported and imported as JSON, and deadlines as `.ics` with a reminder the day before. Everything is kept in `localStorage` (every access in try/catch). The user can preview and share one anonymised outcome. |
| `tests/test_lab.py` | 226 tests. They cover Virginia and California arithmetic (including the FOIA Council AO-02-08 case, the 2026 examples in lab-research.md §3.4, and the published 2026 and 2027 court and DHRM schedules day for day), the part-day decision (the re-check's 18 Nov 2026 case is not overdue on 27 Nov), the earlier reading for a requester's own deadline, the other tables' differences, parsing of every curated deadline (with a report of the ones it cannot parse), the Virginia records timeline with the B.4 default, New York's deemed-denial appeal, the per-case options through the API, the state bundle and its channel filter (mailboxes hidden without a page check; person-level links, labels, sources and office-value pieces dropped), the privacy rules' test table from entities-contacts.md §5.2 and the re-checks' cases (initials from a person's name, upper-case names, staff names in office values, a name after a room number, P.O. box, phone number or street address, phone values, encoded addresses and tildes in links, `vbscript:` and `file:` links, two-letter initials), static checks of every request `lab.js` makes and of its page text (including the Setup sentence), that this row's test count matches a fresh collection, and the router on a throwaway FastAPI app: the outcome whitelist, the random key and absent rowid, the all-or-nothing migration and the recovery of a table left by the old one, query and cross-site refusals, the rate limit, place checks, the summary's thresholds with no group under 10, and that the read endpoints change no row of any table. |

**Walkthrough (the first revision).** The page was driven in the desktop app's browser against a throwaway harness: a
local static server that forwarded `/api/lab/*` to the router through FastAPI's TestClient in the app container, on
a scratch database in the container's `/tmp` (deleted afterwards). Every API request was logged. Choosing Virginia
sent `GET /api/lab/states/va/places` once (322 governments). Typing "Charlo" in the place search sent nothing, and
City of Charlottesville was chosen from the results without a request. Choosing the Virginia records process sent
`GET /models/va.records/steps` (for the preview). Starting a case with the request sent on 21 Dec 2026 sent
`POST /timeline?today=…`, whose body held only event types, dates and the calendar options, with no place, label or
note. The deadline read Wed 30 Dec 2026 (24 and 25 Dec skipped). "Where to send" came from the list already loaded,
with no further request. Ticking Christmas Eve as a day the office was open moved the date to Tue 29 Dec; adding a
closure on 22 Dec moved it back to Wed 30 Dec; both were stored in the case, and importing a copy kept them. The
share preview showed the six fields; it was not sent (the tests cover that path). The console showed no errors, and
in the pane's mobile emulation the page was a single column with no horizontal overflow. On the real app, where
`/api/lab` is not mounted, the page says so, says a new case cannot be started until it is, and still keeps, exports
and imports cases. The second revision's page changes (the state's list loaded for every opened case, the part-day
and share-card wording, kind names for rows whose label was dropped) were checked with `node --check` and the static
tests in `tests/test_lab.py`, not driven in a browser again.

## 1. How it mounts in the dashboard: referenced from Setup

The user asked to "keep it referenced in the setup since that's where it ties in effectively". So the lab gets **no
new top-level tab** in `dashboard/index.html`. It would be reached from Setup, and from a "Start this process" link
on a model page; today neither links to it, and the page says so. Four small changes, for their owners (none is made
yet; until the first is, no case can be started):

1. **Mount the router** (`lexflow/api/app.py`, two lines; order does not matter, since `/static` is a mount):

   ```python
   from ..lab.api import router as lab_router
   app.include_router(lab_router)
   ```

   Optionally add a `/lab` route that stamps `styles.css` and `lab.js` with their mtimes, as `index()` does, so
   browsers fetch new copies. `/static/lab.html` works as is.

2. **A Setup card** (`dashboard/app.js`, `viewSetup` → `load()`, next to "Data folder"). It says where cases live
   and that sharing is off. The card links to the page and does not run a job:

   ```js
   h("a", { class: "card service", href: "/static/lab.html" },
     h("div", { class: "name" }, statusEl("optional", ""), "Process lab"),
     h("div", { class: "sub" }, "Local only · sharing off"),
     h("div", { class: "sub muted" }, "Cases stay in your browser; deadlines counted from statute calendars"))
   ```

3. **A Setup step "Holiday calendars"** (`lexflow/pipeline/steps.py`). This would be an informational step at level
   `optional`, with no `run`. Its `status` is done when `lexflow.lab.deadlines.CALENDARS` loads, and its detail reads
   "12 calendars (10 states, D.C., federal)". It carries the calendars' credits, in the existing `credits.py` format,
   next to the step that uses them. The proposal:
   - `used_for(OPEN_US_LAW, "Holiday and time-computation sections read for the calendars")`;
   - the official publishers as the source of each statute (Code of Virginia, D.C. Code, Maryland General
     Assembly, Texas Legislature, Illinois General Assembly, New York Senate, Washington Legislature, Ohio,
     California Legislative Counsel, North Carolina General Assembly, Florida Legislature);
   - the Judicial Council of California (rule 1.11 and the court holiday schedule) and the Virginia Department of
     Human Resource Management (the Pay and Holiday Calendar), for the published schedules;
   - `OPM_HOLIDAYS` for the federal observed dates.

   As `credits.py` requires, each licence string must be checked on the maker's page before it is added. This work
   checked none of them.

4. **"Start this process"** on the Processes model page (`dashboard/app.js`): a link to
   `/static/lab.html#model=va.records`. The lab reads the hash, preselects the state and process, and links back to
   Setup in its header.

The router reads the same SQLite store as the dashboard (`process_models`, `governments`, `contacts`). Its only write
is the opt-in `lab_outcomes` table, created lazily by `POST /outcomes` itself (`lexflow/store/db.py` is unchanged).

## 2. Lexipedia: a thin DokuWiki syntax plugin that loads the widget

As lab-research.md §1.6 recommends, the plugin is native and thin. It is called `lexflowlab` and has two files that
matter: `syntax.php` and `script.js`.

**Syntax.** `<lexflow-lab model="va.records" />` on a process page, and `<lexflow-lab model="va.records"
place="47210400100000" />` on a place page.

- `handle()` validates `model` against `^[a-z]{2}\.[a-z_]+$` and `place` against `^[0-9]{14}$`. It returns the
  attributes, which DokuWiki caches.
- `render('xhtml', …)` writes a mount point, escaping every value with `hsc()`:

  ```html
  <div class="lexflow-lab" data-model="va.records" data-place="…" data-src="https://LEXFLOW-HOST/static/lab-widget.js"></div>
  <div class="lexflow-lab-data" hidden>BASE64(JSON of /api/lab/models/va.records/steps and /api/lab/calendars/va)</div>
  ```

- The data block follows the bpmnio pattern (lab-research.md §1.2). lexflow's publisher would write it into the page
  with the model, so the widget needs no request to show steps, deadlines and the calendar. On a place page the
  place's office channels would be written into the same block, so the widget needs no place lookup either.

**script.js: a loader of a few lines.** DokuWiki concatenates every plugin's `script.js` into one bundle served on
every page. So the loader only checks for `.lexflow-lab` and, if one is present, adds the widget:

```js
document.querySelectorAll(".lexflow-lab").length && (() => {
  const s = document.createElement("script");
  s.type = "module"; s.src = document.querySelector(".lexflow-lab").dataset.src;
  s.integrity = "sha384-…"; s.crossOrigin = "anonymous";      // pinned to one widget version
  document.head.append(s);
})();
```

**The widget.** `lab.js` would be split into a module that exports `mount(el, {data, api})`.

- The dashboard calls `mount` with `api: "/api/lab"`.
- On Lexipedia, the plugin calls it with the inline `data` and no `api`. The counting must then run in the browser, so
  the second step of this plan is a JavaScript port of `deadlines.py` and of `instances.timeline`, about 400 lines. It
  would be tested for parity against the Python version on the cases in `tests/test_lab.py`. **A user's case is never
  posted to a public host:** `POST /timeline` carries the user's event dates, so it stays on the user's own lexflow.
- Until the port exists, a Lexipedia page can show the steps, deadlines and calendar, and offer two routes:
  - an "Open in my lexflow" link, a top-level navigation to `http://localhost:8000/static/lab.html#model=…`, which is
    not one of the request types Chrome's Local Network Access prompt covers;
  - "export case", which saves a file the dashboard imports.

**CORS settings** apply only if the widget is served from, or calls, a lexflow origin other than the wiki's:

| What | Needs | Setting |
|---|---|---|
| Widget script from a lexflow host | Module scripts and `integrity` require CORS on the script response | `Access-Control-Allow-Origin: https://lexipedia.xyz` on `/static/lab-widget.js` only |
| `GET /api/lab/models…`, `/calendars/…` | Simple GET, cross-origin read | Serve these read-only routes in a sub-application mounted at `/api/lab`, with its own `CORSMiddleware(allow_origins=["https://lexipedia.xyz"], allow_methods=["GET"], allow_credentials=False, max_age=600)`. The dashboard's own API gets no CORS and stays same-origin. They carry only a model id or a calendar key. |
| `POST /api/lab/timeline` | — | **Not exposed cross-origin and not served from a public host.** The body holds the user's event dates. On the wiki the counting runs in the browser (the port above). |
| `GET /api/lab/states/{state}/places` | — | Not needed on the wiki: a place page's channels are written into its data block. |
| `POST /api/lab/outcomes` | — | **Not exposed cross-origin.** The router already refuses a request whose `Origin` or `Sec-Fetch-Site` says it came from another site. A collector, if any, needs its own terms first (§3). |
| Calls to `http://localhost` from the public wiki | Chrome Local Network Access shows a permission prompt | Avoid. Use inline data, in-browser counting and the top-level "Open in my lexflow" link. |

**Wiki side.** No AJAX endpoint, no server-side storage, no outbound call from PHP and no cookie of the plugin's own.
The rendered HTML is the same for every visitor, so DokuWiki's render cache is safe. The HEAD response observed on
10 Oct 2026 carried no Content-Security-Policy; if one is added, `script-src` must list the lexflow host. On the wiki
the case lives in the wiki origin's `localStorage` under `lexflow-lab-cases`, which other plugins' scripts can read.
That is acceptable only because the wiki owner chooses the plugins. IndexedDB (lab-research.md §4.1) is the better
store once cases grow. Installing a plugin on lexipedia.xyz is an admin action for the wiki owner. Adding the block to
pages is a change to `lexflow/publish/lexipedia.py` for its owner. Neither was done.

## 3. What is shared, and what never leaves the browser

| Data | Where it lives | Leaves the browser? |
|---|---|---|
| The case: label, place, events, dates, notes, calendar choices | `localStorage` of the page's origin; any exported `.json` or `.ics` file | **Never**, except as a file the user saves, and the parts listed below |
| Notes on events, the label, the place | the case only | **Never.** `forServer()` in `lab.js` builds the timeline body without them; a test checks every request `lab.js` makes. |
| The place search ("Charlo…") and the "where to send" lookup | the browser, on the state's list | **Never.** There is no server endpoint that takes a place or a search. |
| The state | `GET /api/lab/states/{state}/places` (once per state per page load, when a state is chosen or any case of it is opened, with or without a place), `GET /models/{id}/steps` | Only the state (and the process) reach the user's own lexflow; the list request does not tell it whether an opened case has a place. The page says what is fetched next to the place search. uvicorn's access log records the path, so it records the state. |
| Event types, dates, step ids, an "until" date, the calendar choices (open days, observed holidays, closures, variant) | posted to `POST /api/lab/timeline` on the user's own lexflow (same machine) | Only to the user's own lexflow, which counts and keeps nothing: no table, and the access log records the request line (the path and `?today=`), not the body. A test checks that the read endpoints change no row of any table. |
| One outcome: `state`, `place` (optional, off by default, a government id only), `question`, `step`, `days_taken` (in the model's units), `outcome` (closed list of 8) | `lab_outcomes` in the local SQLite, after the user clicks *Share anonymised outcome*, sees the exact JSON and clicks *Send these six fields* | Only to the user's own lexflow. The table is `WITHOUT ROWID` and keyed by a random 128-bit value, so there is no sequential row number and the stored order is the random key's order, not arrival order. No date is kept, not even a coarse one (a conservative choice: §4's trend analysis would need a quarter, which a collector can add only with terms, §7). Rows leave the table only as summary cells. A query string or a cross-site request is refused. The table is not in `db.SYNCED`, so Turso sync never pushes it. "Save as a file instead" is offered next to "Send". |
| Never collected | names, addresses, request text, documents, event dates in outcomes, notes, device or account ids, IP addresses, cookies, analytics | — |

**Two limits that remain.** (1) `lexflow serve` writes uvicorn access logs at info level with the client address and
time. A row cannot be matched to a log line by its position any more, but anyone who can read the log and watch the
table change between two reports can still link them, so on any shared host the access log should be off or
short-lived. (2) SQLite runs in WAL mode; until a checkpoint, the write-ahead log's page images still reflect the
order of recent writes.

**Before any outcome leaves the machine** (a shared collector is an open question, §7), the report should be
coarsened as lab-research.md §4.2 recommends. That means a bucket instead of an exact `days_taken`, a quarter if trends
are wanted, body type instead of the government id unless the user opts in, batching with a random delay, and a k
threshold at publication. The prototype keeps exact days because the task fixed the six fields, and because the data
stays on the user's machine. `GET /outcomes/summary` applies k = 10 to each cell and to each outcome count inside it
(smaller counts are pooled as "other" without naming them) and never breaks out places. The pool is held to k too:
ten "answered in time" and one "denied" would otherwise show `"other": 1`, which says that exactly one report differs.
So while the pool holds between 1 and 9 reports, the smallest named outcome joins it (complementary suppression), and
that cell shows only `n = 11` and `"other": 11`. Every group shown, and every group that follows from `n` and the
others, is empty or holds at least 10 reports.

The outcome table's creation, or the rebuild of a first-prototype table, runs in the same `BEGIN IMMEDIATE`
transaction as the report: SQLite's DDL is transactional, so an interruption leaves the old table and its rows as
they were, and a second first report waits for the lock and then finds the table rebuilt. The first version renamed
the table before copying it, outside a transaction; rows of a `lab_outcomes_rowid` table left by an interrupted run
of it are moved in by the next report, and that table is dropped.

## 4. How outcomes would feed back into the benchmark

Two questions stay separate (lab-research.md §4.3):

1. **Law in action: does the body meet the statutory time?** This is an on-time share per (state, question, step),
   with time to answer in the model's own units. Cases reported as `still_open` are right-censored: a Kaplan–Meier
   curve handles them, and they are not dropped. A late answer is evidence about bodies, not an error in the model.
2. **Model error: does the model explain what happened?**
   - *Unit and anchor checks.* If `days_taken` for "answered" reports clusters at the calendar-day equivalent of the
     business-day count, the unit or the anchor is probably wrong.
   - *Path checks.* An outcome on a step the model reaches only conditionally, or many `estimate_tolled` reports on a
     model without a tolling step (Virginia today: a gap note), point to missing structure.
   - *Calendar checks.* These need the body's own stated due date, which the six fields do not carry (open question).

The proposed pipeline is a script that is not written here, since benchmark scripts belong to other workflows:

```
lab_outcomes (local or collected) ──> scripts/lab_outcomes_report.py ──> docs/lab_outcomes.json
     cells with n ≥ k only: n, outcome counts, median and KM curve per step, unit, calendar version, "self-reported"
docs/lab_outcomes.json ──> /api/benchmark (app.py already loads docs/{ceiling,learning_curve,askbench}.json; add
     "lab_outcomes" to that list) ──> a "Law in action" panel on the Benchmark page, kept apart from model scores
```

**A benchmark signal that needs no outcomes at all.** The deadline parser is a grounding check. In the curated set,
47 of 53 deadline quotes state the same amount and unit as the model's fields, and 5 state no number. One states a
different figure: California's quote gives the 14-day cap on an extension, while the fields give the 24-day outer
limit. Locally extracted models can be scored the same way, as the share of extracted deadlines whose quote parses to
the extracted amount and unit. That would make a "deadline grounding" column next to the existing benchmark metrics,
computed from `lexflow.lab.deadlines.check_deadline`.

## 5. What building it found

- **The `P5D` unit loss is in every business-day timer.** Each one is written `PnD` in the BPMN. The lab counts from
  the facts' `unit` and shows a note on each deadline. Virginia's five working days from Fri 30 Oct 2026 end on Mon
  9 Nov, not on Wed 4 Nov.
- **Virginia rolls calendar-day periods forward generally.** Va. Code § 1-210(E) lets an act due on a Saturday,
  Sunday, legal holiday or a day the office is closed be done on the next business day. That rule is broader than
  lab-research.md §3.1 reads it ("only for judicial proceedings and limitation periods"). The Virginia calendar uses
  § 1-210(E). The research note may want correcting by its owner.
- **Virginia's executive days off.** DHRM's 2026 calendar gives "8 hours additional holiday time" on Thu 24 Dec and
  "4 hours" on Wed 25 Nov. The table treats the full day as the Governor closing state government, a legal holiday
  under § 1-210(F) and § 2.2-3300's last paragraph: a request received Mon 21 Dec 2026 is due Wed 30 Dec, not Tue
  29 Dec. **Decision on the part day (revised, the conservative choice):** by default 25 Nov is *not* counted as a
  working day. The DHRM calendar grants time off without saying that offices close, but § 1-210(E) covers "part of
  a day" an office is closed, and the lab must not call a body overdue while it may still be in time (the rule it
  already applies to B.4). The first revision counted the day: a request received Wed 18 Nov 2026 was due Wed 25 Nov,
  and the body showed *overdue* on Fri 27 Nov while the § 1-210(E) reading gave Mon 30 Nov. Now the default is
  Mon 30 Nov. The § 1-210(E) reading (the part day counts, and only a period that ends on it runs on) is shown beside
  the date when it differs: 7 working days from Fri 20 Nov 2026 end Fri 4 Dec by default and Thu 3 Dec under it. The
  same applies to 24 Nov and 23 Dec 2027. A local body that stayed open all day on one of these days can mark it open
  for its case, and the date without the executive days is shown as another reading. **For a deadline of the
  requester's own** (none in the curated Virginia models today) the executive days would err late, against the
  requester, since they are set for state employees; such a deadline is counted without them (the earlier date),
  with the default beside it.
- **The Virginia B.4 extension has two dates.** The text does not say whether the seven work days run from the
  extension notice (the model's timer: Mon 16 Nov 2026 for a notice on Wed 4 Nov) or from the end of the five days
  (Thu 19 Nov). Many bodies' own notices describe 12 working days in all. **The lab now counts the body's deadline to
  the later date**, so it never calls a body overdue while it may still be in time, and shows the model's reading
  beside it; a deadline of the requester's own would take the earlier date. This is a conservative choice, not a
  reading of the statute.
- **Texas.** Columbus Day is a business day (§ 662.003 does not list it). December 24 and 26 close offices, but they
  do not extend a period, because § 662.021 makes only (b)(1)-(6) "legal holidays". Optional holidays count only if
  the body observes them; the case can say so.
- **California.** The CPRA's 10 days roll under CCP § 12a, which uses CCP § 135's judicial holidays. Those leave out
  five days that Gov. § 6700 names (Lunar New Year, Diwali, Genocide Remembrance Day, Admission Day and Columbus Day),
  and the courts observe them under rule 1.11: a Saturday holiday on the Friday before, a Sunday one on the Monday
  after. The first version applied only Gov. § 6701's narrower shifts, so Fri 3 Jul 2026 counted as a business day
  (CPRA 10 days from Tue 23 Jun 2026 gave Fri 3 Jul instead of Mon 6 Jul). The table now matches the Judicial
  Council's published schedules for 2026 and 2027, including Farmworkers Day 2027 on Fri 9 Apr (31 Mar 2027 is a
  court day). For later years a Tuesday-to-Thursday 31 March stays on its date until the schedule is published.
  Saturdays count as holidays for the roll.
- **Maryland.** Short periods (7 days or less) skip intermediate Sundays and legal holidays (§ 1-302(c)). Which
  holiday list makes a "working day" is still open, so both are computed and a differing date is shown.
- **North Carolina's § 103-4** lists days many offices are open (Greek Independence Day, the Halifax Resolves and
  others). The table counts them, conservatively for agency deadlines, and the case can mark any of them open.
- **Office channels.** The first channel filter matched role words as substrings, so made-up personal mailboxes
  passed, and it accepted any phone with any label. `lexflow/privacy.py` now applies the whole-token rule of
  entities-contacts.md §5.2. The first revision's count (7 of 9 mailboxes role-shaped, 7 of 11 phones with an office
  label) was a snapshot taken before a crawl began filling the store. Read again, read-only, later on 10 Oct 2026
  while that crawl was still writing: of the 3,216 e-mail rows on governments in the store, 1,196 are role-shaped by
  the rule and 2,020 are refused; 4 of the 5,913 phones carry an office label (the crawl's "Phone on the official
  website" names no office). **No mailbox is shown now.** Rule 5 of §5.2 shows a mailbox only once it is found on the
  office's own page; that needs `contact_status`, which does not exist yet, so the bundle hides every mailbox until a
  `page-contains` check of the last 90 days names it. The re-check also found that labels, links and office values
  were passed through unchecked, and that a label's leading words gave initials even when they were a person's name.
  Now a label gives initials only when it starts with an office name; an upper-case word in a phone label counts only
  as vocabulary or an initialism of the owner or the office named; every label is dropped unless it is office or
  page vocabulary (747 of the 5,555 page rows that pass lose their label, and the page shows "Page"); links to staff, people and directory
  pages and links with an e-mail address are left out (59 rows); and an office value loses a staff name in an Attn or
  c/o piece or anywhere else (the second re-check found that text after a number was still let through; see the next
  point). Refusals are conservative: such a number, mailbox or label is left out, and the page points to the
  government's official website.
- **Office channels, second re-check.** The words after a number in an office value were kept unchecked ("Room 200
  Jane Doe", "P.O. Box 911 Attn Jane Doe", "123 Main St Jane Doe"), phone values were shown as stored (only the
  label was checked), and `is_office_url` tested the raw link, so `%40`, `%7E`, `vbscript:` and `file:` passed. Now
  every word of an office value is checked, before and after a number, except a street's name between a house number
  and a street type ("123 Main St"); an address without a street type word ("100 Broadway") is dropped, a
  conservative loss. Office hours ("8:30 a.m. to 4:30 p.m., Monday through Friday") count as office words, and a
  run-together word is cut only into pieces of three letters or more ("Wayne" is no longer way + ne). A phone's value
  is shown only when nothing but office or line words stands beside the number; anything else refuses the whole
  value, since the number may be the named person's. Links are decoded before they are tested, and only http and
  https are accepted. **The two-letter judgement call, taken the conservative way:** an initialism needs three
  letters or more, so `cc@` for the City of Charlottesville, and "Clerk's Office - CC" as a phone label, are refused.
  Read again, read-only, on the same day (the crawl had changed the store: 1,204 e-mail, 5,929 phone, 5,593 page,
  16,502 website and 29 office rows on governments; `contact_status` still does not exist, so no mailbox is shown):
  4 mailboxes are no longer role-shaped (each only through a two-letter initialism of its owner), 2 phones are no
  longer shown (one label used the owner's two-letter "DC", and one value carried a remark beside its number), and 1
  page is left out (an encoded `~`). 5 phones, 5,567 pages (759 without their label), 16,468 websites and all 29
  office values pass. No office value lost a piece it kept before; 7 now keep their office hours, which the old
  check dropped.
- **Not read: Ohio R.C. 1.14.** It is not in the local copy, and codes.ohio.gov's robots.txt disallows scripted access,
  so Ohio's roll-forward rule is unchecked. The D.C. and Florida roll-forward rules were not checked either. These
  calendars say so in their results.
- **Parse report** (from `tests/test_lab.py`). No number is stated in D.C. `respond` and `respond_extended` (the
  quote is the deemed-denial sentence), D.C. `mayor_review`, Illinois `respond_extended`, and New York `decide_later`
  (an agency-set date). California `determine_extended` differs, as described in §4. For all of them the lab counts the
  fields and says so.

## 6. Limits and next steps

1. **Mounting and Setup.** The router is not mounted and Setup does not reference the lab yet (§1); both belong to
   the owners of `app.py`, `app.js`, `steps.py` and `credits.py`. Until the router is mounted, no case can be started.
2. **Tolling.** Virginia's cost-estimate tolling (§ 2.2-3704(F)) and federal FOIA tolling are not modelled.
   Proposal: `clock_paused` and `clock_resumed` events that shift a running deadline, plus the requester's own 30-day
   clock.
3. **History and later years.** Calendars apply current statute text to every year, so dates before 2021 are
   approximate (for example, Virginia's Lee-Jackson Day was repealed in 2020). Published schedules are carried for
   2026 and 2027 only (California courts, Virginia DHRM); other states' executive closures, and later years', must be
   recorded per case until they are added.
4. **The JavaScript port** of the counting, needed for Lexipedia (§2), with parity tests.
5. **Agency-stated dates.** Let a user record the date a body states for its own deadline, and compare it with the
   lab's date. This is the calendar check of §4.
6. **Outcomes on a shared host.** There is no authentication, only a same-origin check and a global rate limit
   (30 a minute, no per-client record). `docker-compose.yml` maps `${LEXFLOW_PORT:-8000}:8000` with no host address,
   so Docker publishes it on 0.0.0.0 and anyone on the network can reach the app; binding it to 127.0.0.1
   (`127.0.0.1:${LEXFLOW_PORT:-8000}:8000`) is for the compose file's owner.
7. **Check status.** The state bundle already hides every office mailbox until `contact_status` records that a
   check found it on the office's own page (§5.2 rule 5; `state_places` reads the table when it exists). Websites,
   pages, phones and office values are shown by their shape alone. When `contact_status` and the display policy of
   entities-contacts.md §2.2 land, the bundle should hide flagged and unchecked websites, pages and phones as other
   surfaces will, and show each value's "checked" date.
8. **The model changes** proposed in lab-research.md §3.6 (unit, count rules, tolls and extensions carried in the IR
   and BPMN) remain for the owners of `lexflow/extract/*`, `lexflow/ir.py` and `lexflow/bpmn_xml.py`.

## 7. Open questions

- **Setup.** This plan reads "keep it referenced in the setup" as a Setup card, a calendars step with its credits, and
  "Start this process" links, with no new tab. Confirm.
- **Collection.** Who, if anyone, runs a collector beyond the user's own machine, on what terms, and with what
  retention? Should exact days become buckets, and should a quarter be kept, before any report leaves the machine?
- **Thresholds.** Is k = 10 right, per cell, per outcome and for the pool? Should agency-level cells ever be
  published?
- **Unsettled law.** The Virginia B.4 anchor (the lab takes the later date). Whether a Virginia part day off closes
  the office for a count (the lab does not count it by default, and shows the § 1-210(E) date). Whether the state's
  executive days off bind a local body (the lab applies them to a body's deadline and leaves them out of a
  requester's own). Maryland's working-day list. Ohio R.C. 1.14.
  The D.C. and Florida roll-forward rules. New York's annual general election day (the table assumes one every year;
  Election Law § 8-100 was not read).

## Sources

The statutes behind each calendar are cited in the comments of `lexflow/lab/deadlines.py`, with their official
publisher URLs. They were read from lexflow's local open-us-law copy (v2026.09.1) on 10 October 2026. The DokuWiki
plugin types, the bpmnio data pattern, CORS, Chrome Local Network Access, browser storage eviction and the
outcome-privacy literature are cited in [lab-research.md](lab-research.md), which lists each source and whether it
was opened. All requests below were read-only, at most one per second, with lexflow's research User-Agent.

For the first version:
- `codes.ohio.gov/robots.txt`, to see whether R.C. 1.14 could be read. It disallows all scripted access, so it was not
  read.
- `uscode.house.gov/robots.txt`, which allows access.
- The U.S. Code page for 5 U.S.C. § 6103. It answered 200, but its body is a script shell with no statute text. The
  federal list is therefore cited from Cornell LII and OPM, as in lab-research.md.

For this revision:
- Cal. Rules of Court, rule 1.11 (`courts.ca.gov/cms/rules/index.cfm?title=one&linkid=rule1_11`): the
  Saturday-to-Friday and Sunday-to-Monday rule.
- The Judicial Council's court holidays (`courts.ca.gov/about/court-holidays`): the 2026 and 2027 schedules
  (`courts.ca.gov/holidays` answered 404).
- DHRM's home page and `dhrm.virginia.gov/payandholidaycalendar`, and the 2026 and 2027 Pay and Holiday Calendar PDFs
  linked from it.
- The California and Virginia statute texts (CCP §§ 12a, 12b, 135; Gov. §§ 6700-6703; Va. Code §§ 2.2-3300, 1-210)
  were re-read from the local open-us-law copy.
