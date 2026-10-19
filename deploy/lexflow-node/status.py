"""Tiny status endpoint for a lexflow pool node. Stdlib only; run with ``python -I``.

GET /status.json -> JSON; anything else -> 404. Binds 0.0.0.0:9101 inside the container; the
compose file publishes it on the node's NetBird address only.
"""
from __future__ import annotations

import json
import os
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

STARTED = time.time()


def _read(path: str) -> str | None:
    try:
        with open(path, encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return None


def _loadavg() -> list[float] | None:
    raw = _read("/proc/loadavg")
    return [float(x) for x in raw.split()[:3]] if raw else None


def _meminfo() -> dict[str, int]:
    out: dict[str, int] = {}
    raw = _read("/proc/meminfo") or ""
    for line in raw.splitlines():
        key, _, rest = line.partition(":")
        if key in ("MemTotal", "MemAvailable"):
            out[key] = int(rest.split()[0]) // 1024  # MiB
    return out


def _temperature_c() -> float | None:
    base = "/host/thermal"
    try:
        zones = sorted(d for d in os.listdir(base) if d.startswith("thermal_zone"))
    except OSError:
        return None
    temps = []
    for z in zones:
        raw = _read(f"{base}/{z}/temp")
        if raw and raw.lstrip("-").isdigit():
            temps.append(int(raw) / 1000.0)
    return max(temps) if temps else None


def _on_battery() -> bool | None:
    base = "/host/power"
    try:
        supplies = os.listdir(base)
    except OSError:
        return None
    for s in supplies:
        if (_read(f"{base}/{s}/type") or "") == "Mains":
            online = _read(f"{base}/{s}/online")
            if online is not None:
                return online == "0"
    return None


def _ollama_version(url: str) -> str | None:
    try:
        with urllib.request.urlopen(f"{url.rstrip('/')}/api/version", timeout=2) as r:  # noqa: S310
            return json.load(r).get("version")
    except Exception:  # noqa: BLE001
        return None


def status() -> dict:
    mem = _meminfo()
    return {
        "node": os.environ.get("LEXFLOW_NODE_NAME", ""),
        "accept": os.environ.get("LEXFLOW_NODE_ACCEPT", "1") == "1",
        "slots": int(os.environ.get("LEXFLOW_NODE_SLOTS", "1") or 1),
        "hours": os.environ.get("LEXFLOW_NODE_HOURS") or None,
        "models_allowed": [m for m in (os.environ.get("LEXFLOW_NODE_MODELS") or "").split(",") if m],
        "load": _loadavg(),
        "mem_total_mib": mem.get("MemTotal"),
        "mem_available_mib": mem.get("MemAvailable"),
        "temperature_c": _temperature_c(),
        "on_battery": _on_battery(),
        "ollama_version": _ollama_version(os.environ.get("OLLAMA_URL", "http://host-gateway:11434")),
        "uptime_s": int(time.time() - STARTED),
    }


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if self.path != "/status.json":
            self.send_error(404)
            return
        body = json.dumps(status()).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_: object) -> None:
        return


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 9101), Handler).serve_forever()
