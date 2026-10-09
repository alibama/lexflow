"""Runtime settings, read from the environment (see .env.example).

Everything the product writes lives under ``LEXFLOW_DATA`` (``/data`` in Docker,
``./data`` otherwise): the SQLite store, downloaded public data, job logs and
built models.  Nothing outside it is modified at run time.
"""
from __future__ import annotations

import os
import socket
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


DATA_DIR = Path(_env("LEXFLOW_DATA", str(ROOT / "data")))
DB_PATH = Path(_env("LEXFLOW_DB", str(DATA_DIR / "lexflow.db")))
RAW_DIR = DATA_DIR / "raw"
JOBS_DIR = DATA_DIR / "jobs"
BUILD_DIR = DATA_DIR / "build"
CURATED_DIR = ROOT / "curated"
DASHBOARD_DIR = ROOT / "dashboard"
WEB_VENDOR_DIR = Path(_env("LEXFLOW_WEB_VENDOR", str(ROOT / "tools" / "web" / "node_modules")))

OLLAMA_URL = _env("OLLAMA_URL", "http://localhost:11434")
SEARXNG_URL = _env("SEARXNG_URL", "")
MODEL_A = _env("LEXFLOW_MODEL_A", "qwen3:1.7b")
MODEL_B = _env("LEXFLOW_MODEL_B", "gemma3:1b")
NUM_CTX = int(_env("LEXFLOW_NUM_CTX", "16384"))

TURSO_URL = _env("TURSO_DATABASE_URL")
TURSO_TOKEN = _env("TURSO_AUTH_TOKEN")
ORIGIN = _env("LEXFLOW_ORIGIN", socket.gethostname())

DOKUWIKI_URL = _env("DOKUWIKI_URL")
DOKUWIKI_TOKEN = _env("DOKUWIKI_TOKEN")

USER_AGENT = _env("LEXFLOW_USER_AGENT", "lexflow/1.0 (+https://github.com/alibama/lexflow)")
MAX_JOBS = int(_env("LEXFLOW_MAX_JOBS", "2"))


def ensure_dirs() -> None:
    for d in (DATA_DIR, RAW_DIR, JOBS_DIR, BUILD_DIR):
        d.mkdir(parents=True, exist_ok=True)
