# An open-source overlay for lexflow's compute pool

_18 October 2026. Research and design only. Nothing was downloaded, installed or run; no node was contacted; no SSH;
no other file in the repository was changed. Licences were read from the `LICENSE` files in each repository, not
from blog posts. Release dates are the `published_at` of each project's latest GitHub release as of today._

_This note continues [`compute-tailnet.md`](compute-tailnet.md) (11 October). That note designed the node pool,
dispatcher and Compute page (its §3) on top of Tailscale's hosted control plane and compared Headscale, Headplane
and NetBird in its §1.5. This note re-verifies those findings, widens the field, and designs the replacement: a
fully open-source overlay with one always-on "handshake" piece on a DigitalOcean droplet under `lexipedia.xyz`,
everything else peer-to-peer where NAT allows._

Labels, as before: **[source]** read in code or docs today; **[estimate]** worked out; **[unconfirmed]** nobody has
checked it yet. Addresses, keys and the real droplet IP stay out of this file; they belong in `.env`.

---

## Summary

**Recommendation: NetBird, self-hosted on one $12 droplet, with Headscale + Headplane as the documented runner-up.**

- NetBird is the only candidate that ships, from one project, every piece the operator asked for: control server,
  signalling, STUN and relay, a web admin with users, invite links, groups and port-level policies, setup keys for
  one-command joins, peer names under a domain the operator chooses, a REST API that lists peers with their online
  state and overlay IPs, and open-source GUI clients for macOS, Windows and Linux. Its official quickstart is one
  script that writes a `docker compose` file with Traefik and Let's Encrypt [source].
- Licences: the client (including the macOS and Windows GUI under `client/ui`) is **BSD-3-Clause**; the server
  parts `management/`, `signal/`, `relay/`, `combined/` and `proxy/`, and the dashboard repo, are **AGPL-3.0**
  (since v0.53.0, 5 August 2025) [source: the LICENSE files]. Running an unmodified AGPL server for yourself and
  your friends carries no obligation beyond keeping the notices. Only a *modified* server offered to others must
  publish its changes, which lexflow would do anyway.
- The honest costs: no Tailscale Serve and no identity headers, so the lexflow dashboard's sign-in becomes
  per-user tokens (Phase C) with OIDC as an option once an IdP is confirmed; the server is five containers and wants
  2 GB of RAM; the quickstart pulls `latest` tags that the operator should pin; and every device re-enrols.
- Headscale + Headplane is a fine second choice if the operator would rather keep the Tailscale clients already
  installed. It is lighter (a $6 droplet), BSD-3 + MIT, and has grants, SSH, MagicDNS and an embedded DERP relay. It
  loses on three of the operator's own criteria: the macOS and Windows GUIs stay closed source (the open
  `tailscaled` build on macOS needs manual DNS and has no GUI), "invite a friend" needs a separate identity
  provider because Headscale has no user sign-up of its own, and a Tailscale client cannot be logged into Tailscale
  and Headscale at the same time, which makes the coexistence period a profile switch rather than a parallel run.
- ZeroTier is **not** fully open source: today its agent is MPL-2.0 but the controller, the part one would
  self-host, is under a source-available, non-commercial-only licence in `nonfree/` [source]. The task's note that
  it was BSL is historical: BSL 1.1 applied from 1.4.2 until the 2025-01-01 change date.

What to do first (no lexflow code): approve the droplet and the two DNS records (§3.4), run the NetBird quickstart
on the droplet, pin the image tags, create the `compute` group and the policies in §4.2, and join `shop` with the
`lexflow-node` compose in §3.2. Then build Phase A (§6), which makes the Compute page read the overlay.

---

## 1. The candidates, verified

### 1.1 Licence and release per component (read today)

| Component | Repo / file read | Licence | Latest release | Notes |
|---|---|---|---|---|
| Headscale | `juanfont/headscale` `LICENSE` | BSD-3-Clause | v0.29.5, 13 Oct 2026 | the control server; SQLite by default (Postgres "only for legacy reasons") |
| Headplane | `tale/headplane` `LICENSE` | MIT | v0.8.1, 16 Oct 2026 | admin UI for Headscale; needs the Docker socket to reload Headscale |
| headscale-ui | `gurucomputing/headscale-ui` `LICENSE.md` | BSD-3-Clause | 2026.03.17, 16 Mar 2026 | a static-page UI; thinner than Headplane |
| Tailscale client (`tailscaled`, CLI, DERP server code) | `tailscale/tailscale` `LICENSE` | BSD-3-Clause | v1.104.1, 7 Oct 2026 | "where the operating system is closed, the daemon is open source and the GUI is closed source" [source: tailscale.com/opensource] |
| Tailscale coordination server | – | hosted, closed | – | what this note replaces |
| NetBird client, incl. `client/ui` | `netbirdio/netbird` root `LICENSE` | BSD-3-Clause | v0.81.2, 16 Oct 2026 | root licence covers everything except the four directories below |
| NetBird `management/`, `signal/`, `relay/`, `combined/` | each directory's `LICENSE` | AGPL-3.0 | same | `combined/` is the `netbird-server` image the quickstart runs |
| NetBird `proxy/` | `proxy/LICENSE` | AGPL-3.0 | same | the root notice lists only four directories, but `proxy/` carries its own AGPL file; it is optional and this design does not use it |
| NetBird dashboard | `netbirdio/dashboard` `LICENSE` | AGPL-3.0 | v2.95.0, 15 Oct 2026 | |
| Dex (embedded in `netbird-server` since 0.62) | `dexidp/dex` `LICENSE` | Apache-2.0 | – | local users, invite links, external SSO |
| Traefik (written by the NetBird quickstart) | `traefik/traefik` `LICENSE.md` | MIT | pinned by the script to v3.7.14 | Let's Encrypt built in |
| Caddy (for the Headscale variant) | `caddyserver/caddy` `LICENSE` | Apache-2.0 | v2.11.7, 3 Oct 2026 | automatic TLS |
| Pocket ID (an IdP, if one is needed) | `pocket-id/pocket-id` `LICENSE` | BSD-2-Clause | v2.18.0, 4 Oct 2026 | small OIDC provider with passkeys |
| Zitadel | `zitadel/zitadel` `LICENSE` | AGPL-3.0 | – | heavier IdP; not needed here |
| Authentik | `goauthentik/authentik` `LICENSE` | MIT, except `authentik/enterprise/` (own licence) and `website/` (CC BY-SA 4.0) | – | heavier IdP; not needed here |
| Nebula | `slackhq/nebula` `LICENSE` | MIT | v1.11.2, 22 Sep 2026 | no users, no admin UI, no automatic DNS |
| nebula-mesh (community control plane for Nebula) | `forgekeep/nebula-mesh` `LICENSE` | MIT | v0.19.1, 9 Oct 2026 | created May 2026, 33 stars: too young to depend on |
| Managed Nebula (Defined Networking) | – | hosted, closed | – | |
| innernet | `tonarino/innernet` `LICENSE` | MIT | not checked | CLI only; no UI, no relay |
| wesher | `costela/wesher` `LICENSE` | GPL-3.0 | not checked | LAN-oriented gossip mesh; no NAT traversal, no UI |
| ZeroTier | `zerotier/ZeroTierOne` `LICENSE.txt` → `LICENSE-MPL.txt`, `nonfree/LICENSE.md` | agent MPL-2.0; controller **source-available, non-commercial only** | – | **not open source** for the self-hosted part |
| wg-easy | `wg-easy/wg-easy` `LICENSE` | AGPL-3.0 | v15.4.0, 14 Aug 2026 | hub-and-spoke WireGuard with a web UI; everything goes through the droplet |
| Ollama (on every node) | – | MIT (checked in the earlier note) | v0.40.6, 16 Oct 2026 | pin this tag in the node compose |

### 1.2 What each stack gives out of the box

**(a) Headscale + Headplane, with the Tailscale clients.**
- Policy: ACLs and grants, groups, tags, hosts, `autogroup:member/tagged/self/nonroot/internet/danger-all`; ports
  in the `ip` field (`"ip": ["11434"]`) [source: headscale.net/stable/ref/policy]. Tailscale SSH incl. check mode
  (v0.29.5's notes fix "SSH check periods") [source]. OIDC groups cannot be used in policy [source].
- DNS: MagicDNS with `dns.base_domain`, which "must be different from the server_url domain" and "must be a FQDN"
  [source: `config-example.yaml`]; `extra_records` / `extra_records_path` for A/AAAA names.
- Relay: an embedded DERP server (`derp.server.enabled`, STUN on UDP 3478; `server_url` "MUST be using https";
  `derp.urls: []` removes Tailscale's relays) [source]. Peer relays are listed as supported.
- Serve: plain-HTTP `tailscale serve` works; HTTPS Serve is open issue #1921 with active maintainer commits on 15
  October 2026 (`/machine/set-dns`, certificate domains) [source]. Whether plain-HTTP Serve sets the
  `Tailscale-User-Login` headers under Headscale is **[unconfirmed]**: the client fills them from its own netmap's
  user profiles, which Headscale does supply, but nobody has tested it. Funnel is issue #1040, not supported.
- Users: `headscale users create`; node registration by browser (`headscale auth register`) or by pre-auth key
  (`headscale preauthkeys create --user <id>`, then `tailscale up --login-server … --authkey …`) [source]. There is
  no self-service sign-up: an "invite" means either the admin registering the node by hand or a single OIDC
  provider doing the sign-in (only one provider; `allowed_users`/`allowed_domains`/`allowed_groups` filters).
- API: REST under `/api/v1` with `Authorization: Bearer <apikey>` (`headscale apikeys create`, 90-day default), or
  gRPC on 50443 [source]. The nodes endpoint is in `/swagger` on the instance; its field names were not re-read
  today **[unconfirmed]**.
- Admin UI: Headplane (`ghcr.io/tale/headplane`, UI at `/admin`, port 3000): machines, expiry, routes, naming,
  owner, ACL editor, DNS, pre-auth keys, SSO for the UI itself, browser SSH. It needs `headscale.api_key`, the
  Headscale config mounted at the same path, and the Docker socket to restart Headscale after edits [source:
  `config.example.yaml`, headplane.net/install/docker]. The policy must be in database mode for a UI to edit it.
- Clients: Linux (`tailscale up --login-server`), Windows (`tailscale login --login-server`, GUI closed), macOS
  (App Store or Standalone GUI, closed; or the open `tailscaled` via `brew install --formula tailscale`, which uses
  `/dev/utun`, has no GUI, and needs `100.100.100.100` set as DNS by hand for MagicDNS) [source: Tailscale wiki].
  Docker: `tailscale/tailscale` with `TS_AUTHKEY`, `TS_EXTRA_ARGS=--login-server=…`, `TS_STATE_DIR` (the parameter
  page was not re-read today; the variable names are from the earlier note).

**(b) NetBird self-hosted.**
- One script, `getting-started.sh`, writes `docker-compose.yml`, `config.yaml` (mode 600), `dashboard.env`, random
  secrets, and brings up `netbird-traefik` (v3.7.14), `netbird-dashboard`, `netbird-server` (management + signal +
  relay + STUN + embedded Dex IdP in one container) and optionally `netbird-proxy` and CrowdSec. NetBird images come
  as `latest` (unpinned); Traefik and CrowdSec are pinned. Ports: 80/tcp, 443/tcp, 3478/udp. Needs 1 CPU, 2 GB,
  Docker + compose, `jq`, `curl`, and a domain that resolves to the VM [source: the script and the quickstart].
- Users: since 0.62 the Management service has local users (embedded Dex). First admin at `/setup`; Team → Users →
  Add User → **Create User** (generated password shown once) or an **invite link** (role, groups, expiry default
  3 days; the invitee sets their own password); roles Owner / Admin / User; MFA for local users; external OIDC
  providers can be added beside local login (Google, Entra, Okta, Zitadel, Keycloak, Authentik, Pocket ID, Duo,
  generic OIDC); SCIM is not in the community edition [source].
- Peers: setup keys (one-off or reusable, usage limit, expiry, `auto_groups`, `ephemeral`, `allow_extra_dns_labels`)
  [source]. `netbird up --setup-key <key> --management-url https://<host>` or the Docker client with `NB_SETUP_KEY`.
- Policy: ALLOW-only, group → group, protocols `all/tcp/udp/icmp/netbird-ssh`, single ports, ranges or lists;
  one-way rules need TCP/UDP with a port; a new account starts with a **Default all-to-all policy** that must be
  removed; posture checks [source].
- DNS: each peer is `<label>.<dns domain>`; the self-hosted default is `netbird.selfhosted`; Settings → Networks →
  DNS Domain replaces it with e.g. `mesh.lexipedia.xyz` ("use a domain that doesn't resolve publicly"); custom
  zones and internal nameservers exist too [source].
- Relay and NAT: STUN on 3478/udp, relay over the HTTPS port via Traefik; direct WireGuard where hole punching
  works. Rosenpass optional.
- API: `GET /api/peers` with `Authorization: Token <PAT>` returns `id, name, ip, connected, last_seen, os, version,
  groups[], dns_label, hostname, user_id, login_expired` [source]. That is exactly the Compute page's inventory.
- Reverse proxy ("private services"): beta, needs the `netbird-proxy` container and Traefik passthrough; the docs
  describe **no identity headers** for backends, only static header auth and SSO at the proxy; "NetBird-only
  access" needs a cluster advertising the `Private` capability [source]. This design does not use it.
- Clients: Linux packages and a Docker image; macOS and Windows installers with a tray GUI; the GUI source is in
  `client/ui` under the root BSD-3 licence [source]. Android and iOS apps exist.

**(c) Nebula (+ a UI).**
- MIT, mature (Slack), tiny binary, groups-based firewall in the certificate, lighthouses for discovery and UDP hole
  punching, relays (`am_relay`, `relays`, `use_relays`), a lighthouse DNS responder for `A` and `TXT` queries
  (hosts must point at it themselves; nothing like MagicDNS) [source].
- No users, no sign-in, no admin UI, no invites, no API for "which hosts are online". Every host needs a certificate
  signed with `nebula-cert` and a config file distributed by hand. Defined's Managed Nebula adds all of that but is
  hosted and closed. `nebula-mesh` (MIT, May 2026, 33 stars) adds a web UI, single-use join tokens, a REST API and
  CA rotation, and is the only self-hosted Nebula UI found; it is too new to be the foundation here.

**(d) Footnotes.**
- innernet (MIT): WireGuard with a CIDR-based ACL and a CLI invite flow; no relay, no UI, no GUI clients.
- wesher (GPL-3.0): gossip mesh for LANs; no NAT traversal; no UI.
- ZeroTier: agent MPL-2.0; controller and "related components" in `nonfree/` are source-available only, with
  "ANY COMMERCIAL USE OF THIS SOFTWARE REQUIRES A SEPARATE COMMERCIAL LICENSE" and non-commercial use limited to
  personal, academic or 30-day evaluation [source]. **Not open source**, and the controller is the part that
  would run on the droplet.

**(e) WireGuard + wg-easy (minimal fallback).**
- AGPL-3.0, v15.4.0. Web UI with clients, QR codes, one-time links, expiry, 2FA, OIDC login, per-client firewall
  rules, Prometheus metrics [source]. Topology is hub-and-spoke: every packet between `shop` and the Windows box
  goes through the droplet, which costs latency and the droplet's bandwidth and makes "decentralised" false. No
  peer names, no groups, no device API worth the name. Keep it as the known-good fallback only.

### 1.3 Scores

0 = missing, 1 = partial or needs extra pieces, 2 = built in. The weight is the operator's own emphasis.

| Criterion | Headscale + Headplane | NetBird | Nebula (+nebula-mesh) | wg-easy | ZeroTier |
|---|---|---|---|---|---|
| Fully open source, including GUIs | 1 (mac/Win GUI closed) | 2 | 2 | 2 | 0 |
| One-command node join | 2 (pre-auth key) | 2 (setup key) | 1 (cert + config, or nebula-mesh token) | 1 (QR/config per client) | 2 |
| Built-in user management and invites | 0 (needs an IdP) | 2 (local users, invite links, roles) | 0 | 1 (OIDC login for the UI, not users of the mesh) | 1 |
| Admin UI | 1 (separate project, Docker socket) | 2 (same project) | 1 (young community project) | 2 | 2 (hosted) |
| NAT traversal and self-hosted relay | 2 (DERP + STUN) | 2 (STUN + relay) | 2 | 0 (hub only) | 2 |
| Names under `lexipedia.xyz` | 2 (`base_domain`) | 2 (DNS Domain) | 1 (lighthouse DNS, manual resolvers) | 0 | 0 |
| ACLs that limit compute ports to the pool | 2 (grants with ports) | 2 (group policies with ports) | 2 (cert groups + port rules) | 1 (per-client iptables) | 1 |
| macOS / Windows / Linux clients | 2 (installed already) | 2 | 2 | 2 (any WireGuard client) | 2 |
| Docker-friendliness (server and node) | 2 | 2 | 1 | 2 | 1 |
| Burden on a $6–12 droplet | 2 ($6) | 1 ($12, five containers) | 2 | 2 | – |
| Device API for the Compute page | 2 | 2 | 0 | 1 | 1 |
| Projects and licences to carry | 4–5 (Headscale, Headplane, Tailscale, Caddy, + Pocket ID for invites) | 2 (NetBird, Traefik; Dex inside) | 2–3 | 1 | – |
| **Total (of 22)** | **20, with the two "0/1" being the operator's stated asks** | **21** | 14 | 14 | – |

---

## 2. Recommendation and trade-offs

**Choose NetBird.** It is the most "off the shelf" answer to the brief: one project, one script, one domain, one
admin UI that already has users, invites, groups, policies, setup keys and a peers API. Its clients are open on all
three desktops, which Tailscale's are not. It can run beside the existing Tailscale client during the move, which
Headscale cannot (one `tailscaled`, one active login). The AGPL on the server is a feature for this project, not a
problem: lexflow is open and runs the server unmodified.

**Honest trade-offs.**
1. **No Serve, no identity headers.** `compute-tailnet.md` §2.5 built the dashboard's sign-in on
   `Tailscale-User-Login`. That goes. The replacement (§4.3) is per-user bearer tokens issued on the Setup page,
   bound to the user's overlay peers through the NetBird API, with OIDC later if the embedded IdP can register a
   third-party client (**open question 1**). Reads from the overlay stay open to whatever the policy admits, as
   today.
2. **Ollama binds a non-loopback address.** With no Serve `--tcp`, Ollama must listen where overlay packets
   arrive. §3.2 solves it with a network-namespace sidecar: Ollama listens on `0.0.0.0` *inside the NetBird
   container's namespace*, which has the overlay interface and nothing else published. The LAN never sees it.
   The Host-header rebinding guard is lost (as variant B in the earlier note); the policy and the namespace are
   the guard instead.
3. **Five containers and 2 GB.** The $12 droplet, not the $6 one. Headscale would fit in $6.
4. **`latest` tags.** The quickstart writes `netbirdio/netbird-server:latest` and `netbirdio/dashboard:latest`.
   Pin them to the versions in §1.1 right after the first run, and upgrade on purpose.
5. **Re-enrolment.** Every device installs a second client and logs in again. The Tailscale client stays until the
   last step (§5).
6. **Client GUIs.** macOS and Windows get an open tray app. On the Mac, the GPU (Metal) is only reachable from
   native Ollama, so the Mac runs NetBird and Ollama natively rather than through `lexflow-node` compose; the
   compose is for Linux nodes and for the Windows box's Docker Desktop.
7. **A smaller community than Tailscale's.** Releases are frequent (0.81.2 this week) and the docs are good, but
   fewer people have hit each corner case. Headscale has more years behind it.
8. **The server is a single point of trust.** Whoever controls the droplet can add peers and rewrite policy, hence
   admin MFA, backups and the "nothing on the droplet can reach Ollama" rule in §4.1.

**When to pick Headscale instead.** If the operator values keeping the Tailscale clients and grants syntax over
open GUIs and built-in invites, or wants the $6 droplet, Headscale + Headplane + Caddy is a sound stack. Add Pocket
ID (BSD-2) only if friends must sign in themselves. The lexflow adapter in §3.5 supports both back ends, so the
choice is reversible at the cost of re-enrolling devices.

---

## 3. Product design

### 3.1 Server side (the droplet)

**Droplet:** DigitalOcean Basic, 1 vCPU / 2 GiB / 50 GiB SSD, $12/month (the $6 1 GiB plan is below NetBird's
stated 2 GB minimum). Ubuntu LTS. Enable the DO firewall with inbound 22/tcp (admin's IP only), 80/tcp, 443/tcp,
3478/udp; everything else closed. Enable weekly DO snapshots (about 20% of the droplet price) as the coarse backup.

**DNS records at the lexipedia.xyz registrar (the operator creates these):**

| Record | Name | Value | Purpose |
|---|---|---|---|
| A | `net.lexipedia.xyz` | `<droplet IPv4>` | management API, dashboard, signal, relay, Let's Encrypt |
| AAAA (optional) | `net.lexipedia.xyz` | `<droplet IPv6>` | same, over IPv6 |
| CAA (optional) | `lexipedia.xyz` | `0 issue "letsencrypt.org"` | limits who may issue certificates |
| **none** | `mesh.lexipedia.xyz` | – | the peer DNS domain; it must **not** resolve publicly [source: NetBird docs]. Peers become `shop.mesh.lexipedia.xyz` inside the overlay only. |

No wildcard record is needed because the NetBird proxy is not used.

**Bring-up (one line, then two edits).** Run on the droplet as a user in the `docker` group, after Docker and the
compose plugin are installed from Docker's own repository (an approval: §5.3).

```sh
# the official quickstart (read it first: it is ~1,000 lines and writes files in the current directory)
export NETBIRD_DOMAIN=net.lexipedia.xyz NETBIRD_LETSENCRYPT_EMAIL=<operator email> \
       NETBIRD_AGENT_NETWORK=10.231.0.0/16     # outside Tailscale's 100.64.0.0/10 so both clients can coexist (§5)
curl -fsSL https://github.com/netbirdio/netbird/releases/latest/download/getting-started.sh -o getting-started.sh
less getting-started.sh
bash getting-started.sh
```

Then pin the tags the script left as `latest` and restart:

```sh
sed -i 's#netbirdio/netbird-server:latest#netbirdio/netbird-server:0.81.2#; s#netbirdio/dashboard:latest#netbirdio/dashboard:v2.95.0#' docker-compose.yml
docker compose up -d
```

Open `https://net.lexipedia.xyz/setup` once to create the Owner account (email, password of 8+ characters), then
enable MFA for it.

**The shape of the generated compose** (for review; the script's output is authoritative and includes the random
secrets, so do not hand-write this):

```yaml
# docker-compose.yml as written by getting-started.sh (built-in Traefik option), after pinning. Illustrative.
services:
  netbird-traefik:
    image: traefik:v3.7.14
    restart: unless-stopped
    ports: ["80:80", "443:443"]
    command:
      - --providers.docker=true
      - --entrypoints.web.address=:80
      - --entrypoints.websecure.address=:443
      - --certificatesresolvers.letsencrypt.acme.email=${NETBIRD_LETSENCRYPT_EMAIL}
      - --certificatesresolvers.letsencrypt.acme.storage=/letsencrypt/acme.json
      - --certificatesresolvers.letsencrypt.acme.httpchallenge.entrypoint=web
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - traefik-letsencrypt:/letsencrypt
  netbird-dashboard:
    image: netbirdio/dashboard:v2.95.0
    restart: unless-stopped
    env_file: dashboard.env
    labels: ["traefik.http.routers.dashboard.rule=Host(`net.lexipedia.xyz`)", "..."]
  netbird-server:
    image: netbirdio/netbird-server:0.81.2      # management + signal + relay + STUN + embedded Dex; AGPL-3.0
    restart: unless-stopped
    ports: ["3478:3478/udp"]
    volumes:
      - ./config.yaml:/etc/netbird/config.yaml:ro
      - netbird-server-data:/var/lib/netbird
    labels: ["traefik.http.routers.api.rule=Host(`net.lexipedia.xyz`) && PathPrefix(`/api`)", "..."]
volumes:
  traefik-letsencrypt:
  netbird-server-data:
```

**Backups** (§4.4): a nightly job copies the SQLite store with the `sqlite3` online backup API, plus `config.yaml`,
`dashboard.env`, `docker-compose.yml` and Traefik's `acme.json`, into a dated tarball that is then pulled off the
droplet (an `rclone` or `scp` to a machine on the overlay, or DO Spaces).

```yaml
# backup.compose.yml, run with: docker compose -f backup.compose.yml run --rm backup   (cron it nightly)
services:
  backup:
    image: alpine:3.22
    volumes:
      - netbird-server-data:/data:ro
      - traefik-letsencrypt:/le:ro
      - ./:/conf:ro
      - ./backups:/out
    entrypoint: ["/bin/sh", "-c"]
    command:
      - |
        apk add --no-cache sqlite >/dev/null &&
        d=/out/$(date -u +%Y%m%dT%H%M%SZ) && mkdir -p "$d" &&
        sqlite3 /data/store.db ".backup '$d/store.db'" &&
        cp /conf/config.yaml /conf/dashboard.env /conf/docker-compose.yml "$d/" && cp /le/acme.json "$d/" &&
        tar -C /out -czf "$d.tgz" "$(basename $d)" && rm -r "$d" && ls -1 /out | head -n -14 | xargs -r -I{} rm /out/{}
volumes:
  netbird-server-data: {external: true, name: <project>_netbird-server-data}
  traefik-letsencrypt: {external: true, name: <project>_traefik-letsencrypt}
```

The store's file name and path inside the volume (`store.db` under `/var/lib/netbird`) are from the NetBird
"Management SQLite store" page; confirm with `docker compose exec netbird-server ls /var/lib/netbird` before the
first cron run **[unconfirmed]**.

### 3.2 Node side: `lexflow-node`

Goal: on a Linux machine with Docker, **one command** turns it into a pool node. The files live in the repo under
`deploy/lexflow-node/` (Phase B). The overlay client owns the network namespace; Ollama and the status endpoint
share it. Nothing is published on the host, so the LAN cannot reach Ollama, and the overlay policy decides who can.

```yaml
# deploy/lexflow-node/compose.yml
name: lexflow-node
services:
  overlay:
    image: netbirdio/netbird:0.81.2              # BSD-3 client
    hostname: ${NODE_NAME:?set NODE_NAME in .env}
    cap_add: [NET_ADMIN, SYS_ADMIN, SYS_RESOURCE] # per NetBird's Docker docs; SYS_* for eBPF, optional
    devices: ["/dev/net/tun:/dev/net/tun"]
    environment:
      NB_SETUP_KEY: ${NB_SETUP_KEY:?a setup key from the admin UI}
      NB_MANAGEMENT_URL: https://net.lexipedia.xyz
      NB_HOSTNAME: ${NODE_NAME}
    volumes: ["overlay-state:/var/lib/netbird"]
    restart: unless-stopped
  ollama:
    image: ollama/ollama:0.40.6                  # MIT; pin to the version every node runs
    network_mode: "service:overlay"              # listens only inside the overlay namespace
    environment:
      OLLAMA_HOST: 0.0.0.0:11434
      OLLAMA_NO_CLOUD: "1"
      OLLAMA_NUM_PARALLEL: "1"
      OLLAMA_MAX_LOADED_MODELS: "2"
      OLLAMA_KEEP_ALIVE: 30m
      OLLAMA_CONTEXT_LENGTH: "8192"
    volumes: ["models:/root/.ollama"]
    deploy: {resources: {limits: {memory: ${OLLAMA_MEM:-14g}}}}
    depends_on: [overlay]
    restart: unless-stopped
  models:                                        # "sync": pulls the node's model list, then exits
    image: ollama/ollama:0.40.6
    network_mode: "service:overlay"
    entrypoint: ["/bin/sh", "-c"]
    command: ['for m in $(echo "$LEXFLOW_NODE_MODELS" | tr "," " "); do ollama pull "$m" || exit 1; done']
    environment: {OLLAMA_HOST: "127.0.0.1:11434", LEXFLOW_NODE_MODELS: "${LEXFLOW_NODE_MODELS:-qwen3:1.7b}"}
    depends_on: [ollama]
    restart: "no"
  status:                                        # ~60 lines of stdlib Python; GET /status.json on :9101
    image: python:3.12-alpine
    network_mode: "service:overlay"
    command: ["python", "-I", "/app/status.py"]
    environment:
      LEXFLOW_NODE_MODELS: ${LEXFLOW_NODE_MODELS:-qwen3:1.7b}
      LEXFLOW_NODE_ACCEPT: ${LEXFLOW_NODE_ACCEPT:-1}  # 0 = joined but not taking work (the node-side "off" switch)
      LEXFLOW_NODE_SLOTS: ${LEXFLOW_NODE_SLOTS:-1}
      LEXFLOW_NODE_HOURS: ${LEXFLOW_NODE_HOURS:-}
    volumes:
      - ./status.py:/app/status.py:ro
      - /sys/class/thermal:/host/thermal:ro
      - /sys/class/power_supply:/host/power:ro
    read_only: true
    depends_on: [overlay]
    restart: unless-stopped
volumes:
  overlay-state: {}
  models: {}
```

```sh
# deploy/lexflow-node/.env.example
NODE_NAME=shop
NB_SETUP_KEY=                     # from the admin UI: Setup Keys -> Create, auto-group "compute", one-off
LEXFLOW_NODE_MODELS=qwen3:1.7b,qwen3:8b,qwen3:14b
LEXFLOW_NODE_ACCEPT=1
LEXFLOW_NODE_SLOTS=1
LEXFLOW_NODE_HOURS=               # e.g. 18-08
OLLAMA_MEM=14g
```

**The one-liner on a node** (after Docker is installed and the repo's `deploy/lexflow-node/` folder is copied
over, or cloned):

```sh
cp .env.example .env && $EDITOR .env && docker compose up -d && docker compose logs -f models
```

Joining takes the setup key once; the state volume keeps the peer's WireGuard key afterwards, so `docker compose
down && up` does not re-enrol. `docker compose run --rm models` re-syncs the model list after editing `.env`.
`LEXFLOW_NODE_ACCEPT=0` and `docker compose up -d status` take the node out of rotation without leaving the
overlay. `docker compose down -v` removes the peer's key and models: the admin then deletes the peer in the UI.

Notes:
- On Linux, `/proc/loadavg` and `/proc/meminfo` inside the container are the host's, so the status endpoint needs
  no extra mounts for load and RAM; temperature and power come from the two read-only `/sys` mounts.
- **Windows box (node `local`).** Docker Desktop can run this compose, but the existing `ollama` service in
  lexflow's own compose already serves `local`, and the dashboard needs the Windows host on the overlay anyway. So
  the Windows box runs the NetBird Windows app (open source) and keeps `http://ollama:11434` as is. Whether the
  `app` container can reach overlay addresses through Docker Desktop is the same **[unconfirmed]** item as before;
  the one-line `curl` test in `compute-tailnet.md` §4.5 settles it. The fallback is an `overlay` sidecar in
  lexflow's compose with `network_mode: "service:overlay"` on `app`, which also fixes the source-IP question in
  §4.3.
- **The Mac.** Native NetBird app plus native Ollama (Metal). Add the Mac's peer to the `compute` group in the UI.
  The status endpoint is optional there (`python3 -I status.py` under launchd, or none).
- **Friends' machines.** The same compose on Linux; the native apps on macOS and Windows. They get the model list
  from the Compute page's "pull" button or `LEXFLOW_NODE_MODELS`.

### 3.3 Adding a user and designating compute

1. Admin: Team → Users → Add User → **Invite link** with role *User*, groups `members` (and `compute-clients` if
   they may *use* the pool), expiry 3 days. Send the link by whatever channel the operator trusts.
2. Friend: opens the link, sets a password (MFA optional), installs the NetBird app, enters
   `https://net.lexipedia.xyz` as the self-hosted server, logs in. Their device appears under their user in
   Peers, in the groups the account gives them. It can reach nothing until a policy includes one of its groups.
3. Admin: Peers → the device → Groups → add `compute`. From that moment the Compute page lists it (§3.5) and, once
   its Ollama answers `/api/version` on `:11434`, the dispatcher may send it work. Remove the group to un-designate
   it; the dispatcher drains it on the next poll.
4. For a machine that is **only** a node (no person), skip the user: create a setup key with `auto_groups:
   [compute]` and put it in `lexflow-node/.env`. Peers from setup keys are not owned by a person; the key's name
   records who was given it.

### 3.4 Groups, names and ports

| Group | Members | Purpose |
|---|---|---|
| `control` | the Windows box (lexflow app, dashboard) | the only source allowed to reach `11434`/`9101` |
| `compute` | designated nodes: `shop`, the Mac, friends' nodes | destinations for `tcp/11434`, `tcp/9101` |
| `admins` | the operator's own devices | may reach the dashboard on `control:8000`, SSH to nodes |
| `members` | everyone's personal devices | nothing by default; later, read-only dashboard if wanted |

Names: `shop.mesh.lexipedia.xyz`, `win.mesh.lexipedia.xyz`, and so on. Lexflow uses the IPs from the API, not the
names, so the Docker-DNS question from the earlier note does not arise.

### 3.5 How lexflow's Compute page reads the overlay

The pool in `compute-tailnet.md` §3 keeps its tables, dispatcher and page. What changes is **where the node list
comes from**: an *overlay adapter* replaces the hand-written `LEXFLOW_LLM_NODES` list (which stays as a fallback
and for tests).

```sh
# .env
LEXFLOW_OVERLAY=netbird                       # netbird | headscale | none (= LEXFLOW_LLM_NODES as before)
LEXFLOW_OVERLAY_URL=https://net.lexipedia.xyz
LEXFLOW_OVERLAY_TOKEN=<personal access token of a service user>   # read-only use; never leaves the server
LEXFLOW_OVERLAY_COMPUTE_GROUP=compute         # NetBird group, or a Headscale tag such as tag:compute
LEXFLOW_OVERLAY_RANGE=10.231.0.0/16           # the agent network; node URLs must fall inside it
LEXFLOW_OVERLAY_POLL=60
```

```python
# lexflow/compute/overlay.py (Phase A)
@dataclass(frozen=True)
class OverlayNode:
    name: str; ip: str; online: bool; last_seen: str | None; groups: tuple[str, ...]; user: str | None; os: str | None

class NetBirdOverlay:
    """GET {url}/api/peers with 'Authorization: Token …'; keep peers whose groups include COMPUTE_GROUP."""
    def list_nodes(self) -> list[OverlayNode]: ...

class HeadscaleOverlay:
    """GET {url}/api/v1/node with 'Authorization: Bearer …'; keep nodes whose tags include COMPUTE_GROUP."""
    def list_nodes(self) -> list[OverlayNode]: ...
```

Rules:
- The `Poller` (§3.3 of the earlier note) calls `list_nodes()` every `LEXFLOW_OVERLAY_POLL` seconds and upserts
  `llm_nodes` rows with `source='overlay'`, `url=f"http://{ip}:11434"`, `status_url=f"http://{ip}:9101/status.json"`.
  A peer that leaves the group is set `enabled=0` (drain) and deleted after its leases are gone. `connected=false`
  short-circuits the health check to `offline` without a request.
- Node names come from `dns_label`; they must match `[a-z0-9-]{1,20}` or the row is skipped with a log line.
- The URL host must be inside `LEXFLOW_OVERLAY_RANGE` (or the existing CGNAT/ULA list). This keeps the earlier
  rule that no API call can make the server contact an arbitrary address.
- Per-node settings edited on the page (`slots`, `priority`, `threads`, `hours`) stay in `edited` and survive
  re-upserts. The node's own `status.json` supplies defaults (`slots`, `hours`, `accept`, `models_allowed`).
- The browser never talks to the overlay API; the server does, and only `GET`.
- The Compute page gains a column "overlay: online since / last seen / owner", and a note "designated in the
  NetBird admin (group `compute`)" with a link to `https://net.lexipedia.xyz/peers`. There is no "add node" button
  in lexflow: designation lives in one place, the overlay admin.

### 3.6 TLS

Traefik on the droplet gets the certificate for `net.lexipedia.xyz` from Let's Encrypt over HTTP-01 and renews it
(acme.json in a volume; back it up to avoid rate-limit trouble on restore). Inside the overlay, traffic is
WireGuard-encrypted; lexflow and Ollama keep speaking plain HTTP over overlay addresses, as the earlier note's
grants assumed. No certificate for `*.mesh.lexipedia.xyz` is needed or possible (it does not resolve publicly).

---

## 4. Security

### 4.1 What the droplet can and cannot see

- **Keys never leave the devices.** NetBird is WireGuard: each peer generates its private key locally and the
  management service only distributes public keys and the policy. The signal service passes connection offers; the
  relay forwards packets it cannot decrypt. A compromised droplet can therefore *read* nothing in flight and cannot
  impersonate an existing peer.
- **What a compromised droplet can do:** register a new peer, move peers between groups, and rewrite policy. That
  is enough to reach a node's Ollama. Hence: Owner account with MFA; no other admin; the DO firewall; SSH by key
  only from the admin's address; pinned images upgraded on purpose; nightly backups kept off the droplet; and the
  rule that **the droplet is never a member of the overlay**, so even a fully owned server is not itself inside the
  mesh.
- **Metadata the server holds:** peer names, OS, versions, public endpoints (home IPs) and last-seen times. Treat
  the backup tarballs accordingly.
- **Ollama is never public.** Nothing on the droplet proxies to it; the node compose publishes no host port; the
  only path is overlay → policy → the NetBird container's namespace.
- **Rosenpass** (post-quantum pre-shared keys) is a NetBird option; not needed, and it rules out the proxy, which
  is unused anyway.

### 4.2 Policies (NetBird) and the Headscale equivalent

Delete the **Default** all-to-all policy first; with no policies NetBird denies everything [source].

| Policy | Source → Destination | Protocol / ports | Direction |
|---|---|---|---|
| `pool-ollama` | `control` → `compute` | tcp 11434, 9101 | one-way (needs TCP with ports) |
| `admin-dashboard` | `admins` → `control` | tcp 8000 | one-way |
| `admin-ssh` | `admins` → `compute` | `netbird-ssh` or tcp 22 | one-way |
| `members-nothing` | – | – | there is deliberately no policy for `members` |

As the API would carry it (NetBird's policy object; `rules[].ports` and `protocol` per the docs):

```jsonc
{"name": "pool-ollama", "enabled": true,
 "rules": [{"name": "control to compute ollama", "enabled": true, "action": "accept", "bidirectional": false,
            "protocol": "tcp", "ports": ["11434", "9101"],
            "sources": ["<group id of control>"], "destinations": ["<group id of compute>"]}]}
```

The Headscale form, if that stack is chosen (HuJSON; the policy in database mode so Headplane can edit it):

```jsonc
{
  "groups": {"group:admins": ["<operator>@"], "group:members": ["<operator>@", "<friend>@"]},
  "tagOwners": {"tag:control": ["group:admins"], "tag:compute": ["group:admins", "group:members"]},
  "grants": [
    {"src": ["tag:control"], "dst": ["tag:compute"], "ip": ["tcp:11434", "tcp:9101"]},
    {"src": ["group:admins"], "dst": ["tag:control"], "ip": ["tcp:8000"]},
    {"src": ["group:admins"], "dst": ["tag:compute"], "ip": ["tcp:22"]}
  ],
  "ssh": [{"action": "check", "src": ["group:admins"], "dst": ["tag:compute"], "users": ["autogroup:nonroot", "root"]}],
  "tests": [{"src": "tag:control", "proto": "tcp", "accept": ["<shop-ip>:11434"]},
            {"src": "group:members", "proto": "tcp", "deny": ["<shop-ip>:11434"]}]
}
```

(Headscale's policy page shows ports as `"ip": ["80,443"]`; the `tcp:` prefix is Tailscale grant syntax that the
earlier note used. Write a `tests` block and let the server reject the file if the form is wrong.)

### 4.3 Dashboard sign-in without Tailscale headers

Keep everything in `compute-tailnet.md` §2.5 that did not depend on the headers: the Host allowlist, same-origin
and JSON-only rules for writes, the reviewer token, and "no headers = local use". Replace rule 3 with:

1. **Per-user tokens (Phase C, first).** The Setup page, reachable only locally or by an existing admin token,
   mints a token per person (`lexflow tokens create --user alice --role admin|reviewer|reader`; stored as a salted
   hash in `lexflow.db`, shown once). The browser keeps it in `localStorage` and sends `Authorization: Bearer`.
   Writes need a token with the right role; reads over the overlay stay open as today's rule 6.
2. **Overlay peer binding (same phase, cheap).** When the request's source address is inside
   `LEXFLOW_OVERLAY_RANGE`, the API looks the address up in the overlay inventory (already polled: `ip → user_id`)
   and logs `via = {peer, user}` in `review_log`, as the earlier design logged `X-Forwarded-For`. If the token's
   user and the peer's owner differ, the write is refused (403). WireGuard's cryptokey routing makes the source IP
   trustworthy *when the packet arrives directly on the overlay interface*. Behind Docker Desktop's port proxy
   the source is rewritten **[unconfirmed]**, which is why the `overlay` sidecar for `app` is the clean fix and the
   binding is "when available", never the only check.
3. **OIDC (Phase C′, optional).** If NetBird's embedded Dex can register a client for lexflow (**open question
   1**), or if Pocket ID is added, the dashboard logs in with the same account as the overlay, and the token step
   becomes a session cookie. Until confirmed, tokens are the design.

### 4.4 Backup and restore of the control server

- **What matters:** the SQLite store (`store.db`: users, peers, groups, policies, setup keys, the embedded IdP's
  users), `config.yaml` (secrets for relay, datastore encryption and sessions), `dashboard.env`,
  `docker-compose.yml`, and Traefik's `acme.json`. Losing `config.yaml`'s datastore key makes the store
  unreadable, so it is in the same tarball.
- **How:** §3.1's nightly `backup` job (SQLite online backup, so the server keeps running) plus DO snapshots weekly.
  Keep 14 nightly tarballs on the droplet and copy each off-box.
- **Restore:** new droplet, same DNS, install Docker, unpack the tarball into the compose directory, restore the
  two volumes (`docker run --rm -v <vol>:/v -v $PWD:/b alpine tar -C /v -xzf /b/<file>` for each), `docker
  compose up -d`. Peers reconnect with their existing keys; nothing re-enrols. Test this once before relying on it.
- **Headscale variant:** `/var/lib/headscale` (SQLite `db.sqlite`, `noise_private.key`), `config.yaml`, the policy
  file, Caddy's data volume. The `noise_private.key` is what clients trust; without it every node re-registers.

---

## 5. Migration from the current tailnet

### 5.1 Coexistence

NetBird and Tailscale run side by side on one machine as long as their address ranges differ. Tailscale owns
`100.64.0.0/10`; §3.1 sets NetBird to `10.231.0.0/16`. (With Headscale this is not possible: Headscale must use
the CGNAT range, and one `tailscaled` has one active login, so coexistence would be `tailscale switch` between
profiles, not both at once.)

### 5.2 Order of moves

1. Droplet + DNS + server (§3.1), pin tags, Owner account with MFA. Delete the Default policy; create the groups
   and policies of §4.2. Nothing is connected yet, so nothing can break.
2. **Windows box** joins (native app, user login) → group `control` and `admins`. Verify from the `app` container:
   `curl http://<droplet-side nothing>`: there is nothing to reach yet, so just `netbird status` on the host.
3. **`shop`** joins with `lexflow-node` compose (setup key, auto-group `compute`). From the Windows box:
   `curl http://<shop overlay ip>:11434/api/version` and the same from the `app` container (the §4.5 test).
   From the WordPress node and from a phone off the overlay: must fail.
4. Lexflow `.env`: `LEXFLOW_OVERLAY=netbird` (Phase A landed). The Compute page shows `shop` from the overlay.
   Run the §5 measurements of the earlier note over the new path; compare `netbird status -d` (direct vs relayed)
   with the earlier `tailscale ping` result.
5. **Mac** joins (native app) → `compute` when wanted. Phone joins → `members`.
6. Dashboard sign-in: Phase C tokens issued; the Tailscale Serve for the dashboard (never turned on in the earlier
   plan) is simply not needed.
7. Per device, once it has worked on the overlay for a week: `tailscale down` (not uninstall). After all devices:
   leave the tailnet in Tailscale's console; uninstall the clients; remove the Tailscale grants file.
8. Delete the setup keys that were one-off anyway; rotate the `LEXFLOW_OVERLAY_TOKEN`.

### 5.3 Rollback

At every step before 7, `LEXFLOW_OVERLAY=none` and the old `LEXFLOW_LLM_NODES` list bring the pool back onto
Tailscale addresses in one restart; the Tailscale clients are still logged in. After step 7, rollback means
`tailscale up` on each device (keys are kept for the expiry period) and the same `.env` change. The droplet can be
destroyed at any time; the backup tarball recreates it.

### 5.4 Operator checklist with every approval point

| # | Approval | Source | Size | Notes |
|---|---|---|---|---|
| 1 | Create the droplet ($12/month) and its firewall | DigitalOcean | – | Ubuntu LTS; SSH key only |
| 2 | DNS: `A net.lexipedia.xyz → <droplet>` (+ AAAA, CAA) | registrar | – | nothing for `mesh.lexipedia.xyz` |
| 3 | Docker Engine + compose plugin on the droplet | `https://download.docker.com` apt repo | ~100 MB **[estimate]** | read the install page, not a piped script |
| 4 | `getting-started.sh` | `github.com/netbirdio/netbird/releases/latest/download/getting-started.sh` | ~50 KB **[estimate]** | read it before running; it pulls the images in 5 |
| 5 | Images: `netbirdio/netbird-server:0.81.2`, `netbirdio/dashboard:v2.95.0`, `traefik:v3.7.14` | Docker Hub | check `docker images` after pull; tens to a few hundred MB each **[unconfirmed]** | pin before second `up` |
| 6 | NetBird Windows installer (open-source tray app) | `github.com/netbirdio/netbird/releases/v0.81.2` assets | check the asset size on the release page | the Windows box |
| 7 | NetBird macOS installer | same release assets | check on the page | the Mac; friends' Macs later |
| 8 | NetBird Linux client image `netbirdio/netbird:0.81.2` (inside `lexflow-node`) | Docker Hub | check after pull | `shop` and Linux friends |
| 9 | `ollama/ollama:0.40.6` image on each Linux node | Docker Hub | large: it bundles GPU libraries; check after pull | replaces the native install from the earlier note on Linux nodes |
| 10 | Models per node (`LEXFLOW_NODE_MODELS`) | ollama.com registry | 1.4 GB / 5.2 GB / 9.3 GB for qwen3 1.7b / 8b / 14b (earlier note) | from each node to the internet |
| 11 | Pin `ollama/ollama` in lexflow's own compose to 0.40.6 | – | – | so `local` matches the nodes |
| 12 | A personal access token for lexflow's read-only service user | NetBird admin UI | – | into `.env` only |
| 13 | Invite links for each friend; which of their devices become `compute` | NetBird admin UI | – | per person |
| 14 | `tailscale down`, then leaving the tailnet | Tailscale console | – | after a week of clean overlay use |

Not on the list on purpose: the NetBird proxy, CrowdSec, Rosenpass, and any IdP beyond the embedded one.

---

## 6. Build order for lexflow, with tests

All phases keep today's behaviour when `LEXFLOW_OVERLAY` is unset or `none`. HTTP is mocked with `responses`, as in
`tests/test_extract.py`; no test touches the network.

**Phase A: the overlay adapter and a read-only Compute inventory.** (After Phase 2 of the earlier note, or
alongside it: the poller is the shared piece.)
- Changes: `lexflow/compute/overlay.py` with `NetBirdOverlay` and `HeadscaleOverlay`; the five `LEXFLOW_OVERLAY_*`
  settings in `config.py`; the poller upsert with `source='overlay'`; the Compute page's overlay column and link;
  `.env.example`.
- Tests: a mocked `/api/peers` with three peers (one in `compute` and online, one in `compute` and offline, one
  not in the group) yields exactly two `llm_nodes` rows with the right `status`; a peer with an IP outside
  `LEXFLOW_OVERLAY_RANGE` is skipped and logged; a peer that leaves the group is drained, and deleted once its
  leases are gone; edited settings survive an upsert; a bad `dns_label` is skipped; the Headscale adapter maps
  `validTags` the same way; `LEXFLOW_OVERLAY=none` leaves the env list in charge; a static check that `app.js`
  never fetches the overlay URL.

**Phase B: the node image.**
- Changes: `deploy/lexflow-node/{compose.yml,.env.example,status.py,README.md}`. `status.py` is stdlib only,
  answers `GET /status.json` (fields of `compute-tailnet.md` §4.4 plus `accept`, `slots`, `hours`,
  `models_allowed`), 404 otherwise, binds `0.0.0.0:9101` inside the overlay namespace.
- Tests: `status.py` imported under `pytest`: the JSON shape, the 404, the fallbacks when `/host/thermal` is
  absent; a `docker compose config` run in CI checks the compose file parses (no containers started); a check
  that the compose publishes no ports (`grep -c 'ports:' == 0`).

**Phase C: sign-in without headers.**
- Changes: the token table and `lexflow tokens` CLI; the bearer middleware replacing rule 3 of §2.5; peer binding
  from the overlay inventory; `review_log.via`; the Setup page's token panel and plain statement of limits.
- Tests: a write with no token and an overlay source IP gets 401; with a reader token, 403; with an admin token,
  200; a token whose user is not the peer's owner, 403; a local request with no token keeps today's behaviour; the
  reviewer token is still required; tokens are stored hashed and shown once.

**Phase C′ (optional): OIDC** once open question 1 is answered; tests mock the discovery document and the token
endpoint.

**Phase D: policy tests as code.** A small `scripts/overlay_check.py` (run by the operator, not CI) reads the
overlay API and asserts: Default policy absent; `control → compute` has only `tcp 11434, 9101`; no policy has
`members` as a source; every `compute` peer answers `/api/version` from the control host and refuses from a
non-member. This is the equivalent of the Tailscale `tests` block.

**Phase E: decommission.** Remove `LEXFLOW_TAILSCALE_*` settings and the header code paths if Phase 5 of the
earlier note was ever built (it was not yet); update `compute-tailnet.md`'s §2.5 pointer to this note.

---

## 7. Open questions for the operator

1. **The embedded IdP as an OIDC provider.** NetBird's Dex issues tokens at `/oauth2` for the dashboard and CLI.
   Can it register a third client (lexflow)? The docs do not say; the management config may or may not expose Dex's
   static clients. If not, is Pocket ID (BSD-2, one more container) acceptable, or are per-user tokens enough?
2. **Address range.** Is `10.231.0.0/16` free on every home and work network involved (the work MacBook's VPN in
   particular)? Pick another private /16 if not; it only has to avoid Tailscale's CGNAT range during coexistence.
3. **The work MacBook Pro.** Does its employer allow a third-party VPN client and a tray app? If not, it can still
   be a *user* device via policy, or stay off the overlay.
4. **Who may use the pool.** Only the Windows box (`control`) dispatches today. Should friends' lexflow copies
   also dispatch to the pool (a `control` group with several members), and if so, who pays for whose compute?
5. **Peer binding behind Docker Desktop.** Does the `app` container see overlay source addresses, or Docker's
   proxy address? One `curl` from the Mac and a log line answers it; it decides whether the `overlay` sidecar is
   needed for `app`.
6. **Service-user scope.** Does `GET /api/peers` with a *User*-role service token list every peer, or only the
   caller's? If only the caller's, the token must be Admin-role and is kept correspondingly carefully.
7. **Headscale instead?** If keeping the Tailscale clients matters more than open GUIs and invites, say so before
   Phase A; the adapter is written for both, but the migration plan differs (§5.1).
8. **Backup destination.** Where do the nightly tarballs go: a machine on the overlay, DO Spaces, or the
   operator's own storage? They contain the IdP's user records.
9. **Ollama in Docker on `shop`.** The earlier note installed native Ollama on Linux. The node compose moves it
   into a container (CPU only; Vulkan for an Intel iGPU would need extra device mounts). Is a possible iGPU
   speed-up worth keeping native Ollama on `shop` with `OLLAMA_HOST` on the overlay address instead?
10. **Serve identity headers under Headscale** (only if 7 is "yes"): worth a one-hour test before designing
    around their absence.
11. **Images' sizes.** Approvals 5–9 list no exact sizes; is "check `docker images` after the pull" acceptable, or
    should each be looked up on Docker Hub first?

---

## Sources (read today)

- Headscale: `LICENSE`; releases (v0.29.5); `config-example.yaml`; headscale.net `about/features` (stable and
  development), `ref/policy`, `ref/dns`, `ref/oidc`, `ref/api`, `ref/derp`, `setup/install/container`,
  `usage/getting-started`, `usage/connect/windows`, `usage/connect/apple`; issue #1921.
- Headplane: `LICENSE`; releases (v0.8.1); `config.example.yaml`; headplane.net `/install`, `/install/docker`.
- headscale-ui: `LICENSE.md`; releases (2026.03.17).
- Tailscale: `LICENSE`; releases (v1.104.1); tailscale.com/opensource; the "Tailscaled on macOS" wiki;
  kb/1312 (Serve headers); kb/1282 (Docker overview).
- NetBird: root `LICENSE`, `LICENSES/`, `management/LICENSE`, `signal/LICENSE`, `relay/LICENSE`, `proxy/LICENSE`;
  `netbirdio/dashboard` `LICENSE`; releases (v0.81.2, dashboard v2.95.0); `infrastructure_files/getting-started.sh`;
  docs: selfhosted quickstart, identity providers, local user management, manage network access, setup keys,
  settings/networks (DNS Domain), custom zones, reverse proxy, API peers, Docker client install, SQLite store;
  the AGPL announcement (4 August 2025, effective v0.53.0).
- Nebula: `LICENSE`; releases (v1.11.2); docs `config/relay`, `config/lighthouse`; `forgekeep/nebula-mesh`
  `LICENSE`, repository metadata and releases (v0.19.1).
- innernet `LICENSE`; wesher `LICENSE`; ZeroTier `LICENSE.txt`, `LICENSE-MPL.txt`, `nonfree/LICENSE.md`;
  wg-easy `LICENSE`, README and releases (v15.4.0).
- Pocket ID `LICENSE` and releases; Zitadel `LICENSE`; Authentik `LICENSE`; Dex `LICENSE`; Caddy `LICENSE` and
  releases; Traefik `LICENSE.md`; Ollama releases (v0.40.6).
- DigitalOcean droplet pricing page.

---

## Runbook for the dtech droplet

_19 October 2026. Research only, again: nothing was installed, run or contacted. This section adapts §3.1 to the
operator's existing droplet instead of a new one, and corrects one mistake in §3.1. The files are in
[`deploy/netbird-server/`](../../deploy/netbird-server/README.md) (server) and
[`deploy/lexflow-node/`](../../deploy/lexflow-node/README.md) (nodes, the Mac, and lexflow's `.env`); both compose
files parse with `docker compose config`._

**The box.** Ubuntu 22.04.5, 1 vCPU, 1.9 GB (1.1 GB free), 16 GB disk, Docker 29.1.4. Apache 2.4 owns 80 and
443 for a dozen sites with certbot (snap) certificates; Postgres, MariaDB, uvicorn, Streamlit, tailscaled, sshd
and postfix are also there. The operator wants the droplet to do the handshake only.

**Shape.** Three containers, 512 MB cap in total, two published ports, no Apache involvement:

| Container | Image (pinned, verified today) | Port | Cap |
|---|---|---|---|
| `caddy` | `caddy:2.11.7` | **8443/tcp**: TLS from the box's certbot files for `net.lexipedia.xyz`; routes gRPC (h2c), `/relay* /ws-proxy/* /api/* /oauth2/*` to the server and everything else to the dashboard, per the docs' "External Caddy" template | 64 MB |
| `netbird-server` | `netbirdio/netbird-server:0.81.3` (combined: management, signal, relay, STUN, embedded Dex; AGPL) | **3478/udp** STUN; plain `:80` on the compose network for Caddy | 384 MB |
| `dashboard` | `netbirdio/dashboard:v2.95.0` | none (compose network only) | 64 MB |

No separate signal, relay or coturn container exists in 0.81.x; the combined `config.yaml.example` states
"Management: Always runs locally … Signal: Local by default … Relay: Local by default … STUN: Local on port 3478"
[source]. The relay is on and idle until a peer pair cannot hole-punch.

**Why Caddy and not the server's own TLS.** `combined/config.yaml.example` has `server.tls.certFile/keyFile` and a
`letsencrypt` block [source], so the API, gRPC and relay could terminate TLS themselves. The dashboard image cannot
take certificate files (its `docker/init_cert.sh` only runs `certbot --nginx` inside the container, which would need
port 80) [source], so the one-port rule forces one front for both. Caddy is the lightest documented option.

**Corrections to §3.1 and §5.1.** (1) `NETBIRD_AGENT_NETWORK` is **not** the overlay address range: in
`getting-started.sh` it is a `true` switch for NetBird's "Agent Network" (LLM-API access) preset [source: the script's
header and `docs.netbird.io/agent-network/quickstart`]. The range is set in the dashboard, Settings → Networks →
**Network Range** (default: a random /16 inside `100.64.0.0/10`; changing it re-allocates every peer's IP, so do
it before the first peer joins) [source: `manage/settings/networks`]. `10.231.0.0/16` stays the choice for
coexistence with Tailscale. (2) The management URL everywhere is `https://net.lexipedia.xyz:8443`, with the port;
`exposedAddress`, `auth.issuer`, the redirect URIs and `dashboard.env` all carry it. (3) The backup unit is the
`netbird_data` volume plus `config.yaml`/`dashboard.env`/`compose.yml` [source: `maintenance/backup`]; the store
file names inside the volume are still [unconfirmed].

**Order of operations (exact commands in the server README).**

1. DNS: `net.lexipedia.xyz` → `137.184.50.98` (today it points at `134.209.128.119`); `dig +short` must show the
   new address before step 3; `mesh.lexipedia.xyz` stays unresolvable.
2. Firewall: DO cloud firewall inbound `8443/tcp`, `3478/udp` (Networking → Firewalls → Rules → Add inbound rule
   [source]); the same in ufw if ufw is active.
3. `sudo certbot certonly --apache -d net.lexipedia.xyz`; install `certbot-deploy-hook.sh` as
   `/etc/letsencrypt/renewal-hooks/deploy/netbird-caddy.sh` (restarts Caddy; `$RENEWED_LINEAGE` per certbot's docs
   [source]); `certbot renew --dry-run`.
4. `/opt/netbird-server`: copy the files, generate the three secrets (`authSecret`, `sessionCookieEncryptionKey`,
   `store.encryptionKey`) with `openssl rand -base64 32`, `chmod 600 config.yaml`, `docker compose config`.
5. `docker compose pull && docker compose up -d`; `/health` on the server's internal `:9000`; `docker stats`.
6. `https://net.lexipedia.xyz:8443/` → `/setup` (Owner: email, name, 8+ character password; the page then returns
   412 forever) [source]; Settings → Authentication → **Local MFA** → Save, re-login to enrol TOTP [source];
   Settings → Networks → Network Range `10.231.0.0/16`, DNS Domain `mesh.lexipedia.xyz`.
7. Groups `control`, `compute`, `admins`, `members` (Access Control → Groups); policies `pool-ollama`
   (`control`→`compute`, TCP 11434, 9101, one-way), `admin-dashboard` (`admins`→`control`, TCP 8000, one-way),
   `admin-ssh` (`admins`→`compute`, TCP 22, one-way); delete **Default** [source: `manage-network-access`];
   Settings → Setup Keys → Create: one-off, auto-assign `compute`, for `shop` [source]; Team → Service Users →
   role User (read-only) → token, into lexflow's `.env` only [source: `manage/public-api`].
8. `backup.sh` nightly at 04:00 (SQLite online backups of every `*.db` in the volume plus the config files; 14
   kept; copy off-box).

**Verify from elsewhere:** `curl -s https://net.lexipedia.xyz:8443/api/instance` → `{"setup_required":false}`
(unauthenticated [source: `api/resources/instance`]); `curl -sI https://net.lexipedia.xyz:8443/` → 200; with the
token, `GET /api/peers` lists the peers with `ip`, `connected`, `groups[]`, `dns_label` [source].

**Nodes.** `shop` runs the native `netbird` package (apt repo `https://pkgs.netbird.io/debian stable main`
[source]) rather than the container: native Ollama needs `wt0` on the host anyway, and the container route only
provides it as a privileged host-network container. Join: `sudo netbird up --setup-key … --management-url
https://net.lexipedia.xyz:8443 --hostname shop`. Ollama moves from the Tailscale IP to `OLLAMA_HOST=0.0.0.0:11434`
with ufw admitting 11434/9101 only `in on wt0` (and `tailscale0` until the move is done), or binds the NetBird IP
with `Restart=on-failure` and `After=netbird.service`; both in the node README. The compose there runs only the
status endpoint, published on the NetBird address. The Mac installs `netbird_0.81.3_darwin_arm64.pkg` (the only
signed build [source]) or `brew install --cask netbirdio/tap/netbird-ui`, enters the self-hosted URL in the GUI,
and sets `launchctl setenv OLLAMA_HOST "<netbird ip>:11434"` [source: Ollama FAQ].

**lexflow `.env`, final names:** `LEXFLOW_OVERLAY=netbird`, `LEXFLOW_OVERLAY_URL=https://net.lexipedia.xyz:8443`,
`LEXFLOW_OVERLAY_TOKEN=<service-user PAT>`, `LEXFLOW_OVERLAY_COMPUTE_GROUP=compute`,
`LEXFLOW_OVERLAY_RANGE=10.231.0.0/16`, `LEXFLOW_OVERLAY_POLL=60`; `LEXFLOW_LLM_NODES` keeps today's
`name=url|opt` format with `10.231.*` addresses as the fallback and the rollback (`LEXFLOW_OVERLAY=none`).

**Still [unconfirmed] after today's reading:** that `netbirdio/dashboard:v2.95.0` exists as a Docker Hub tag (the
first page of the tag list showed only `sha-*`/`pr-*`/`main`; the GitHub release is v2.95.0); the file names inside
`/var/lib/netbird`; the Dex discovery path `/oauth2/.well-known/openid-configuration`; the exact `doctl` inbound
rule string; whether the policy dialog takes a port list or one port per rule; NetBird 0.81.3 on Ubuntu 26.04 and
on macOS 27; running NetBird and Tailscale together on the Mac; the server's real idle memory on this box
(`docker stats` for a day); `alpine:3.22` as the current backup helper tag; and the earlier open questions 1, 3,
5 and 6 of §7.

**Sources added today:** `docs.netbird.io`: `selfhosted/selfhosted-quickstart`, `selfhosted/external-reverse-proxy`,
`selfhosted/maintenance/{configuration-files,backup,admin-cli}`, `selfhosted/identity-providers/{local,enable-local-mfa}`,
`selfhosted/sqlite-store`, `manage/settings/networks`, `manage/peers/register-machines-using-setup-keys`,
`manage/access-control/manage-network-access`, `manage/public-api`, `api/guides/authentication`,
`api/resources/{peers,instance}`, `get-started/cli`, `get-started/install/{linux,macos,docker,windows}`,
`client/environment-variables`, `agent-network/quickstart`; `github.com/netbirdio/netbird`: release v0.81.3 and its
assets, `combined/{config.yaml.example,Dockerfile,Dockerfile.multistage}`, `combined/cmd/config.go`,
`infrastructure_files/getting-started.sh`; `github.com/netbirdio/dashboard`: release v2.95.0,
`docker/{README.md,init_cert.sh,default.conf}`; Docker Hub tag lists for `netbirdio/netbird-server`,
`netbirdio/netbird`, `netbirdio/dashboard`, `library/caddy`; `caddyserver.com/docs/caddyfile/directives/{tls,reverse_proxy}`;
`eff-certbot.readthedocs.io` (using); `docs.digitalocean.com` (firewall rules); `docs.ollama.com/{faq,linux}`;
`github.com/ollama/ollama` release v0.40.6.
