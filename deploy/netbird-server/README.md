# NetBird control plane on the dtech droplet

The self-hosted overlay server from [`docs/design/open-overlay.md`](../../docs/design/open-overlay.md),
fitted to the operator's existing droplet instead of a fresh one. The droplet only does the handshake:
management, signalling, STUN and (idle unless needed) relay. It is never a member of the overlay and
never proxies to a node.

Written 19 October 2026 from the NetBird docs and the `netbirdio/netbird` repository. Every version
and key below was read there; anything that could not be read is marked **[unconfirmed]**. Nothing
here was run against the droplet.

## What is different from the design note

| Design note (§3.1) | This runbook | Why |
|---|---|---|
| `getting-started.sh` writes everything, Traefik on 80/443 | hand-written `compose.yml`, Caddy on **8443** | Apache owns 80/443 for a dozen sites; the operator wants no Apache involvement |
| Let's Encrypt inside Traefik | the box's own certbot (`certonly`, HTTP-01 through Apache's port 80) with a deploy hook | one certificate authority on the box, already working |
| `NETBIRD_AGENT_NETWORK=10.231.0.0/16` to pick the overlay range | **do not use that variable**: in the script it is a `true/false` switch for NetBird's "Agent Network" (LLM-API access) preset, not an IP range. The range is set in the dashboard: Settings → Networks → Network Range (source: the script header and `docs.netbird.io/manage/settings/networks`) | the design note misread the variable |
| 2 GB droplet for NetBird alone | 512 MB cap across three containers on a 1.9 GB box | the WordPress stack must never be starved |
| `netbird-server` + dashboard + Traefik (+ optional proxy, CrowdSec) | `netbird-server` + dashboard + Caddy | proxy and CrowdSec were already excluded |

Why a proxy at all, if the combined server can take certificate files? `combined/config.yaml.example`
does have `server.tls.certFile` / `keyFile` / `letsencrypt` (source), so the API, gRPC and relay could
terminate TLS themselves. The **dashboard** cannot: its image only knows `certbot --nginx` inside the
container (`docker/init_cert.sh`) and its README offers no custom-certificate path (source). A single
Caddy on 8443 is the documented "external reverse proxy" layout (`docs.netbird.io/selfhosted/external-reverse-proxy`,
"External Caddy", combined server) and keeps the operator's "one port" rule. Caddy 2.11.7 idles at a
few tens of MB.

Which image is the combined server: `netbirdio/netbird-server` (Docker Hub), built from `combined/`;
one process runs Management, Signal, Relay, STUN and the embedded IdP (Dex). "Management: Always runs
locally … Signal: Local by default … Relay: Local by default … STUN: Local on port 3478 by default"
(source: `combined/config.yaml.example`). **No separate signal, relay or coturn container is needed**
in 0.81.x; those belong to the legacy multi-container layout. `netbirdio/netbird` is the *client* image.

## Pinned versions (verified 19 Oct 2026)

| Image | Tag | Where verified |
|---|---|---|
| `netbirdio/netbird-server` | `0.81.3` | Docker Hub tags API (`0.81.3` pushed 2026-10-19T14:40Z); GitHub release `v0.81.3`, published 2026-10-19T13:50:20Z |
| `netbirdio/dashboard` | `v2.95.0` | GitHub `netbirdio/dashboard` latest release `v2.95.0` (15 Oct). The Hub tag list returned only `sha-*`/`pr-*`/`main` tags on its first page; that `v2.95.0` exists as a Hub tag is **[unconfirmed]** — `docker pull` will tell |
| `caddy` | `2.11.7` | Docker Hub tags API (`2.11.7` pushed 2026-10-14) |
| `netbirdio/netbird` (client, Linux nodes if containerised) | `0.81.3` | Docker Hub tags API (`0.81.3` pushed 2026-10-19T14:39Z) |
| `alpine` (backup helper) | `3.22` | not re-checked today, carried from the design note **[unconfirmed]** |

Doc URLs read: `docs.netbird.io/selfhosted/selfhosted-quickstart`, `/selfhosted/external-reverse-proxy`,
`/selfhosted/maintenance/configuration-files`, `/selfhosted/maintenance/backup`, `/selfhosted/maintenance/admin-cli`,
`/selfhosted/identity-providers/local`, `/selfhosted/identity-providers/enable-local-mfa`, `/selfhosted/sqlite-store`,
`/manage/settings/networks`, `/manage/peers/register-machines-using-setup-keys`, `/manage/access-control/manage-network-access`,
`/manage/public-api`, `/api/guides/authentication`, `/api/resources/peers`, `/api/resources/instance`, `/get-started/cli`,
`/get-started/install/linux`, `/get-started/install/macos`, `/get-started/install/docker`, `/client/environment-variables`;
`github.com/netbirdio/netbird`: `combined/config.yaml.example`, `combined/cmd/config.go`, `combined/Dockerfile`,
`infrastructure_files/getting-started.sh`; `github.com/netbirdio/dashboard`: `docker/README.md`, `docker/init_cert.sh`,
`docker/default.conf`; `caddyserver.com/docs/caddyfile/directives/{tls,reverse_proxy}`;
`eff-certbot.readthedocs.io/en/stable/using.html`; `docs.digitalocean.com/products/networking/firewalls/how-to/configure-rules/`.

## Files

| File | Purpose |
|---|---|
| `compose.yml` | the three services; memory caps; only 8443/tcp and 3478/udp published |
| `.env.example` → `.env` | image tags and the server memory cap |
| `config.yaml.example` → `config.yaml` (mode 600) | the combined server's config; three secrets to generate |
| `dashboard.env.example` → `dashboard.env` | dashboard URLs with `:8443` |
| `Caddyfile` | TLS from certbot's files; the three routes |
| `certbot-deploy-hook.sh` | restarts Caddy after a renewal |
| `backup.sh` | nightly state backup, 14 kept |

## One-time commands on the droplet, in order

All as a sudo-capable user. `/opt/netbird-server` is the install directory; change it in the two
scripts if another is used.

### 0. Preconditions

```sh
free -m; df -h /; docker --version; docker compose version     # 1.1 GB free, 16 GB disk, Docker 29.1.4, compose v2
sudo ss -ltnup | grep -E ':8443|:3478'                           # both must be free (expect no output)
```

### 1. DNS

`net.lexipedia.xyz` currently points at `134.209.128.119`; it must be `137.184.50.98` **before** certbot
runs (HTTP-01 is validated against the A record). Fix it at the registrar, then wait until:

```sh
dig +short net.lexipedia.xyz A            # must print exactly 137.184.50.98
dig +short net.lexipedia.xyz AAAA         # empty, unless the droplet has IPv6 and you add it on purpose
dig +short mesh.lexipedia.xyz             # must stay empty: the peer DNS domain must not resolve publicly
```

### 2. Firewall: DigitalOcean cloud firewall, then ufw if it is active

Control panel: **Networking → Firewalls → (the droplet's firewall) → Rules → Inbound rules → Add inbound
rule** (source). Add `Custom TCP 8443` and `Custom UDP 3478` from `All IPv4`. With `doctl`:

```sh
doctl compute firewall list
doctl compute firewall add-rules <firewall-id> \
  --inbound-rules "protocol:tcp,ports:8443,address:0.0.0.0/0 protocol:udp,ports:3478,address:0.0.0.0/0"
```

(`doctl … add-rules --inbound-rules` is documented; the `address:` source form was only shown in the
docs' outbound example, so the exact inbound string is **[unconfirmed]** — the control panel is the
sure path.)

On the box:

```sh
sudo ufw status            # if "inactive", skip; if active:
sudo ufw allow 8443/tcp comment 'netbird api/dashboard/relay'
sudo ufw allow 3478/udp comment 'netbird stun'
```

Docker publishes ports through its own iptables chains, ahead of ufw's INPUT rules, so the cloud
firewall is the one that actually gates these ports.

### 3. Certificate from the box's certbot (HTTP-01 through Apache's port 80)

```sh
sudo certbot certificates                                   # see what exists
sudo certbot certonly --apache -d net.lexipedia.xyz         # Apache plugin answers the challenge on :80
# or, if there is a webroot you prefer:  sudo certbot certonly --webroot -w /var/www/html -d net.lexipedia.xyz
sudo ls -l /etc/letsencrypt/live/net.lexipedia.xyz/         # fullchain.pem, privkey.pem (symlinks into archive/)
```

`certonly` issues the files without touching any Apache vhost. Then install the deploy hook and test
the renewal path:

```sh
sudo install -m 755 certbot-deploy-hook.sh /etc/letsencrypt/renewal-hooks/deploy/netbird-caddy.sh
sudo certbot renew --dry-run        # the hook is skipped on dry runs; it exits 0 for other lineages anyway
```

certbot's docs: "`/etc/letsencrypt/renewal-hooks/deploy`" scripts run "once for each successfully
issued certificate, including on subsequent renewals", with `$RENEWED_LINEAGE` pointing at the `live/`
subdirectory (source). The official `caddy` image runs as root, so the `0700` directories are readable
inside the container; if Caddy logs a permission error, certbot's docs say
`chmod 0755 /etc/letsencrypt/{live,archive}` is safe (source).

### 4. Install the files and generate the secrets

```sh
sudo mkdir -p /opt/netbird-server && cd /opt/netbird-server
# copy compose.yml .env.example config.yaml.example dashboard.env.example Caddyfile backup.sh here (scp or git)
cp .env.example .env
cp dashboard.env.example dashboard.env
cp config.yaml.example config.yaml && sudo chmod 600 config.yaml
# three secrets, as getting-started.sh generates them:
sed -i "s#REPLACE_ME_RELAY_SECRET#$(openssl rand -base64 32 | tr -d '=')#" config.yaml
sed -i "0,/REPLACE_ME_32_BYTE_BASE64/s##$(openssl rand -base64 32)#" config.yaml      # sessionCookieEncryptionKey
sed -i "0,/REPLACE_ME_32_BYTE_BASE64/s##$(openssl rand -base64 32)#" config.yaml      # store.encryptionKey
grep -c REPLACE_ME config.yaml      # must print 0
docker compose config >/dev/null && echo compose ok
```

Keep a copy of `config.yaml` with the backups: "losing `config.yaml`'s datastore key makes the store
unreadable" (design note §4.4; `store.encryptionKey` here).

### 5. Start

```sh
docker compose pull                 # three images; check sizes with: docker images
docker compose up -d
docker compose ps                   # all three "running"
docker compose logs -f netbird-server   # until it reports the listeners; Ctrl-C
# health, from inside the server container (ubuntu base has bash but no curl):
docker compose exec netbird-server bash -c 'exec 3<>/dev/tcp/127.0.0.1/9000; printf "GET /health HTTP/1.0\r\n\r\n" >&3; head -1 <&3'
docker stats --no-stream            # the three containers; expect well under 512 MB in total
```

### 6. First run: Owner with MFA

1. Open `https://net.lexipedia.xyz:8443/` — the dashboard redirects to `/setup` while
   `GET /api/instance` answers `{"setup_required": true}` (source). Enter email, name, password (8+
   characters). "The `/setup` page is only accessible when no users exist"; afterwards it returns 412
   and redirects to login (source).
2. Log in. **Settings → Authentication → Local MFA → Save** (source: enable-local-mfa). Log out and in
   again: you are asked to enrol a TOTP app. Keep the recovery path in mind: the admin CLI can reset it:
   `docker exec -it netbird-netbird-server-1 /go/bin/netbird-server --config /etc/netbird/config.yaml admin user reset-mfa --email <owner>`
   (source: admin-cli; container name is compose's default `<project>-<service>-1` — confirm with `docker compose ps`).
3. **Settings → Networks**:
   - **Network Range** → `10.231.0.0/16` (outside Tailscale's `100.64.0.0/10`, so both clients can run
     side by side during the move). Do this **before any peer joins**: "Changing the network range
     immediately re-allocates the NetBird IP of every peer" (source).
   - **DNS Domain** → `mesh.lexipedia.xyz` (must not resolve publicly; source).

### 7. Groups, policies, setup key

Groups (**Access Control → Groups**, or type a new name in any group field and press Enter; source):
`control`, `compute`, `admins`, `members`.

Policies (**Access Control → Policies → Add policy**; fields: source groups, destination groups,
protocol, ports, direction, name; source). All three are one-way, which NetBird allows only for TCP/UDP
with a port (source):

| Name | Source → Destination | Protocol / ports | Direction |
|---|---|---|---|
| `pool-ollama` | `control` → `compute` | TCP `11434`, `9101` | one-way (uncheck bidirectional) |
| `admin-dashboard` | `admins` → `control` | TCP `8000` | one-way |
| `admin-ssh` | `admins` → `compute` | TCP `22` | one-way |

The dashboard's port field takes a list; if it only takes one port per rule in this version, make two
rules inside `pool-ollama` **[unconfirmed]**.

Then delete the **Default** policy (Policies table → Delete → confirm; source). "The `Default` policy is
created when you first create your account" and allows all-to-all; "new policies will take effect once
you remove the `Default` policy" (source). With it gone and the three above in place, `members` can
reach nothing.

Setup key (**Settings → Setup Keys → Create Setup Key**; source): name `shop`, type **One-off**,
expiration 7 days (the dialog's default), **Auto-assign groups** `compute`, no ephemeral. Copy it once
into `deploy/lexflow-node/.env` on `shop`. Revoking it later does not disconnect the peer (source).

Read-only API token for lexflow (**Team → Service Users → create**, role **User** = read-only; then
select it and create a token with an expiry; the plain token is shown once; source: manage/public-api).
It goes into lexflow's `.env` as `LEXFLOW_OVERLAY_TOKEN` and nowhere else. Open question 6 of the design
note (does a User-role token list every peer?) is settled by the first `GET /api/peers` call.

### 8. Nightly backup

```sh
sudo install -m 700 backup.sh /opt/netbird-server/backup.sh
sudo mkdir -p /var/backups/netbird
docker volume ls | grep netbird_data        # confirm the volume name used in backup.sh (netbird_netbird_data)
sudo /opt/netbird-server/backup.sh          # first run by hand; prints the tarball path and size
( sudo crontab -l 2>/dev/null; echo '0 4 * * * /opt/netbird-server/backup.sh >> /var/log/netbird-backup.log 2>&1' ) | sudo crontab -
```

The docs' own backup is `docker compose stop; docker compose cp -a netbird-server:/var/lib/netbird/ backup/`
(source: maintenance/backup); `backup.sh` does the same without stopping the stack by taking SQLite
online backups of every `*.db` in the volume. The exact file names in `/var/lib/netbird` (store, IdP
store `idp.db`, events `events.db` per the configuration reference's defaults) are **[unconfirmed]**
until `docker compose exec netbird-server ls -la /var/lib/netbird` has been run once. Copy the
tarballs off the box; they hold the IdP's user records and the store key.

Restore (docs): new or same box, same domain, `docker compose create netbird-server`, `docker compose cp
-a backup/netbird/. netbird-server:/var/lib/netbird/`, copy `config.yaml` and `dashboard.env` back,
`docker compose up -d`. Peers keep their keys; nothing re-enrols.

## Verify from another machine

```sh
curl -s  https://net.lexipedia.xyz:8443/api/instance          # {"setup_required":false}  (no auth needed; source)
curl -sI https://net.lexipedia.xyz:8443/ | head -1             # HTTP/2 200 from the dashboard
curl -s  https://net.lexipedia.xyz:8443/oauth2/.well-known/openid-configuration | head -c 200   # Dex discovery; path [unconfirmed]
curl -s  -H "Authorization: Token $LEXFLOW_OVERLAY_TOKEN" https://net.lexipedia.xyz:8443/api/peers   # [] before any peer joins
openssl s_client -connect net.lexipedia.xyz:8443 -servername net.lexipedia.xyz </dev/null 2>/dev/null | openssl x509 -noout -dates -subject
```

STUN cannot be tested with curl; the first peer's `netbird status -d` shows whether it got a direct
connection, and the server log shows STUN bindings.

## Upgrading

Change the tag in `.env`, `docker compose pull && docker compose up -d`. Read the release notes first;
the server is AGPL and unmodified, so nothing else is required.

## Memory note

Caps: server 384 MB, Caddy 64 MB, dashboard 64 MB. The docs' "2 GB" minimum is for the whole quickstart
stack (Traefik, dashboard, optional proxy and CrowdSec) on a box doing nothing else; an idle combined
server with a handful of peers is far below that, but the real figure on this box is **[unconfirmed]**
until `docker stats` has been watched for a day. If the server container is OOM-killed, raise
`NETBIRD_SERVER_MEM` rather than removing the cap.
