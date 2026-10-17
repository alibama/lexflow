"""Name every CourtListener court lexflow searches: ``fixtures/entities/courts.json``.

``lexflow.municipal.caselaw.COURTS`` lists the CourtListener court ids searched for each state; the graph builds one
item per id, and until now an id with no opinion in ``case_law`` had no name ("Virginia court vactapp"), which the
lint held.  This script reads each court's record from CourtListener's public courts API, read-only and without a
key (``GET /api/rest/v4/courts/<id>/``; User-Agent ``lexflow-research/0.1``; one request a second), caches the JSON
under ``data/cache/courts/<id>.json`` and writes the fixture.  The anonymous allowance is a burst of a few requests
a minute (a 429 is waited out for its ``Retry-After``, else a minute), so the first run of the 98 courts takes about
twenty minutes; a re-run reads the cache.  The fixture:

    {"<id>": {"name": "Court of Appeals of Virginia", "jurisdiction": "va", "url": "http://...",
              "citation": "Va. Ct. App.", "type": "SA"}, ...}

``jurisdiction`` is lexflow's state code (the key of ``COURTS``); ``type`` is CourtListener's own jurisdiction code
(S state supreme, SA state appellate, ST state trial ...).  Nothing is written anywhere else.

    python scripts/fetch_courts.py [--only-missing] [--refresh]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lexflow import config  # noqa: E402
from lexflow.municipal.caselaw import COURTS  # noqa: E402

API = "https://www.courtlistener.com/api/rest/v4/courts/"
USER_AGENT = "lexflow-research/0.1"
FIXTURE = ROOT / "fixtures" / "entities" / "courts.json"
ATTEMPTS = 8
_last = 0.0


def cache_dir() -> Path:
    return Path(config.DATA_DIR) / "cache" / "courts"


def throttle() -> None:
    global _last
    wait = _last + 1.0 - time.monotonic()
    if wait > 0:
        time.sleep(wait)
    _last = time.monotonic()


def fetch(cid: str, refresh: bool = False, log=print) -> dict | None:
    """The court's JSON record, from the cache or (one request a second) from CourtListener; None on a 404."""
    path = cache_dir() / f"{cid}.json"
    if path.exists() and not refresh:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            pass
    for attempt in range(ATTEMPTS):
        throttle()
        r = requests.get(f"{API}{cid}/", headers={"User-Agent": USER_AGENT, "Accept": "application/json"}, timeout=60)
        if r.status_code == 404:
            log(f"{cid}: not a CourtListener court (404)")
            return None
        if r.status_code != 429 and r.status_code < 500:
            break
        # the anonymous allowance is a burst of a few requests a minute (measured 15 October 2026: 429 after
        # five in five seconds): wait what the server asks, else a minute, and try again; a 5xx (a 502 was seen
        # once) is tried again after a short pause
        after = str(r.headers.get("Retry-After", "")).strip()
        pause = float(after) if after.isdigit() else (60.0 if r.status_code == 429 else 10.0)
        log(f"{cid}: HTTP {r.status_code}; waiting {pause:.0f} s (try {attempt + 1} of {ATTEMPTS})")
        time.sleep(pause)
    r.raise_for_status()
    data = r.json()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    return data


def entry(st: str, rec: dict) -> dict:
    name = (rec.get("full_name") or rec.get("short_name") or "").strip()
    out = {"name": name, "jurisdiction": st, "url": (rec.get("url") or "").strip()}
    if rec.get("short_name") and rec["short_name"].strip() != name:
        out["short_name"] = rec["short_name"].strip()
    if rec.get("citation_string"):
        out["citation"] = rec["citation_string"].strip()
    if rec.get("jurisdiction"):
        out["type"] = rec["jurisdiction"]
    if rec.get("end_date"):
        out["ended"] = rec["end_date"]
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--refresh", action="store_true", help="read every court again even when cached")
    ap.add_argument("--only-missing", action="store_true", help="keep the fixture's entries and fetch the others")
    args = ap.parse_args(argv)
    old = {}
    if args.only_missing and FIXTURE.exists():
        old = json.loads(FIXTURE.read_text(encoding="utf-8")).get("courts") or {}
    courts: dict[str, dict] = {}
    missing = []
    for st in sorted(COURTS):
        for cid in COURTS[st]:
            if cid in old and not args.refresh:
                courts[cid] = old[cid]
                continue
            rec = fetch(cid, refresh=args.refresh)
            if rec is None or not (rec.get("full_name") or rec.get("short_name")):
                missing.append(cid)
                continue
            courts[cid] = entry(st, rec)
            print(f"{st}:{cid}: {courts[cid]['name']}")
    data = {"note": "CourtListener courts lexflow searches (lexflow.municipal.caselaw.COURTS), named from "
                    "CourtListener's public courts API (https://www.courtlistener.com/api/rest/v4/courts/<id>/); "
                    "the graph labels each court item with the name and keeps the id as an alias. "
                    "jurisdiction is lexflow's state code; type is CourtListener's jurisdiction code.",
            "source": API, "checked": time.strftime("%Y-%m-%d"), "courts": dict(sorted(courts.items()))}
    FIXTURE.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{len(courts)} courts named, {len(missing)} without a record ({', '.join(missing) or '-'}); {FIXTURE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
