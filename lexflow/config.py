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
# how local models extract facts: see lexflow/extract/strategies.py and the Benchmark page
STRATEGY = _env("LEXFLOW_STRATEGY", "stack")
# the independent second extraction when STRATEGY needs no chat model ("" = none: such models stay single)
CHECK_STRATEGY = _env("LEXFLOW_CHECK_STRATEGY", "pick_review")
EMBED_MODEL = _env("LEXFLOW_EMBED_MODEL", "nomic-embed-text")
VECTORS = _env("LEXFLOW_VECTORS", "combo")     # clause vectors for the learned selector: combo | tfidf | embed | none

TURSO_URL = _env("TURSO_DATABASE_URL")
TURSO_TOKEN = _env("TURSO_AUTH_TOKEN")
ORIGIN = _env("LEXFLOW_ORIGIN", socket.gethostname())

# The wiki to publish to.  LEXIPEDIA_TOKEN is accepted as a shorthand for lexipedia.xyz.
DOKUWIKI_TOKEN = _env("DOKUWIKI_TOKEN") or _env("LEXIPEDIA_TOKEN")
DOKUWIKI_URL = _env("DOKUWIKI_URL") or ("https://lexipedia.xyz" if _env("LEXIPEDIA_TOKEN") else "")

COURTLISTENER_TOKEN = _env("COURTLISTENER_TOKEN")   # optional: higher rate limits for case-law search
WIKIBASE_URL = _env("WIKIBASE_URL", "https://lexipedia.wikibase.cloud")
WIKIBASE_BOT_USER = _env("WIKIBASE_BOT_USER") or _env("LEXI_USER")          # a bot password (Special:BotPasswords)
WIKIBASE_BOT_PASSWORD = _env("WIKIBASE_BOT_PASSWORD") or _env("LEXI_PASS")

USER_AGENT = _env("LEXFLOW_USER_AGENT", "lexflow/1.0 (+https://github.com/alibama/lexflow)")
MAX_JOBS = int(_env("LEXFLOW_MAX_JOBS", "2"))


def ensure_dirs() -> None:
    for d in (DATA_DIR, RAW_DIR, JOBS_DIR, BUILD_DIR):
        d.mkdir(parents=True, exist_ok=True)
