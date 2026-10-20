"""The node list: ``data/compute.db`` (this copy's own; never synced), the ``LEXFLOW_LLM_NODES`` parser and the
URL allow-list.

``LEXFLOW_LLM_NODES`` is ``name=url|opt|key=value, ...``: ``threads=7`` (sent as ``options.num_thread``), ``max=1``
(calls at once; ``slots`` is an alias), ``status=http://...`` (the node's host-status JSON), ``embed`` (this node
embeds), ``tags=cpu+gpu``, ``models=qwen3:8b+qwen3:14b`` (the models wanted there, shown on the Compute page),
``priority=50``, ``part_time``.  Names are ``[a-z0-9-]{1,20}``.

Node URLs come only from the environment or the overlay, never from the API, and every host must be on the
allow-list (compose service names, localhost, the CGNAT and overlay ranges, ``*.ts.net``,
``*.mesh.lexipedia.xyz``): a typo can then never send statute text to a public host.  Nothing discovers nodes.
"""
from __future__ import annotations

import ipaddress
import json
import re
import sqlite3
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from .. import config

NAME_RE = re.compile(r"^[a-z0-9-]{1,20}$")
MODEL_RE = re.compile(r"^[a-z0-9][a-z0-9._/-]{0,60}(:[a-z0-9._-]{1,40})?$")
ALLOWED_HOSTS = {"localhost", "host.docker.internal"}
ALLOWED_SUFFIXES = (".ts.net", ".mesh.lexipedia.xyz")
ALLOWED_NETS = ("100.64.0.0/10", "10.231.0.0/16", "fd7a:115c:a1e0::/48", "127.0.0.0/8", "::1/128")
COMPOSE_NAME_RE = re.compile(r"^[a-z][a-z0-9_-]{0,40}$")      # a compose service name: one label, no dots

SCHEMA = """
CREATE TABLE IF NOT EXISTS nodes (
  name TEXT PRIMARY KEY,
  url TEXT NOT NULL,
  source TEXT NOT NULL DEFAULT 'env',      -- env | overlay
  enabled INTEGER NOT NULL DEFAULT 1,      -- 0 = disabled by the operator: no new work
  draining INTEGER NOT NULL DEFAULT 0,     -- 1 = calls in flight finish, no new ones
  max_concurrency INTEGER NOT NULL DEFAULT 1,
  threads INTEGER,
  priority INTEGER NOT NULL DEFAULT 50,
  tags TEXT NOT NULL DEFAULT '[]',
  models_wanted TEXT NOT NULL DEFAULT '[]',
  embed INTEGER NOT NULL DEFAULT 0,
  status_url TEXT,
  part_time INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'unknown',  -- online | backoff | offline | unknown
  fails INTEGER NOT NULL DEFAULT 0,
  backoff_until TEXT,
  version TEXT,
  models TEXT,                             -- JSON from /api/tags
  loaded TEXT,                             -- JSON from /api/ps
  host TEXT,                               -- JSON from the status URL
  last_ok TEXT, last_error TEXT, checked_at TEXT,
  edited TEXT NOT NULL DEFAULT '{}',       -- settings changed on the Compute page: they survive a re-sync
  gone INTEGER NOT NULL DEFAULT 0,         -- an overlay peer that left the group: deleted once its leases are gone
  overlay TEXT,                            -- JSON: connected, last_seen, user, os
  updated_at TEXT
);
CREATE TABLE IF NOT EXISTS leases (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  node TEXT NOT NULL, model TEXT NOT NULL, kind TEXT NOT NULL,
  job_id INTEGER, step TEXT, runner TEXT, pid INTEGER,
  started_at TEXT NOT NULL, beat_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS leases_node ON leases(node);
CREATE TABLE IF NOT EXISTS calls (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  at TEXT NOT NULL, node TEXT NOT NULL, model TEXT NOT NULL, digest TEXT, kind TEXT NOT NULL,
  job_id INTEGER, step TEXT, num_ctx INTEGER, attempt INTEGER NOT NULL DEFAULT 1,
  prompt_tokens INTEGER, prompt_s REAL, out_tokens INTEGER, out_s REAL,
  load_s REAL, total_s REAL, wait_s REAL,
  ok INTEGER NOT NULL, error TEXT
);
CREATE INDEX IF NOT EXISTS calls_at ON calls(at);
CREATE INDEX IF NOT EXISTS calls_job ON calls(job_id);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
"""

_ready: set[str] = set()
_lock = threading.Lock()
REFUSED: list[str] = []          # entries of LEXFLOW_LLM_NODES refused at the last sync, for the Compute page


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def pool_on() -> bool:
    """The pool is on when nodes are configured or an overlay lists them; otherwise today's single OLLAMA_URL."""
    return bool(config.LLM_NODES.strip()) or config.OVERLAY in ("netbird", "headscale")


def db_path() -> Path:
    return config.DATA_DIR / "compute.db"


def connect(path: Path | str | None = None) -> sqlite3.Connection:
    path = Path(path or db_path())
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(path), timeout=60, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA busy_timeout=60000")
    key = str(path.resolve())
    if key not in _ready:
        with _lock:
            con.executescript(SCHEMA)
            _ready.add(key)
    return con


# ------------------------------------------------------------------------------------------------ allow-list
def url_allowed(url: str) -> bool:
    """http(s) to a compose service name, localhost, the CGNAT (100.64/10) or overlay (10.231/16, the ULA
    fd7a:115c:a1e0::/48, LEXFLOW_OVERLAY_RANGE) ranges, or a *.ts.net / *.mesh.lexipedia.xyz name."""
    try:
        u = urlsplit(url)
    except ValueError:
        return False
    if u.scheme not in ("http", "https") or not u.hostname:
        return False
    host = u.hostname.lower().rstrip(".")
    if host in ALLOWED_HOSTS or any(host.endswith(s) for s in ALLOWED_SUFFIXES):
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return bool(COMPOSE_NAME_RE.match(host))         # a compose service name: one label, no dots
    nets = list(ALLOWED_NETS) + ([config.OVERLAY_RANGE] if config.OVERLAY_RANGE else [])
    for n in nets:
        try:
            if ip in ipaddress.ip_network(n, strict=False):
                return True
        except ValueError:
            continue
    return False


# ------------------------------------------------------------------------------------------------ the env list
def parse_entry(part: str) -> dict:
    """One ``name=url|opt|key=value`` entry; raises ValueError for a bad name, URL or option."""
    part = part.strip()
    if "=" not in part:
        raise ValueError(f"{part!r}: expected name=url")
    name, rest = part.split("=", 1)
    name = name.strip()
    if not NAME_RE.match(name):
        raise ValueError(f"{name!r}: a node name is [a-z0-9-]{{1,20}}")
    bits = [b.strip() for b in rest.split("|")]
    url = bits[0].rstrip("/")
    if not url_allowed(url):
        raise ValueError(f"{name}: {url!r} is not on the allow-list (compose service names, localhost, "
                         "100.64.0.0/10, 10.231.0.0/16, fd7a:115c:a1e0::/48, *.ts.net, *.mesh.lexipedia.xyz)")
    node = {"name": name, "url": url, "threads": None, "max_concurrency": 1, "status_url": None, "embed": 0,
            "tags": [], "models_wanted": [], "priority": 50, "part_time": 0}
    for opt in bits[1:]:
        if not opt:
            continue
        k, _, v = opt.partition("=")
        k = k.strip().lower()
        v = v.strip()
        if k == "threads":
            node["threads"] = max(1, min(64, int(v)))
        elif k in ("max", "slots"):
            node["max_concurrency"] = max(1, min(8, int(v)))
        elif k == "status":
            if not url_allowed(v):
                raise ValueError(f"{name}: status URL {v!r} is not on the allow-list")
            node["status_url"] = v
        elif k == "embed":
            node["embed"] = 1
        elif k == "part_time":
            node["part_time"] = 1
        elif k == "tags":
            node["tags"] = [t for t in re.split(r"[+;]", v) if t]
        elif k == "models":
            node["models_wanted"] = [m for m in re.split(r"[+;]", v) if m]
        elif k == "priority":
            node["priority"] = max(0, min(100, int(v)))
        else:
            raise ValueError(f"{name}: unknown option {k!r}")
    return node


def parse_env(text: str | None = None) -> tuple[list[dict], list[str]]:
    """Every entry of LEXFLOW_LLM_NODES (or ``text``): the good ones, and the reasons the others were refused."""
    text = config.LLM_NODES if text is None else text
    good, bad = [], []
    for part in (text or "").split(","):
        if not part.strip():
            continue
        try:
            good.append(parse_entry(part))
        except (ValueError, TypeError) as e:
            bad.append(str(e))
    return good, bad


def env_urls() -> dict[str, str]:
    """name -> url from the environment alone (no database)."""
    return {n["name"]: n["url"] for n in parse_env()[0]}


# -------------------------------------------------------------------------------------------------- the table
def _row(r) -> dict:
    d = dict(r)
    for k in ("tags", "models_wanted", "models", "loaded", "host", "edited", "overlay"):
        v = d.get(k)
        try:
            d[k] = json.loads(v) if v else ([] if k in ("tags", "models_wanted", "models", "loaded") else {} if k == "edited" else None)
        except ValueError:
            d[k] = None
    return d


def load_nodes(con) -> list[dict]:
    return [_row(r) for r in con.execute("SELECT * FROM nodes ORDER BY name")]


def get_node(con, name: str) -> dict | None:
    r = con.execute("SELECT * FROM nodes WHERE name=?", (name,)).fetchone()
    return _row(r) if r else None


def names(con=None) -> list[str]:
    """Every configured node name: the environment's plus the overlay's rows."""
    out = list(env_urls())
    if pool_on():
        c = con or connect()
        try:
            out += [r["name"] for r in c.execute("SELECT name FROM nodes WHERE gone=0")]
        finally:
            if con is None:
                c.close()
    return sorted(dict.fromkeys(out))


def url_of(name: str, con=None) -> str | None:
    """The URL of a configured node, from the environment first, else the table (overlay nodes)."""
    urls = env_urls()
    if name in urls:
        return urls[name]
    if not pool_on():
        return None
    c = con or connect()
    try:
        r = c.execute("SELECT url FROM nodes WHERE name=? AND gone=0", (name,)).fetchone()
        return r["url"] if r else None
    finally:
        if con is None:
            c.close()


def name_for_url(url: str, con=None) -> str:
    """The configured name of a URL, else its host (how coverage.node_of names an unconfigured Ollama)."""
    u = (url or "").rstrip("/")
    for n, nu in env_urls().items():
        if nu == u:
            return n
    if pool_on():
        c = con or connect()
        try:
            r = c.execute("SELECT name FROM nodes WHERE url=?", (u,)).fetchone()
            if r:
                return r["name"]
        finally:
            if con is None:
                c.close()
    return urlsplit(u).hostname or u


def upsert(con, node: dict, source: str = "env") -> None:
    """Insert or refresh a node row.  Settings the operator edited on the Compute page (``edited``) win over the
    environment's or the overlay's values, so a re-sync never undoes a drain or a thread count."""
    cur = get_node(con, node["name"])
    edited = (cur or {}).get("edited") or {}
    vals = {"name": node["name"], "url": node["url"].rstrip("/"), "source": source,
            "max_concurrency": int(node.get("max_concurrency") or 1), "threads": node.get("threads"),
            "priority": int(node.get("priority") or 50), "tags": json.dumps(node.get("tags") or []),
            "models_wanted": json.dumps(node.get("models_wanted") or []), "embed": int(node.get("embed") or 0),
            "status_url": node.get("status_url"), "part_time": int(node.get("part_time") or 0),
            "gone": 0, "updated_at": now()}
    for k in ("max_concurrency", "threads", "enabled", "draining"):
        if k in edited:
            vals[k] = edited[k]
    if "overlay" in node:
        vals["overlay"] = json.dumps(node["overlay"])
    if cur is None:
        vals.setdefault("enabled", 1)
        vals.setdefault("draining", 0)
        cols = ", ".join(vals)
        con.execute(f"INSERT INTO nodes ({cols}) VALUES ({', '.join('?' for _ in vals)})", list(vals.values()))
    else:
        sets = ", ".join(f"{k}=?" for k in vals if k != "name")
        con.execute(f"UPDATE nodes SET {sets} WHERE name=?", [v for k, v in vals.items() if k != "name"] + [node["name"]])


def sync_env(con) -> list[dict]:
    """Make the table's ``env`` rows match LEXFLOW_LLM_NODES: upsert the entries, drop the rows no longer listed
    (once their leases are gone).  Refused entries are logged and kept in ``REFUSED`` for the page."""
    good, bad = parse_env()
    REFUSED[:] = bad
    for msg in bad:
        print(f"compute: LEXFLOW_LLM_NODES entry refused: {msg}", file=sys.stderr)
    if not good and not bad and config.OVERLAY == "none":
        return []
    keep = {n["name"] for n in good}
    for n in good:
        upsert(con, n, "env")
    for r in con.execute("SELECT name FROM nodes WHERE source='env'").fetchall():
        if r["name"] not in keep:
            con.execute("DELETE FROM nodes WHERE name=? AND source='env' AND "
                        "NOT EXISTS (SELECT 1 FROM leases WHERE node=nodes.name)", (r["name"],))
    con.commit()
    return good


def embed_node(con=None) -> tuple[str, str]:
    """``(name, url)`` of the one node that embeds: LEXFLOW_EMBED_URL, else the node marked ``embed``, else the
    first node of the environment, else OLLAMA_URL (named after its host)."""
    if config.EMBED_URL:
        u = config.EMBED_URL.rstrip("/")
        return name_for_url(u, con), u
    if pool_on():
        env, _ = parse_env()
        for n in env:
            if n["embed"]:
                return n["name"], n["url"]
        c = con or connect()
        try:
            r = c.execute("SELECT name, url FROM nodes WHERE embed=1 AND gone=0 ORDER BY name").fetchone()
            if r:
                return r["name"], r["url"]
        finally:
            if con is None:
                c.close()
        if env:
            return env[0]["name"], env[0]["url"]
    u = config.OLLAMA_URL.rstrip("/")
    return name_for_url(u, con), u


def set_edited(con, name: str, **changes) -> dict | None:
    """Record settings changed on the Compute page (max_concurrency, threads, enabled, draining) on the row and in
    ``edited``, so they survive the next sync."""
    cur = get_node(con, name)
    if cur is None:
        return None
    edited = dict(cur.get("edited") or {})
    sets, vals = [], []
    for k, v in changes.items():
        if k not in ("max_concurrency", "threads", "enabled", "draining"):
            raise ValueError(f"cannot edit {k}")
        edited[k] = v
        sets.append(f"{k}=?")
        vals.append(v)
    sets.append("edited=?")
    vals.append(json.dumps(edited))
    sets.append("updated_at=?")
    vals.append(now())
    con.execute(f"UPDATE nodes SET {', '.join(sets)} WHERE name=?", vals + [name])
    con.commit()
    return get_node(con, name)
