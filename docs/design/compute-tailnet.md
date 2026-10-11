# Compute on the tailnet: design and recommendation

_11 October 2026. Research and design only. Nothing was downloaded, installed or run on any node. No node was
contacted, nobody used SSH, and no other file in the repository was changed. Sources were read on the public web
(GitHub, the projects' docs and licence files). The line numbers below were read today, and they will drift
while the other workflow edits the code._

_Addresses are placeholders: `<shop-ip>`, `<mac-ip>`, `<win-ip>`, `<win-name>` (the Windows box's MagicDNS name)
and `<tailnet>` (the `….ts.net` suffix). The real values are in the Tailscale admin console and belong in `.env`,
not in a file that may be published. The node shared in from another user's tailnet is never a compute target. The
WordPress node is never one either, and it appears below only so the policy can lock it out._

Labels used in this note:
- **[measured]**: someone measured it.
- **[source]**: read in the code, not tested.
- **[estimate]**: worked out, not measured.
- **[unconfirmed]**: nobody has checked it yet.

---

## Summary

**Recommendation: run whole models on each node as separate copies. Do not split one model across machines.**

- Run **Ollama** (MIT) on `shop`, keep the Ollama container on the Windows box, and add the Mac when it is awake.
- Lexflow gets its own **node pool**: a small dispatcher plus a **Compute** page on the dashboard. The dispatcher
  sends each model call to a node that has the model and a free slot. When a node drops out, the work moves to
  another node.
- Every useful model fits on one node. On 16 GB, `shop` can hold `qwen3:14b` (9.3 GB). Lexflow's work is many
  small, independent calls, so copies of the model scale with the number of nodes. Splitting a model over Wi-Fi or
  Tailscale makes every token wait on the network.
- **Parallax** (Apache-2.0), the project the request pointed to, is a poor fit here. It has no CPU executor, so a
  CPU-only `shop` cannot hold model layers. On Windows it needs an NVIDIA GPU under WSL2. Its LAN discovery does not
  cross a tailnet. Its remote mode uses a public relay that sees node IPs. It has no embeddings.
- **exo** (Apache-2.0, with a dashboard) is the closest fully open-source equivalent. It is also a poor fit: it is
  CPU-only on Linux, does not support Windows, cannot find peers across a tailnet except in old pinned releases, and
  has no embeddings.

**Is it fully open source?** Ollama, the Qwen3 models, nomic-embed-text and lexflow's own Compute page are open
source. So is the Tailscale client. Tailscale's coordination server is not. To make that part open too, replace it
with Headscale (BSD-3) and give up Tailscale Serve and its identity headers. §2.3 has a variant that works without
Serve.

**What to do first. Steps 1 and 2 need no lexflow code.**
1. Run the read-only probe on `shop` (§4.1) and paste the output back. It tells us the CPU, GPU, memory channels,
   disk and power.
2. Replace Tailscale's default allow-all policy with the grants and tests in §2.2. Install Ollama on `shop` with the
   outline in §4.3, then time the speeds in §5.1.
3. Land the small Phase 1 changes (§6): recording which node and model made each row, and sending a job to a named
   node. Then run the quality benchmarks in §5.2. Build the rest only if §5.3's gate passes.

---

## 1. Recommendation

### 1.1 The hardware and the work

| Node | What it is | Model memory | Speed-up hardware | Online | Plan |
|---|---|---|---|---|---|
| Windows box (Docker) | Dell Latitude 9520, i7-1185G7 (4 cores, 8 threads), 16 GB LPDDR4x-4267, Iris Xe, no discrete GPU [measured with a CIM query] | The Docker VM has 8 CPUs and 8 GB, shared with the app | none in Docker (Vulkan on the Iris Xe only with native Windows Ollama) | always | node `local`: `qwen3:1.7b` and embeddings, as now |
| `shop` | Linux laptop, 16 GB. Kernel 7.0 matches Ubuntu 26.04 LTS | about 13 GB after the OS | unknown: run the probe | idle most of the day | node `shop`: `qwen3:8b` and `qwen3:14b`, plus `qwen3:1.7b` for extra capacity |
| Mac | macOS 27.0.1. macOS 27 runs only on Apple silicon, so this is an M-series chip; RAM unknown | depends on RAM | Metal | part-time (last seen 2:16 PM) | node `mac`: fastest when awake, never depended on |
| WordPress node | small public server | – | – | always | never a node |
| node shared in from another tailnet | not ours | – | – | – | never a node |

Some features of lexflow's model work matter for this design [source]:
- The calls are many and small, and each is independent. Inside a job everything runs one call at a time.
- Prompts are long and outputs are short. The `stack_llm` judge returns 12 tokens. `pick_review` shows up to 14
  clauses of 400 characters. The asker's summary is capped at 400 tokens. Reading the prompt therefore takes most of
  the time.
- Lexflow uses Ollama's own API:
  - `/api/chat` with a JSON-schema `format` and `think: false`
  - `/api/embed` with batches of 32
  - `/api/tags` and `/api/pull`
- It needs embeddings (`nomic-embed-text`). Neither Parallax nor exo serves them.
- Each job runs as its own `python -m lexflow run` process. At most `LEXFLOW_MAX_JOBS=2` jobs run at once.
  `build`, `quickstart`, `models` and `ask` never run together, because "these share Ollama"
  (`pipeline/jobs.py:24`).

### 1.2 Options compared

| Option | Licence | Uses a CPU-only `shop` | Windows box | Mac | Works across the tailnet | Embeddings | Lexflow's API unchanged | Dashboard | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| **Ollama on each node + lexflow pool and Compute page** | MIT, plus lexflow's code | yes | yes (already) | yes (Metal) | yes: plain HTTP to 100.x addresses | yes | yes | lexflow's Compute page | **recommended** |
| Ollama + Olla proxy | Apache-2.0 (pre-1.0) | yes | yes | yes | yes | `/api/embed` is not in its Ollama profile [unconfirmed passthrough] | mostly | read-only, at `/internal/ui/` | a no-code fallback; it cannot tell lexflow which node answered |
| Ollama + LiteLLM | MIT except `enterprise/` | yes | yes | yes | yes | yes, in OpenAI form | no: OpenAI format only | Admin UI needs Postgres | heavier. PyPI 1.82.7 and 1.82.8 were malicious on 24 March 2026 |
| Ollama + nginx `least_conn` | BSD-2 | yes | Windows build is beta | yes | yes | yes | yes | none | simplest, but has no model awareness |
| LocalAI (federated mode) | MIT | yes | containers only | yes | its P2P token and DHT, or custom bootstrap peers; with the DHT off it falls back to mDNS, which does not cross | yes | Ollama API since 4.2.0; `format` and `think` [unconfirmed] | yes | the best ready-made open option, but it would replace lexflow's Ollama |
| **Parallax** (GradientHQ) | Apache-2.0 (Lattica: MIT) | **no**: executors are CUDA or MLX only, and anything else raises "Unsupported device type" [source] | only with an NVIDIA RTX 3060 Ti or better under WSL2 | yes (MLX) | its LAN discovery is mDNS. A static-peer recipe exists in the code but is undocumented and untested | no | no: OpenAI format only | yes (:3001) | **no** |
| **exo** | Apache-2.0 (GPL-3.0 before v1, December 2025) | CPU only (MLX on CPU); Linux is not a tested tier | not supported | yes (main platform) | v1.0.69 to v1.0.71 accept `--bootstrap-peers`. Main removed it and uses IPv6 multicast | no | partly (an `/ollama` shim with MLX model names) | yes (:52415) | no, except as an experiment on the Mac |
| llama.cpp RPC | MIT | yes | yes | yes | yes, but "fragile and insecure" | yes (llama-server) | no | basic | only for a model too large for any single node |
| GPUStack v2 | Apache-2.0 | no: GPU first, Linux-only workers | WSL2 only | no | – | – | no | yes | no |
| distributed-llama | MIT | yes | yes | yes | needs 2^n nodes; slower on 1 GbE | no | no | none | no |

### 1.3 Why copies win here, and when splitting a model would be worth it

**Why copies win here:**
- **Every model that helps fits on one node.** Up to `qwen3:14b`, a model fits whole on `shop` (§4.3, model
  sizes).
- **Splitting a model costs speed on every token.** Decode speed is limited by memory bandwidth. Splitting a model
  adds a network round trip at each split point, for every token. Published runs show the cost:
  - llama.cpp RPC over 10GbE direct-attach with a Metal and CUDA pair: 7B fell from 91.8 to 52.7 tokens/s, and 72B
    from 11.1 to 5.9.
  - distributed-llama on 1 GbE: two nodes gave 2.60 tokens/s against 3.69 on one.
  - exo PR #2103 (unmerged; the author's numbers, GPU machines): about 180 tokens/s on one machine, 69 split over
    "Local network + Tailscale".
  Over Wi-Fi and Tailscale it would be worse.
- **Lexflow's work is many independent calls.** With copies, two nodes do two calls at once. With a split, two nodes
  do one call, more slowly.
- **The nodes are mixed and part-time.** A split model fails whenever any one machine sleeps. With copies, a lost
  node costs a retry on another.
- **No discovery is needed.** Tailscale carries no multicast, so mDNS discovery (Parallax, LocalAI with the DHT off,
  exo) does not cross it. Copies need only plain HTTP to a known address.

**When splitting would be worth it.** All of these must hold:
1. A model that is clearly better for lexflow does not fit on any single node. For example, `qwen3:30b-a3b`
   (19 GB) or `qwen3:32b` (20 GB) on `shop`'s 16 GB.
2. No single machine can hold it. Check the Mac first: with 32 GB or more it could run `qwen3:30b-a3b` alone, which
   is again a copy.
3. The machines are wired to the same LAN with a direct Tailscale path (`tailscale ping` shows an IP:port, not
   `DERP(...)`), or better, 10GbE or Thunderbolt.
4. The operator accepts slower tokens in exchange for the bigger model. Splitting buys capacity, not speed.

If all four hold, try llama.cpp RPC between those two machines only, with grants limited to them, or exo v1.0.71
pinned between Macs. Do not try Parallax: it cannot use the CPU nodes.

### 1.4 Honest trade-offs of the recommendation

- **CPU speed is the real limit.** These are [estimates]. On a 16 GB laptop CPU, `qwen3:8b` might generate about 4
  to 9 tokens/s and read prompts at about 10 to 80 tokens/s. `qwen3:14b` would be roughly half that. If `shop` has
  a single memory stick, halve again. A 1,500-token prompt could take 20 seconds to several minutes, so big-model
  benchmarks are overnight runs. The gain we are looking for is quality, not speed. §5 measures both before we
  build anything large.
- **Lexflow has to maintain new code.** The pool, the poller and the page come to a few hundred lines plus tests.
  Olla or LocalAI would cost no lexflow code, but neither knows lexflow's models or embeddings. Neither records
  which node answered a row, and the Compute page needs that.
- **`shop` is a laptop.** It sleeps, closes its lid, runs on battery and gets hot. It needs the keep-awake and
  thermal settings in §4.3. The pool must expect it to vanish: the restart check in `jobs.py`
  (`STALE`, 300 s) catches dead processes, not a sleeping node.
- **Results can differ by backend.** Even at temperature 0, CPU, Metal and Vulkan can give slightly different
  outputs. Benchmark rows will record the node, and a strict model comparison should pin one node.
- **The Windows box is weak for models.** `qwen3:4b` ran at 0.25 tokens/s in the 8 GB Docker VM [measured]. That
  probably reflects memory pressure in the VM more than the CPU. Native Windows Ollama, or a larger VM, might be a
  cheap win, and it is worth one measurement (§5.1, optional).
- **Some network details are untested.** It is [unconfirmed] that Docker Desktop containers can reach 100.x
  addresses. One `curl` settles it (§4.5).

### 1.5 Open-source status of each piece

| Piece | Licence | OSI open source | Notes |
|---|---|---|---|
| Ollama | MIT | yes | It has cloud models and web search; `OLLAMA_NO_CLOUD=1` turns them off. The macOS and Windows apps update themselves. Models come from the ollama.com registry. |
| Qwen3, Qwen3.5 weights | Apache-2.0 | yes | |
| nomic-embed-text v1.5 | Apache-2.0 | yes | |
| gemma3 (lexflow's default `LEXFLOW_MODEL_B`, `gemma3:1b`) | Gemma Terms of Use | **no** | |
| Gemma 4 | Apache-2.0, per the Gemma terms page and press reports | yes | check the model card before relying on it |
| Lexflow pool and Compute page | lexflow's licence | – | new code in this repo |
| Tailscale client (`tailscaled`, CLI, Serve, SSH server) | BSD-3-Clause | yes | The Windows, macOS and iOS GUIs are closed; the Linux and Android GUIs are open. |
| Tailscale coordination server, admin console, Funnel | hosted service | **no** | Serve's identity headers depend on it. |
| DERP relay code | BSD-3 | yes | the hosted relays are Tailscale's |
| Headscale | BSD-3-Clause | yes | An open control server: grants, tests, MagicDNS, and SSH check mode (0.29+). **No Serve or Funnel.** It needs a public server: a new small VPS, not the WordPress node. Latest v0.29.4. |
| Headplane (Headscale web UI) | MIT | yes | community project |
| NetBird | client BSD-3; management, signal, relay and dashboard AGPLv3 | yes | An open alternative mesh with a dashboard, and group-gated private services with identity headers (beta, v0.72+). Every device must re-enrol. |
| ufw, systemd, thermald, TLP | GPL-3, LGPL-2.1+, GPL-2.0+, GPL-2.0+ | yes | |
| Docker Desktop (already in use) | proprietary | no | Only the Windows box uses it; the Linux nodes need no Docker. |
| Parallax / exo / LocalAI / Olla / llama.cpp | Apache-2.0 / Apache-2.0 / MIT / Apache-2.0 / MIT | yes | |
| LiteLLM | MIT except `enterprise/` | mostly | |
| Open WebUI (if a chat UI is ever wanted) | own licence since v0.6.6 | **no** | v0.6.5 and earlier were BSD-3 |

---

## 2. Security

### 2.1 Rules

- **Bind every service to 127.0.0.1 on its own machine.** Reach it over the tailnet with `tailscale serve`, or with
  a bind to the Tailscale address only (§2.3). Never use 0.0.0.0: on a laptop that also opens the service to the
  home or café network.
- **Ollama has no authentication.** On a local server, anyone who can reach port 11434 can chat, `pull`, `create`,
  `push`, `copy` and `delete` models [source: `server/routes.go`]. Only the Windows box may reach the nodes' Ollama,
  and the tailnet policy enforces that. Set `OLLAMA_NO_CLOUD=1` on every node.
- **The dashboard and its job API have no sign-in, and the job API runs any step** (`docker-compose.yml:39` and
  `:88`). The dashboard stays on 127.0.0.1. It goes on the tailnet only behind Serve and the sign-in in §2.5.
- **Never use Funnel** (§2.6). Leave the `funnel` node attribute out of the policy.
- **Write grants before anything listens.** A new tailnet's default policy "enables communication between all
  devices". Grants only add access: a new grant restricts nothing while the allow-all rule is still there. The
  allow-all rule must be **replaced**.
- **Trust only the operator's own devices.** Never list the shared-in node as a target. A shared-in machine "can
  receive incoming connections … but cannot start connections". Never use `src: ["*"]`, which also covers invited
  users.
- **Turn off key expiry for `shop`** in the admin console (Machines → shop → Disable key expiry). Otherwise it
  drops off the tailnet unattended after 180 days by default. Tagging `shop` would also turn expiry off, but it
  changes the device's owner and the SSH rules, so disabling expiry is simpler.

### 2.2 Tailscale policy (a sketch to adapt in the admin console; not applied)

```jsonc
{
  "hosts": {
    "win":   "<win-ip>",     // the Windows box: Docker, lexflow, the dashboard
    "shop":  "<shop-ip>",
    "mac":   "<mac-ip>",
    "phone": "<phone-ip>",
    "wp":    "<wordpress-ip>"  // the WordPress node: listed only so the tests can lock it out
  },
  "grants": [
    // the dashboard, from your own devices (tcp:443 instead if you serve it over HTTPS)
    {"src": ["win", "mac", "phone"], "dst": ["win"],         "ip": ["tcp:8000"]},
    // model servers and the status endpoint: from the Windows box only
    {"src": ["win"],                 "dst": ["shop", "mac"], "ip": ["tcp:11434"]},
    {"src": ["win"],                 "dst": ["shop"],        "ip": ["tcp:9101"]},
    // administration
    {"src": ["win", "mac"],          "dst": ["shop", "wp"],  "ip": ["tcp:22"]}
    // + everything you use today: list it before saving (RDP, file shares, Taildrop, the WordPress admin ...)
  ],
  "ssh": [
    // keep the rule your file has now; the default is check mode for your own devices
    {"action": "check", "src": ["autogroup:member"], "dst": ["autogroup:self"],
     "users": ["autogroup:nonroot", "root"]}
  ],
  "tests": [
    {"src": "win",   "proto": "tcp", "accept": ["shop:11434", "shop:9101", "mac:11434"]},
    {"src": "wp",    "proto": "tcp", "deny":   ["shop:11434", "shop:9101", "mac:11434", "win:8000", "shop:22"]},
    {"src": "phone", "proto": "tcp", "deny":   ["shop:11434", "mac:11434"]}
  ]
}
```

Notes:
- **Write ports with a protocol.** A port without one opens TCP, UDP and ICMP, so write `tcp:11434`.
- **Selectors are aliases, IPs, users, groups, tags or autogroups, not machine names.** That is why the sketch uses
  `hosts` aliases. Tests accept a host alias as `src`, but not CIDR ranges.
- **The tests are the guard.** The docs do not say whether a file that has `grants` but no `acls` key is still
  allow-all [unconfirmed]. If allow-all were still in force, the `wp` deny test would fail and the console would
  reject the file.
- **Traffic from the Docker container should appear on the tailnet as `win`** [unconfirmed]. If the `win` accept
  test passes but the container cannot connect, the cause is the container's path to the tailnet, not the policy
  (§4.5).
- **Check the path type.** `tailscale ping shop` from the Windows box shows a direct path (IP:port) or a relayed one
  (`DERP(...)`). Relaying matters little for copies, because the prompts are small, but a direct path is better.

### 2.3 Putting Ollama on the tailnet: two variants

**Variant A (recommended with Tailscale): Ollama on 127.0.0.1, published with `tailscale serve --tcp`.**

```sh
# on shop
sudo tailscale serve --bg --tcp=11434 tcp://127.0.0.1:11434   # tailnet only; --bg survives reboots
```

Lexflow calls `http://<shop-ip>:11434`. **Use the IP, not the name**:
- Ollama checks the `Host` header when it listens on loopback [source].
- It accepts an IP that belongs to one of the machine's own interfaces. `<shop-ip>` belongs to `tailscale0` in
  kernel mode, so it passes.
- The short name passes only if `shop`'s OS hostname is exactly `shop`.
- The `….ts.net` name gets a 403.

That is also why the HTTP or HTTPS forms of Serve do not work here: Serve passes the original Host header through,
so Ollama refuses it with a 403 [source: `ipn/ipnlocal/serve.go`, `server/routes.go`].

Keeping the loopback listener keeps Ollama's Host check, which guards against DNS rebinding from a browser. A device
on `shop`'s home network cannot reach it either: nothing listens on 11434 except on 127.0.0.1 [inference]. One
thing to test: the Serve docs say HTTPS certificates must be enabled for Serve. The CLI checks this only for
`--https`, so whether it applies to `--tcp` is [unconfirmed].

**Variant B (needed with Headscale, which has no Serve): Ollama bound to the Tailscale address.**

```ini
# /etc/systemd/system/ollama.service.d/tailnet.conf
[Unit]
After=tailscale-online.target
Wants=tailscale-online.target
[Service]
Environment="OLLAMA_HOST=<shop-ip>:11434"
```

- `tailscale-online.target` runs `tailscale wait`, so Ollama starts only once the address exists [source:
  `cmd/tailscale/cli/wait.go`]. The probe checks that the unit exists.
- A non-loopback listener skips Ollama's Host check. That works with any name, but it also loses the DNS-rebinding
  guard. A web page open in a browser on the Windows box could then reach `shop`'s Ollama through a rebound name
  [inference]. Restricting the grant source to `win` does not help, because that browser runs on `win`.
- ufw's default deny on incoming traffic (§4.3) matters here. Linux accepts a packet for any of its own addresses
  on any interface unless a firewall stops it, so a device on the home network could otherwise aim at the tailnet
  address directly.

**ufw and the tailnet.** ufw does **not** filter tailnet traffic: `tailscaled` puts its `ts-input` chain first in
INPUT and accepts everything on `tailscale0` [source: `util/linuxfw`]. Per-port control on the tailnet comes from
grants. On `shop`, ufw's job is to keep the laptop's LAN and Wi-Fi interfaces closed.

### 2.4 Putting the dashboard on the tailnet (optional, and only after §2.5 lands)

```powershell
# on the Windows box: Docker keeps publishing on 127.0.0.1:8000; Serve listens on the tailnet address
tailscale serve --bg --http=8000 http://127.0.0.1:8000
```

- **Browse by name: `http://<win-name>:8000`.** For plain HTTP, Serve looks up its handler by
  `<name>.<tailnet>.ts.net:<port>`, so `http://<win-ip>:8000` gets a 404 [source]. A side effect is useful: a
  rebound foreign name also gets a 404.
- **`--http` keeps the machine name out of public certificate-transparency logs.** WireGuard still encrypts the
  traffic. `--https=443` would publish `<win-name>.<tailnet>.ts.net` in those logs.
- **Serve passes Host through unchanged.** So `lexflow/lab/api.py:261`'s same-origin check (Origin netloc equals
  Host) still works behind Serve.
- **One thing to test:** whether Windows `tailscale serve` needs an elevated console [unconfirmed].

### 2.5 Tailscale identity as the dashboard's sign-in

**What Serve does** (HTTP and HTTPS forms only, not `--tcp`) [source: `serve.go`]:
- It **deletes** any `Tailscale-User-Login`, `-Name` and `-Profile-Pic` headers the client sent.
- It **sets** them from the connecting device's owner, but only when that device is **untagged**.
- It sets `X-Forwarded-For` to the peer's tailnet IP.
- Funnel requests get only `Tailscale-Funnel-Request: ?1`.
- Values may be RFC 2047-encoded.

**Proposed rules.** These are new settings, off by default:

```sh
LEXFLOW_TAILSCALE_AUTH=1                       # trust the headers Serve sets
LEXFLOW_TAILSCALE_USERS=you@example.com        # logins that may change things (your own; kept in .env)
LEXFLOW_ALLOWED_HOSTS=localhost,127.0.0.1,<win-name>,<win-name>.<tailnet>.ts.net
```

1. **Every request:** the Host must be in `LEXFLOW_ALLOWED_HOSTS` (Starlette's `TrustedHostMiddleware`; no new
   dependency). Otherwise 400.
2. **Requests that change something** (POST, PUT, PATCH or DELETE under `/api/`): the jobs API, cancel, settings,
   method, `POST /api/ask`, publish, review, and the new `/api/compute/*` actions.
   - The request must be same-origin. The `Origin` netloc, or `Referer` when there is no Origin, must equal Host.
     Otherwise 403.
   - The body must be `application/json`. A cross-site form cannot send that without a CORS preflight, which
     lexflow never answers.
3. **With a `Tailscale-User-Login` header:** allowed only if the lower-cased login is in `LEXFLOW_TAILSCALE_USERS`;
   otherwise 403.
4. **With no login but with `X-Forwarded-For`:** the request came through Serve from a tagged device, or some
   other way without an identity, so changes get a 403.
5. **With neither header:** this is local use on the Windows box (`http://localhost:8000`), and it works as today.
6. **GET requests are unchanged.** Whoever the grants let in can read the dashboard.
7. **Review API.** The reviewer's own token (`X-Lexflow-Reviewer-Token`) **stays required**. The tailnet login only
   decides who may call the review API at all. `review_log` gains a `via` value with the login and the
   `X-Forwarded-For` device IP, for the record.

**Limits.** Say these plainly on the Setup page:
- **The header is only as trustworthy as the path to the app.** Anything that reaches the app's port without going
  through Serve can send any header it likes. That includes other processes on the Windows box and the other
  compose containers (`ollama`, `searxng`, `libsql` can reach `app:8000`). Rule 5 therefore gives such callers what
  they already have today, and rule 3 adds nothing for them.
  - For a hard boundary, use a Tailscale sidecar container: the app shares its network namespace and publishes no
    host port, so only the sidecar can reach it. The cost is another tailnet device, an auth key or OAuth client to
    keep, and an image download.
  - Telling Docker Desktop's port proxy apart from a neighbour container by source IP is [unconfirmed]. Do not rely
    on it.
- **On this tailnet every device has the same owner.** The header names an account, not a person or a device, so
  an unlocked phone is "you". It cannot tell reviewers apart. That is why the reviewer token stays.
- **The header is ambient authority, like a cookie.** Without rule 2, any web page open in your browser could post
  to the job API as you (cross-site request forgery). The same-origin check and the JSON-only body are not
  optional.
- **Tagged devices and Funnel requests carry no identity.** They can only read.
- **Serve is a feature of Tailscale's hosted control plane.** With Headscale there are no headers. The fallback is
  the dashboard on 127.0.0.1 only, plus reviewer tokens.

### 2.6 No Funnel

Funnel publishes a port to the public internet, and visitors need no Tailscale. Funnel requests carry no user
identity. Neither lexflow's job API nor Ollama has authentication. Funnel is never used, and the policy file leaves
out its `funnel` node attribute so it cannot be turned on by mistake.

---

## 3. Lexflow changes

### 3.1 Configuration

```sh
# .env (all optional; unset = today's behaviour: one Ollama at OLLAMA_URL, no pool)
LEXFLOW_LLM_NODES=local=http://ollama:11434|embed, shop=http://<shop-ip>:11434|threads=6|status=http://<shop-ip>:9101/status.json, mac=http://<mac-ip>:11434|part_time
LEXFLOW_LLM_WAIT=900        # seconds a call waits for a free slot before the job fails with a clear message
LEXFLOW_LLM_POLL=15         # seconds between health checks of an online node
LEXFLOW_MAX_JOBS=3          # with the pool: nodes + 1 is a sensible start (each job also uses the Docker VM's RAM)
```

Each entry is `name=url`, optionally followed by `|key=value` options:

| Option | Meaning | Default |
|---|---|---|
| `slots` | calls at once. Match the node's `OLLAMA_NUM_PARALLEL`. Use 1 on CPU nodes: more parallel calls only split the same memory bandwidth and multiply KV memory | 1 |
| `priority` | 0 to 100; breaks ties after the speed measured on that node | 50 |
| `threads` | sent as `options.num_thread`. Leave a core for the desktop on a laptop | Ollama's choice |
| `embed` | this node embeds. Exactly one node does | the first node |
| `status` | URL of the node's host-status JSON (§4.4) | none |
| `part_time` | expected to sleep: shown greyed out, never waited on for long | off |
| `hours` | e.g. `18-08`: takes new work only in these hours (the container's `TZ`) | always |

Rules:
- Names are `[a-z0-9-]{1,20}`.
- URLs must be `http(s)`. The host must be a 100.64.0.0/10 or `fd7a:115c:a1e0::/48` address, a `*.ts.net` name,
  `ollama`, `localhost` or `host.docker.internal`, unless `LEXFLOW_LLM_ALLOW_ANY=1`. This stops a typo from
  sending statute text to a public host.
- **Node URLs come only from the environment.** No API can add or change one, so the page cannot be used to make
  the server call arbitrary addresses.

### 3.2 Tables

The pool's tables go in **a separate SQLite file, `data/compute.db`**, not in `lexflow.db`.
- Python's `sqlite3` opens a write transaction at the first INSERT and keeps it until commit. A step can therefore
  hold the store's write lock while it waits on a model; `JobContext` notes this.
- A lease written through a second connection to `lexflow.db` would wait out the 60-second `busy_timeout` and then
  fail.
- A separate file avoids that, and it can never be synced: `turso.check_tables` sees only `lexflow.db`.

```sql
-- data/compute.db: this copy's own; never synced
CREATE TABLE IF NOT EXISTS llm_nodes (
  name TEXT PRIMARY KEY,                 -- local | shop | mac (from LEXFLOW_LLM_NODES)
  url TEXT NOT NULL,                     -- from LEXFLOW_LLM_NODES only
  enabled INTEGER NOT NULL DEFAULT 1,    -- 0 = drained by the operator: in-flight calls finish, no new ones
  slots INTEGER NOT NULL DEFAULT 1,
  priority INTEGER NOT NULL DEFAULT 50,
  threads INTEGER,
  roles TEXT NOT NULL DEFAULT 'chat',    -- 'chat' or 'chat,embed'
  part_time INTEGER NOT NULL DEFAULT 0,
  hours TEXT,
  status TEXT NOT NULL DEFAULT 'unknown',-- online | backoff | offline | unknown
  fails INTEGER NOT NULL DEFAULT 0,      -- consecutive failures
  backoff_until TEXT,
  version TEXT,                          -- GET /api/version
  models TEXT,                           -- JSON from GET /api/tags: name, size, digest, parameter_size, quantization_level
  loaded TEXT,                           -- JSON from GET /api/ps: name, size, size_vram, context_length, expires_at
  host TEXT,                             -- JSON from the status URL (CPU, RAM, load, temperature, power), if any
  embed_ok INTEGER,                      -- its nomic-embed-text digest equals the embed node's
  last_ok TEXT, last_error TEXT, checked_at TEXT,
  edited TEXT                            -- JSON of settings changed on the Compute page (slots, priority, threads, hours)
);

CREATE TABLE IF NOT EXISTS llm_leases (  -- one row per call in flight
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  node TEXT NOT NULL, model TEXT NOT NULL, kind TEXT NOT NULL,   -- chat | embed
  job_id INTEGER, step TEXT, runner TEXT, pid INTEGER,
  started_at TEXT NOT NULL, beat_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS llm_leases_node ON llm_leases(node);

CREATE TABLE IF NOT EXISTS llm_calls (   -- one row per finished or failed call; pruned after 30 days
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  at TEXT NOT NULL, node TEXT NOT NULL, model TEXT NOT NULL, digest TEXT, kind TEXT NOT NULL,
  job_id INTEGER, step TEXT, num_ctx INTEGER, attempt INTEGER NOT NULL DEFAULT 1,
  prompt_tokens INTEGER, prompt_s REAL,  -- prompt_eval_count, prompt_eval_duration / 1e9 (uncached tokens only)
  out_tokens INTEGER, out_s REAL,        -- eval_count, eval_duration / 1e9
  load_s REAL, total_s REAL, wait_s REAL,-- load_duration; total_duration; time spent waiting for a slot
  ok INTEGER NOT NULL, error TEXT
);
CREATE INDEX IF NOT EXISTS llm_calls_at ON llm_calls(at);
CREATE INDEX IF NOT EXISTS llm_calls_job ON llm_calls(job_id);
```

**In `lexflow.db`: provenance, written through the step's own connection.**

```sql
-- MIGRATIONS (local tables)
ALTER TABLE benchmarks ADD COLUMN nodes TEXT;    -- JSON {"shop": 11, "local": 1}: calls per node for this row
ALTER TABLE benchmarks ADD COLUMN digest TEXT;   -- the model's digest on the node(s) used
ALTER TABLE ask_bench  ADD COLUMN model TEXT;
ALTER TABLE ask_bench  ADD COLUMN nodes TEXT;
ALTER TABLE ask_bench  ADD COLUMN digest TEXT;

-- shared tables (extractions, asked_answers, answers ...) keep node names off Turso: a local side table
CREATE TABLE IF NOT EXISTS llm_provenance (
  table_name TEXT NOT NULL, row_key TEXT NOT NULL,
  job_id INTEGER, model TEXT, digest TEXT, nodes TEXT,
  created_at TEXT NOT NULL,
  PRIMARY KEY (table_name, row_key)
);
```

**The AskBench key problem has to be fixed first.**
- `ask_bench`'s primary key is `(case_id, arm)` (`store/db.py:271-278`).
- An LLM arm is named `local+llmplan` or `local+llm`, with no model in the name (`ask/bench.py:268-269`).
- So a `qwen3:8b` run would **overwrite** the `qwen3:1.7b` rows. `lexflow ask-bench` would then rewrite
  `docs/askbench.json` (`cli.py:220`, mounted from the repo under `docker-compose.dev.yml`) with the 8b numbers
  under the old label.

The fix: new LLM arms are named `local+llmplan@<model>`. The key stays the same, and `summary()` already groups by
arm, so each model becomes its own arm on the Benchmark page. Existing rows keep their names. Relabel them
`@qwen3:1.7b` only if the operator confirms `LEXFLOW_ASK_MODEL` was unset when they ran.

### 3.3 Health polling

- A `Poller` thread starts in the API's `lifespan` beside the job `Runner` (`api/app.py:29-38`). It checks each node
  in its own small thread pool, so one dead node's timeouts do not delay the others.
- **Online nodes, every `LEXFLOW_LLM_POLL` seconds:**
  - `GET /api/version` (3 s timeout) proves the node is reachable. Ollama answers it even while it is generating.
  - `GET /api/ps` shows the loaded models.
  - `GET /api/tags` every 60 s, or when the version changes.
  - The status URL every 30 s.
- **Offline or backing-off nodes:** checked at `backoff_until`. One success sets `online` and `fails=0`.
- **Embeddings:** the poller compares each node's `nomic-embed-text` digest with the embed node's and sets
  `embed_ok`. A mismatch is shown on the page, and that node never embeds.
  - The reason: the embedding cache file is keyed by model name and text hash
    (`data/cache/embed-<model>.jsonl`), so vectors from another build of the model would mix in silently.
- **Stale leases:** the poller deletes a lease whose `pid` is dead under the same `runner`, or whose `beat_at` is
  more than 120 s old. A killed job then never holds a slot.
- **CLI-only runs** (`lexflow run …` with no API process): the dispatcher re-checks a node inline when its
  `checked_at` is more than 60 s old.

### 3.4 The dispatcher

The dispatcher is a new module, `lexflow/compute/pool.py`. It works across processes: each job is its own process,
and all of them share `compute.db`.

```python
def acquire(model, kind, num_ctx, exclude=()):
    """A node with `model` and a free slot, claimed for this call. Blocks up to LLM_WAIT seconds."""
    deadline = time.time() + config.LLM_WAIT
    while True:
        nodes = [n for n in load_nodes() if n.serves(kind, model) and n.name not in exclude]
        if not nodes:      # nothing on the tailnet has it: say so at once
            raise NoNode(f"no node has {model}: pull it on the Compute page")
        ready = [n for n in nodes if n.ready()]   # enabled, online, not backing off, inside its hours
        # least busy first; then a node that already has the model loaded with this context length (a different
        # num_ctx makes Ollama reload it); then the speed measured on that node; then priority
        for n in sorted(ready, key=lambda n: (n.busy / n.slots, not n.loaded(model, num_ctx),
                                              -n.tokens_per_s(model), -n.priority)):
            if claim_slot(n, model, kind):        # one statement, below
                return n
        if time.time() > deadline:
            raise NoFreeSlot(f"{model}: {', '.join(n.why_not() for n in nodes)}")   # e.g. "shop: drained"
        time.sleep(random.uniform(0.5, 1.5))
```

```sql
-- claim_slot: atomic in SQLite, like jobs.claim()
INSERT INTO llm_leases(node, model, kind, job_id, step, runner, pid, started_at, beat_at)
SELECT :node, :model, :kind, :job, :step, :runner, :pid, :now, :now
WHERE (SELECT enabled FROM llm_nodes WHERE name = :node) = 1
  AND (SELECT count(*) FROM llm_leases WHERE node = :node) < (SELECT slots FROM llm_nodes WHERE name = :node);
```

```python
def call(path, body, *, model, kind, timeout):
    """POST to the best node; when a node fails, try another (at most 3 nodes)."""
    tried = []
    for attempt in (1, 2, 3):
        node = acquire(model, kind, body.get("options", {}).get("num_ctx"), exclude=tried)
        try:
            r = watched_post(node, path, body, timeout)    # raises NodeLost (below)
            if r.status_code == 404 and "not found" in r.text.lower():
                note_missing(node, model); tried.append(node.name); continue    # stale /api/tags
            if r.status_code >= 500:
                fail(node, f"HTTP {r.status_code}"); tried.append(node.name); continue
            succeed(node); record(node, model, kind, r, attempt)                 # llm_calls row
            return r            # other 4xx go back to the caller: OllamaClient keeps its 400 "think" retry
        except (requests.ConnectionError, requests.Timeout, NodeLost) as e:
            fail(node, e); record_error(node, model, kind, e, attempt); tried.append(node.name)
        finally:
            release(node)       # delete the lease
    raise NoNodeLeft(f"{model}: tried {', '.join(tried)}")
```

**Back-off.** Each failure sets
`backoff_until = now + min(900, 30 × 2^(fails−1)) × random(0.8–1.2)` seconds: 30 s, 1 min, 2 min, and so on up to
15 min. After 5 failures in a row the node is `offline` and is polled every 2 minutes. One good health check
restores it. Retrying a call is safe because lexflow's calls hold no state and run at temperature 0.

**Watchdog for a node that goes to sleep in the middle of a call.**
- `watched_post` sends the request from a worker thread. Every 15 s it refreshes the lease's `beat_at` and sends
  `HEAD /` to the node with a 5 s timeout.
- Three misses in a row (about 45 s) raise `NodeLost`, and the call moves on. Without the watchdog, a laptop that
  sleeps would hold the job until the 1,800 s read timeout.
- The abandoned request stays open until its socket times out. If the node wakes up, Ollama may finish that request
  first [inference].

**Drain.** `enabled=0` stops new leases. Calls in flight finish. The page shows "draining (1 in flight)" and then
"drained". A model that only a drained node has makes the calls wait, and when the wait times out the job fails
with "qwen3:14b is only on shop, which is drained".

**Job-level rules once the pool is on.**
- `build`, `quickstart` and `ask` no longer need the "share Ollama" exclusion: the leases limit each node to its
  slots. `EXCLUSIVE` keeps only `models`, so two pulls never run together.
- `INDEXING` (`index`, `ask`) stays global, because routed jobs still run on this machine and write its local index
  files.
- A job may be pinned with `args.node`. That passes `LEXFLOW_LLM_ONLY=<node>` to its process, and the dispatcher
  then uses only that node. Use it for strict benchmark comparisons.

### 3.5 Where it hooks in

| File (line today) | Now | Change |
|---|---|---|
| `lexflow/config.py:29` | `OLLAMA_URL` | Add `LLM_NODES` (parsed), `LLM_WAIT`, `LLM_POLL`, `LLM_ONLY`, `EMBED_NODE`. `OLLAMA_URL` stays the single-node default. |
| `lexflow/extract/ollama.py:97-131` `OllamaClient` | `requests.post(base_url + "/api/chat")` twice, and `/api/embed`; `log` keeps `eval_count` and `total_duration` | Add `_post(path, body)`: `pool.call(...)` when the pool is on and `base_url == config.OLLAMA_URL`, otherwise the direct post as now (tests that pass `http://ollama.test:11434` keep working). Add `threads` to `options`. `log` gains `node`, `digest`, `prompt_eval_count`, `prompt_eval_duration`, `eval_duration` and `load_duration`. |
| `lexflow/extract/selector.py:456-494` `Embedder` | posts `/api/embed` to `OLLAMA_URL` | Use `pool.call(kind="embed")`, pinned to the embed node (or a node with `embed_ok`). Put a `threading.Lock` around the missing, compute and append section, so threads never write a key twice or interleave lines. |
| `lexflow/municipal/build.py:39-49` `ollama_models`, `_has` | `/api/tags` of one URL | With the pool: the union of models on enabled, online nodes. `asker_for` (`ask/pipeline.py:28`) then finds a model that only `shop` has. |
| `lexflow/municipal/build.py:401`, `ask/pipeline.py:39`, `extract/benchmark.py:153` | `OllamaClient(base_url=config.OLLAMA_URL, …)` | Unchanged: they get the pool through `_post`. |
| `lexflow/pipeline/steps.py:122` `ollama_state` | `/api/tags` of one URL | With the pool: a summary for the Setup card ("2 of 3 nodes online, see Compute"). |
| `lexflow/pipeline/steps.py:385` `run_models` | pulls three models into `OLLAMA_URL` | Accept `args.node` and `args.models`, and pull into that node's URL. |
| `lexflow/pipeline/jobs.py:24, 41-56, 176-182` | `EXCLUSIVE`, `_clash`, `claim`, the subprocess `env` | Phase 1: `args.node` becomes `OLLAMA_URL` in the subprocess env, and `EXCLUSIVE` clashes count only jobs on the same node (in `_clash` and in the `claim` SQL: `coalesce(json_extract(args,'$.node'),'local')`). Phase 3: the rules in §3.4. |
| `lexflow/api/app.py:29-38, 103-117, 125-143` | `lifespan`, `services()`, `create_job` | Start the `Poller`; `services()` shows the pool; `create_job` checks `args.node` against the configured names (400 for an unknown one); add the `/api/compute` routes (§3.9). |
| `lexflow/extract/benchmark.py:149-200` | `run_one` inserts a row; `run` loops over the grid | Split compute from storing; fan out (§3.6); write `nodes` and `digest`. |
| `lexflow/ask/bench.py:225-283` | arms; module globals `RT.USE_LEARNED` and `RV.OVERRIDE` set per arm | `@model` in LLM arm names; `model`, `nodes` and `digest` columns; the globals become `contextvars` before fanning out. |
| `dashboard/index.html:24-32`, `dashboard/app.js:119` | nav and `routes` | Add `Compute` after `Jobs`, and `compute: viewCompute`. |
| `.env.example`, `docker-compose.yml` | – | Document the new settings. Pin `ollama/ollama` to the version the other nodes run, instead of `latest`. |

`scripts/terms_eval.py:446` keeps `OLLAMA_URL`: it is an experiment script, not a pipeline step.

### 3.6 How batches fan out

The pattern is the same everywhere:
- **Worker threads compute.** Each worker's model calls go through the dispatcher, which leases a slot per call.
- **The main thread stores.** It does every SQLite write, logs and reports progress. Workers never touch the job's
  connection.
- **Worker count:** the total slots of online nodes that have the batch's models, capped by `LEXFLOW_LLM_FANOUT`
  (default 4).
- **Two jobs that fan out at once share the nodes through the leases.**

- **Extraction benchmark** (`extract/benchmark.run`). The items are the case × strategy × model grid.
  - The main thread reads `_prior` (snap) before submitting an item.
  - The workers run `ST.run(...)` and the scoring.
  - The main thread inserts the row, as `run_one` does now.
  - Items for `qwen3:14b` go only to nodes that have it. `qwen3:1.7b` items spread over all three nodes.
  - Before fanning out, audit `ST.run` for module-level caches (learned selector models, vectors). Load them in the
    main thread first.
- **AskBench** (`ask/bench.run`).
  - Planning comes first: one call per question (6), all at once across nodes.
  - Then the `+llm` arm's summary calls, one worker per case. That is possible only after `RT.USE_LEARNED` and
    `RV.OVERRIDE` stop being module globals: they change per question (the held-out reranker), so threads would
    read each other's values.
  - The retrieval-only arms stay sequential. They make no model calls.
- **Ask** (`ask/pipeline.run`, per state). Workers call `answer_state(..., store=False)`, which AskBench already
  uses, and the main thread stores each row.
- **Build** (`municipal/build.run`, per state and question). Workers extract and the main thread writes. This comes
  last, because build writes the most.
- **Embeddings stay on one node.** The `Embedder` lock serialises them. Most texts are already in the cache.
- **The fallback if thread safety turns out to be hard:** the parent job enqueues one child job per node, with
  `args.node` set. The children take items from a small queue table, each claim one atomic UPDATE. Separate
  processes share no globals.

### 3.7 Phase 1 shortcut: send a whole job to a node

This comes before the pool exists. It is enough to run the §5 measurements on `shop` from the dashboard or the
CLI.
- `POST /api/jobs {"step": "benchmark", "args": {"node": "shop", "models": "qwen3:8b", ...}}`
- `Runner._start` sets `OLLAMA_URL` in the job's environment to the node's URL.
- Only same-node `EXCLUSIVE` jobs clash, so a build on `local` and a benchmark on `shop` run together.
- Embeddings follow `OLLAMA_URL` too, unless `LEXFLOW_EMBED_URL` pins them. Pin them to `http://ollama:11434`.

### 3.8 Recording which node and model made each row

- **Every call:** an `llm_calls` row with node, model, digest, job, step, tokens and durations.
- **Benchmark rows:** `model` (as now), plus `nodes` (calls per node) and `digest`. The Benchmark page shows a small
  "on shop" note beside the model.
- **AskBench rows:** the arm name carries `@model`, and the new columns hold `model`, `nodes` and `digest`.
- **Shared rows** (`extractions`, `asked_answers`, `answers`, `local_answers`): an `llm_provenance` row in this
  copy only. Node names are local details and never go to Turso. `asked_answers.model` already exists and stays as
  it is.
- **Jobs page:** a "Nodes" note per job, read from `llm_calls` (for example "shop ×11, local ×1").

### 3.9 API endpoints

| Method | Path | What it does | Changes state |
|---|---|---|---|
| GET | `/api/compute` | Nodes, calls in flight, totals and the last 20 calls (shape below). Lexflow's server asks the nodes; the browser never calls them. | no |
| GET | `/api/compute/calls?node=&model=&job=&limit=100` | recent calls, newest first (limit up to 500) | no |
| GET | `/api/compute/nodes/{name}` | one node: every model, plus the last 200 calls for a speed chart | no |
| POST | `/api/compute/nodes/{name}/check` | check the node now | the node's row |
| POST | `/api/compute/nodes/{name}/drain` | stop new work; calls in flight finish | yes |
| POST | `/api/compute/nodes/{name}/resume` | take work again | yes |
| PUT | `/api/compute/nodes/{name}` | `{slots 1-4, priority 0-100, threads 1-64 or null, hours "HH-HH" or null}` | yes |
| POST | `/api/compute/nodes/{name}/pull` | `{model}` queues a `models` job with `{node, models}`; returns `{job_id}` so the Jobs page shows its log | yes: a download on that node |
| POST | `/api/compute/nodes/{name}/unload` | `{model}` sends `keep_alive: 0` to free memory | yes |

Checks:
- `name` must be a configured node; otherwise 404.
- `model` must match `^[a-z0-9][a-z0-9._/-]{0,60}(:[a-z0-9._-]{1,40})?$`; otherwise 400.
- A pull is refused (409) for a node that is not online.
- A pull warns when a built-in size table says the model plus 3 GB is more than the node's RAM, and it needs
  `{"confirm": true}` to go ahead.
- There is no delete button: removing a model is done with `ollama rm` on the node.
- No endpoint sets a URL.
- Every POST and PUT follows §2.5.

```jsonc
// GET /api/compute
{"pool": true, "embed_node": "local",
 "totals": {"nodes": 3, "online": 2, "slots": 3, "busy": 1, "calls_1h": 148},
 "nodes": [{"name": "shop", "url": "http://<shop-ip>:11434", "status": "online", "enabled": true,
            "slots": 1, "busy": 1, "priority": 50, "threads": 6, "part_time": false, "hours": null,
            "version": "0.40.3", "last_ok": "2026-10-11T18:02:11Z", "last_error": null, "backoff_until": null,
            "host": {"cpu": "…", "cores": 8, "threads": 16, "ram_total_gb": 15.4, "ram_available_gb": 6.1,
                     "load1": 7.8, "temp_c": 78, "on_ac": true, "battery_pct": 80, "uptime_h": 52},
            "models": [{"name": "qwen3:8b", "size_gb": 5.2, "quant": "Q4_K_M", "params": "8.2B",
                        "digest": "…12 chars", "loaded": true, "context_length": 4096, "expires_at": "…",
                        "speed": {"prefill_tps": 38.1, "gen_tps": 6.2, "calls": 20}}],
            "embed_ok": null}],
 "in_flight": [{"node": "shop", "model": "qwen3:8b", "kind": "chat", "job_id": 812, "step": "benchmark",
                "started_at": "…", "elapsed_s": 41}],
 "recent": [{"at": "…", "node": "shop", "model": "qwen3:8b", "kind": "chat", "job_id": 812, "step": "benchmark",
             "prompt_tokens": 1412, "prefill_tps": 38.1, "out_tokens": 12, "gen_tps": 6.2, "total_s": 39.0,
             "ok": true}]}
```

Tokens per second come from these fields:
- generation: `eval_count / eval_duration × 1e9`
- prompt: `prompt_eval_count / prompt_eval_duration × 1e9`
Ollama's durations are in nanoseconds. Prompt tokens already in Ollama's cache are not counted.

### 3.10 The Compute page

It uses the components the dashboard already has (`page-head`, `card`, `sortableTable`, `meter`, `statusEl`). The
node cards stack into one column on a phone.

```
Compute                                                                   [Check all now]
Model servers lexflow can send work to. Each call goes to a node that has the model and a
free slot; if a node drops out, its work moves to another.

[ 2 of 3 nodes online ]  [ 1 of 3 slots busy ]  [ 148 calls in the last hour ]  [ Embeddings: local ]

┌ shop ──────────────────────── ● online ┐ ┌ local (Docker) ─────────── ● online ┐ ┌ mac ─────── ○ asleep ┐
│ Ollama 0.40.3 · checked 4 s ago         │ │ Ollama 0.40.3 · Docker VM 8 GB       │ │ last seen 14:16      │
│ CPU … · 16 threads · load 7.8           │ │ qwen3:1.7b  loaded · 4k              │ │ part-time            │
│ RAM ▓▓▓▓▓▓▓░░░ 9.3 of 15.4 GB in use    │ │ nomic-embed-text  loaded  (embeds)   │ │                      │
│ 78 °C · on AC · battery 80 %            │ │ idle                                 │ │ [Check now]          │
│ Now: qwen3:8b · job #812 benchmark · 41 s│ │                                     │ │                      │
│ Models                                  │ │ Models                               │ └──────────────────────┘
│  qwen3:8b   5.2 GB Q4_K_M  loaded · 4k  │ │  qwen3:1.7b  1.4 GB  read 120 · 9 t/s│
│             reads 38 t/s · writes 6.2   │ │  …                                   │
│  qwen3:14b  9.3 GB Q4_K_M  on disk      │ │                                      │
│ [Pull a model ▾] [Drain] [Check now]    │ │ [Pull a model ▾] [Drain] [Check now] │
└─────────────────────────────────────────┘ └──────────────────────────────────────┘

Recent work                                                         [Node ▾] [Model ▾]
Time   Job    Step       Node  Model      Kind   Prompt  Read t/s  Out  Write t/s  Took   Result
18:02  #812   benchmark  shop  qwen3:8b   chat    1,412     38.1    12      6.2     39 s   ok
18:01  #812   benchmark  local nomic-…    embed      32        –     –        –    0.8 s   ok
```

- **Status pills:** online (green); backing off "until 18:07" (amber); offline or asleep (grey, with when it was
  last seen); draining or drained (blue, with the number in flight); "embeddings differ" (amber note, when the
  digests do not match).
- **"Pull a model ▾"** lists sizes for the node's free RAM: qwen3 1.7b, 4b-q4_K_M, 8b, 14b, nomic-embed-text, then
  "other…" with a text box. It says "This downloads N GB from the Ollama registry onto shop", and the job's log
  shows progress.
- **Host lines** appear only when the node has a `status` URL. Otherwise the card shows only Ollama's own facts.
- **Setup's Ollama card** says "2 of 3 nodes online" and links to Compute. The **Jobs** page shows each job's
  nodes.

---

## 4. Node setup

### 4.1 The read-only probe: run it first, on `shop`, yourself

It changes nothing. `sudo` is needed only for `dmidecode` and `ufw status`. Paste the output back. It shows hardware
details and the tailnet address, so do not post it publicly.

```sh
# lexflow node probe: read-only
echo "== os";        lsb_release -ds 2>/dev/null; uname -r; hostname; echo "desktop: ${XDG_CURRENT_DESKTOP:-none}"
echo "== cpu";       lscpu | grep -E 'Model name|^CPU\(s\)|Thread\(s\) per core|Core\(s\) per socket|Socket\(s\)|L3'
                     grep -owE 'avx2|avx512f|avx512_vnni|avx_vnni|amx_tile|fma|f16c' /proc/cpuinfo | sort -u | tr '\n' ' '; echo
                     cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_driver 2>/dev/null
                     cat /sys/devices/system/cpu/intel_pstate/status 2>/dev/null
echo "== memory";    free -h; swapon --show
                     sudo dmidecode -t memory | grep -E '^\s+(Size|Type|Speed|Configured Memory Speed|Locator):' | grep -v 'No Module'
echo "== gpu";       lspci -nnk | grep -iA3 -E 'vga|3d|display'; ls /dev/dri 2>/dev/null
                     command -v nvidia-smi >/dev/null && nvidia-smi -L
echo "== disk";      df -h / /usr/share /var/lib 2>/dev/null; lsblk -d -o NAME,SIZE,ROTA,MODEL
echo "== power";     for p in /sys/class/power_supply/*; do echo "$(basename $p): type=$(cat $p/type 2>/dev/null) online=$(cat $p/online 2>/dev/null) capacity=$(cat $p/capacity 2>/dev/null) status=$(cat $p/status 2>/dev/null) end_threshold=$(cat $p/charge_control_end_threshold 2>/dev/null)"; done
echo "== thermal";   for z in /sys/class/thermal/thermal_zone*; do echo "$(cat $z/type) $(( $(cat $z/temp) / 1000 ))C"; done
                     systemctl is-active thermald 2>/dev/null
echo "== sleep";     systemd-analyze cat-config systemd/logind.conf | grep -E '^(HandleLid|IdleAction|LidSwitch)'
                     systemctl is-enabled sleep.target suspend.target hibernate.target 2>/dev/null
                     gsettings get org.gnome.settings-daemon.plugins.power sleep-inactive-ac-type 2>/dev/null
echo "== tailscale"; tailscale version | head -1; tailscale ip -4; ip -br addr show tailscale0
                     tailscale serve status 2>/dev/null; systemctl list-unit-files 'tailscale*'
                     tailscale ping -c 3 <win-name>      # direct (IP:port) or DERP(...)
echo "== firewall";  sudo ufw status verbose
echo "== listening"; ss -ltn
echo "== ollama";    command -v ollama && ollama --version; systemctl is-active ollama 2>/dev/null
```

What each part decides:
- **CPU flags and memory channels:** the speed to expect, and whether `qwen3:14b` is worth trying.
- **GPU:** whether Vulkan (Intel or AMD iGPU) or CUDA changes the plan. An NVIDIA GPU would also reopen Parallax and
  GPUStack.
- **Disk:** the space for about 17 GB of models.
- **Power and thermal:** the battery and heat settings.
- **`tailscale0` with an address:** confirms kernel mode, which variant A's Host check needs.
- **`tailscale-online.target`:** must exist for variant B.

### 4.2 What the operator approves

Each download is its own approval, done by the operator on the node. Download the file, verify it, then install.

| # | What | Source | Size | Needed |
|---|---|---|---|---|
| 1 | Ollama for Linux, pinned to the version the Docker container runs (`docker compose exec ollama ollama --version`; latest is v0.40.3, released today, 11 Oct 2026) | the official install script `https://ollama.com/install.sh`, read first and run with `OLLAMA_VERSION=<v>`; or the release archive from `https://github.com/ollama/ollama/releases` | Check the asset size on the release page before approving. The archive bundles GPU libraries and is large. The script is small but downloads the same archive. On a machine with an NVIDIA or AMD GPU it may also install driver packages: read it first. | yes |
| 2 | `qwen3:1.7b` | ollama.com registry (`ollama pull`) | 1.4 GB | yes: parity and extra capacity |
| 3 | `qwen3:8b` (q4_K_M) | registry | 5.2 GB | yes |
| 4 | `qwen3:14b` (q4_K_M) | registry | 9.3 GB | yes, for the quality test |
| 5 | `nomic-embed-text` | registry | 274 MB | only if `shop` is to embed (its digest must match `local`'s) |
| 6 | `qwen3:4b-q4_K_M` (pin this tag: bare `qwen3:4b` now points to a different 2.5 GB, 256K-context build) | registry | 2.6 GB | optional |
| 7 | `gemma4:12b-it-q4_K_M` (Apache-2.0, as reported) | registry | 8.0 GB | later, as a second model family |
| 8 | TLP | Ubuntu archive (`apt`) | small | optional: battery thresholds when sysfs lacks them |
| 9 | Mac: Ollama.dmg | `https://ollama.com/download` | check on the page | when the Mac joins |

Downloads 1 to 5 come to about 17 GB on disk. Every model pull goes from `shop` to the internet, not over the
tailnet.

Do not pull these on `shop`. They do not fit in 16 GB:
- `qwen3:14b-q8_0` (16 GB)
- `qwen3:30b-a3b` (19 GB)
- `qwen3:32b` (20 GB)
- `qwen3.5:27b` (17 GB)
- `qwen3.5:35b-a3b` (22 GB)

How much memory `qwen3:14b` needs depends on the context length [estimate from Qwen's config: 40 layers × 8 KV
heads × 128 dims, so 160 KiB per token at f16]:
- 9.3 GB of weights.
- KV cache at f16: 0.63 GiB at 4k context, 2.5 GiB at 16k.
- About 10 to 12 GB in all, with `OLLAMA_NUM_PARALLEL=1`.
- Lexflow asks for `num_ctx` 4096 for its decomposed calls, and 16384 (`LEXFLOW_NUM_CTX`) only for `oneshot` and
  `snap`.
- `OLLAMA_KV_CACHE_TYPE=q8_0` roughly halves the KV cache. Measure it before turning it on.

### 4.3 `shop` setup outline

This is an outline for the operator to read and run block by block, not a script for an agent. It assumes
Ubuntu 26.04 with systemd, and variant A from §2.3.

```sh
#!/usr/bin/env bash
# lexflow node setup for shop: OUTLINE. Run one block at a time; each download stops for your approval.
set -euo pipefail
OLLAMA_VERSION=0.40.3          # the version every node runs (check the Docker container's first)

## 1. Ollama, from its official source (approval 1)
curl -fsSL https://ollama.com/install.sh -o /tmp/ollama-install.sh
less /tmp/ollama-install.sh                       # read it: what it downloads, the user and unit it creates
OLLAMA_VERSION="$OLLAMA_VERSION" sh /tmp/ollama-install.sh
# (alternative: the release archive and its checksum from GitHub, extracted as docs.ollama.com/linux describes)

## 2. lexflow's settings for the service
sudo mkdir -p /etc/systemd/system/ollama.service.d
sudo tee /etc/systemd/system/ollama.service.d/lexflow.conf >/dev/null <<'EOF'
[Service]
Environment="OLLAMA_HOST=127.0.0.1:11434"
Environment="OLLAMA_NO_CLOUD=1"
Environment="OLLAMA_NUM_PARALLEL=1"
Environment="OLLAMA_MAX_LOADED_MODELS=2"
Environment="OLLAMA_KEEP_ALIVE=30m"
Environment="OLLAMA_CONTEXT_LENGTH=8192"
# a model in swap is unusably slow; past 14 GB, kill Ollama (it restarts) rather than freeze the desktop
MemorySwapMax=0
MemoryMax=14G
Nice=5
EOF
sudo systemctl daemon-reload && sudo systemctl restart ollama
curl -s http://127.0.0.1:11434/api/version        # {"version":"0.40.3"}
ss -ltn | grep 11434                              # 127.0.0.1:11434 only

## 3. Publish on the tailnet only (variant A); grants decide who may connect
sudo tailscale serve --bg --tcp=11434 tcp://127.0.0.1:11434
tailscale serve status
# Variant B instead (Headscale, or no Serve): the tailnet.conf drop-in in §2.3, and skip this block.

## 4. Firewall: close the laptop's LAN and Wi-Fi interfaces
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow in on tailscale0                   # tailnet traffic; tailscaled's own ts-input accepts it first anyway
sudo ufw enable                                   # if you ever SSH over the LAN rather than Tailscale SSH, allow it first
sudo ufw status verbose

## 5. Stay awake on AC, lid closed or open
sudo mkdir -p /etc/systemd/logind.conf.d /etc/systemd/sleep.conf.d
printf '[Login]\nHandleLidSwitch=ignore\nHandleLidSwitchExternalPower=ignore\nHandleLidSwitchDocked=ignore\nIdleAction=ignore\n' \
  | sudo tee /etc/systemd/logind.conf.d/lexflow-node.conf
printf '[Sleep]\nAllowSuspend=no\nAllowHibernation=no\nAllowSuspendThenHibernate=no\nAllowHybridSleep=no\n' \
  | sudo tee /etc/systemd/sleep.conf.d/lexflow-node.conf
# GNOME only (the probe shows the desktop): your session and the login screen have separate settings
gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-ac-type 'nothing'
sudo -u gdm dbus-run-session gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-ac-type 'nothing'
# then reboot (restarting systemd-logind can end the graphical session)
# and in the Tailscale admin console: Machines -> shop -> Disable key expiry

## 6. Heat and battery
# battery: stop charging at 80 % if the probe showed charge_control_end_threshold (drivers round to what they support)
echo 80 | sudo tee /sys/class/power_supply/BAT0/charge_control_end_threshold
# Intel only, and only if a measured run throttles: no turbo (decode speed is bound by memory bandwidth, so the loss
# should be small; prompt reading loses more; measure both ways)
# echo 1 | sudo tee /sys/devices/system/cpu/intel_pstate/no_turbo
# make either setting survive a reboot with a small oneshot unit (or TLP, approval 8)
# threads: set lexflow's |threads=N for shop to physical cores minus one, rather than a CPUQuota: llama.cpp's
# threads wait for each other, so throttling some of them slows all of them (expected; measure)
# physically: hard surface, vents clear; lid open if the keyboard deck vents

## 7. Models (approvals 2-5), one at a time
ollama pull qwen3:1.7b       # 1.4 GB
ollama pull qwen3:8b         # 5.2 GB
ollama pull qwen3:14b        # 9.3 GB
# ollama pull nomic-embed-text   # 274 MB, only if shop is to embed
ollama list                  # compare digests with: docker compose exec ollama ollama list

## 8. Optional: host status for the Compute page (§4.4), python3 standard library only, no download
# install /usr/local/bin/lexflow-node-status and its unit, then:
# sudo tailscale serve --bg --tcp=9101 tcp://127.0.0.1:9101
```

**Undo.** Remove the Serve settings with `sudo tailscale serve reset`, then `sudo systemctl disable --now ollama`.
Remove the drop-ins under `/etc/systemd/{system/ollama.service.d,logind.conf.d,sleep.conf.d}`, and with them
`ufw disable` if ufw was off before. To remove Ollama itself, delete the files the installer put in place and the
models under `/usr/share/ollama`. That deletion is permanent, so it is the operator's call.

### 4.4 The status endpoint

The status endpoint is optional. It is a single Python 3 file using only the standard library (about 60 lines).
Ubuntu ships `python3`, so there is nothing to download.

- **Where it runs:** a systemd service with `DynamicUser=yes`, `ProtectSystem=strict`, `ProtectHome=yes` and
  `NoNewPrivileges=yes`. It listens on `127.0.0.1:9101` and answers only `GET /status.json` (anything else is a
  404).
- **How it is reached:** `tailscale serve --tcp=9101`, granted to `win` only. Use `--tcp`: an `--http` Serve must
  be called by name, not IP (§2.4).
- **What it reads on each request:**
  - `/proc/cpuinfo` (model name), `os.cpu_count()` and `/proc/loadavg`
  - `/proc/meminfo` (MemTotal, MemAvailable, SwapTotal, SwapFree)
  - the highest `/sys/class/thermal/thermal_zone*/temp`
  - `/sys/class/power_supply/*` (AC online, battery capacity, status, end threshold)
  - `/proc/uptime`
  - `systemctl is-active ollama`
- **It never includes** hostnames of other machines, user names, process lists or file paths.

The alternative is Prometheus `node_exporter` (Apache-2.0, a download). It has more data than the Compute page
needs.

### 4.5 The Windows box (node `local`)

The compose `ollama` service stays as it is. It is reached as `http://ollama:11434` on the compose network and is
never on the tailnet.

**Test first:** can the app container reach `shop` over the tailnet? It is [unconfirmed] that Docker Desktop
containers can reach 100.x addresses.

```powershell
docker compose exec app python -c "import requests; print(requests.get('http://<shop-ip>:11434/api/version', timeout=5).json())"
```

If this fails while the `win → shop` policy test passes, try these in order:
1. Check the Windows firewall and the Tailscale adapter's route.
2. Use a Tailscale sidecar container that offers an outbound proxy (`TS_OUTBOUND_HTTP_PROXY_LISTEN`). That is one
   more image download.

Inside containers, MagicDNS names may not resolve. Use IPs.

**Optional measurement:** native Ollama for Windows outside Docker, or a larger WSL2 VM. Either might make `local`
much faster than 0.25 tokens/s for `qwen3:4b`. Native Ollama is a download, it updates itself, and it would share
the 16 GB with the Docker VM. Measure it before switching.

### 4.6 The Mac (node `mac`, when wanted)

- **Install:** Ollama.dmg (approval 9). Then `launchctl setenv OLLAMA_NO_CLOUD 1`, leave `OLLAMA_HOST` at its
  default, and restart the app.
- **Publish:** `tailscale serve --bg --tcp=11434 tcp://127.0.0.1:11434`. The App Store and Standalone Tailscale
  builds can serve ports, though not files.
- **Stay awake on the adapter:** System Settings → Battery → Options → "Prevent automatic sleeping on power adapter
  when the display is off", or `caffeinate -s` while a batch runs.
- **It is `part_time`,** so the dispatcher uses it when it is online and never waits for it long.
- **Which models depend on its RAM:**
  - 8 GB: 1.7b and 4b.
  - 16 GB: 8b comfortably.
  - 24 GB or more: 14b.
  - 32 GB or more: `qwen3:30b-a3b` (19 GB) alone, as a copy, with no splitting.
- **Expected speed:** on Apple silicon, llama.cpp 7B Q4 reads prompts at about 110 to 440 tokens/s and generates
  at about 14 to 50 tokens/s, depending on the chip. That makes it much faster than `shop` when awake.
- **The app updates itself.** `llm_calls` records each node's version, so a change in results can be traced.

---

## 5. Measured plan

### 5.1 Speed first (M1: needs only §4.3; no lexflow code)

Run inside the app container. It sends a fixed real statute text (about 1,500 tokens) from a benchmark case. Each
run starts with a different number, so Ollama's prompt cache cannot skip the reading.

```powershell
# PowerShell: a single-quoted here-string piped into Python in the container (in Git Bash use <<'EOF' ... EOF)
@'
import requests
from lexflow.extract.benchmark import load_case
text = load_case("va.records")[3][:6000]                 # the statute text of one benchmark case
NODES = {"local": ("http://ollama:11434", ["qwen3:1.7b"]),
         "shop":  ("http://<shop-ip>:11434", ["qwen3:1.7b", "qwen3:8b", "qwen3:14b"])}
for node, (url, models) in NODES.items():
    for m in models:
        for run in range(3):
            body = {"model": m, "stream": False, "think": False, "keep_alive": "30m",
                    "prompt": f"Run {run}. List the duties in this text in one sentence.\n\n{text}",
                    "options": {"temperature": 0, "num_ctx": 4096, "num_predict": 64}}
            d = requests.post(url + "/api/generate", json=body, timeout=3600).json()
            print(node, m, run, "prompt", d["prompt_eval_count"],
                  "read t/s", round(d["prompt_eval_count"] / d["prompt_eval_duration"] * 1e9, 1),
                  "write t/s", round(d["eval_count"] / d["eval_duration"] * 1e9, 1),
                  "load s", round(d.get("load_duration", 0) / 1e9, 1))
'@ | docker compose exec -T app python -
```

While it runs, watch `free -h`, `sensors` (or the thermal zones) and the power state on `shop`. Fill in a table:

| Node | Model | Read tokens/s | Write tokens/s | Load s | Peak RAM | Max °C | Notes |
|---|---|---|---|---|---|---|---|
| local | qwen3:1.7b | | | | | | |
| shop | qwen3:1.7b | | | | | | |
| shop | qwen3:8b | | | | | | |
| shop | qwen3:14b | | | | | | |

Rough cost of one `stack_llm` judgement: prompt tokens ÷ read speed + 12 ÷ write speed.

### 5.2 Quality, cheapest first (M2: needs Phase 1)

Phase 1 changes `ask/bench.py`, and AskBench's version hash covers `ask/*.py`. Every stored AskBench row therefore
goes stale, so **re-run the baselines on the same code first**: `--arms local,heuristic,oracle`, and
`--llm-plan` with `qwen3:1.7b` on `local`. Today's numbers (`docs/askbench.json`, version 2, 30 cases) are local
(rules plan) 0.403, `local+llmplan` with qwen3:1.7b 0.387, Claude's concept groups (`profile`) 0.507, and oracle
0.749.

1. **AskBench planning with a bigger model.** This is 6 model calls per run, one per question.
   ```sh
   # Phase 1 in place (arms carry @model; embeddings pinned to local); the same line works in PowerShell
   docker compose exec -e LEXFLOW_ASK_MODEL=qwen3:8b -e OLLAMA_URL=http://<shop-ip>:11434 -e LEXFLOW_EMBED_URL=http://ollama:11434 app python -m lexflow ask-bench --arms local --llm-plan
   docker compose exec -e LEXFLOW_ASK_MODEL=qwen3:14b -e OLLAMA_URL=http://<shop-ip>:11434 -e LEXFLOW_EMBED_URL=http://ollama:11434 app python -m lexflow ask-bench --arms local --llm-plan
   ```
   The 30 cases are 6 questions × 5 states, and one plan serves all five states of a question. So bootstrap over
   questions (6 clusters) as well as over cases, and report both. The question-level interval will be wide.
2. **Extraction cross-check with a bigger model.** VA's cases first, then all 22 held-out cases overnight.
   ```sh
   # VA first: a job sent to shop (Phase 1), e.g. POST /api/jobs
   #   {"step": "benchmark", "args": {"node": "shop", "strategies": "stack_llm,pick_review", "models": "qwen3:8b", "cases": "va.records,va.business"}}
   # then every held-out case, overnight
   docker compose exec -e OLLAMA_URL=http://<shop-ip>:11434 -e LEXFLOW_EMBED_URL=http://ollama:11434 app python -m lexflow run benchmark --strategies stack_llm,pick_review --models qwen3:8b,qwen3:14b
   ```
   Compare with the selector (`stack_combo`) at 0.604. For reference: perfect selection 0.76, Claude against
   Claude 0.887, and `qwen3:4b` `stack_llm` matched the selector on VA records (0.71). Use the paired bootstrap
   90% interval from `scripts/selector_experiments.py`.
   - Check also whether the Method page's "agreed" flag becomes useful as a confidence signal: compare equivalence
     where the 8b or 14b check agrees with the selector against where it does not.
3. **The `+llm` summary arm on VA's 6 cases.** Use `--arms local --llm --cases
   court_debt.va,license_conviction.va,phone_commissary.va,pretrial_clock.va,prison_wages.va,record_sealing.va`,
   with the same `-e` settings. With `qwen3:1.7b`, 10 of 12 runs gave no claims.
4. **Throughput.** Record the wall-clock time of each run, and the calls per hour per node, from the logs (Phase 1)
   or from `llm_calls` (Phase 3).

### 5.3 What result justifies keeping it

Keep `shop` as a node and build Phases 2 to 5 if **(a) or (c) holds, and (b) holds as well:**

- **(a) Quality.** `qwen3:8b` or `qwen3:14b` on `shop` beats today's best local result on at least one benchmark,
  with the paired-bootstrap 90% interval of the gain above zero:
  - AskBench planning (`local+llmplan@…`) reaches **0.43 or more** on the 30 cases, against 0.403 for the rules
    plan. That is at least a quarter of the way to Claude's concept groups (0.507).
  - Or extraction: `stack_llm` or `pick_review` reaches **0.634 or more**, the selector plus 0.03, on the 22
    held-out cases.
  - Or "agreed" cases score at least 0.10 higher than "disagreed" ones, which would make the check a usable flag.
  - Or the `+llm` summary makes claims in at least 4 of VA's 6 cases, with `claim_vital_recall` above 0.
- **(b) Practical.** All of these:
  - The winning model's full 22-case extraction run finishes in one night (10 h or less), and AskBench planning in
    an hour or less.
  - `shop` answers 95% or more of health checks over a week.
  - There is no thermal shutdown and no sustained throttling, judged from the status endpoint's temperature trace.
- **(c) Capacity, even without a quality gain.** `shop` runs `qwen3:1.7b` at least as fast as `local` reads and
  writes. It then at least doubles throughput for today's default model, and the Phase 5 fan-out pays for itself.

**If neither (a) nor (c) holds:** stop after Phase 1. Its job-level routing costs little and allows the occasional
overnight run on `shop`. Or remove Ollama from `shop`.

**If only 14b passes and it is slow:** keep `shop` as the "big model" node with job-level routing only. Build the
dispatcher when such runs become routine.

### 5.4 Pitfalls to avoid in the runs

- **Embeddings must come from one place.** Pin them to `local` with `LEXFLOW_EMBED_URL` in Phase 1. Until then, any
  run with `OLLAMA_URL` pointed at `shop` would embed on `shop`. That is acceptable only if `shop`'s
  `nomic-embed-text` digest equals `local`'s.
- **Do not run AskBench with a second model before the `@model` arm lands.** It would overwrite rows and rewrite
  `docs/askbench.json` under the wrong label. If it happens by mistake, restore `docs/askbench.json` from git.
- **Pin a model to one node when comparing.** Backends can differ slightly at temperature 0.
- **Keep the context length the same within a run.** A different `num_ctx` makes Ollama reload the model.
- **Pin the model tag:** use `qwen3:4b-q4_K_M`, not `qwen3:4b`.

---

## 6. Build order, with tests

Every phase keeps today's behaviour when `LEXFLOW_LLM_NODES` is unset, and the existing tests must pass unchanged.
The tests below are added to `tests/`. The node URLs are mocked with `responses`, as `tests/test_extract.py` does,
and there are no real network calls (the compose `test` service already sets `OLLAMA_URL=http://127.0.0.1:9`).

**Phase 0: the operator only, no lexflow code.** Probe (§4.1), policy with tests (§2.2), `shop` setup (§4.3), and
the speed run (§5.1).
- Check from `shop`: `ss -ltn` shows 11434 on 127.0.0.1 only.
- Check from the container: §4.5.
- Check from the WordPress node: `curl -m 5 http://<shop-ip>:11434/` must fail.
- Check from a home-network device with Tailscale off: `curl -m 5 http://<shop-lan-ip>:11434/` must be refused.

**Phase 1: provenance and job-level routing.** This is small, and it unblocks §5.2.
- **Changes:**
  - `OllamaClient.log` gains its new fields.
  - `benchmarks.nodes` and `digest`.
  - `ask_bench` gets `model`, `nodes` and `digest`, and LLM arms are named `@model`.
  - `LEXFLOW_LLM_NODES` is parsed (names to URLs only, at this stage), and `LEXFLOW_EMBED_URL` is added.
  - `args.node` becomes `OLLAMA_URL` in the job's environment.
  - `EXCLUSIVE` clashes count only jobs on the same node.
- **Tests:**
  - The log fields are read from a mocked `/api/chat` reply.
  - Two AskBench runs with different models keep both rows.
  - `POST /api/jobs` with an unknown node gives a 400.
  - Two builds on different nodes are claimed together; two on one node are not; `index` and `ask` still never run
    together. Use a temporary database, as `tests/test_review_jobs.py` does.
  - The started process's environment carries the node URL (monkeypatch `subprocess.Popen`).
  - Config parsing rejects bad names, a missing URL and public hosts.
- **Then:** run §5.2 and decide with §5.3.

**Phase 2: nodes, the poller, and a read-only Compute page.**
- **Changes:** `compute.db`, the `Poller`, `GET /api/compute`, `GET /api/compute/calls` and `GET
  /api/compute/nodes/{name}`, `viewCompute`, the nav link, and the Setup card summary.
- **Tests:**
  - Status changes with a fake clock: online, then backoff after a failure, offline after 5, and online again
    after one success.
  - A digest mismatch sets `embed_ok=0`.
  - A node without a status URL still reports.
  - The `/api/compute` shape is right, and the browser never gets a request to make to a node: a static check that
    `app.js` fetches only `/api/…`, like `tests/test_lab.py`'s check of `lab.js`.
  - The nav link and the route exist.

**Phase 3: the dispatcher, drain, pull and unload.**
- **Changes:** `pool.acquire`, `pool.call` and `watched_post`; `llm_leases` and `llm_calls`; the hooks in
  `OllamaClient._post`, the `Embedder` and `ollama_models`; the relaxed `EXCLUSIVE`; the POST and PUT endpoints and
  their buttons.
- **Tests:**
  - Slot limits hold across two processes (multiprocessing on a temporary `compute.db`).
  - The model-aware choice: a model only on `shop` goes there; a model on no node fails at once with the
    "pull it" message.
  - A loaded model with the same `num_ctx` is preferred.
  - A `ConnectionError` makes the call fail over to the next node, and the failed node backs off.
  - A 404 "model not found" marks the model missing and re-routes.
  - A 5xx fails over.
  - The watchdog raises `NodeLost` when HEAD stops answering.
  - Drain stops new leases while calls in flight finish.
  - A stale lease (dead pid) is reclaimed.
  - Embeddings never go to a node with `embed_ok=0`.
  - `LEXFLOW_LLM_ONLY` pins a job to one node.
  - Pull queues a `models` job with `{node, models}`; a bad name is a 400 and an offline node a 409.
  - The settings PUT bounds are enforced.
  - Unset `LEXFLOW_LLM_NODES` means direct calls, as today.

**Phase 4: fan-out.**
- **Changes:**
  - The extraction benchmark's grid.
  - AskBench planning and the `+llm` arm, with `RT.USE_LEARNED` and `RV.OVERRIDE` as `contextvars`.
  - Ask per state.
  - Build per state and question, last.
  - The `Embedder` lock.
- **Tests:**
  - With a deterministic mocked model, a sequential run and a fan-out run give identical rows (compare everything
    but ids and timings).
  - A node that dies mid-run leaves no item lost or duplicated.
  - Threads embedding overlapping texts write each key once, and every cache line still parses.
  - Two jobs that fan out at once together never exceed any node's slots.

**Phase 5: tailnet sign-in, then (optionally) Serve for the dashboard.**
- **Changes:** §2.5's middleware and settings, `review_log.via`, and the Setup page's statement of the limits.
- **Tests:**
  - A Host outside the allowlist gets a 400.
  - A cross-origin POST gets a 403, and so does a non-JSON POST.
  - An allowed login gets a 200 on `POST /api/jobs`; another login gets a 403.
  - `X-Forwarded-For` without a login gets a 403 on writes.
  - No headers keeps today's local behaviour.
  - The headers are ignored while `LEXFLOW_TAILSCALE_AUTH` is off.
  - The review API still needs the reviewer's token, even with an allowed login.
- **Only after this lands:** `tailscale serve --http=8000` on the Windows box (§2.4).

**Phase 6: tidy-ups.** The Mac node, `hours`, the Jobs page's nodes column, `.env.example`, and pinning
`ollama/ollama` in `docker-compose.yml`. Add a short README section that links here.

---

## 7. Open questions for the operator

1. **`shop`'s hardware.** What does the §4.1 probe show? Is there an NVIDIA GPU? That would reopen Parallax and
   GPUStack for `shop`. How many memory sticks does it have, and how much free disk?
2. **When `shop` may work.** Does anyone use it during the day? When may it run heavy work: always, or nights only
   (the `hours` option)? Can it stay plugged in, with the lid open or closed? Is an 80% battery cap OK?
3. **The Mac.** Which chip and how much RAM (About This Mac)? How often is it awake? Should it be a node at all?
4. **Ollama version.** Which version does the Docker container run? Is it OK to pin every node to that version and
   change `ollama/ollama:latest` to it?
5. **The policy file.** What does the tailnet use today that the new grants must keep: RDP, file shares, Taildrop,
   SSH, the WordPress admin? Is it OK to replace allow-all?
6. **The dashboard on the tailnet.** Should it be reachable from the Mac and phone (Phase 5 plus Serve), or stay on
   the Windows box only?
7. **Open control plane.** Is a fully open control plane worth a new small VPS for Headscale, which loses Serve and
   identity headers? Or stay on Tailscale's hosted coordination?
8. **Model families.** Stay with Qwen3 (Apache-2.0), or test Gemma 4 (Apache-2.0, as reported) as the second
   family in place of `gemma3:1b`, which is under the Gemma Terms?
9. **Old AskBench rows.** Were the existing `local+llmplan` and `local+llm` rows made with `qwen3:1.7b`, with
   `LEXFLOW_ASK_MODEL` unset? If so, they can be relabelled `@qwen3:1.7b`.
10. **Timing with the other workflow.** When can Phase 1 land alongside the workflow now editing the code? Its
    changes to `ask/*.py` make stored AskBench rows stale either way, so the baselines are re-run after both land.
11. **Approvals.** Which of the downloads in §4.2 do you approve, and at which version?
12. **The Windows box itself.** Is one measurement of native Windows Ollama, or a larger Docker VM, worth it for the
    `local` node?
13. **Public repo.** Is the repository public? This note keeps addresses as placeholders; the real ones go in
    `.env`.

---

## Sources

- **Parallax**
  - https://github.com/GradientHQ/parallax: README; `docs/user_guide/install.md` and `quick_start.md`
  - source files: `src/parallax/server/executor/factory.py`, `src/parallax/cli.py`, `src/parallax/p2p/server.py`,
    `src/backend/main.py`, `src/backend/server/scheduler_manage.py`
  - releases and the LICENSE; https://github.com/GradientHQ/lattica (`bindings/python/src/core.rs`)
  - the paper: https://arxiv.org/abs/2509.26182
- **exo**
  - https://github.com/exo-explore/exo: README at main and v1.0.71; `PLATFORMS.md`; `TODO.md`
  - `rust/networking/src/discovery.rs` at main and v1.0.71; `src/exo/api/main.py`
  - pull requests #1690, #2060, #2080, #2103 and #2132; issues #879 and #966; the LICENSE history
- **Ollama**
  - https://github.com/ollama/ollama: LICENSE, `server/routes.go`, `docs/api.md`, releases
  - https://docs.ollama.com/faq, https://docs.ollama.com/linux, https://docs.ollama.com/gpu,
    https://docs.ollama.com/api/ps
  - model tags: https://ollama.com/library/qwen3/tags
- **Olla:** https://github.com/thushan/olla and `config/profiles/ollama.yaml`;
  https://thushan.github.io/olla/
- **LocalAI:** https://github.com/mudler/LocalAI; https://localai.io/docs/features/distribute/
- **llama.cpp RPC:** https://github.com/ggml-org/llama.cpp/blob/master/tools/rpc/README.md
- **Benchmarks of split models**
  - https://github.com/kjaiswal/llama-cpp-distributed-benchmarks
  - https://github.com/b4rtaz/distributed-llama/discussions/41 and /147
- **Tailscale**
  - Serve: https://tailscale.com/kb/1312/serve, https://tailscale.com/kb/1242/tailscale-serve
  - grants and policy: https://tailscale.com/kb/1324/grants, https://tailscale.com/kb/1018/acls,
    https://tailscale.com/docs/reference/syntax/policy-file
  - sharing, Funnel, HTTPS, SSH and connection types: https://tailscale.com/kb/1084/sharing,
    https://tailscale.com/kb/1223/funnel, https://tailscale.com/kb/1153/enabling-https,
    https://tailscale.com/kb/1193/tailscale-ssh, https://tailscale.com/kb/1257/connection-types,
    https://tailscale.com/opensource
  - source files: `ipn/ipnlocal/serve.go`, `cmd/tailscale/cli/wait.go`, `util/linuxfw/*`
  - multicast: https://github.com/tailscale/tailscale/issues/11134 and
    https://forum.tailscale.com/t/broadcast-multicast-support/156
- **Headscale:** https://github.com/juanfont/headscale and `docs/about/features.md`;
  https://headscale.net/stable/setup/requirements/
- **Headplane:** https://github.com/tale/headplane
- **NetBird:** https://github.com/netbirdio/netbird; https://docs.netbird.io/manage/reverse-proxy
- **Linux power, sleep and heat**
  - logind and sleep: https://manpages.ubuntu.com/manpages/noble/man5/logind.conf.5.html,
    https://wiki.debian.org/Suspend
  - Intel P-states: https://docs.kernel.org/admin-guide/pm/intel_pstate.html
  - systemd resource limits: https://manpages.debian.org/trixie/systemd/systemd.resource-control.5.en.html
  - battery thresholds: https://linrunner.de/tlp/settings/battery.html
- **Model licences:** https://huggingface.co/Qwen/Qwen3-14B, https://ai.google.dev/gemma/terms
