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
# run background jobs in this instance (off for a second, read-only server on the same database)
JOB_RUNNER = _env("LEXFLOW_JOB_RUNNER", "1") not in ("0", "false", "no")
# how local models extract facts: see lexflow/extract/strategies.py and the Benchmark page
STRATEGY = _env("LEXFLOW_STRATEGY", "stack")
# the independent second extraction when STRATEGY needs no chat model ("" = none: such models stay single)
CHECK_STRATEGY = _env("LEXFLOW_CHECK_STRATEGY", "pick_review")
EMBED_MODEL = _env("LEXFLOW_EMBED_MODEL", "nomic-embed-text")
# answering new questions: the chat model for the plain-language summary, and the weakest retrieval that still
# counts as having found the law (cosine of the question and the best section's heading and opening words)
ASK_MODEL = _env("LEXFLOW_ASK_MODEL", "qwen3:1.7b")
ASK_MIN_SIMILARITY = float(_env("LEXFLOW_ASK_MIN_SIMILARITY", "0.55"))
# with a trained section-relevance model (scripts/train_relevance.py): the least probability that still answers
ASK_MIN_RELEVANCE = float(_env("LEXFLOW_ASK_MIN_RELEVANCE", "0.25"))
VECTORS = _env("LEXFLOW_VECTORS", "combo")     # clause vectors for the learned selector: combo | tfidf | embed | none
# Decision models (Ollama POST /v1/systemone; lexflow/extract/decide.py, docs/design/decision-models.md).  The
# Ollama that serves decisions may be a second, newer server beside the main one (tev1 needs Ollama >= 0.40.4);
# the chat fallback answers the same questions with a JSON schema when no decision model is pulled.  LEXFLOW_DECIDE
# turns the live uses on (local step kinds in extract/strategies.py and publish/graph.py); off, the rules alone run.
DECIDE_URL = _env("LEXFLOW_DECIDE_URL") or OLLAMA_URL
DECIDE_MODEL = _env("LEXFLOW_DECIDE_MODEL", "tev1:0.8b")
DECIDE_FALLBACK = _env("LEXFLOW_DECIDE_FALLBACK") or MODEL_A or "qwen3:1.7b"
DECIDE = _env("LEXFLOW_DECIDE", "0") not in ("", "0", "false", "no")

TURSO_URL = _env("TURSO_DATABASE_URL")
TURSO_TOKEN = _env("TURSO_AUTH_TOKEN")
ORIGIN = _env("LEXFLOW_ORIGIN", socket.gethostname())

# The wiki to publish to.  LEXIPEDIA_TOKEN is accepted as a shorthand for lexipedia.xyz.
DOKUWIKI_TOKEN = _env("DOKUWIKI_TOKEN") or _env("LEXIPEDIA_TOKEN")
DOKUWIKI_URL = _env("DOKUWIKI_URL") or ("https://lexipedia.xyz" if _env("LEXIPEDIA_TOKEN") else "")
# where readers report an error, shown on lexflow:method's "Corrections:" line: an e-mail address or an http(s) URL
# that the operator sets.  Every page links lexflow:method, so until it is set the publish step writes no page.
CORRECTIONS = _env("LEXFLOW_CORRECTIONS")

COURTLISTENER_TOKEN = _env("COURTLISTENER_TOKEN")   # optional: higher rate limits for case-law search
WIKIBASE_URL = _env("WIKIBASE_URL", "https://lexipedia.wikibase.cloud")
WIKIBASE_BOT_USER = _env("WIKIBASE_BOT_USER") or _env("LEXI_USER")          # a bot password (Special:BotPasswords)
WIKIBASE_BOT_PASSWORD = _env("WIKIBASE_BOT_PASSWORD") or _env("LEXI_PASS")

USER_AGENT = _env("LEXFLOW_USER_AGENT", "lexflow/1.0 (+https://github.com/alibama/lexflow)")
MAX_JOBS = int(_env("LEXFLOW_MAX_JOBS", "2"))


def ensure_dirs() -> None:
    for d in (DATA_DIR, RAW_DIR, JOBS_DIR, BUILD_DIR):
        d.mkdir(parents=True, exist_ok=True)
