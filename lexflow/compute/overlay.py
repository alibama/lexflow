"""The overlay as the source of the node list (docs/design/open-overlay.md §3.5).

``LEXFLOW_OVERLAY=netbird`` reads ``GET {LEXFLOW_OVERLAY_URL}/api/peers`` with ``Authorization: Token ...`` (a
read-only service user's token; the server reads, the browser never does) and keeps the peers whose groups include
``LEXFLOW_OVERLAY_COMPUTE_GROUP``.  Each becomes a node ``source='overlay'`` at ``http://<peer ip>:11434`` with the
status URL ``http://<peer ip>:9101/status.json``; ``connected`` sets its online state without a request.  A peer
that leaves the group is marked ``gone`` (no new work) and deleted once its leases are gone.  ``headscale`` has
the same interface over ``GET /api/v1/node`` (``Authorization: Bearer``), keeping nodes whose tags include the
group; ``none`` is today's behaviour: ``LEXFLOW_LLM_NODES`` alone.
"""
from __future__ import annotations

import ipaddress
import sys
from dataclasses import dataclass

import requests

from .. import config
from . import nodes as N

OLLAMA_PORT = 11434
STATUS_PORT = 9101


@dataclass(frozen=True)
class OverlayNode:
    name: str
    ip: str
    online: bool
    last_seen: str | None
    groups: tuple[str, ...]
    user: str | None
    os: str | None


class NetBirdOverlay:
    """``GET {url}/api/peers`` with ``Authorization: Token ...``; peers whose groups include ``group``."""

    def __init__(self, url: str | None = None, token: str | None = None, group: str | None = None, timeout: float = 10):
        self.url = (url or config.OVERLAY_URL).rstrip("/")
        self.token = token if token is not None else config.OVERLAY_TOKEN
        self.group = group or config.OVERLAY_COMPUTE_GROUP
        self.timeout = timeout

    def _peers(self) -> list[dict]:
        r = requests.get(f"{self.url}/api/peers", headers={"Authorization": f"Token {self.token}", "Accept": "application/json"},
                         timeout=self.timeout)
        r.raise_for_status()
        data = r.json()
        return data if isinstance(data, list) else []

    def list_nodes(self) -> list[OverlayNode]:
        out = []
        for p in self._peers():
            groups = tuple(g.get("name") for g in (p.get("groups") or []) if isinstance(g, dict) and g.get("name"))
            if self.group not in groups:
                continue
            label = (p.get("dns_label") or p.get("hostname") or p.get("name") or "").split(".")[0].lower()
            user = p.get("user_id") or (p.get("user") or {}).get("email") if isinstance(p.get("user"), dict) else p.get("user_id")
            out.append(OverlayNode(name=label, ip=str(p.get("ip") or ""), online=bool(p.get("connected")),
                                   last_seen=p.get("last_seen"), groups=groups, user=user, os=p.get("os")))
        return out


class HeadscaleOverlay:
    """``GET {url}/api/v1/node`` with ``Authorization: Bearer ...``; nodes whose tags include ``group`` (for
    example ``tag:compute``).  The same interface as NetBird's; mapped from the API's documented shape and not yet
    run against a Headscale server."""

    def __init__(self, url: str | None = None, token: str | None = None, group: str | None = None, timeout: float = 10):
        self.url = (url or config.OVERLAY_URL).rstrip("/")
        self.token = token if token is not None else config.OVERLAY_TOKEN
        self.group = group or config.OVERLAY_COMPUTE_GROUP
        self.timeout = timeout

    def list_nodes(self) -> list[OverlayNode]:
        r = requests.get(f"{self.url}/api/v1/node", headers={"Authorization": f"Bearer {self.token}", "Accept": "application/json"},
                         timeout=self.timeout)
        r.raise_for_status()
        out = []
        for n in (r.json() or {}).get("nodes", []):
            tags = tuple((n.get("validTags") or []) + (n.get("forcedTags") or []))
            if self.group not in tags:
                continue
            ips = [ip for ip in (n.get("ipAddresses") or []) if ":" not in ip] or (n.get("ipAddresses") or [])
            out.append(OverlayNode(name=(n.get("givenName") or n.get("name") or "").split(".")[0].lower(),
                                   ip=ips[0] if ips else "", online=bool(n.get("online")), last_seen=n.get("lastSeen"),
                                   groups=tags, user=(n.get("user") or {}).get("name"), os=None))
        return out


def adapter(kind: str | None = None):
    kind = (kind or config.OVERLAY or "none").lower()
    if kind == "netbird":
        return NetBirdOverlay()
    if kind == "headscale":
        return HeadscaleOverlay()
    return None


def in_range(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    nets = [config.OVERLAY_RANGE] + list(N.ALLOWED_NETS)
    for n in nets:
        try:
            if addr in ipaddress.ip_network(n, strict=False):
                return True
        except ValueError:
            continue
    return False


def sync(con, peers: list[OverlayNode] | None = None, log=None) -> dict:
    """Upsert the overlay's compute peers as ``overlay`` nodes; mark the ones that left as gone and delete those
    with no leases.  Returns counts.  Settings edited on the page survive (nodes.upsert keeps ``edited``)."""
    log = log or (lambda m: print(f"compute overlay: {m}", file=sys.stderr))
    if peers is None:
        ad = adapter()
        if ad is None:
            return {"kept": 0, "skipped": 0, "gone": 0}
        try:
            peers = ad.list_nodes()
        except (requests.RequestException, ValueError) as e:
            log(f"could not read the overlay: {type(e).__name__}: {str(e)[:160]}")
            return {"kept": 0, "skipped": 0, "gone": 0, "error": f"{type(e).__name__}"}
    kept, skipped = set(), 0
    for p in peers:
        if not N.NAME_RE.match(p.name or ""):
            log(f"peer {p.name!r} skipped: a node name is [a-z0-9-]{{1,20}}")
            skipped += 1
            continue
        if not in_range(p.ip):
            log(f"peer {p.name} skipped: {p.ip!r} is outside LEXFLOW_OVERLAY_RANGE ({config.OVERLAY_RANGE})")
            skipped += 1
            continue
        if p.name in N.env_urls():
            log(f"peer {p.name} skipped: LEXFLOW_LLM_NODES already names it")
            skipped += 1
            continue
        host = f"[{p.ip}]" if ":" in p.ip else p.ip
        N.upsert(con, {"name": p.name, "url": f"http://{host}:{OLLAMA_PORT}", "status_url": f"http://{host}:{STATUS_PORT}/status.json",
                       "overlay": {"connected": p.online, "last_seen": p.last_seen, "user": p.user, "os": p.os,
                                   "groups": list(p.groups)}}, source="overlay")
        if not p.online:
            con.execute("UPDATE nodes SET status='offline', last_error='overlay: disconnected', loaded='[]', checked_at=? "
                        "WHERE name=?", (N.now(), p.name))
        kept.add(p.name)
    gone = 0
    for r in con.execute("SELECT name FROM nodes WHERE source='overlay'").fetchall():
        if r["name"] not in kept:
            con.execute("UPDATE nodes SET gone=1, updated_at=? WHERE name=?", (N.now(), r["name"]))
            gone += con.execute("DELETE FROM nodes WHERE name=? AND gone=1 AND "
                                "NOT EXISTS (SELECT 1 FROM leases WHERE node=nodes.name)", (r["name"],)).rowcount
    con.commit()
    return {"kept": len(kept), "skipped": skipped, "gone": gone}
