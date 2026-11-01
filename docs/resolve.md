# Resolve: local models on the Glass Database's open Wikidata questions

The Glass Database (glassdatabase.org) moves its public record to a Wikibase, and on the way looks every staged
person, place, institution and vocabulary term up on Wikidata. Its lookup is deliberately narrow: one candidate
that passes its rules is *matched*, several are *unsure*, none is *none*. The unsure rows are a queue of small,
well-posed questions, "is this record the same thing as one of these Wikidata items?", with the candidates already
found. `lexflow/resolve` puts that queue through local models, measures how right each model is on the rows that
are already decided, writes each answer back as a suggestion the reviewer sees, and (only when told to) applies the
answers a panel of models agrees on. It runs on the same stack as everything else here: the Ollama client, the
compute pool, the `search` profile, the job runner and the dashboard.

## 1. Setup

```sh
docker compose --profile llm --profile search up -d       # Ollama and SearXNG beside the app
docker compose exec app ollama list                        # or pull from the Compute page: qwen3:8b, gemma3:12b …
```

In `.env` (everything optional; reads need nothing):

```sh
# GLASSDB_URL=https://glassdatabase.org/api
# GLASSDB_ADMIN_TOKEN=...                 # the site's API key: suggestions go back; decisions only with apply
# LEXFLOW_RESOLVE_MODELS=qwen3:8b,gemma3:12b   # the panel; default LEXFLOW_MODEL_A
# LEXFLOW_RESOLVE_THRESHOLD=0.8           # below it an answer is a suggestion, never settled
# LEXFLOW_RESOLVE_THINK=0                 # 1 lets thinking models think (slower)
# SEARXNG_URL=http://searxng:8080         # web search snippets as evidence; off when unset
```

The API key is the Glass Database's own admin token. Without it the run is a report. It is never sent anywhere
but the Glass Database, and the dashboard's apply button goes through lexflow's server, so the browser never
holds it.

## 2. The two jobs

```sh
# the open queue: one verdict per model, a consensus, suggestions written back when the token is set
docker compose exec app lexflow run resolve
docker compose exec app lexflow run resolve --models qwen3:8b,gemma3:12b --node shop
docker compose exec app lexflow run resolve --args '{"limit": 20, "kinds": "person", "no_search": true}'
# apply the settled answers (every model agrees, confidence >= apply_above, default max(threshold, 0.9))
docker compose exec app lexflow run resolve --args '{"apply": true, "apply_above": 0.95}'

# ResolveBench: the same judge on the rows already decided; writes docs/resolvebench.json
docker compose exec app lexflow run resolve-bench --models qwen3:8b,gemma3:12b
docker compose exec app lexflow run resolve-bench --args '{"status": "confirmed,rejected", "limit": 100}'
```

Both are jobs on the dashboard too (the **Resolve** page has the buttons; the **Jobs** page follows the log), and
both take `--node <name>` to pin their model calls to one node of the pool.

**What a run does, per case.**

1. Reads the record's own statements from `/api/wikibase/items/{key}` (work location, techniques, website,
   Instagram, collection, schooling …) and keeps them in `resolve_cases`.
2. Reads each candidate's Wikidata item once (`wbgetentities`: what it is, occupation, citizenship, birth and
   death years, work location, residence, education, employer, affiliation, collections, awards, website,
   Instagram, where a place is) and the lead of its English Wikipedia article; both cached in `resolve_evidence`
   for 30 days, so a second model reads exactly what the first did.
3. Asks SearXNG a query or two (`"Name" glass`; `"Name" Tacoma glass artist`) and keeps the first five hits.
4. Shows all of that to the model and asks for one JSON object: `verdict` (a candidate's Q id, `none` or
   `unsure`), `confidence` 0–1, `because`. Plain JSON mode by default: under a grammar a thinking model with its
   reasoning off drifts to the shortest legal reply, which here would be `unsure`
   (`docs/design/askbench-json-mode.md`); `"mode": "schema"` is kept for comparison.
5. Applies what the evidence settles without a model: a verdict that is not one of the candidates is no
   verdict; a person's record cannot be a non-human item and a place cannot be a person; a candidate who died
   decades before the record's Instagram account is not the maker. Those lower the confidence or turn the
   verdict to `unsure`, and the row says why.

**The consensus.** Settled when every model in the panel names the same verdict (not `unsure`) and the least
confident is at or above the threshold. Otherwise the most common non-unsure verdict is the suggestion, marked
open; a tie is `unsure`. With a token, every case's panel answer is written to the Glass Database as a
suggestion (`POST /api/wikibase/wikidata/{key}` with `{"suggest": …}`); its review page shows it beside the
candidates with the suggested one marked, and the reviewer still clicks. `apply` decides a settled case at or
above `apply_above` through the same route the reviewer's click uses, so the Glass Database records who decided.

## 3. ResolveBench: how right is each model

The gold set is what the Glass Database has already decided: a person's `confirmed` and `rejected` rows (the
trusted gold), and the lookup's own `matched` and `none` rows that had candidates to choose between (its narrow
rules are right far more often than not, and there are hundreds of them; the summary keeps the two apart). Each
model is an arm, `judge@<model>[+search][+schema]`; each case × arm row is stored with a version hash of
`lexflow/resolve/*.py`, like AskBench's rows, and `docs/resolvebench.json` keeps the current rows. Per arm:

| Number | Meaning |
|---|---|
| accuracy | how often the verdict equals the gold (`unsure` never does) |
| decided | the share of cases the arm would settle alone: a verdict other than `unsure` at or above the threshold |
| precision when decided | how often those settled answers are right: **the number that has to reach 95%** before an arm's answers are applied without a person, and then only for the cases it decides |
| human-decided accuracy | the same accuracy on the rows a person decided |
| unsure | the share the arm left open |
| seconds a case | wall time per case on the node(s) that ran it |

Read it the way AskBench is read: compare arms on the same cases, trust precision over accuracy, and rerun when
the version changes (the Resolve page says when the stored rows are from older code; the version hashes
`source.py`, `evidence.py` and `judge.py`, the code behind an answer, not the reporting). The threshold trades
coverage for precision; raise it until precision holds, then look at what is left open.

**The panel as an arm.** When two or more arms judged the same cases, the summary adds `panel(<arm>+<arm>)`:
the consensus of those arms on each case, from the stored rows and no new calls. It settles only where every
model agrees at or above the threshold, so it shows what agreement buys in precision and costs in coverage.

**First numbers (1 November 2026, the `shop` node, a laptop CPU, no web search).** On 21 rule-decided
colour and occupation terms, `qwen3:1.7b` was right 43% of the time and said 0.90 to almost everything, so its
precision when decided was 37%: it picks heraldic "or" for the colour gold and "audio technician" for
technician. `qwen3:8b` on 8 of the same cases: 63% right, 71% precision when decided, 69 seconds a case; one
of its "misses" (clear → *clear glass*) was right and the rule-decided gold wrong, which is the caveat below.
The panel of the two settled 4 of the 8 cases and was right on all 4. Far from 95%: the lever is bigger models
on a GPU node, web search on, and the panel. Nothing was applied.

## 4. More compute

Every model call goes through the compute pool (`docs/compute.md`). Name the panel's models, and each call is
sent to a node that has the model and a free slot; the bench fans the models out over the pool's free slots, and
the live run judges a case's panel in parallel. Adding a machine is one entry in `LEXFLOW_LLM_NODES`
(`name=url|threads=N|max=1|models=qwen3:8b`) or a peer in the overlay's compute group; nothing in `lexflow/resolve`
changes. A node that sleeps costs a retry on another, not a failed run.

## 5. Tables

`resolve_cases` (the queue and gold rows, their statements, when fetched), `resolve_evidence` (Wikidata and
Wikipedia facts per candidate, search hits per query, with a fetch time), `resolve_bench` (case × arm rows),
`resolve_queue` (the live run's last conclusion per case, the panel's verdicts, when a suggestion went back and
when an answer was applied). All local to this copy; nothing is synced.

## 6. Checks before trusting it

* Run the bench before the first live run with `apply`, on the human-decided rows if there are enough
  (`"status": "confirmed,rejected"`), and read the open rows on the Resolve page: the `because` lines say what
  the model took as evidence.
* The Wikidata and Wikipedia reads are public and paced; SearXNG's engines have their own terms (the `search`
  profile is the same unmodified service the Ask page uses).
* The lookup's `matched` rows are rules, not truth: a bench row where every model disagrees with a rule-decided
  gold is worth a look at the gold.
