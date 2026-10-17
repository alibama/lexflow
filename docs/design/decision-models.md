# Decision models (Ollama `/v1/systemone`) in lexflow

Date: 2026-10-15. A design note with a measured benchmark. Nothing here was committed, no model was pulled by this
work, the live store and the statute index were read only, and nothing was written to the wiki.

## 1. What a Jev-style decision model is

Ollama 0.35 added "decision models", after TypeSafe's Jev API ([blog post](https://ollama.com/blog/ollama-now-supports-jev-style-decision-models)).
A chat model is asked a question and writes an answer token by token; a decision model is given a *state* (named
text fields) and a set of named, typed *questions*, and returns every answer in one forward pass with a
probability over the options. Three question types exist:

| type | criteria | answer |
|---|---|---|
| `choice` | a map of option name to description | `choice`, `probabilities` (option to probability), `confidence` |
| `noul` | none (a yes/no question) | one probability, `noul` |
| `score` | an ordered list of level names | `score` in 0..1, `legend` (index to level), `probabilities` by index, `confidence` |

The request is `POST /v1/systemone` with `{"model", "state": {field: text}, "questions": {name: {"type",
"instructions", "criteria"}}}`; the response is `{"model", "answers": {name: ...}, "usage": {"input_tokens",
"output_tokens"}}`. The output is a handful of tokens, so the cost is the prompt pass alone: the blog measures
Nimble 9B at 91 ms per decision on an M5 Max. The answers are calibrated probabilities rather than text, so a
caller can set a threshold, route the unsure cases to a person or a bigger model, and never parse JSON.

Models at launch (ollama.com/library, read 2026-10-15):

| tag | parameters | base | maker | registry size | licence on the page |
|---|---|---|---|---|---|
| `tev1:0.8b` | 0.8B | Qwen3.5 | Together AI | 834 MB (the page shows "834MB - 1.5GB" across quantisations) | none named for the weights; "dataset builders and training scripts are MIT licensed"; the model is called experimental |
| `tev1` (= `tev1:4b`) | 4B | Qwen3.5 | Together AI | 4.4-4.6 GB | as above |
| `nimble` (= `nimble:9b`) | 9B | Qwen3.5-9B | Bespoke Labs | 9.3-9.5 GB | Apache 2.0 |

Both pages list 256K context. Ollama's page says more models, and cloud-served ones, are coming. The `tev1`
models need Ollama >= 0.40.4; the main `lexflow-ollama-1` container runs 0.40.2, so a second server
(`lexflow-ollama2`, Ollama 0.40.4, sharing the model volume) was started by the operator for this work; the
client reads its address from `LEXFLOW_DECIDE_URL`.

## 2. The client: `lexflow/extract/decide.py`

- `decide(state, questions, model=None)`: `POST /v1/systemone` with a timeout and one retry (connection error,
  timeout or 5xx; a 4xx is raised at once). `state` may be a string (sent as `{"text": ...}`) or a map of named
  fields; a question may say `question` or `instructions`, and a choice's criteria may be a list of names or a
  map of name to description. Every answer comes back as `{"type", "choice", "probabilities", "confidence"}`,
  plus `probability` for `noul` and `score`/`legend` for `score`; the result also carries `usage` and `ms`.
- `backend()`: `GET /api/tags`; `decision` when a decision model is pulled (`LEXFLOW_DECIDE_MODEL`, default
  `tev1:0.8b`, else the first `tev1`/`nimble` tag), `chat` when only the fallback chat model is, `none` otherwise.
- `fallback_chat()`: the same questions put to a chat model (`qwen3:1.7b`, thinking off, temperature 0) with a
  JSON schema in `format` that lists the same options (an enum per choice or score, a boolean per noul); the same
  shape with `confidence` None and one-hot probabilities.
- `Decider`: picks the backend once, answers through a small SQLite cache keyed by (model, state hash,
  questions hash) under `LEXFLOW_DATA/cache/decide/`, and keeps call/hit/ms counts. `decide_many(rows, questions,
  concurrency=1)` batches rows (threads when `concurrency` > 1).
- Settings live in `config.py` (from `.env`): `LEXFLOW_DECIDE_URL` (default `OLLAMA_URL`), `LEXFLOW_DECIDE_MODEL`
  (default `tev1:0.8b`), `LEXFLOW_DECIDE_FALLBACK` (default `LEXFLOW_MODEL_A`, `qwen3:1.7b`) and the switch
  `LEXFLOW_DECIDE` (default 0). With the switch on, `decide.shared()` is the one `Decider` the live uses share:
  `extract/strategies.py` classifies every draft step's kind (`decide.step_kind`, state = action + clause, the
  model's choice only at confidence >= 0.8, else the verb rule; `kind_by` on the step says which) and
  `publish/graph.py` does the same for a researched local step whose file gives no kind. Topics and audiences for
  unmapped place categories are a batch (`scripts/assign_topics.py` -> `fixtures/places/topics.json`), used by the
  graph only when accepted by a person or at confidence >= 0.9 (section 5's verdict).

Tests: `tests/test_decide.py` runs a fake HTTP server for `/v1/systemone` and `/api/tags` (all three question
types, the retry, the 4xx path), the fallback against a stubbed chat client, the cache, `decide_many`, and the
mailbox task's loader.

## 3. The benchmark: `scripts/decide_bench.py`

Five tasks from lexflow's own labelled data, each with at least 100 examples and a deterministic 70/30 split by a
hash of the state text; three arms on the test split:

- **(a) rules**: the code lexflow uses today for that task.
- **(b) embed**: `nomic-embed-text` vectors (Ollama `/api/embed`), fit on the train split: kNN (k = 5, cosine,
  distance-weighted) and nearest centroid. Its per-decision time includes embedding the test text.
- **(c) decision model** through `Decider` when `backend()` finds one; otherwise **(c') the chat fallback**
  (`qwen3:1.7b` with a JSON schema), capped at 150 decisions over all tasks (30 per task, a deterministic sample
  of the test split) because it is slow. When (c') runs on a sample, the table also re-scores (a) and (b) on that
  same sample for a like-for-like line.

| task | label | state given to (b) and (c) | rule (a) |
|---|---|---|---|
| step_kind | `steps[].kind` of the 22 reviewed models (275 steps, 9 kinds) | the step's action + its source quote | `extract.strategies.kind_of` (verb lists) |
| xref_role | the role of a cross-reference in the hand-labelled gold (`fixtures/xref/gold_*.json`, 893 references, 10 roles) | the citing sentence with the reference marked `[[...]]` | `law.xref.role_of` (cue words; the rules were written while reading this gold, so (a) is in-sample) |
| topic | topic vocabulary slug of a process (142: 38 place processes through `CATEGORY_TOPIC`, 104 state models through `QUESTION_TOPIC`) | title + question | the lookup itself, which sees the category field the other arms do not: a ceiling, not a competitor |
| unit_level | unit-level slug of a statutory unit (532 unique units from 16 state indexes, 9 levels); label = `schema.unit_level(path word, act_id token)`, what the publish step writes | the unit's path element and the one above it (the act_id token, whose letter is the label's other source, is withheld from every arm) | `schema.unit_level` on the path word alone |
| mailbox | office (role-shaped) vs personal (180 synthetic addresses at RFC 2606 example domains, built from `privacy.py`'s vocabulary and placeholder surnames such as doe, bloggs, mustermann; no real address or person) | address + owning office | `privacy.mailbox_shape` (the whole-token rule) |

The unit_level and topic tasks have labels that come from lexflow's own rules, so the rule arm is at or near 100%
by construction; they measure whether a model can reproduce a vocabulary decision from text, not whether it beats
the rule. step_kind, xref_role and mailbox have labels independent of the rule (a reviewer's, the gold's, the
generator's).

### 3.1 Results

<!-- decide_bench:begin -->
Run: 2026-10-15 19:38 UTC + 2026-10-15 19:57 UTC; 5 tasks; chat-fallback budget 150 decisions in all.

| task | n test | arm | accuracy | macro-F1 | ms/decision | arm time | top confusions |
|---|---:|---|---:|---:|---:|---:|---|
| step_kind | 90 | (a) rules | 53.3 | 43.8 | 0.014 | 0.0 s | filing->act x6; record->filing x5; decision->payment x4 |
| step_kind | 90 | (b) embed kNN | 60.0 | 52.9 | 93 | 27.8 s | filing->act x7; filing->notice x5; decision->notice x4 |
| step_kind | 90 | (b') embed centroid | 62.2 | 55.8 | 93 | 27.8 s | filing->act x5; filing->notice x5; decision->notice x4 |
| step_kind | 90 | (c) decision model | 63.3 | 64.3 | 5,554 | 501.5 s | notice->filing x5; record->filing x4; act->record x4 |
| step_kind | 30 | (c') chat fallback [slow] | 43.3 | 28.3 | 3,838 | 115.6 s | filing->record x5; decision->act x2; record->filing x2 |
| step_kind | 30 | (a) rules, same sample | 46.7 | 35.2 | 0.015 | 0.0 s | record->filing x3; filing->act x3; decision->payment x2 |
| step_kind | 30 | (b) embed kNN, same sample | 53.3 | 53.9 | 93 | 27.8 s | filing->act x3; record->act x2; filing->notice x2 |
| xref_role | 264 | (a) rules | 59.1 | 57.1 | 0.167 | 0.0 s | condition->scope x18; exception->scope x11; other->scope x10 |
| xref_role | 264 | (b) embed kNN | 50.0 | 37.8 | 212 | 180.4 s | other->scope x7; exception->scope x7; scope->exception x7 |
| xref_role | 264 | (b') embed centroid | 40.2 | 39.1 | 212 | 180.4 s | scope->prerequisite_process x17; procedure->prerequisite_process x11; condition->prerequisite_process x8 |
| xref_role | 264 | (c) decision model | 28.8 | 29.6 | 5,101 | 1350.3 s | scope->definition x38; scope->procedure x18; authority->definition x10 |
| xref_role | 30 | (c') chat fallback [slow] | 30.0 | 14.5 | 6,026 | 181.1 s | scope->authority x3; prerequisite_process->authority x2; scope->condition x2 |
| xref_role | 30 | (a) rules, same sample | 66.7 | 55.0 | 0.346 | 0.0 s | authority->scope x4; exception->scope x2; scope->prerequisite_process x1 |
| xref_role | 30 | (b) embed kNN, same sample | 46.7 | 20.2 | 212 | 180.4 s | authority->scope x2; scope->exception x2; prerequisite_process->procedure x1 |
| topic | 51 | (a) rules | 100.0 | 100.0 | 0.001 | 0.0 s | - |
| topic | 51 | (b) embed kNN | 94.1 | 67.2 | 69 | 11.5 s | business->taxes x2; courts->taxes x1 |
| topic | 51 | (b') embed centroid | 92.2 | 71.0 | 69 | 11.5 s | business->taxes x3; business->animals x1 |
| topic | 51 | (c) decision model | 96.1 | 75.6 | 4,438 | 107.7 s | taxes->property x1; business->taxes x1 |
| topic | 30 | (c') chat fallback [slow] | 100.0 | 100.0 | 4,213 | 70.1 s | - |
| topic | 30 | (a) rules, same sample | 100.0 | 100.0 | 0.001 | 0.0 s | - |
| topic | 30 | (b) embed kNN, same sample | 96.7 | 92.7 | 69 | 11.5 s | business->taxes x1 |
| unit_level | 157 | (a) rules | 99.4 | 99.5 | 0.003 | 0.0 s | subtitle->none x1 |
| unit_level | 157 | (b) embed kNN | 93.0 | 90.6 | 103 | 42.4 s | chapter->act x2; division->title x1; division->chapter x1 |
| unit_level | 157 | (b') embed centroid | 89.8 | 86.8 | 103 | 42.4 s | part->division x5; chapter->act x5; chapter->section x2 |
| unit_level | 157 | (c) decision model | 71.3 | 66.0 | 4,073 | 641.7 s | title->code x36; act->code x4; act->chapter x1 |
| unit_level | 30 | (c') chat fallback [slow] | 90.0 | 88.6 | 3,598 | 108.3 s | act->chapter x2; title->part x1 |
| unit_level | 30 | (a) rules, same sample | 100.0 | 100.0 | 0.004 | 0.0 s | - |
| unit_level | 30 | (b) embed kNN, same sample | 93.3 | 90.3 | 103 | 42.4 s | division->title x1; division->chapter x1 |
| mailbox | 61 | (a) rules | 90.2 | 90.0 | 0.050 | 0.0 s | office->personal x6 |
| mailbox | 61 | (b) embed kNN | 86.9 | 86.9 | 57 | 9.6 s | personal->office x7; office->personal x1 |
| mailbox | 61 | (b') embed centroid | 93.4 | 93.4 | 57 | 9.6 s | personal->office x3; office->personal x1 |
| mailbox | 61 | (c) decision model | 47.5 | 32.2 | 1,845 | 113.3 s | personal->office x32 |
| mailbox | 30 | (c') chat fallback [slow] | 83.3 | 82.4 | 2,568 | 77.4 s | personal->office x5 |
| mailbox | 30 | (a) rules, same sample | 93.3 | 93.3 | 0.017 | 0.0 s | office->personal x2 |
| mailbox | 30 | (b) embed kNN, same sample | 83.3 | 82.9 | 57 | 9.6 s | personal->office x4; office->personal x1 |

Backend seen by `decide.backend()` at `http://lexflow-ollama2:11434`: kind `decision`, model `tev1:0.8b`; tags pulled: tev1:0.8b, qwen3:4b, nomic-embed-text:latest, gemma3:1b, qwen3:1.7b.

- **step_kind**: 275 examples (185 train / 90 test), labels filing 71, payment 28, decision 52, record 23, act 35, notice 52, inspection 8, review 2, hearing 4. Rule: `extract.strategies.kind_of`. reviewed models' steps; state = action + source quote.
  - (a) rules: extract.strategies.kind_of; n=90, accuracy 53.3, macro-F1 43.8, 0.001 s.
  - (b) embed kNN: nomic-embed-text, k=5, train n=185; n=90, accuracy 60.0, macro-F1 52.9, 27.77 s; embedding the train split took 19.43 s.
  - (b') embed centroid: nomic-embed-text, nearest centroid, train n=185; n=90, accuracy 62.2, macro-F1 55.8, 27.77 s; embedding the train split took 19.43 s.
  - (c) decision model: tev1:0.8b via /v1/systemone; n=90, accuracy 63.3, macro-F1 64.3, 501.5 s; warm-up call 15231.1 ms, left out of the timing; 5572.1 ms wall per decision including the cache.
  - (c') chat fallback [slow]: qwen3:1.7b via /api/chat + JSON schema; n=30, accuracy 43.3, macro-F1 28.3, 115.6 s; warm-up call 33852.8 ms, left out of the timing; 3853.1 ms wall per decision including the cache.
  - (a) rules, same sample: extract.strategies.kind_of; n=30, accuracy 46.7, macro-F1 35.2, 0.0 s.
  - (b) embed kNN, same sample: nomic-embed-text, k=5, train n=185; n=30, accuracy 53.3, macro-F1 53.9, 27.77 s; embedding the train split took 19.43 s.
- **xref_role**: 893 examples (629 train / 264 test), labels scope 305, prerequisite_process 76, exception 107, penalty 25, authority 81, condition 116, procedure 96, other 40, definition 26, override 21. Rule: `law.xref.role_of`. gold references with text in the index; 0 skipped (text drift or unknown role).
  - (a) rules: law.xref.role_of; n=264, accuracy 59.1, macro-F1 57.1, 0.044 s.
  - (b) embed kNN: nomic-embed-text, k=5, train n=629; n=264, accuracy 50.0, macro-F1 37.8, 180.37 s; embedding the train split took 124.27 s.
  - (b') embed centroid: nomic-embed-text, nearest centroid, train n=629; n=264, accuracy 40.2, macro-F1 39.1, 180.37 s; embedding the train split took 124.27 s.
  - (c) decision model: tev1:0.8b via /v1/systemone; n=264, accuracy 28.8, macro-F1 29.6, 1350.3 s; warm-up call 4974.0 ms, left out of the timing; 5114.6 ms wall per decision including the cache.
  - (c') chat fallback [slow]: qwen3:1.7b via /api/chat + JSON schema; n=30, accuracy 30.0, macro-F1 14.5, 181.1 s; warm-up call 4493.3 ms, left out of the timing; 6037.7 ms wall per decision including the cache.
  - (a) rules, same sample: law.xref.role_of; n=30, accuracy 66.7, macro-F1 55.0, 0.01 s.
  - (b) embed kNN, same sample: nomic-embed-text, k=5, train n=629; n=30, accuracy 46.7, macro-F1 20.2, 180.37 s; embedding the train split took 124.27 s.
- **topic**: 142 examples (91 train / 51 test), labels voting 6, business 63, animals 3, taxes 14, public-records 54, courts 2. Rule: `schema.CATEGORY_TOPIC/QUESTION_TOPIC lookup (sees the category: ceiling)`. place processes + state models; unmapped place categories left out.
  - (a) rules: schema.CATEGORY_TOPIC/QUESTION_TOPIC lookup (sees the category: ceiling); n=51, accuracy 100.0, macro-F1 100.0, 0.0 s.
  - (b) embed kNN: nomic-embed-text, k=5, train n=91; n=51, accuracy 94.1, macro-F1 67.2, 11.46 s; embedding the train split took 7.96 s.
  - (b') embed centroid: nomic-embed-text, nearest centroid, train n=91; n=51, accuracy 92.2, macro-F1 71.0, 11.46 s; embedding the train split took 7.96 s.
  - (c) decision model: tev1:0.8b via /v1/systemone; n=51, accuracy 96.1, macro-F1 75.6, 107.7 s; warm-up call 5842.7 ms, left out of the timing; 2111.3 ms wall per decision including the cache.
  - (c') chat fallback [slow]: qwen3:1.7b via /api/chat + JSON schema; n=30, accuracy 100.0, macro-F1 100.0, 70.1 s; warm-up call 4959.9 ms, left out of the timing; 2336.2 ms wall per decision including the cache.
  - (a) rules, same sample: schema.CATEGORY_TOPIC/QUESTION_TOPIC lookup (sees the category: ceiling); n=30, accuracy 100.0, macro-F1 100.0, 0.0 s.
  - (b) embed kNN, same sample: nomic-embed-text, k=5, train n=91; n=30, accuracy 96.7, macro-F1 92.7, 11.46 s; embedding the train split took 7.96 s.
- **unit_level**: 532 examples (375 train / 157 test), labels title 132, subtitle 35, chapter 168, article 48, part 65, code 24, division 12, act 36, section 12. Rule: `publish.schema.unit_level (path word only)`. unique (unit, level) pairs, <= 12 per state and level, 16 states.
  - (a) rules: publish.schema.unit_level (path word only); n=157, accuracy 99.4, macro-F1 99.5, 0.0 s.
  - (b) embed kNN: nomic-embed-text, k=5, train n=375; n=157, accuracy 93.0, macro-F1 90.6, 42.35 s; embedding the train split took 26.19 s.
  - (b') embed centroid: nomic-embed-text, nearest centroid, train n=375; n=157, accuracy 89.8, macro-F1 86.8, 42.35 s; embedding the train split took 26.19 s.
  - (c) decision model: tev1:0.8b via /v1/systemone; n=157, accuracy 71.3, macro-F1 66.0, 641.7 s; warm-up call 4907.0 ms, left out of the timing; 4087.0 ms wall per decision including the cache.
  - (c') chat fallback [slow]: qwen3:1.7b via /api/chat + JSON schema; n=30, accuracy 90.0, macro-F1 88.6, 108.3 s; warm-up call 5273.0 ms, left out of the timing; 3609.4 ms wall per decision including the cache.
  - (a) rules, same sample: publish.schema.unit_level (path word only); n=30, accuracy 100.0, macro-F1 100.0, 0.0 s.
  - (b) embed kNN, same sample: nomic-embed-text, k=5, train n=375; n=30, accuracy 93.3, macro-F1 90.3, 42.35 s; embedding the train split took 26.19 s.
- **mailbox**: 180 examples (119 train / 61 test), labels office 90, personal 90. Rule: `privacy.mailbox_shape`. synthetic: role words, pairs and initialisms vs placeholder names; example.* domains only.
  - (a) rules: privacy.mailbox_shape; n=61, accuracy 90.2, macro-F1 90.0, 0.003 s.
  - (b) embed kNN: nomic-embed-text, k=5, train n=119; n=61, accuracy 86.9, macro-F1 86.9, 9.55 s; embedding the train split took 6.07 s.
  - (b') embed centroid: nomic-embed-text, nearest centroid, train n=119; n=61, accuracy 93.4, macro-F1 93.4, 9.55 s; embedding the train split took 6.07 s.
  - (c) decision model: tev1:0.8b via /v1/systemone; n=61, accuracy 47.5, macro-F1 32.2, 113.3 s; warm-up call 1972.5 ms, left out of the timing; 1856.7 ms wall per decision including the cache.
  - (c') chat fallback [slow]: qwen3:1.7b via /api/chat + JSON schema; n=30, accuracy 83.3, macro-F1 82.4, 77.4 s; warm-up call 2728.6 ms, left out of the timing; 2581.2 ms wall per decision including the cache.
  - (a) rules, same sample: privacy.mailbox_shape; n=30, accuracy 93.3, macro-F1 93.3, 0.001 s.
  - (b) embed kNN, same sample: nomic-embed-text, k=5, train n=119; n=30, accuracy 83.3, macro-F1 82.9, 9.55 s; embedding the train split took 6.07 s.

Later run, backend seen by `decide.backend()` at `http://ollama:11434`: kind `chat`, model `qwen3:1.7b`; tags pulled: tev1:0.8b, qwen3:4b, nomic-embed-text:latest, gemma3:1b, qwen3:1.7b.
<!-- decide_bench:end -->

### 3.2 Reading the numbers

Hardware: the app container's CPU (8 threads, no GPU), Ollama 0.40.4 for `/v1/systemone` (`lexflow-ollama2`),
Ollama 0.40.2 for embeddings and the chat fallback (`lexflow-ollama-1`). `tev1:0.8b` is the Q8_0 build Ollama
serves (773M parameters, 834 MB). Every decision-model call was a cold-cache call except the duplicated topic
states (the 104 state models share 24 titles, so 29 of 599 calls hit the cache); each task's first call was a
warm-up left out of the timing.

**Speed.** The decision model took 1.8-5.6 s per decision here, growing with the prompt: a mailbox question
with one `noul` and a short state is ~1.8 s, a 9-option `choice` with descriptions and a quoted sentence
(330-440 input tokens by `usage`) is 4-5.6 s. That is the prompt pass of a 0.8B model on CPU at roughly 80
tokens/s; the blog's 91 ms is Nimble 9B on an M5 Max, where the same pass is memory-bandwidth bound on a GPU-class
part. On this machine a decision model is not a fast path; it is a *cheaper-than-chat* path only in that it
generates no output tokens and needs no JSON parsing. The rules cost microseconds; the embedding classifier
56-250 ms, nearly all of it the `nomic-embed-text` call.

**Accuracy, where the labels are independent of the rule:**

- *step_kind* (reviewer-labelled, 9 kinds): the decision model is the best arm, 63.3% / macro-F1 64.3, against
  the verb-list rule at 53.3 / 43.8 and kNN at 60.0 / 52.9. Its `confidence` is informative: at confidence >= 0.8 it
  covers 42% of the steps at 87% precision (33 right, 5 wrong), where the rule is at 53% overall.
- *xref_role* (gold-labelled, 10 roles): the decision model is the worst arm by a wide margin, 28.8% against the
  cue-word rule's 59.1% (in-sample) and kNN's 50.0%. It calls 38 `scope` references `definition` and 18
  `procedure`: a 10-way legal distinction from one sentence is beyond a 0.8B model with one-line criteria, and its
  confidence does not separate right from wrong (0.54 vs 0.40 mean; only 9 of 264 answers reach 0.8).
- *mailbox* (generator-labelled, `noul`): 47.5%, because it answers "yes, an office mailbox" for nearly every
  address: the `noul` probability lies between 0.84 and 0.99 for both classes (office median 0.975, personal
  median 0.948; AUC 0.72; the best threshold, 0.969, would give 70.5%). The whole-token rule is at 90.2% and
  nearest-centroid at 93.4%. A `noul` answer from this model is not calibrated at 0.5 for a question of this kind.

**Accuracy, where the labels come from lexflow's own vocabulary rules:**

- *topic*: 96.1% zero-shot (2 misses in 51: one `taxes` process called `property`, one `business` called
  `taxes`), against kNN's 94.1%; the lookup is 100% because it reads the category field. The point of this
  task is the 22 of 60 place processes whose category (`courts_legal`, `permits_construction`,
  `zoning_land_use`, `health_social_services`) has no entry in `CATEGORY_TOPIC` and so no topic today; the
  model would give them one. Note that kNN is flattered here by duplicated titles across the split.
- *unit_level*: 71.3%, against the path-word rule's 99.4% and kNN's 93.0%. 36 of the 45 misses are `Title N`
  called `code`: the `code` criterion's description ("a named code inside a state's collection of codes")
  pulls titles toward it. The rule needs nothing from a model here.

**Confusions** are in the table; the full predictions are in the run's JSON (`--json`).

**The chat fallback (c')**, `qwen3:1.7b` (Q4_K_M) with the same options in a JSON schema, thinking off, on a
30-example sample per task (the first 30 of the test split in hash order; the table re-scores (a) and (b) on the
same 30, and the decision model's answers for those same 30 are below):

| task (n=30) | (c') chat fallback acc / F1 | (c) decision model acc / F1 | ms per decision, (c') : (c) |
|---|---:|---:|---:|
| step_kind | 43.3 / 28.3 | 56.7 / 36.6 | 3,838 : 5,554 (0.69x) |
| xref_role | 30.0 / 14.5 | 33.3 / 19.4 | 6,026 : 5,101 (1.18x) |
| topic | 100.0 / 100.0 | 96.7 / 72.7 | 4,213 : 4,438 (0.95x) |
| unit_level | 90.0 / 88.6 | 83.3 / 72.8 | 3,598 : 4,073 (0.88x) |
| mailbox | 83.3 / 82.4 | 53.3 / 34.8 | 2,568 : 1,845 (1.39x) |

On this CPU the chat fallback is as fast as the decision model (0.7x to 1.4x of its time per decision): the
Q4 1.7B chat model's prompt pass plus a dozen output tokens costs about what the Q8 0.8B decision model's prompt
pass costs. The decision model is the more accurate of the two on step kinds and reference roles, the chat model
on unit levels and mailboxes (it reads the `noul` question as a question, where the decision model's probability
is uncalibrated), and both are at the ceiling on topics. Thirty examples is a wide interval (about +/- 9 points),
so only the step_kind and mailbox gaps are clear.

## 4. Where a decision model would plug in

Each of these is today either a regex/vocabulary rule, a chat-model call with a JSON schema, or nothing:

| place | today | as a decision | type |
|---|---|---|---|
| `publish/lint.py` person / jargon / readable checks on item labels | `qwen3:1.7b` chat, batches of 25 labels, JSON schema | one state per label, three `noul` questions (person? jargon? readable?); the probability gives the report a sort order and a threshold | noul |
| `extract/strategies.py` step kinds in the local (non-Claude) strategies | `kind_of` verb lists, then a chat repair pass | `choice` over the 9 kinds from action + quote | choice |
| `publish/graph.py` topic and audience of a process | `CATEGORY_TOPIC`/`QUESTION_TOPIC` lookups; audiences from a fixed map; unmapped categories get no topic | `choice` over `VOCAB["topic"]` and `VOCAB["audience"]` from title + question, for the categories the map does not cover | choice |
| `publish/schema.unit_level` | path word, else the act_id letter | a `choice` fallback for the paths neither covers (today logged as "no unit level") | choice |
| `law/xref.role_of` reference type | cue-word regexes, ~59% on the gold | `choice` over `ROLES` from the citing sentence, or as a second opinion where the rule's confidence is <= 0.5 | choice |
| `ask/plan.kind_of` routing of an asked question (process / facts / either) | regexes on the question | `choice` process / facts / either, and a `score` for how much the question needs a place's local law | choice, score |
| `privacy.mailbox_shape`, `is_office_phone`, `office_label` contact kinds | whole-token vocabulary rules | a `noul` "is this a person's own channel?" as a second gate: the rule stays authoritative (it refuses what it cannot account for); the model could only add refusals, never admit | noul |

The lint checks are the clearest win: they are already a model call per label, with a boolean schema, and a
decision model answers the same three questions in one pass with a probability.

## 5. Recommendation

**Go/no-go rule.** Adopt a decision model for a task only where, on at least 100 labelled examples lexflow already
holds, it (i) beats the current rule by >= 5 points of accuracy *and* of macro-F1, or (ii) matches the rule
within 2 points at >= 20x the chat fallback's measured speed; and where a `noul`/`choice` threshold has been
checked on that task's own data rather than assumed at 0.5. Re-run `scripts/decide_bench.py` for the decision
(it takes about an hour for the full test sets at this CPU's speed; `--cap-decision-model` samples).

**On today's numbers, with `tev1:0.8b` on this CPU:**

| plug-in point | verdict | why |
|---|---|---|
| local step kinds (`extract/strategies.py`) | **go, behind a flag** | +10.0 accuracy, +20.5 macro-F1 over the verb rule; confidence >= 0.8 is 87% precise, so it can replace the rule only where it is sure and leave the rest to the rule (today's rule stays the default). Cost: ~5 s per step on CPU, cached by state. |
| topic (and audience) for unmapped place categories (`publish/graph.py`) | **go, for the gap only** | 96% on the mapped categories; the lookup stays authoritative where a category is mapped. A one-off batch over the 22 unmapped processes, written to the spec's `topic` for a reviewer to accept, not a live call. |
| lint person / jargon / readable (`publish/lint.py`) | **not yet** | the same three `noul` questions the chat pass asks, but the mailbox task shows this model's `noul` is not usable at a 0.5 threshold; calibrate on a labelled sample of lint findings first (the lint report's own `person` column is the label). Expected gain is cost, not accuracy: no output tokens and no JSON parsing. |
| reference type (`law/xref.role_of`) | **no-go** | 28.8% vs 59.1%; try again only with `nimble` (9B) on the shop node. |
| unit level (`publish/schema.unit_level`) | **no-go** | the rule is at 99.4%; the model confuses titles with codes. |
| contact kind (`privacy.mailbox_shape` etc.) | **no-go** | 47.5% vs 90.2%, and the privacy rule must stay the authority in any case (a model can add refusals, never admit a channel). |
| asked-question routing (`ask/plan.kind_of`) | **untested** | no labelled set of >= 100 exists yet; AskBench's questions carry a kind and could become one. |

**Speed against the chat fallback.** Measured (section 3.2): 1.8-5.6 s per decision for `tev1:0.8b` against
2.6-6.0 s for the `qwen3:1.7b` chat fallback, a ratio between 0.7x and 1.4x, not 20x, because on CPU both are
the prompt pass of a small model (the decision model's output is zero tokens, the chat model's a dozen). Rule
(ii) is therefore not met on this machine for any task; the case for a decision model here is accuracy (step
kinds, unmapped topics) and the probability distribution it returns, not speed. On a GPU node, where the prompt
pass is cheap and output tokens are the cost, the ratio should move toward the blog's; that is unmeasured.

**Which model to pull first.** `tev1:0.8b` (834 MB, already pulled on the shared volume) is the right model for
this CPU box: it is the only one that fits the latency budget at all, and it is enough for step kinds and
topics. For the 16 GB "shop" node, `nimble` (9.3 GB, Apache 2.0, Bespoke Labs) is the one to try next: it is
the only launch model with a stated open licence, and the tasks this 0.8B model loses (reference roles, unit
levels, the `noul` calibration) are the ones a 9B model is most likely to change. `tev1:4b` (4.4 GB) is the
middle option if the shop node is shared with other models. Any pull needs the operator's approval, and the
same script with `--decision-model nimble` gives the comparison. Licence note: the Ollama pages name Apache 2.0
for `nimble` and no licence for the `tev1` weights (only MIT for the dataset builders and training scripts);
until Together AI states one, treat `tev1` as experimental and do not publish its outputs as lexflow's own
without review.

**What has to change in the stack.** `/v1/systemone` with `tev1` needs Ollama >= 0.40.4: either upgrade
`lexflow-ollama-1` or keep the second server and point `LEXFLOW_DECIDE_URL` at it. `LEXFLOW_DECIDE_URL`,
`LEXFLOW_DECIDE_MODEL` and `LEXFLOW_DECIDE_FALLBACK` should move from `decide.py` into `config.py` (not done here:
outside this task's files). The `Decider` cache under `LEXFLOW_DATA/cache/decide/` keeps a re-run free.

## 6. Open questions

1. **Hardware.** All timings are from an 8-thread CPU container. The shop node's GPU would change the speed
   verdict (rule (ii)) entirely; nothing here measures it.
2. **Calibration.** `noul` probabilities sat in 0.84-0.99 for both mailbox classes; is that this question's
   wording, this model, or `noul` in general? `confidence` meant something on step kinds and topics and nothing
   on reference roles. Both need a per-task threshold study before any threshold is relied on.
3. **Prompt design.** Criteria descriptions steer the model (the `code` description captured titles). There is
   no few-shot mechanism in the API; whether examples placed in the `state` text help is untested.
4. **API shape.** Ollama's endpoint takes `state` as one string and `criteria` as an object, which differs from
   the blog's examples; the models are labelled experimental, so the shape and the models may move. The client
   normalises both, and the tests pin the shape it sends.
5. **Bigger models.** `nimble` and `tev1:4b` are unmeasured. The losing tasks (reference roles, unit levels) are
   the ones to re-run first when one is pulled.
6. **Sample sizes.** The topic and mailbox test splits are 51 and 61 examples (about +/- 7 and +/- 6 points at
   one standard error); the fallback sample is 30 per task (+/- 9). The step_kind and xref_role numbers rest on
   90 and 264.
7. **Throughput.** Every call here was sequential (`concurrency=1`). Whether Ollama batches concurrent
   `/v1/systemone` requests, and so whether a nightly batch over thousands of steps is feasible on CPU, is
   untested.
8. **Routing task.** The asked-question routing has no labelled set yet; AskBench (`ask_bench`, 162 rows) with
   its question kinds is the natural source.
