# Compute: more than one model server

Lexflow's model calls (extraction, AskBench, answering new questions, the coverage test and its `--fill`, the
Wikibase lint) go through one Ollama client. With nothing configured they go to `OLLAMA_URL`, as they always did.
Set `LEXFLOW_LLM_NODES` and the same calls go through a small **pool**: each call is sent to a node that has the
model and a free slot; when a node drops out, its work moves to another; every call is logged with its node,
model, tokens and durations; and the **Compute** page of the dashboard shows the nodes, what is loaded, how fast
each one reads and writes, and what ran where. The design is in `docs/design/compute-tailnet.md` §3 and the
overlay in `docs/design/open-overlay.md` §3.5; this page is the operator's runbook.

Everything the pool keeps lives in `data/compute.db`, this copy's own file. It is never synced (Turso sees only
`lexflow.db`), so node names and addresses stay on this machine.

## 1. Setup

In `.env` (all optional; see `.env.example`):

```sh
# name=url, then |options.  Names are [a-z0-9-]{1,20}.
LEXFLOW_LLM_NODES=local=http://ollama:11434|embed, ollama2=http://lexflow-ollama2:11434, shop=http://100.98.35.19:11434|threads=7|max=1
# LEXFLOW_EMBED_URL=http://ollama:11434     # the one node that embeds (default: the node marked |embed, else the first)
# LEXFLOW_LLM_WAIT=900                      # seconds a call waits for a free slot before the job fails
# LEXFLOW_LLM_POLL=15                       # seconds between health checks of an online node
# LEXFLOW_LLM_FANOUT=4                      # most worker threads a batch (the extraction benchmark) fans out over
```

Options per node: `threads=N` (sent as Ollama's `num_thread`; leave a core for the desktop on a laptop), `max=N`
(calls at once; match the node's `OLLAMA_NUM_PARALLEL`, and keep 1 on a CPU node), `status=URL` (the node's
host-status JSON: CPU, RAM, load, temperature, shown on its card), `embed` (this node embeds), `models=a+b` (the
models wanted there: the card flags any not pulled), `tags=cpu+gpu`, `priority=0..100`, `part_time`.

**The allow-list.** A node URL must be `http(s)` to a compose service name (`ollama`, `lexflow-ollama2`),
`localhost` / `host.docker.internal`, an address in `100.64.0.0/10` (Tailscale), `10.231.0.0/16` (the planned
NetBird range), `fd7a:115c:a1e0::/48`, or a `*.ts.net` / `*.mesh.lexipedia.xyz` name. Anything else is refused
with a line in the server log and a note on the Compute page, so a typo never sends statute text to a public host.
Nothing discovers nodes: they come from `.env` or the overlay (§3), never from the dashboard.

Restart the app after changing `.env` (`docker compose up -d app`). The API then starts a poller that checks each
node every `LEXFLOW_LLM_POLL` seconds (`GET /api/version`, `/api/tags`, `/api/ps`, the status URL): all read-only,
nothing is ever written to a node. A node that fails backs off (30 s, 1 min, 2 min ... 15 min); after five
failures it is `offline` and checked every two minutes; one good check restores it. A CLI-only run with no API
process re-checks a node itself when its last check is over a minute old.

From the command line: `lexflow compute nodes` lists the nodes and their last check; `lexflow compute check`
probes them now.

## 2. Joining a node

A node is any machine running Ollama that this box can reach on one of the allowed addresses.

1. Install Ollama from its official source on the node and pull the models you want there (`ollama pull qwen3:8b`).
   Lexflow never pulls on its own: the Compute page's **Pull a model** runs a `models` job that you start, says how
   many GB it downloads, and shows progress in the job's log.
2. Make Ollama listen on the overlay address only (`OLLAMA_HOST=<tailnet-or-netbird-ip>:11434`), with the LAN
   interface closed; `OLLAMA_NUM_PARALLEL=1` on a CPU node; `OLLAMA_KEEP_ALIVE=10m`. `compute-tailnet.md` §4.3 has
   the full outline for `shop`, including the stay-awake settings for a laptop.
3. Optional: the host-status endpoint (`compute-tailnet.md` §4.4, `deploy/lexflow-node/`), standard library only,
   on port 9101. With it the card shows CPU, RAM, load, temperature and battery, and a pull is refused when the
   model plus 3 GB is more than the node's RAM unless you confirm.
4. Add the node to `LEXFLOW_LLM_NODES` and restart the app. Its card appears on the Compute page; **Check now**
   probes it at once.

Each node's `nomic-embed-text` must be the same build as the embed node's: the embedding cache
(`data/cache/embed-*.jsonl`) is keyed by model name and text, so vectors from another build would mix in. That is
why embeddings always go to one node (`LEXFLOW_EMBED_URL`, or the node marked `|embed`, or the first).

## 3. The overlay as the node list

Instead of writing the list by hand, `LEXFLOW_OVERLAY=netbird` reads it from the NetBird management API
(`docs/design/open-overlay.md` §3.5 and its runbook):

```sh
LEXFLOW_OVERLAY=netbird                       # netbird | headscale | none (= LEXFLOW_LLM_NODES alone)
LEXFLOW_OVERLAY_URL=https://net.lexipedia.xyz:8443
LEXFLOW_OVERLAY_TOKEN=<personal access token of a read-only service user>
LEXFLOW_OVERLAY_COMPUTE_GROUP=compute
LEXFLOW_OVERLAY_RANGE=10.231.0.0/16
LEXFLOW_OVERLAY_POLL=60
```

Every `LEXFLOW_OVERLAY_POLL` seconds the poller does `GET {URL}/api/peers` with `Authorization: Token ...` (read
only; the browser never talks to the overlay) and keeps the peers whose groups include the compute group. Each
becomes a node named after its `dns_label` at `http://<peer ip>:11434`, with the status URL on port 9101, and its
`connected` flag sets the online state without a request. A peer whose address is outside the range, or whose name
is not `[a-z0-9-]{1,20}`, is skipped with a log line. A peer that leaves the group takes no new work and is deleted
once its calls finish. Settings you changed on the page (drain, threads, slots) survive every re-read.
`headscale` has the same shape over `GET /api/v1/node` (nodes tagged with the group) and has not yet been run
against a real server. `LEXFLOW_LLM_NODES` keeps working beside an overlay, as the fallback and for tests; a name in
both is the environment's.

## 4. The scale commands

Every step takes `--node <name>` to pin its model calls to one node (strict comparisons: the same model on the
same hardware). Without `--node`, calls spread over the nodes that have the model.

```sh
# the coverage test for some states, its model calls on shop
lexflow run coverage --states va,dc --node shop
# answer the gap cells of the latest coverage run with the ask pipeline, on shop, at most 6 cells per state
lexflow run coverage --states va,dc --fill --node shop --llm-cells 6
# answer a new question for two states, the summary written on ollama2
lexflow run ask --args '{"question": "How do I appeal a denied records request?", "targets": "va,dc"}' --node ollama2
# the extraction benchmark for one model on shop (pinned, so sequential), or over the whole pool (fans out)
lexflow run benchmark --models qwen3:8b --node shop
lexflow run benchmark --models qwen3:1.7b
# AskBench with the local model, on shop: the arm is stored as local+llm@qwen3:8b
lexflow ask-bench --arms local --llm --model qwen3:8b --node shop
# pull a model onto a node (what the Compute page's button queues)
lexflow run models --models qwen3:8b --node shop
```

From the dashboard the same jobs take a `node` argument (`POST /api/jobs {"step": "coverage", "args": {"states":
"va", "node": "shop"}}`); an unknown name is a 400. A pinned job runs with `LEXFLOW_LLM_ONLY=<node>` in its
process, so every call of that process, including embeddings' chat fallbacks, stays there.

**How batches spread.** A call holds a lease on its node (one row in `compute.db`, claimed atomically), so two
jobs that run at once share the nodes through the leases. With more than one node in the pool the "one heavy job at
a time" rule relaxes: only `models` (a download) stays exclusive, and `index`/`ask` still never run together (they
write the same index files). The extraction benchmark fans out over the pool's free slots (worker threads compute,
the main thread stores every row); AskBench, `ask` and the coverage `--fill` run their cells in order, each call
going to the least busy node that has the model.

**What a row records.** AskBench LLM arms are named `<arm>@<model>` (`local+llm@qwen3:1.7b`), so a run with
another model is its own arm on the Benchmark page and never overwrites another's rows; each row's metrics carry
`model`, `node` and `nodes` (calls per node). Extraction benchmark rows carry `model` and `node`. Rows made before
the pool existed were relabelled once (`lexflow compute relabel`, idempotent, with a backup of the two tables under
`data/backup/`); their bench `version` was left as it was.

## 5. What to watch

- **The pills**: nodes online, slots busy, calls in the last hour, which node embeds.
- **A card's status**: online; backing off until a time (it failed; it is retried); offline (five failures, or the
  overlay says it is disconnected); draining (n in flight) and drained; disabled.
- **Reads and writes per second** beside each model: from the last 20 good calls on that node. A CPU node reads
  (prompt processing) much faster than it writes (generation); a long prompt with a short answer is read-bound.
- **Host lines** (only with a status URL): RAM in use against the node's total, temperature, load, battery.
- **Recent work**: filter by node and model; a `failed` result names the error, and the next row for the same
  call is usually the retry on another node.
- **The job log** says `compute: <node> failed (...); trying another node` when a call moved, and a job fails with
  `no node has <model>: pull it on the Compute page` or `<model>: shop: draining; local: no qwen3:8b` when nothing
  can take it within `LEXFLOW_LLM_WAIT`.
- **`lexflow compute nodes`** when the dashboard is not running.

Drain a node before putting it to sleep or pulling a big model on it: calls in flight finish, no new ones start,
and **Enable** takes it back.
