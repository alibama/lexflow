# Laws in the shape of WikiProject Brazilian Laws: Lexipedia, Wikidata and the push plan

_22 October 2026. Code: `lexflow/publish/{schema,graph,push,lint}.py`, `lexflow/publish/wikidata_export.py`,
`lexflow/corpus/countries/japan.py` (amendments), tests `tests/test_wikidata_laws.py`. Nothing in this work wrote to
Wikidata or to the Lexipedia Wikibase: Wikidata and Lexipedia were only read (lexflow's research user agent, at most
one request a second), and every push below is a dry run. The operator runs real pushes and any Wikidata edits
under his own account._

## 1. What the Brazilian project models

Wikidata:WikiProject Brazilian Laws describes about 28,000 Brazilian federal laws and decree-laws as whole acts (no
article items): *instance of* legal act / statute (federal law, decree-law), *country*, *applies to jurisdiction*,
*publication date*, *title* (language-tagged), *legal citation of this text*, *short name*, *law digest* (the
ementa), *main subject*, *facet of*, *language of work*, *full work available at URL*, *published in* the official
gazette (qualifiers page and object named as), *approved by* (qualifiers point in time, determination method
promulgation, signatory), *legislated by*, *place of publication*, the LexML Brazil ID, and the amendment
properties *amended by*, *repealed by*, *repeals* and *overrules*, which are essentially unpopulated (an outside
analysis of 38,018 items found no *amended by* statement). References are *reference URL*, *retrieved* and *stated
in*.

## 2. Alignment: Brazilian property → Lexipedia property → who has the data

Each Lexipedia property names its Wikidata equivalent with `P7 equivalent property`: new properties through
`schema.Prop.wikidata`, the live P5–P25 through `schema.EXISTING_WIKIDATA` (written by pass 2 as the first `P7`).

| Wikidata (Brazilian items) | Lexipedia property (doc #, live P) | Japan | Australia | US |
|---|---|---|---|---|
| P31 instance of | instance of (P5) → *statutory unit*, unit level *act* | all 9,567 laws | when built | codes, units |
| P17 country / P1001 applies to jurisdiction | applies to jurisdiction (P15 ≡ P1001) | all | when built | all |
| P577 publication date | promulgation date (64 ≡ P7589): a Japanese law is promulgated by publication in the 官報 | 9,566 | assent date in the list (not mapped yet) | – |
| P1476 title | heading text (11 ≡ P1476), monolingual | 9,567 (ja) | titles (allowed, §5) | unit headings |
| P1031 legal citation of this text | citation (P22 ≡ P1031) | articles only; a law is cited by its number | – | sections |
| P1813 short name | short name (67 ≡ P1813) | 2,452 (e-Gov abbreviation) | – | – |
| P9376 law digest | law digest (68 ≡ P9376) | no digest in the source | long titles withheld (§5) | – |
| P921 main subject | topic (48 ≡ P921) | 1,566 (e-Gov category mapped) | – | processes |
| P1269 facet of | – (not modelled) | | | |
| P407 language of work | language of work (73 ≡ P407) → vocab *Japanese*/*English* | 9,567 + the code | en (when built) | not yet |
| P953 full work available at URL | official text (P23 ≡ P953) | 9,567 | when built | sections |
| P1433 published in (+ P304 page, P1932) | published in (69) + page (70) | no data: e-Gov gives no 官報 issue or page (NDL 日本法令索引 does) | – | – |
| P790 approved by (+ P585, P459 promulgation, P1891 signatory) | approved by (71): the office or body, **never a person** — lexflow does not write the Brazilian items' signatory | no data yet | – | – |
| P467 legislated by | legislated by (72) | 11,272 statements on 9,564 laws, 70 bodies (from the law's type and number, `schema.egov_makers`) | – | – |
| P291 place of publication, P5008 on focus list | – (not applicable) | | | |
| P9119 LexML Brazil ID (national id) | e-Gov law ID (65 ≡ P8610); ComLaw ID (66 ≡ P2461) | 9,567 | 4,776 listed acts | act identifier (lexflow's) |
| P8550 law identifier | law number (63 ≡ P8550), as e-Gov writes it (平成五年法律第八十八号); Wikidata writes 平成5年法律第88号 | 9,567 | – | – |
| P7588 effective date | effective date (P24 ≡ P7588): the enforcement date of the version described | 8,997 | – | sections |
| P7589 date of promulgation | promulgation date (64 ≡ P7589) | 9,566 | – | – |
| P2567 amended by | amended by (74) when the amending law has an item; amending law number (77, monolingual) when it has none | 11,821 item statements on 2,908 laws; 139,499 numbers on 7,326 laws | – | – |
| P2568 repealed by / P3148 repeals | repealed by (75) / repeals (76) | 157 / 157 | – | – |
| P4006 overrules | – (case law; not modelled) | | | |
| ref. P854 / P813 / P248 | source URL (16 ≡ P854) / retrieved (17 ≡ P813) / stated in (79 ≡ P248) → `lexflow:source:egov-laws` | every statement but lexflow's bookkeeping | stated in `lexflow:source:frl` | unchanged |
| qualifier P585 point in time | point in time (78 ≡ P585) | amendments (the amending law's promulgation) | | |

Also mapped: heading text ≡ P1476, topic ≡ P921, and the live *instance of* ≡ P31, *subclass of* ≡ P279, *part
of* ≡ P361, *has part* ≡ P527, *follows* ≡ P155, *followed by* ≡ P156, *based on* ≡ P144, *exact match* ≡ P2888,
*equivalent property* ≡ P1628. Lexipedia already had *citation*, *official text* and *effective date*, so the brief's
"legal citation", "full work available at URL" and "effective date" are those live properties with a Wikidata
equivalent rather than duplicates, and "law identifier" is the existing *law number*. Fifteen properties are new
(65–79); with 62–64 they are created by the next push's pass 1 (18 properties).

## 3. The Japanese law item

```
lexflow:unit:jpn:405ac0000000088     (no English label)   ja 行政手続法
  en description  Japanese law (Act No. 88 of 1993)         ja description 平成五年法律第八十八号（法律・行政手続）
  en alias        Act No. 88 of 1993                        ja aliases 行手法, 平成五年法律第八十八号
  instance of statutory unit; unit level act; sort key; act identifier 405AC0000000088 (lexflow's own, no reference)
  applies to jurisdiction Japan · part of Laws of Japan · e-Gov law ID 405AC0000000088 · heading text 行政手続法@ja
  law number 平成五年法律第八十八号@ja · short name 行手法@ja · official text https://laws.e-gov.go.jp/law/405AC0000000088
  effective date 2026-07-24 (the version indexed) · promulgation date 1993-11-12 · language of work Japanese
  legislated by National Diet · Wikidata item ID Q4683484 / exact match (confident reconciliation, §6)
  amending law number 平成十一年法律第百五十一号@ja  [point in time 1999-12-08]  … one per amending law without an item
  amended by <a listed law>  [point in time = its promulgation; effective date = the revision's enforcement]
  every statement above (but the bookkeeping): reference = source URL (the law's page, or the revision's page
  https://laws.e-gov.go.jp/law/<id>/<YYYYMMDD>_<amending id>), retrieved 2026-10-22, stated in e-Gov法令検索
```

* **Labels.** The `ja` label is the title. The English label is the official English title of the Japanese Law
  Translation database when lexflow has one (`title_en`; none yet), never a romanisation; without one the item has
  no English label and an English description says what it is ("Japanese law (Act No. 88 of 1993)", "Repealed
  Japanese law (…)", "… , not yet in force"). `push.labels_body` sends no empty English label; `lint` holds an item
  only when it has no label in any language, or a label in another language and no English description; duplicate
  label-and-description checks run per language (the wiki enforces them per language).
* **Makers.** `schema.EGOV_ISSUERS` maps the 70 bodies law numbers name (国会, 帝国議会, 内閣, 天皇, 太政官, the
  ministries, agencies and commissions, current and abolished) to items `lexflow:agency:jpn:<slug>` (class
  *legislature* or *government agency*) and `lexflow:position:jpn:<slug>` (the Emperor's and the Prime Minister's
  offices: offices, never office-holders). English labels are the Wikidata items' (CC0, read 22 October 2026 by their
  jawiki articles); a body with no sourced English name keeps a Japanese label only. A 法律 is the National Diet's
  from 3 May 1947 and the Imperial Diet's from 29 November 1890; earlier ones get no maker (3 laws have none).
* **Repealed and not-yet-in-force laws.** The API v2 list's 586 laws outside the bulk zip (560 repealed, 26 not in
  force) are items too, with *effective until* and *repealed by* where the list names the repealing law.
* **Limits.** At most 500 *amending law number* statements on one law, the latest kept (1,038 numbers left out,
  on the few laws such as 登記事務委任規則 with more); the largest body is 地方税法's, 759 KB with 690 statements. Dates
  before 1 January 1873 (two) are left out: e-Gov writes them in the lunar calendar of the time.

## 4. Amendments (`law_amendments`)

`python -m lexflow.corpus.countries.japan amendments` reads the bulk zip and the law list (80 s, one XML in memory at a
time; rows staged in a scratch file and copied into the lexflow database in one short transaction) into
`law_amendments(jurisdiction, law_key, amending_key, amending_num, date, kind amended|repealed|repeals, source,
date_kind, enforced, amending_title, revision, retrieved)`. Sources: each revision folder of the zip
(`egov-bulk-revision`, enforcement date), each 附則 with an `AmendLawNum` in the consolidated XML (`egov-bulk-suppl`,
the amending law's promulgation date as the attribute spells it), and the API list's current revision and repeals
(`egov-api-list`). Numbers are joined across spellings by `japan.law_num_key` (平成5年法律第88号).

| | rows | distinct edges | with an e-Gov law_id | to a law of the API list (an item) |
|---|---|---|---|---|
| amended | 167,868 | 152,356 on 7,424 laws, 66,797 amending laws | 19,222 | 11,819 |
| repealed | 427 | 427 | 427 | 157 |
| repeals (inverse) | 427 | 427 | 427 | 427 (the repealing law is listed for 157) |

Rows by source: 152,283 from 附則, 8,182 from revision folders, 7,403 + 427 + 427 from the list. 140,537 amendments are
by laws that have no entry of their own (一部改正法 folded into the laws they amend): those become *amending law
number* statements; 270 repeals are by such laws and give only *effective until*.

## 5. The licence rule (the wiki is CC0)

Lexipedia's structured data is CC0 (Wikibase Cloud requires it, §8.5). Provision text — quotes, article headings,
digests — goes to the wiki only from a source whose text is free of copyright: a US state's statutes (edicts of
government, *Georgia v. Public.Resource.Org*, 590 U.S. 255 (2020)) and Japan's laws (著作権法第十三条: "次の各号のいずれ
かに該当する著作物は、この章の規定による権利の目的となることができない。一 憲法その他の法令", read in lexflow's index on 22
October 2026). **Australia's Federal Register of Legislation is CC BY 4.0**, whose attribution and change-notice terms
a CC0 wiki cannot carry: Australian Acts go to the wiki as titles, ids (ComLaw ID) and dates only, with no section
text, heading, long title or quote. `schema.PROVISION_TEXT` lists the jurisdictions whose text may go;
`graph.Build.claim` drops *quoted text*, *quoted text in language* and *law digest* (value, qualifier or reference)
for any other jurisdiction, by the item's key or the reference's *source section*, and an Australian article item gets
no heading; every drop is counted ("provision text withheld"). A new country is text-free until it is added there.

## 6. Reconciliation with Wikidata (read-only)

`python -m lexflow.publish.wikidata_export reconcile` (≈200 requests, cached in `data/cache/wikidata/`; result in the
local table `wikidata_laws` and `out/wikidata/reconcile-report.json`). Japan: *e-GOV law ID* (P8610) equal to the
law_id; *law identifier* (P8550) equal to the number on an item of Japan or the Empire of Japan; the jawiki article
titled like the law (or `<title> (日本)`) on an item that is an instance of a legal act or statute (P31/P279*); the
Japanese label likewise (reported only). A match is **confident** when the best method finds one item, the item has
no other law's identifier or another country, and no other law finds it. Wikidata already has 1,721 P8610 and 3,245
era-style P8550 statements, and 1,721 NDL law IDs (P8635) on the same items: an earlier coordinated import.

| Japan | laws | with a Wikidata item | confident | conflicts (review) | without an item |
|---|---|---|---|---|---|
| in force (index) | 8,981 | 1,695 | 1,679 | 11 | 7,286 |
| listed (incl. repealed / not in force) | 9,567 | 1,736 | 1,717 | 14 | 7,831 |

Of the 1,679 confident items in force, these lack: P8610 13, P8550 3, P7588 211, P7589 87, P953 1,532, P2567 1,655
(1,525 of them where lexflow knows an amendment). Methods: P8610 1,671, P8550 23, label 1 (the jawiki articles found
the same items). `out/wikidata/jpn-review.json` lists the 53 doubtful matches (e-Gov ids that changed, such as
132AC0000000040 / 132AC1000000040; two items with one number; label-only hits). The 7,831 without an item are the
candidates for new items: each has an official identifier, which Wikidata generally accepts, but creating them in
bulk needs its own bot approval and community discussion (§7.2).

**United States** (small scale; English labels and aliases of the legal acts, statutes and codes of law that apply
to the state): of the 47 code items lexflow builds, 10 have a Wikidata item (lexflow's Virginia Code → Q5140088,
California Code → Q5020339, Ohio Revised Code → Q7080878, Arizona, Illinois, Nevada, New Jersey, North Carolina,
Oregon, D.C.); of 78 named acts lexflow models (unit headings ending in Act, Law or Code), 2 (California Public Records
Act → Q5020891, Illinois's Freedom of Information Act → Q104876318). No such item was found for the Virginia Freedom
of Information Act.
**Australia:** Wikidata has 16,243 ComLaw IDs (P2461); 3,798 of the 4,776 Acts in lexflow's list have an item (1,053 of
the 1,261 principal Acts; 836 of the 858 fetched so far); none has two.

## 7. QuickStatements for Wikidata, and the drafts the operator posts

`python -m lexflow.publish.wikidata_export qs` writes `out/wikidata/jpn-<property>.qs` (QuickStatements V1; a header
of `#` lines to strip with `grep -v '^#'` before pasting). Only confident matches; only where the item has no value
for the property (P2567: not that value); never a label, description or existing statement; never a new item. Every
statement: `S854` the e-Gov page, `S813` 2026-10-22, `S248` Q48746885 (e-Gov法令検索), and an edit summary.

| file | adds | statements | note |
|---|---|---|---|
| jpn-p8610.qs | e-GOV law ID | 14 | items found by their law identifier |
| jpn-p8550.qs | law identifier (平成5年法律第88号 form) | 1 | numberless "明治三十三年勅令" and 昭和二十一年憲法 are not identifiers and are skipped |
| jpn-p7589.qs | date of promulgation | 90 | dates before 1873 skipped (lunar calendar) |
| jpn-p7588.qs | effective date | 24 | only laws whose indexed revision is the original text and that no amendment touches: e-Gov gives a revision's enforcement, not the law's |
| jpn-p953.qs | full work available at URL, qualifier P407 Japanese | 1,568 | |
| jpn-p2567.qs | amended by, qualifier P585 (the amending law's promulgation) | 4,219 on 1,046 items | both laws confident on Wikidata |

### 7.1 Draft: Wikidata bot request (for the operator to post in his own words)

> **Operator:** (your account). **Bot name:** (a new account, e.g. *<you>Bot*, with a bot password limited to
> editing).
> **Task:** add missing statements to existing items about Japanese laws from e-Gov法令検索 (the Digital Agency's
> law database): e-GOV law ID (P8610), law identifier (P8550), date of promulgation (P7589), effective date (P7588,
> only for laws never amended), full work available at URL (P953) and amended by (P2567, only between two items
> that already exist). About 5,900 statements on about 1,700 items.
> **Source and licence:** e-Gov法令検索 bulk XML and Law API v2, retrieved 22 October 2026, under the Public Data
> License 1.0 (compatible with CC BY 4.0). The statements are identifiers, dates and amendment relations (facts);
> each carries *stated in* e-Gov法令検索 (Q48746885), the law's e-Gov URL and the retrieval date, which is the source
> statement PDL 1.0 asks for.
> **Matching:** an item is edited only when exactly one item carries the law's e-GOV law ID or law identifier (or,
> failing both, is the item of the law's jawiki article and an instance of a legal act or statute), carries no other
> law's identifier and no other country than Japan or the Empire of Japan. 53 doubtful matches are left for people.
> **What it never does:** create items, change labels, descriptions or aliases, add a second value, touch an
> existing statement or remove anything.
> **Code:** lexflow (github.com/alibama/lexflow), `lexflow/publish/wikidata_export.py`; the edits are QuickStatements
> batches reviewed before they run. **Test edits:** 50 on request. **Edit rate:** QuickStatements' pace.
> **Later, separately:** creating items for the ~7,800 laws without one would be a second request after discussion
> at the WikiProject below.

### 7.2 Draft: WikiProject Japanese Laws (modelled on WikiProject Brazilian Laws)

Before posting, look at the history of the items that carry P8610 and P8635 together and at WikiProject Japan for
whoever coordinated that import, and propose this with them rather than beside them.

> **Scope.** The national laws and regulations of Japan (法令) that e-Gov法令検索 lists: the Constitution, Acts
> (法律), Cabinet Orders (政令), Imperial Ordinances (勅令), ministerial ordinances (府省令), rules (規則) and Dajōkan
> proclamations; in force (8,981 on 22 October 2026) and repealed (586 more in the Law API list). One item per
> law; no item per article.
> **Data model.** P31: statute (Q820655) or the specific class — law of Japan (Q951841), Cabinet Order (Q55754272),
> ministerial decree in Japan (Q55884772), imperial ordinance in the Japanese Empire (Q67421961), Daijō-kan's
> proclamation (Q11444008). P17 and P1001 Japan (Q17; the Empire of Japan Q188712 for prewar laws). P1476 title
> (ja) and P1813 short name. Identifiers: P8610 e-GOV law ID, P8550 law identifier (平成5年法律第88号), P8635 NDL law
> ID, P13993 Japanese Law Translation ID. Dates: P7589 date of promulgation; P7588 effective date of the law (not of
> a later revision). P467 legislated by (National Diet Q202384; Imperial Diet Q704408; Cabinet of Japan Q529012;
> the ministry for an ordinance). P407 Japanese (Q5287). P953 the e-Gov URL. P2567 amended by / P2568 repealed by /
> P3148 repeals with P585. P921 main subject. Every statement referenced: P248 e-Gov法令検索 (Q48746885), P854, P813.
> **Open questions for the project.** How to record amendments by laws that have no item (most 一部改正法: an item
> each, or *amended by* "some value" with the law identifier as qualifier); whether P1433 published in 官報 with its
> issue and page should come from NDL 日本法令索引; how to give English labels (official translations only).
> **Status.** 1,736 of 9,567 laws have items; queries and the gap list from lexflow's reconciliation.

## 8. Lexipedia: putting "as much as possible" on the wiki

### 8.1 The write rate, measured

From the real pushes' logs in `/data/wikibase-push/` (first line to last write; ≈127 s of graph build and live
reads taken off, as measured on the 20 October dry run). Every write is one `wbeditentity` plus lexflow's 0.5 s pause.

| run | writes | seconds | s per write |
|---|---|---|---|
| 15 Oct, pass 1 (3,414 creates + 64 properties) | 3,478 | ≈6,090 | 1.75 |
| 16 Oct, pass 2 (4,423 replaces + property appends) | ≈4,500 | ≈4,000 | 0.89 |
| 18 Oct, pass 1 (111 creates) | 111 | ≈97 | 0.87 |
| 18 Oct, pass 2 (1,931 updates, 21 failures, 42 property appends) | ≈1,994 | ≈4,224 | 2.12 |
| **all** | **≈10,080** | **≈14,410** | **1.43 (≈2,500 writes an hour, ≈60,000 a day)** |

Those bodies were small (pass-2 median 2.3 KB). Japan's law items are larger (median 13.7 KB, mean 25 KB), so the
plan below uses 2.0 s a write for them and 1.43 s for everything else.

### 8.2 Single pass

`lexflow wikibase push --single-pass` creates a new item with its full statement set when every item it names has
an id at its turn (Kahn's order over the kind order; a cycle is broken at the item most others wait for, which is
created bare and completed in pass 2); its content hash is recorded so `--resume` skips it. The wiki ends in the same
state as with two passes. Japan's dry run: 9,502 of 9,667 creates carry every statement, and pass 2 shrinks from
9,673 writes to 171 (147 laws in amendment cycles, one vocabulary item, 23 property appends): **9,838 writes instead
of 19,340**. Tests: `tests/test_wikidata_laws.py` (one write per item, the 2-cycle, resume, two passes unchanged
without the flag, the dry-run counts).

### 8.3 Volume and time

| what | items | writes, two passes | writes, single pass | time, two passes | time, single pass |
|---|---|---|---|---|---|
| Japan: laws with amendments (dry run, §9) | 9,667 new | 19,340 | 9,838 | ≈9.2 h | ≈5.5 h |
| Japan: articles as provision items, main provisions (条 241,912 + 本則 1,198) | 243,110 | ≈486,000 | ≈243,000 | ≈8.0 days | ≈4.0 days |
| … with the 附則 articles too | 484,159 | ≈968,000 | ≈484,000 | ≈16.0 days | ≈8.0 days |
| US code units (47 codes, every level) | 109,542 | ≈219,000 | ≈110,000 | ≈3.6 days | ≈1.8 days |
| US sections | 1,676,357 | ≈3.35 M | ≈1.68 M (+ cross-reference cycles) | ≈55 days | ≈28 days |
| regulation sections (39 sets; their units not counted) | 851,889 | ≈1.70 M | ≈852,000 | ≈28 days | ≈14 days |
| Australia: Acts (titles, ComLaw IDs, dates; no text, §5) | 4,776 | 9,552 | ≈4,800 | ≈3.8 h | ≈1.9 h |
| **everything (main articles only)** | **≈2.9 M** | **≈5.8 M** | **≈2.9 M** | **≈96 days** | **≈48 days** |

Japanese articles are CC0-clean (§5) and fit the existing *statute* shape (unit level *article*, part of the law's
item, heading text in `ja`, section number, official text with the e-Gov anchor, effective date, follows); they need
a builder that walks the index (today an article becomes an item only when a process cites it). The main provisions
first; the 附則 articles are mostly amending laws' transition rules. Every row past the first needs the graph built in
batches (per state or per law range): `graph.build` holds every item in memory, which a million sections would not
fit on this PC, and the plan file would run to gigabytes.

### 8.4 What raising the rate takes

* **The bot group.** Only the operator can grant it, on his own wiki: Special:UserRights → the push account → *bot*.
  Then a bot password (Special:BotPasswords) with the *High-volume (bot) access* grant, and `push --bot` sends
  `bot=1` so the edits are marked as bot edits and kept out of recent changes. In stock MediaWiki the *bot* group
  has `apihighlimits` but not `noratelimit` (sysops and bureaucrats have that), so the edit rate limit, if Wikibase
  Cloud sets one, still applies; the measured 0.7 writes a second is latency, not a limit.
* **The pause.** `push --pause 0` (default 0.5 s) removes lexflow's own wait: about a third of each small write's
  time, so ≈0.9 s a write and ≈31 days instead of 48 for everything, if the wiki keeps answering.
* **maxlag.** Every write sends `maxlag=5`; when the database replicas lag more than 5 s the API refuses the write
  and the client waits 15 s × attempt (eight attempts). Keep it: it is what stops a bulk load from slowing the
  shared platform. One writer at a time; no parallel pushes.
* **Single pass** (§8.2) halves the writes; it is the largest gain available today.

### 8.5 Wikibase Cloud before a multi-million-item load

From the hosting policy (the draft at mediawiki.org, Wikibase/Wikibase.cloud/Hosting_policy; check the current one
at wikibase.cloud/hosting-policy before acting): new instances are temporary and need an application for long-term
hosting; the structured data must be public domain or CC0 and the licence must be stated on **Project:Copyrights**;
the main page or **Project:About** must describe the intended use; there are no fixed size or edit limits but
"decisions about size and load will be made empirically", and a size beyond what the platform can support is
disqualifying, so the application should state the planned scale (≈3 M items, ≈2,500 writes an hour for weeks) and
the purpose (open law data, a staging ground for Wikidata). Steps for the operator: (1) write Project:Copyrights
(structured data CC0; sources' terms: e-Gov PDL 1.0, US statutes public domain, Australian text excluded) and
Project:About; (2) apply for long-term hosting with the numbers above; (3) load in stages (Japan's laws, then
articles, then US units, then sections) and watch for maxlag and the reviewers' word between stages.

## 9. Dry runs (22 October 2026, in the app container)

`lexflow wikibase lint --no-ollama --states jpn`: 9,771 items in the graph, 9,649 new, **0 held** (69 s). Gaps
logged: 139,499 amendments by laws with no item; 1,038 amending law numbers over the 500 cap; 8,001 laws whose
e-Gov category has no topic; 3 laws with no maker; 2 dates before 1873; 270 repeals by laws with no item.

`lexflow wikibase push --dry-run --no-drafts --resume --states jpn`: **creates 9,667** (18 properties, 3 classes —
legislature, database, language —, 6 vocabulary items, the jurisdiction, the e-Gov source, the code, 9,567 laws, 68
bodies, 2 offices) and **updates 9,673** (9,567 laws replaced, 23 property appends …): 19,340 writes; 276 MB of
request bodies. With `--single-pass`: 9,838 writes (§8.2). Snaks dropped for want of an id: 0.

Copies on the host: `out/wikibase-jpn/` (lint report, `push-plan.two-pass.json`, `push-plan.single-pass.json`; the
276 MB bodies files stayed in the container). Run them again, and the real push, with an `--out` of their own
(`/data/wikibase-push-jpn`): a lint report covers the states it was run for, and `push --really` now refuses a push
of other states with it. For the operator's terminal:

```
lexflow wikibase lint --no-ollama --states jpn --out /data/wikibase-push-jpn
lexflow wikibase push --dry-run --no-drafts --resume --single-pass --states jpn --out /data/wikibase-push-jpn
lexflow wikibase push --really  --no-drafts --resume --single-pass --states jpn --out /data/wikibase-push-jpn
```

## 10. Open problems

* **Amendments by laws without items.** 140,537 of 152,356 amendment edges name an amending law that has no item; on
  Lexipedia they are *amending law number* strings, on Wikidata nothing yet (§7.2). Items for the 66,797 amending
  laws, from their numbers alone, would need a decision (they are real laws with official numbers).
* **The effective date of a law.** e-Gov gives the enforcement date of the version in force, not of the law; the
  original commencement is in the first 附則 as text ("公布の日から起算して…"). Lexipedia's *effective date* keeps the
  version's date (as schema §4.8 says); Wikidata gets P7588 only for laws never amended.
* **published in / approved by** have no data: e-Gov carries no 官報 issue or page (NDL 日本法令索引 does), and the
  promulgating office (the Emperor's, Constitution art. 7) would need a reference to that article.
* **English labels** need the Japanese Law Translation titles (P13993 ids): a fetch from japaneselawtranslation.go.jp
  (PDL 1.0), not done.
* **Australia** is not in `states.COUNTRIES` and has no `law` table yet (another change owns it); the graph code is
  ready for it (ComLaw ID, *stated in* the Register, the text rule) but `legislated by` (the Parliament of
  Australia) and the assent date are not mapped. US items do not carry *language of work* or *legislated by* yet.
* **The pipeline's Wikibase step** (`lexflow/pipeline/steps.py`) does not pass `--single-pass`, `--pause` or `--bot`;
  wiring them is that step's owner's.
* **A push of every state now includes Japan** (9.6k items, 276 MB): the operator may prefer `--states` for the
  first Japanese load.
* **Big pushes need a batched graph build** (§8.3).
* **jpn-review.json:** 53 matches for a person to settle (changed e-Gov ids, duplicate items on Wikidata).
* **The old QuickStatements packet** (`lexflow qs write`, `qs.py`, not changed here) writes an English label line
  for every new item; for a law with no English label it would send an empty one. The API push is the route in use.
* **Ontology equivalents** (`ontology_map.PROPERTY_EQUIV`) for the new properties (ELI `amended_by`, `repealed_by`,
  `repeals`, `passed_by`, `title_short`, `language`, `published_in`) are not added yet: each IRI should be checked
  against the ELI ontology file first, as the others were.
