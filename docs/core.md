# lexflow core: local law text to BPMN, DMN and Lexipedia pages

_This was the README of the 6 October 2026 package. The product README is [../README.md](../README.md); paths below are relative to the repository root, and the old docker/ files are replaced by the root Dockerfile and docker-compose.yml._

lexflow turns a section of a local code into a checked legal-process model and publishes it.

1. **Discover** process sections (LOCUS function labels, SearXNG, Legal Data Hunter for citations only).
2. **Fetch** the original text with its URL and date.
3. **Clean** OCR furniture and re-join split sections, with flags for anything repaired.
4. **Extract** quote-anchored facts with a local Ollama model and a JSON schema.
5. **Compile** the facts deterministically into BPMN 2.0 (with diagram layout) and DMN 1.3.
6. **Check** the result: OMG schemas, bpmnlint plus five legal rules, SpiffWorkflow runs, and Petri-net soundness, with POWL derived from the net.
7. **Publish** to DokuWiki through JSON-RPC, and to Wikibase through QuickStatements.
8. **Review** by a person.

Built and tested on 6 October 2026 against real LOCUS-v1 rows for Albemarle County Code § 17-211 and Charlottesville City Code chapter 16.

## What is verified

| Check | Result |
|---|---|
| Test suite | 46 passed (45 offline, plus 1 live round trip to a local DokuWiki) |
| BPMN and DMN schema errors, layout warnings, bpmnlint findings | 0 across all models |
| Quotes matching the code text word for word | 111 of 111 |
| Petri nets sound (pm4py) | 5 of 5 |
| Decision tables: our FEEL evaluator vs SpiffWorkflow | agree on all 334 grid inputs |

`out/report.json` holds the per-model numbers; `scripts/build_all.py` regenerates it.

**Not yet verified:** no live Ollama model has been scored. The client and its repair loop were tested against a mock server. `fixtures/gold/albemarle_17_211.facts.json` stands in for model output. `sources/locus.py:load_jurisdiction` (streaming the LOCUS parquet files) has not been run against the live dataset.

## Layout

```
lexflow/            the package
  ir.py             the model (LPIR): processes, pools, lanes, nodes, sources, decisions
  bpmn_xml.py       BPMN 2.0 writer (XSD order, DI seed, lex: extensions, Spiff/Camunda hints)
  dmn_xml.py        DMN 1.3 writer (FEEL; Python dialect for SpiffWorkflow, one decision per file)
  layout.py         diagram layout via bpmn-auto-layout 2.0.0-alpha.2
  validate.py       XSD, bpmnlint/dmnlint, legal checks (quotes, grounding, timers)
  simulate.py       SpiffWorkflow runner (+ runtime patch for nested data objects)
  feel.py, dmn_eval.py   FEEL unary tests; table evaluation, completeness and overlaps
  petri.py          BPMN -> workflow net (pm4py) -> soundness + POWL
  render_svg.py     static SVG rendering with grounding styles
  gold.py           hand-built gold models (§ 17-211, ch. 16, state judicial-review stub)
  text/             clean, re-segment, history notes, citations
  extract/          facts schema, Ollama client, compiler, scorer, SearXNG client
  sources/          LOCUS loader and triage, Legistar client and conformance
  publish/          DokuWiki JSON-RPC publisher, Wikibase QuickStatements export
tests/              46 tests
fixtures/           20 real LOCUS rows, gold facts, Albemarle Legistar sample
schemas/            OMG BPMN 2.0 and DMN 1.3 XSDs
tools/              bpmnlint-plugin-lexipedia (legal rules), node tool manifests, bpmn-js CSS
scripts/            build_all.py, build_viewer.py (+ template), fixture makers, bpmn-assistant probe
docker/             docker-compose (Ollama, SearXNG, lexflow), SearXNG settings, DokuWiki config
patches/            bpmn-assistant Ollama + targetNamespace patch; SpiffWorkflow nested data object fix
out/                generated models, Petri nets, Wikibase payloads, report.json, viewer
```

## Run it

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
(cd tools/node && npm ci --install-links)     # bpmnlint + Lexipedia rules, dmnlint, bpmn-moddle
(cd tools/node-alpha && npm ci)               # bpmn-auto-layout 2.x (keeps expanded sub-processes)
python -m pytest -q                           # 45 pass offline; the live DokuWiki test is skipped
python scripts/build_all.py                   # rebuild out/ and out/report.json
python scripts/build_viewer.py                # rebuild out/viewer/lexipedia-viewer.html
```

`graphviz` and `libcairo2` are needed for the POWL drawings and SVG-to-PNG rendering. The Dockerfile installs both.

### Search and extraction stack

```bash
cd docker && docker compose up -d ollama searxng
docker compose exec ollama ollama pull qwen3.6:27b     # or any candidate; pick by score
```

`docker/searxng/settings.yml` enables the `json` output format, which SearXNG ships disabled.

```python
from lexflow import gold
from lexflow.extract.ollama import OllamaClient, extract
from lexflow.extract.compile import compile_facts
from lexflow.extract.evaluate import score
from lexflow.extract.schema import LegalProcessFacts
from lexflow.bpmn_xml import to_bpmn_xml
from lexflow.layout import auto_layout

g = gold.albemarle_17_211()
text = g.texts[0]                                   # § 17-211 rebuilt from LOCUS rows
res = extract(OllamaClient(model="qwen3.6:27b"), text=text.text, section=text.section, title=text.title,
              code="Albemarle County Code", jurisdiction="Albemarle County, Virginia")
print(res.rounds, res.problems)                     # repair rounds used; quotes the model got wrong
gold_facts = LegalProcessFacts.model_validate_json(open("fixtures/gold/albemarle_17_211.facts.json").read())
print(score(res.facts, gold_facts, text.text))      # quote validity, step recall/precision, modality, deadlines
model = compile_facts(res.facts, model_id="va-albemarle-17-211-llm", jurisdiction=g.jurisdiction,
                      jurisdiction_name=g.jurisdiction_name, code="Albemarle County Code", text=text)
bpmn, warnings = auto_layout(to_bpmn_xml(model))
```

### Publishing to DokuWiki

The wiki needs the settings in `docker/dokuwiki/local.php.snippet`:

- `remote = 1`
- `remoteuser = @bots`. Never leave it empty, because an empty value lets everyone call the API.
- Registration disabled.
- `docker/dokuwiki/mime.local.conf`, so `.bpmn` and `.dmn` files can be uploaded.

Give a bot user an API token from its profile page (with edit rights on `lexflow:*` only), then publish the `lexflow:` pages with the publish step, a dry run first:

```bash
python -m lexflow run publish --dry-run
python -m lexflow run publish
```

lexflow writes only the `lexflow:` namespace. The publish step checks every page id before the first write, and the DokuWiki client refuses any other page or media id (`lexflow/publish/dokuwiki.py`, `require_namespace`). `scripts/build_all.py --publish`, which used to write the gold models as `law:<state>:<locality>:<section>` and `process:<state>:<locality>:<section>` pages with media, now refuses before it builds anything; `publish()` still renders those pages for the tests but refuses to write them.

Before the first real publish, the operator has two steps that lexflow does not take itself:

- **Corrections address.** Set `LEXFLOW_CORRECTIONS` in `.env` to the e-mail address or the http(s) URL readers should write to; `lexflow:method` shows it on its "Corrections:" line. Every page links `lexflow:method`, so until the check accepts it the publish step writes no page at all, a dry run included, and says why in one line of the job log. The check (`lexipedia.corrections_problem`) refuses what it knows stands for no reader: the example value from `.env.example`; names reserved for examples and tests (example.com, example.org and example.net, any `.example`, `.invalid` or `.test` name); `localhost`, `localhost.localdomain` and any `.localhost` name; IP addresses in any form, and names that point back to one (`lvh.me`, `localtest.me`, `nip.io`, `sslip.io`, `xip.io`, or a name with an address written in it); special-use and private names (`.local`, `.home.arpa`, `.internal`, `.lan`, `.home`, `.corp`, `.intranet`, `.private`, `.localdomain`, `.onion`, `.alt`); and placeholder addresses (a placeholder local part such as `user`, `name`, `foo` or `test` on a placeholder domain such as domain.com, email.com, bar.com or test.com, and "yourdomain" names as any label of the host, so `www.yourdomain.com` and `mail.yourdomain.com` too). It cannot tell whether a reader's message will reach anyone: the operator answers for that. Once it is accepted, the first line of the publish log, in a dry run too, names the address every page will send readers to. Pages rendered with `lexflow wiki-pages` show the placeholder `Corrections: <address to be set by the operator>` until then.
- **Draft items on the Wikibase.** The 26 items an earlier run loaded from single-extraction models are marked "Unreviewed draft" but are still public and searchable. Hiding them, or keeping them out of search, is done on lexipedia.wikibase.cloud by its administrator (deleting or hiding items there is not something lexflow does).

**Reviewers.** A page names a reviewer only from the list the operator of this copy keeps, in its own `reviewers` table (`lexflow/reviewers.py`). The table is not synced: push and pull take only the shared tables (`db.SYNCED`) and refuse any other, `reviewers` and `review_log` among them, before the server is reached (`turso.check_tables`, from `lexflow sync`, `lexflow run sync` and `POST /api/jobs` alike), so a pull never adds, renames or removes a reviewer. A review naming an id that is not on this copy's list counts as not reviewed, with a log line. The operator vouches for each reviewer on it: lexflow cannot check that a reviewer is a person, or their role or licence.

- `lexflow reviewer add "<name>" --role <role> [--licensed-in <state>] --added-by <operator>` puts someone on the list and prints their id and their token, once. Only the token's scrypt hash is stored, and it is compared in constant time. `lexflow reviewer token <id>` prints a new token, and the old one stops working. The role is one of `signoff.ROLES`, and `--licensed-in` is only for the attorney roles.
- The name is cleaned first (`signoff.clean_name`). It is put in NFKC form, and it must be 2 to 80 characters of letters (any script), spaces, hyphens, apostrophes and full stops. It may hold no default-ignorable code point (zero-width and bidirectional controls, the Hangul fillers U+115F, U+1160, U+3164 and U+FFA0, the Khmer inherent vowels U+17B4 and U+17B5, variation selectors and the rest of the set), and each word must be in one script (UTS #39's single-script rule, Common and Inherited characters allowed). It must hold none of the role and credential words and placeholders in `signoff.ROLE_WORDS`, `ROLE_PHRASES`, `CREDENTIALS`, `PLACEHOLDERS` and `PLACEHOLDER_WORDS`, compared through a short table of look-alike letters (`signoff.LOOKALIKE`, not the whole of Unicode's confusables list), each letter read in its own case or folded (the Cyrillic capitals "ЕЅԚ" read "esq"). A role word that is also a surname (`signoff.SURNAME_ROLE_WORDS`: Lawyer, Clerk, Staff) passes only as the surname after one given name, as in Jane Lawyer. Those lists catch only what they hold: the operator answers for every name on the list.
- A name that contains the name of an AI system or product brings a warning, and the reviewer is added only with `--confirm-person`. People are named Wenxin Li or Marie Lechat, and the check proves nothing either way.
- `lexflow reviewer list [--all]` shows the list. `lexflow reviewer remove <id>` takes someone off it; the row stays with `removed_at`, their token stops working, and their name leaves every page of this copy at the next render.

A review names a reviewer by that id, with the hash of the text they read. For a curated file, `lexflow review-hash <file>` prints the `text_hash` to put in `"reviewed_by": {"reviewer": "<id>", "date": "YYYY-MM-DD", "attested": true, "text_hash": "..."}`; keep the file's drafting note as `drafted_by`. A sign-off dated in the future, or before the model was first built, is refused. The first-built date (`first_built` in the model's metrics, `municipal/build.py`) is stored at the model's first build on this copy, from the date the drafting note opens with (not the earliest date anywhere in it), else that build's own date; a model stored by older code without one takes the earliest build its row records. Once stored it is kept: a later build, an edited drafting note or a pull (`turso.keep_first_built`) never moves it back. Whoever edits the file records that sign-off, so it is not bound to any token, and the operator answers for it. For an asked answer, the dashboard (a choice from the list and the reviewer's token) and `PUT /api/ask/<question>/<target>/review` record it. That call takes only `reviewer`, `attested` and `text_hash` in the body, and the named reviewer's own token in the `X-Lexflow-Reviewer-Token` header: a typed name, role, licence or date, or a malformed hash, is a 400; no token is a 401; a token that is no reviewer's, or another reviewer's, is a 403. `DELETE` on the same path takes the token of any reviewer on the list. `review_log` keeps whose token recorded or removed each review. A token shows only that whoever sent it had it: the operator gives each reviewer their own. A page names the reviewer, with the name, role and licence from the list, only while they are on it, the page is built from the text they signed (`lexflow/signoff.py`), and this copy recorded the review: for an asked answer, the last `review_log` entry for it is that review, with the same reviewer, text_hash and date (`reviewers.recorded`; the wiki tick and the dashboard's counts check the same); for a curated model, a place file or a researched process, this copy's own file carries the sign-off. Any other review field, pulled from another copy or written into the database by hand, counts as not reviewed, and one log line per item says so.

**The dashboard's port.** The dashboard and its API have no sign-in, so `docker-compose.yml` publishes port 8000 on `127.0.0.1` only. To reach it from other machines, put it behind your own sign-in and use the commented `ports` line. The `test-ui` dashboard (`docker compose --profile test-ui up -d test-ui`) is published on `127.0.0.1:8001` only, on a store of its own; a one-off started with `docker compose run -p 8001:8000` would publish on every interface.

**The shared database.** The bundled libSQL server (profile `shared`) has no sign-in unless sqld is given a key, so `docker-compose.yml` publishes it on `127.0.0.1` only (`LIBSQL_BIND`, default `127.0.0.1`). The shared server must not be reachable from untrusted networks: to share it, bind it to the interface of a network you control and give it a key (`SQLD_AUTH_JWT_KEY` or `SQLD_AUTH_JWT_KEY_FILE`: the Ed25519 public key that checks the JWT sent as `TURSO_AUTH_TOKEN`). A pull is trusted data only as far as that server is: whoever can write it can change what pulled rows say. A review that arrives through sync never names a reviewer here, and a state model's quote count on a page is made again against this copy's statute text when the page is made (`lexipedia.model_matched`), never read from the pulled metrics; if that text is not at hand, the page says the quotes were not matched.

### Loading the Wikibase

1. Create the eight properties in `out/wikibase/property_proposals.txt`.
2. Run `out/wikibase/<model>.phase1.qs` in QuickStatements. It creates the items, each with alias `lexflow:<key>`.
3. Map those aliases to the new Q-numbers and call `publish.wikibase.resolve()` on the phase 2 file to substitute them.
4. Run phase 2 to add the statements.

`WikibaseBot` does the same through the action API with a bot password. Strings are capped at 400 characters, so full quotes stay on DokuWiki.

## Patches

- `patches/bpmn-assistant-ollama.patch` (6 files). Adds an Ollama provider through LiteLLM that passes `format`, temperature and `num_ctx`. Adds `targetNamespace` to exported BPMN: 18 of 18 fixtures pass the XSD afterwards, against 1 of 18 before. Its 82 tests pass.
- `patches/spiffworkflow-nested-data-object.patch`. Fixes an endless loop when a data object is used inside a nested sub-process. `simulate.py` applies the same fix at runtime.

## Licences to know about

- pm4py 2.7.23.8 and powl 2.3.7 are AGPL-3.0. SpiffWorkflow is LGPL-3.0.
- The LOCUS-v1 data is CC BY-NC 4.0 and its models are Apache-2.0.
- Municode's terms forbid republishing.
- wikibase.cloud expects CC0 structured data.
- No licence has been chosen for lexflow itself yet.

None of this is legal advice. Take the licensing questions to counsel before loading LOCUS-derived data anywhere public.
