# The schema-mode defect, and which Ollama calls it touches

**Date:** 2026-10-20. **Status:** fixed for the answer summary (`LEXFLOW_ASK_MODE` now defaults to `json`); every
other schema-constrained call stays on the schema, with the evidence below.

## What went wrong

The ask pipeline's summary (`lexflow/ask/answer.py`, `SUMMARY_SCHEMA`: a status and a list of cited claims) was
asked for with Ollama's grammar-guided JSON (`format` = the schema, thinking off). Under that grammar qwen3 1.7b
and qwen3 8b both answer `{"status": "not_found", "claims": []}` to every cell, whatever the quotes say: the
grammar steers a thinking model, with its reasoning turned off, to the shortest reply it allows. The same prompt
with the schema described in words and plain `format: json` (`Asker` mode `json`, `extract/strategies.py`) gives
real, cited claims from both models.

What this means for the numbers published before 20 October 2026:

- every stored summary in the coverage runs `20261017a`, `20261018b` and `20261020s` (and the `20261020g` and
  `20261020j` fills) is "not_found, no claims": the `+llm` lanes measured retrieval, quotes and steps, never a
  summary;
- the AskBench arms `local+llm@qwen3:1.7b` and `oracle+llm@qwen3:1.7b` (six Virginia cases, "no claims in 10 of
  12 runs") and `local+llmplan@qwen3:1.7b` measured retrieval only, and the "once it wrongly said the law was not
  found" was the grammar, not the model;
- the README's Known gap "qwen3:1.7b, constrained by the answer schema, gave no claims" described the defect
  without naming it.

The ask pipeline is in `json` mode by default from this date (`lexflow/config.py`, `ASK_MODE`); `schema` and
`lines` stay selectable with `LEXFLOW_ASK_MODE`. `tests/test_ask.py` pins the default and that the pipeline's,
AskBench's and the coverage fill's askers take the mode from config.

## Which other calls have the same defect

Every schema-constrained Ollama call of the extraction and ask paths was run once in each mode against the real
models with a known input (Virginia's records law, curated `va.records`, with DC's reference as the examples;
`/data/jobs/probe_modes.py`, results in `/data/jobs/probe-modes-*.json`). "schema" is the grammar; "json" is the
same prompt with the shape in words and `format: json`, think-tags stripped. Seconds are one call's wall time on
that node (local: qwen3:1.7b on the Docker Ollama 0.40.2; shop: qwen3:8b on Ollama 0.40.6, 2 cores; the 8b json
column was run while the 20261020m fill shared the node, so its seconds include queueing).

| Call (schema) | Where | qwen3:1.7b schema | qwen3:1.7b json | qwen3:8b schema | qwen3:8b json | Verdict |
|---|---|---|---|---|---|---|
| summary (`SUMMARY_SCHEMA`) | ask/answer.py | not_found, 0 claims, 13 s | answered, 3 cited claims, all verified, 13 s | not_found, 0 claims, 48 s | answered, 4 cited claims, all verified, 74 s | **switch to json** (done) |
| judge (`JUDGE_SCHEMA`, 12 tokens) | strategies.stacked_drafts (stack_llm) | 1 of 4 right (3 x true); the reply pads with tabs to the token cap | 2 of 4 (4 x false) | 2 of 4 (4 x true), 67 s | 2 of 4 (4 x true), 38 s | keep schema: neither model judges; json is no better |
| pick (`PICK_SCHEMA`) | strategies.pick_drafts (pick, pick_review) | c2, c7 with actions and enum kinds | c2, c7 but kinds "record", "action" (outside the enum) | c2, c7, enum kinds, 90 s | c2, c7, kinds inspection and act (in the enum this time), 266 s | keep schema: the enum holds only under the grammar |
| review (`REVIEW_SCHEMA`) | strategies.review (*_review) | drops 4 of 8 | drops none | drops 4 of 8, 28 s | the same 4 of 8, 29 s | keep schema: json makes the review a no-op |
| label (`LABEL_SCHEMA`) | strategies.hybrid_drafts | 1 of the 2 gold clauses a step | none | both gold clauses (and 2 fee clauses), 90 s | 1 of the 2 gold clauses (and 2 fee clauses), 1382 s with the fill running beside it | keep schema |
| select (`SELECT_SCHEMA`) | strategies.select_drafts | 13 of 17 chosen, 3 of 4 gold | 13 chosen, 4 of 4 gold | 8 chosen, 4 of 4 gold, 98 s | 8 chosen, 4 of 4 gold, 284 s | keep schema (json is a wash and loses the id list's shape) |
| plan (`PLAN_SCHEMA`) | ask/plan.py llm_groups (`+llmplan`, `+llm`) | 4 concept groups | the terms came as a list, which `llm_groups` could not split (TypeError) | 4 groups, 45 s | 4 groups, 53 s | keep schema for the shape; `llm_groups` now accepts a list, since the `+llm` arm's planner shares the json-mode asker |
| lint (`SCHEMA`, 5 items) | publish/lint.py ollama_pass | 5 of 5 verdicts right (x3 unreadable+jargon, p1 a person) | 4 of 5 answered, x3 "readable", p1 not a person | 5 of 5 right, 97 s | 4 of 5 answered, x3 "readable" and "a person", p1 not a person, 106 s | keep schema |
| decide fallback (enum schema) | extract/decide.py fallback_chat | billing, refund true, Routine, 4 s | the same, 4 s | billing, true, Urgent, 32 s | the same, 37 s | keep schema (the enum is the point) |
| oneshot facts (`ollama_schema()`) | extract/ollama.py extract | a facts object, 5 steps, 2 actors, 4 recipient problems, 700 s (14 KB) | invalid JSON (cut off mid-string), 174 s | not run (killed after 25 minutes) | not run | keep schema |

Reading: the grammar hurts exactly one call, the one whose shortest legal reply is a complete non-answer
("not_found" with an empty list). Every other schema either has no short escape (the judge must say true or false,
the enums must pick one) or the grammar is what keeps the reply usable (the enum kinds, the id list, the oneshot
object). So the rule is: a call whose schema allows a trivially short, valid reply must not be grammar-constrained
with a thinking model's reasoning turned off; the rest should be.

The judge rows are a separate finding: at 12 tokens neither model separates steps from non-steps in either mode
(1.7b says false to everything in json mode and mostly true under the grammar; 8b says true to everything), so
the `stack_llm` strategy's re-judging adds nothing on these models. That is consistent with the benchmark, where
`stack` (no chat model) is the strategy in use.

## What was re-measured

See the README's AskBench block and `docs/coverage-20261020l.json` (qwen3:1.7b on local) and
`docs/coverage-20261020m.json` (qwen3:8b on shop): the coverage fill over the same 24 cells per state, the
probe over the 12 gold cells per state, and AskBench's `local+llm@<model>` arm, all in json mode.
