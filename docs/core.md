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

Give a bot user an API token from its profile page, then run:

```bash
DOKUWIKI_URL=https://lexipedia.xyz DOKUWIKI_TOKEN=... python scripts/build_all.py --publish
DOKUWIKI_TEST_URL=... DOKUWIKI_TEST_TOKEN=... python -m pytest -q   # runs the live round trip as well
```

Pages are `law:<state>:<locality>:<section>` and `process:<state>:<locality>:<section>`. Diagrams are stored as media in the process namespace and rendered with the bpmnio plugin. Step names become `[[law:…|label]]` links.

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
