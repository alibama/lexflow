"""Share the store through Turso (or a self-hosted libSQL server) over the Hrana HTTP API.

Turso and ``libsql-server`` both accept ``POST /v2/pipeline``; no native driver is needed.

* **push** sends local rows changed since the last push (optionally one state at a time);
* **pull** fetches rows for the states you ask for, so a new machine can load only what it
  needs, and the dashboard can pull a state the first time someone opens it;
* conflicts are settled last-writer-wins on ``updated_at``; every row keeps the ``origin``
  (machine) that wrote it.

``TURSO_DATABASE_URL`` may be ``libsql://<db>-<org>.turso.io`` (sent as https) or
``http://libsql:8080`` for the bundled server.  ``TURSO_AUTH_TOKEN`` is a database token.
"""
from __future__ import annotations

import base64
import json
import re
import sqlite3
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

import requests

from .. import config
from . import db

CHUNK_BYTES = 1_500_000
PAGE_ROWS = 500


class TursoError(RuntimeError):
    pass


def http_url(url: str) -> str:
    url = url.strip().rstrip("/")
    if url.startswith("libsql://"):
        url = "https://" + url[len("libsql://"):]
    elif url.startswith("wss://"):
        url = "https://" + url[len("wss://"):]
    elif url.startswith("ws://"):
        url = "http://" + url[len("ws://"):]
    if not re.match(r"^https?://", url):
        raise ValueError(f"not a libSQL URL: {url!r}")
    return url


def _arg(v: Any) -> dict:
    if v is None:
        return {"type": "null"}
    if isinstance(v, bool):
        return {"type": "integer", "value": str(int(v))}
    if isinstance(v, int):
        return {"type": "integer", "value": str(v)}
    if isinstance(v, float):
        return {"type": "float", "value": v}
    if isinstance(v, (bytes, bytearray)):
        return {"type": "blob", "base64": base64.b64encode(bytes(v)).decode()}
    if isinstance(v, (dict, list)):
        return {"type": "text", "value": json.dumps(v, ensure_ascii=False)}
    return {"type": "text", "value": str(v)}


def _value(v: dict) -> Any:
    t = v.get("type")
    if t == "null":
        return None
    if t == "integer":
        return int(v["value"])
    if t == "float":
        return float(v["value"])
    if t == "blob":
        return base64.b64decode(v.get("base64", ""))
    return v.get("value")


@dataclass
class Turso:
    url: str
    token: str | None = None
    timeout: int = 120
    session: requests.Session = field(default_factory=requests.Session)

    def __post_init__(self):
        self.base = http_url(self.url)
        if self.token:
            self.session.headers["Authorization"] = f"Bearer {self.token}"
        self.session.headers["User-Agent"] = config.USER_AGENT

    @classmethod
    def from_env(cls) -> "Turso | None":
        return cls(config.TURSO_URL, config.TURSO_TOKEN or None) if config.TURSO_URL else None

    def pipeline(self, statements: list[tuple[str, Iterable[Any]]]) -> list[dict]:
        """Run statements in order on one stream; returns one {cols, rows, affected} per statement."""
        reqs = [{"type": "execute", "stmt": {"sql": sql, "args": [_arg(a) for a in args]}}
                for sql, args in statements]
        reqs.append({"type": "close"})
        try:
            r = self.session.post(f"{self.base}/v2/pipeline", json={"baton": None, "requests": reqs},
                                  timeout=self.timeout)
        except requests.RequestException as e:
            raise TursoError(f"cannot reach {self.base}: {e}") from e
        if r.status_code in (401, 403):
            raise TursoError(f"{self.base} refused the token ({r.status_code})")
        if r.status_code >= 400:
            raise TursoError(f"{self.base} answered {r.status_code}: {r.text[:300]}")
        out = []
        for i, res in enumerate(r.json().get("results", [])[:len(statements)]):
            if res.get("type") == "error":
                msg = res.get("error", {}).get("message", "unknown error")
                raise TursoError(f"statement {i + 1} failed: {msg} [{statements[i][0][:120]}]")
            result = res["response"]["result"]
            cols = [c.get("name") for c in result.get("cols", [])]
            out.append({"cols": cols, "rows": [dict(zip(cols, map(_value, row))) for row in result.get("rows", [])],
                        "affected": result.get("affected_row_count", 0)})
        return out

    def query(self, sql: str, *args: Any) -> list[dict]:
        return self.pipeline([(sql, args)])[0]["rows"]

    def ping(self) -> bool:
        return self.query("SELECT 1 AS ok")[0]["ok"] == 1


# ------------------------------------------------------------------ schema
def remote_schema() -> list[str]:
    """CREATE statements for the shared tables, taken from the local schema."""
    out = []
    for stmt in db.SCHEMA.split(";"):
        s = stmt.strip()
        m = re.match(r"CREATE (?:TABLE|INDEX) IF NOT EXISTS (\w+)(?: ON (\w+))?", s)
        if m and (m.group(2) or m.group(1)) in db.SYNCED:
            out.append(s)
    return out


def ensure_schema(client: Turso) -> None:
    client.pipeline([(s, ()) for s in remote_schema()])


# ------------------------------------------------------------------- marks
def _scope(states: list[str] | None) -> str:
    return ",".join(sorted(states)) if states else "all"


def _mark(con: sqlite3.Connection, table: str, direction: str, scope: str) -> str | None:
    return db.scalar(con, "SELECT last_at FROM sync_marks WHERE table_name=? AND direction=? AND scope=?",
                     table, direction, scope)


def _set_mark(con, table, direction, scope, last_at):
    con.execute("INSERT INTO sync_marks(table_name, direction, scope, last_at) VALUES (?,?,?,?) "
                "ON CONFLICT(table_name, direction, scope) DO UPDATE SET last_at=excluded.last_at",
                (table, direction, scope, last_at))


def _state_filter(states: list[str] | None) -> tuple[str, list]:
    if not states:
        return "", []
    return f" AND state IN ({','.join('?' for _ in states)})", list(states)


def _upsert_sql(table: str, cols: list[str]) -> str:
    keys = db.SYNCED[table]
    update = [c for c in cols if c not in keys]
    return (f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join('?' for _ in cols)}) "
            f"ON CONFLICT ({', '.join(keys)}) DO UPDATE SET {', '.join(f'{c}=excluded.{c}' for c in update)} "
            f"WHERE excluded.updated_at >= {table}.updated_at")


# -------------------------------------------------------------------- push
def push(con: sqlite3.Connection, client: Turso, tables: list[str] | None = None, states: list[str] | None = None,
         full: bool = False, log: Callable[[str], None] = print) -> dict[str, int]:
    tables = tables or list(db.SYNCED)
    ensure_schema(client)
    scope = _scope(states)
    sent: dict[str, int] = {}
    for table in tables:
        cols = db.columns(con, table)
        since = None if full else _mark(con, table, "push", scope)
        where, args = _state_filter(states)
        if since:
            where += " AND updated_at >= ?"
            args.append(since)
        sql = _upsert_sql(table, cols)
        batch, size, count, newest = [], 0, 0, since
        cur = con.execute(f"SELECT {', '.join(cols)} FROM {table} WHERE 1=1{where} ORDER BY updated_at", args)
        for row in cur:
            values = tuple(row)
            batch.append((sql, values))
            size += sum(len(v) if isinstance(v, str) else 8 for v in values)
            newest = max(newest or "", row["updated_at"] or "")
            if size >= CHUNK_BYTES or len(batch) >= 400:
                client.pipeline([("BEGIN", ())] + batch + [("COMMIT", ())])
                count += len(batch)
                batch, size = [], 0
                log(f"push {table}: {count} rows")
        if batch:
            client.pipeline([("BEGIN", ())] + batch + [("COMMIT", ())])
            count += len(batch)
        if newest:
            _set_mark(con, table, "push", scope, newest)
        sent[table] = count
        log(f"push {table}: {count} rows sent")
    con.commit()
    return sent


# -------------------------------------------------------------------- pull
def pull(con: sqlite3.Connection, client: Turso, tables: list[str] | None = None, states: list[str] | None = None,
         full: bool = False, log: Callable[[str], None] = print) -> dict[str, int]:
    tables = tables or list(db.SYNCED)
    scope = _scope(states)
    got: dict[str, int] = {}
    for table in tables:
        cols = db.columns(con, table)
        since = None if full else _mark(con, table, "pull", scope)
        where, args = _state_filter(states)
        if since:
            where += " AND updated_at >= ?"
            args.append(since)
        last_rowid, count, newest = 0, 0, since
        while True:
            page = client.query(f"SELECT rowid AS _rowid, {', '.join(cols)} FROM {table} "
                                f"WHERE rowid > ?{where} ORDER BY rowid LIMIT {PAGE_ROWS}", last_rowid, *args)
            if not page:
                break
            last_rowid = page[-1]["_rowid"]
            for r in page:
                r.pop("_rowid", None)
                newest = max(newest or "", r.get("updated_at") or "")
            db.upsert(con, table, page, stamp=False, newer_only=True)
            count += len(page)
            if count % 5000 < PAGE_ROWS:
                log(f"pull {table}: {count} rows")
        if newest:
            _set_mark(con, table, "pull", scope, newest)
        got[table] = count
        log(f"pull {table}: {count} rows received")
    if any(got.values()):
        db.bump(con)
    con.commit()
    return got


# ------------------------------------------------------------------ status
def status(con: sqlite3.Connection, client: Turso | None) -> dict:
    local = {t: db.scalar(con, f"SELECT count(*) FROM {t}", default=0) for t in db.SYNCED}
    out = {"configured": client is not None, "url": client.base if client else None,
           "origin": config.ORIGIN, "local": local, "remote": None, "remote_states": {}, "error": None,
           "marks": db.rows(con, "SELECT * FROM sync_marks ORDER BY table_name, direction")}
    if client is None:
        return out
    try:
        ensure_schema(client)
        res = client.pipeline([(f"SELECT count(*) AS n FROM {t}", ()) for t in db.SYNCED] +
                              [("SELECT state, count(*) AS n FROM governments GROUP BY state", ()),
                               ("SELECT state, count(*) AS n FROM answers GROUP BY state", ()),
                               ("SELECT state, count(*) AS n FROM process_models GROUP BY state", ()),
                               ("SELECT origin, count(*) AS n, max(updated_at) AS last FROM process_models "
                                "GROUP BY origin", ())])
        out["remote"] = {t: res[i]["rows"][0]["n"] for i, t in enumerate(db.SYNCED)}
        k = len(db.SYNCED)
        states: dict[str, dict] = {}
        for key, part in (("governments", res[k]), ("answers", res[k + 1]), ("process_models", res[k + 2])):
            for r in part["rows"]:
                states.setdefault(r["state"], {})[key] = r["n"]
        out["remote_states"] = states
        out["contributors"] = res[k + 3]["rows"]
    except TursoError as e:
        out["error"] = str(e)
    return out


def log_sync(con: sqlite3.Connection, direction: str, tables, states, counts: dict | None, ok: bool, message: str,
             started: str) -> None:
    con.execute("INSERT INTO sync_log(direction, tables, states, rows, ok, message, started_at, finished_at) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (direction, json.dumps(tables), json.dumps(states), sum((counts or {}).values()), int(ok),
                 message, started, db.now()))
    con.commit()
