# lexflow pool nodes: `shop` (Linux), the Mac, and the lexflow side

Companion to [`deploy/netbird-server`](../netbird-server/README.md). Written 19 October 2026 from the
NetBird and Ollama docs; nothing was run on any node. **[unconfirmed]** marks what the docs do not say.

## 1. `shop` (Ubuntu 26.04, native Ollama already bound to its Tailscale IP)

### Native `netbird` package, not the container — why

- Ollama is native and must bind the overlay address, so the overlay interface (`wt0`) must exist on
  the host anyway. The container route only achieves that with `network_mode: host` plus `NET_ADMIN`,
  `SYS_ADMIN`, `SYS_RESOURCE` and `/dev/net/tun` (source: install/docker), i.e. a privileged container
  managing the host's network: more moving parts than a package, for nothing gained.
- The package installs a systemd unit that comes up before Ollama; the state (`/var/lib/netbird`,
  source: client env vars `NB_STATE_DIR`) survives upgrades; `netbird status`/`netbird ssh` work as the
  docs describe. Laptop sleep/resume is handled by the daemon, not by Docker's restart policy.
- The compose file still carries an `overlay` service behind the `container-overlay` profile for a
  node where a package is unwanted; it is not started by default.

### Install and join

```sh
# NetBird's apt repo and package (source: get-started/install/linux). Read the script before piping it,
# or add the repo by hand as the same page shows ("deb https://pkgs.netbird.io/debian stable main").
curl -fsSL https://pkgs.netbird.io/install.sh -o /tmp/netbird-install.sh && less /tmp/netbird-install.sh
sh /tmp/netbird-install.sh                 # CLI + daemon; the GTK UI is optional (netbird-ui)
sudo systemctl enable --now netbird
netbird version                            # expect 0.81.3 (release 19 Oct 2026)

# The join one-liner. --management-url is the flag the CLI documents, "[http|https]://[host]:[port]".
sudo netbird up --setup-key <KEY FROM THE DASHBOARD> --management-url https://net.lexipedia.xyz:8443 --hostname shop
netbird status -d                          # Management: Connected, Signal: Connected; NetBird IP: 10.231.x.y
ip addr show wt0                           # the interface (source: linux install page)
```

Every flag has an `NB_` environment form (`NB_SETUP_KEY`, `NB_MANAGEMENT_URL`, `NB_HOSTNAME`; source:
cli page); on the daemon they are set with `netbird service install --service-env` or `reconfigure`.
The setup key is used once; after that the peer's own WireGuard key in `/var/lib/netbird` is what logs
it in. The dashboard shows `shop` under Peers in group `compute` (from the key's auto-assign group).

Ubuntu 26.04 is newer than any distribution the docs list; the repo is a single `stable main` suite,
so it should install, but that is **[unconfirmed]** until tried. If nftables probing fails on a new
kernel, `NB_SKIP_NFTABLES_CHECK` exists (source: client env vars).

### Ollama: from the Tailscale IP to the NetBird IP

Today: `/etc/systemd/system/ollama.service.d/override.conf` has `Environment="OLLAMA_HOST=<tailscale ip>:11434"`
(Ollama's documented way: `systemctl edit ollama.service`, `Environment=` under `[Service]`, then
`daemon-reload` and `restart`; source: docs.ollama.com/faq).

Two ways; **A** is recommended because it survives the interface coming up after Ollama and lets both
overlays serve during the move.

**A. Bind all addresses, let the host firewall admit only the overlay interface(s).**

```sh
sudo systemctl edit ollama.service        # set:  [Service]\nEnvironment="OLLAMA_HOST=0.0.0.0:11434"
sudo ufw status verbose                   # default must be "deny (incoming)"; if ufw is inactive:
sudo ufw default deny incoming && sudo ufw default allow outgoing && sudo ufw allow in on wt0 to any port 22 proto tcp
sudo ufw allow in on wt0 to any port 11434 proto tcp comment 'ollama via netbird'
sudo ufw allow in on wt0 to any port 9101  proto tcp comment 'lexflow status via netbird'
sudo ufw allow in on tailscale0 to any port 11434 proto tcp comment 'ollama via tailscale (remove after the move)'
sudo ufw enable
sudo systemctl daemon-reload && sudo systemctl restart ollama
ss -ltn | grep 11434                      # 0.0.0.0:11434
```

(Keep whatever ufw rules already exist for the LAN or SSH; `ufw status numbered` before touching it.)
NetBird itself also enforces the overlay policy on `wt0` with its own nftables table (`NB_NFTABLES_TABLE`,
default `netbird`; source), so even on `wt0` only `control` peers reach 11434. The Host-header
rebinding guard that `127.0.0.1` gave is gone, as the design note's §2 item 2 accepted.

**B. Bind the NetBird address only** (closest to today's setup):

```sh
sudo systemctl edit ollama.service
# [Service]
# Environment="OLLAMA_HOST=10.231.x.y:11434"
# Restart=on-failure
# RestartSec=5
# [Unit]
# After=netbird.service
# Wants=netbird.service
sudo systemctl daemon-reload && sudo systemctl restart ollama
```

Ollama fails to bind until `wt0` has its address; the `Restart=` lines cover that. The systemd unit name
of the NetBird daemon is `netbird` (source: `sudo systemctl status netbird` on the Linux page).

Either way, from the Windows box (group `control`), once it has joined:
`curl http://10.231.x.y:11434/api/version` must answer; from a `members` device or the droplet it must
not.

### The status endpoint

```sh
cd deploy/lexflow-node && cp .env.example .env && $EDITOR .env     # NODE_OVERLAY_IP from `netbird status`
docker compose config >/dev/null && docker compose up -d status
curl http://10.231.x.y:9101/status.json                             # from a control peer
```

`status.py` is stdlib Python; it reads `/proc/loadavg` and `/proc/meminfo` (the host's, inside a
container), thermal and power from the two read-only `/sys` mounts, and Ollama's `/api/version` through
Docker's host gateway. `LEXFLOW_NODE_ACCEPT=0` + `docker compose up -d status` takes the node out of
rotation without leaving the overlay.

### Leaving / rollback

`sudo netbird down` stops the overlay (keys kept); `tailscale` is untouched throughout. To remove:
`sudo netbird service uninstall`, delete the peer in the dashboard, `apt remove netbird`.

## 2. The Mac (macOS 27, Apple silicon)

- **Install**, either (source: get-started/install/macos):
  - Homebrew: `brew install --cask netbirdio/tap/netbird-ui` (GUI + daemon), or CLI only
    `brew install netbirdio/tap/netbird && sudo netbird service install && sudo netbird service start`.
  - The signed package: `netbird_0.81.3_darwin_arm64.pkg` from the `v0.81.3` release assets
    (`github.com/netbirdio/netbird/releases/tag/v0.81.3`), also linked as `https://pkgs.netbird.io/macos/arm64`.
    "Only the official .pkg contains signed binaries"; the tarballs are not notarized (source). The pkg
    installs `/Applications/NetBird.app` and a launchd daemon `/Library/LaunchDaemons/netbird.plist`
    running as root (source).
  - macOS 27 is newer than anything the docs mention; whether 0.81.3 runs on it unchanged is
    **[unconfirmed]** (no system extension is involved; the client uses a `utun` device).
- **Join**, either:
  - GUI: first launch → choose the self-hosted option and enter `https://net.lexipedia.xyz:8443` → the
    browser opens the embedded IdP login (source: "On first launch, choose NetBird Cloud or enter the
    URL of your self-hosted deployment"). Log in as the operator's user; the Mac appears under that
    user. Add it to `compute` (and `admins`) in Peers → Groups.
  - CLI: `sudo netbird up --management-url https://net.lexipedia.xyz:8443` (SSO in the browser), or with a
    setup key as on Linux. `netbird status -d`; the interface is `utun100` (source: `sudo ifconfig utun100`).
- **Coexistence with Tailscale.** The docs say nothing about other VPNs. The two use separate `utun`
  devices and, with the Network Range set to `10.231.0.0/16`, disjoint address ranges, so routes do not
  overlap; DNS: NetBird only claims `mesh.lexipedia.xyz` and Tailscale its MagicDNS suffix. Running both
  at once is therefore expected to work but is **[unconfirmed]** until the Mac has done it for a day.
  The work MacBook's MDM is open question 3 of the design note.
- **Ollama (native, Metal).** `launchctl setenv OLLAMA_HOST "10.231.x.y:11434"` then restart the Ollama
  app (source: docs.ollama.com/faq, "If Ollama is run as a macOS application, environment variables
  should be set using `launchctl`"). `launchctl setenv` does not survive a reboot; a LaunchAgent that
  runs the same command at login, or `OLLAMA_HOST=0.0.0.0:11434` with the macOS application firewall
  limited to the NetBird app, are the persistent forms **[unconfirmed which the operator prefers]**.
  `OLLAMA_ORIGINS` is not needed (lexflow is not a browser origin).
- The status endpoint is optional on the Mac (`python3 -I status.py` under launchd, bound to the NetBird
  address by changing the last line, or none).

## 3. The lexflow side: `.env` values that will not need renaming

From `docs/design/open-overlay.md` §3.5, with the port and the IPs this deployment produces:

```sh
# overlay adapter (Phase A): the inventory comes from the NetBird API
LEXFLOW_OVERLAY=netbird
LEXFLOW_OVERLAY_URL=https://net.lexipedia.xyz:8443
LEXFLOW_OVERLAY_TOKEN=<read-only service-user token from Team -> Service Users; never leaves the server>
LEXFLOW_OVERLAY_COMPUTE_GROUP=compute
LEXFLOW_OVERLAY_RANGE=10.231.0.0/16
LEXFLOW_OVERLAY_POLL=60

# fallback / until Phase A lands: the hand list, in the format lexflow/ask/coverage.py already parses
# (name=url|opt, ...). Replace the 10.231.* addresses with the ones `netbird status` prints.
LEXFLOW_LLM_NODES=local=http://ollama:11434|embed, shop=http://10.231.x.y:11434|threads=6|status=http://10.231.x.y:9101/status.json, mac=http://10.231.x.z:11434|part_time
```

`LEXFLOW_OVERLAY=none` (or unset) keeps `LEXFLOW_LLM_NODES` in charge, which is the rollback. The API
the adapter will call: `GET /api/peers` with `Authorization: Token <PAT>`, fields `id, name, ip,
connected, last_seen, os, version, groups[].name, dns_label, hostname, user_id, login_expired`
(source: api/resources/peers).

Pinned client tag for the optional container route: `netbirdio/netbird:0.81.3` (Docker Hub, pushed
2026-10-19). Ollama's current release is `v0.40.6` (GitHub, 2026-10-16) for whoever pins it on a node.
