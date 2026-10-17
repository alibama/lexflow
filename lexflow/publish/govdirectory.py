"""Govdirectory page links for a Wikidata item, read-only.

Govdirectory (docs/design/entities-sources.md section 2) is built from Wikidata; an organisation's page is
``https://www.govdirectory.org/<country-slug>/<QID>/`` for a federal body and
``https://www.govdirectory.org/<country-slug>/<state-slug>/<QID>/`` for a body in one of the state listings (today
only North Carolina and New York).  ``candidates(qid, state)`` gives the URLs a QID could have; ``page_url(qid,
state)`` checks them (``GET``, ``User-Agent: lexflow-research/0.1``, at most one request a second, the page itself
only, never a listing) and caches the outcome in ``fixtures/entities/govdirectory_links.json``
(``{qid: {"url", "checked", "status"}}``), so a QID is asked once.  ``python -m lexflow.publish.govdirectory
Q1553390 [--state nc]`` prints the result; ``--known`` checks the three known cases.
"""
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from .. import config

BASE = "https://www.govdirectory.org/"
COUNTRY = "united-states"
STATE_SLUG: dict[str, str] = {"nc": "north-carolina", "ny": "new-york"}      # the state listings that exist
USER_AGENT = "lexflow-research/0.1"
CACHE = config.ROOT / "fixtures" / "entities" / "govdirectory_links.json"
# three pages known from the design notes: a federal department, a North Carolina agency, a New York agency
KNOWN: dict[str, str | None] = {"Q1553390": None, "Q136481241": "nc", "Q17110658": "ny"}
_last = 0.0


def candidates(qid: str, state: str | None = None) -> list[str]:
    """The page URLs a QID could have, the state listing's first when the state has one."""
    q = (qid or "").strip().upper()
    if not q.startswith("Q") or not q[1:].isdigit():
        return []
    out = []
    st = (state or "").lower()
    if st in STATE_SLUG:
        out.append(f"{BASE}{COUNTRY}/{STATE_SLUG[st]}/{q}/")
    out.append(f"{BASE}{COUNTRY}/{q}/")
    for s, slug in STATE_SLUG.items():
        if s != st:
            out.append(f"{BASE}{COUNTRY}/{slug}/{q}/")
    return out


def _throttle() -> None:
    global _last
    wait = _last + 1.0 - time.monotonic()
    if wait > 0:
        time.sleep(wait)
    _last = time.monotonic()


def _read(path: Path) -> dict:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def cached(qid: str, path: Path | str | None = None) -> dict | None:
    return _read(Path(path) if path else CACHE).get((qid or "").upper())


def page_url(qid: str, state: str | None = None, *, check: bool = True, path: Path | str | None = None,
             session=None, timeout: float = 15) -> str | None:
    """The Govdirectory page of ``qid`` when one exists, else None.  Answers from the cache first; with ``check``
    the candidates are fetched (at most one request a second) and the outcome cached, a miss included."""
    cache_path = Path(path) if path else CACHE
    hit = cached(qid, cache_path)
    if hit is not None:
        return hit.get("url")
    if not check:
        return None
    http = session or requests
    found, status = None, None
    for url in candidates(qid, state):
        _throttle()
        try:
            r = http.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout, allow_redirects=True)
            status = r.status_code
        except requests.RequestException:
            status = "error"
            continue
        if r.status_code == 200:
            found = url
            break
    data = _read(cache_path)
    data[qid.upper()] = {"url": found, "checked": datetime.now(timezone.utc).strftime("%Y-%m-%d"), "status": status,
                         "state": (state or "").lower() or None}
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(data, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return found


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m lexflow.publish.govdirectory")
    ap.add_argument("qid", nargs="?")
    ap.add_argument("--state")
    ap.add_argument("--known", action="store_true", help="check the three known pages")
    ap.add_argument("--no-check", action="store_true", help="cache only, no request")
    a = ap.parse_args(argv)
    todo = list(KNOWN.items()) if a.known else ([(a.qid, a.state)] if a.qid else [])
    if not todo:
        ap.print_help()
        return 2
    for qid, st in todo:
        print(qid, st or "-", page_url(qid, st, check=not a.no_check) or "no page")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
