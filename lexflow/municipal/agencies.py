"""State bodies' office channels into ``contacts``, keyed by the body's key, so bodies (not only governments) can
be reached from an answer.

    python -m lexflow.municipal.agencies --load [--dry-run]

Sources, both read from the fixtures (nothing is fetched):

* ``fixtures/entities/agencies.json``: every body with an ``exact`` Wikidata match (the ones ``graph.build`` makes
  items of, under the same keys: the ladder's key for that QID when it has one, else
  ``lexflow:agency:<st>:<slug>``; a position is ``lexflow:position:<st>:<slug>``), its units
  (``lexflow:agency:<st>:<unit slug>``) and its related positions.  Channels: ``website`` (official website),
  ``email`` (an office mailbox, ``privacy.is_office_mailbox``), ``phone`` (the body's main line, Wikidata P1329,
  labelled "Main office line") and ``govdirectory_url`` (kind ``govdirectory``: a link to the body's Govdirectory
  page, never copied).  The row's ``question`` is ``general``, its ``source`` ``wikidata`` (the fixture's values
  are the item's P856/P968/P1329) and its ``origin`` ``agencies-fixture``.
* ``fixtures/entities/contacts_pilot.json``: the pilot's live check of governments' channels.  A ``moved`` website
  (the stored URL redirects to another domain) adds the live URL as a second ``website`` row with source
  ``pilot-2026-10-10``; ``ok`` rows already exist and are left alone; broken and unverifiable ones write nothing.

Every value passes ``lexflow.privacy.is_office_channel`` before it is written; refused values are counted.  Writes
are one short transaction (about 250 rows).  The graph does not read these rows yet: the three-line hook for
``graph.Build._agencies_fixture`` is ``self.channels(it, key, "general", name, mailboxes=False)`` after the item is
made (and the same for each unit); ``lexflow.ask.who`` reads them directly meanwhile.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .. import config, privacy
from ..publish import schema as SC
from ..store import db

AGENCIES = config.ROOT / "fixtures" / "entities" / "agencies.json"
LADDERS = config.ROOT / "fixtures" / "authority" / "ladders.json"
PILOT = config.ROOT / "fixtures" / "entities" / "contacts_pilot.json"
ORIGIN = "agencies-fixture"
PHONE_LABEL = "Main office line"


def _json(path: Path) -> dict:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def body_key(b: dict, ladder_keys: dict[str, str]) -> str | None:
    """The key ``graph.build`` gives this fixture body (see the module docstring)."""
    st, name = b.get("state"), b.get("resolved_name")
    if not st or not name:
        return None
    if b.get("item_kind") == "position":
        return SC.key_for("position", st, name)
    key = ladder_keys.get(b.get("qid") or "") or SC.key_for("agency", st, name)
    return key if SC.kind_of(key) == "agency" else SC.key_for("agency", st, name)


def agency_rows(agencies: dict | None = None, ladders: dict | None = None, now: str | None = None) -> tuple[list[dict], dict]:
    """The contact rows the agencies fixture gives, and the counts of what was kept and refused."""
    agencies = agencies if agencies is not None else _json(AGENCIES)
    ladders = ladders if ladders is not None else _json(LADDERS)
    ladder_keys = {b["qid"]: b["key"] for b in (ladders.get("bodies") or {}).values()
                   if b.get("qid") and b.get("qid_status") == "exact" and b.get("key")}
    now = now or db.now()
    rows: list[dict] = []
    stats = {"bodies": 0, "rows": 0, "refused": 0}

    def add(owner_key: str, st: str, kind: str, value: str | None, label: str | None, owner_name: str):
        if not value:
            return
        v = value.strip()
        ok = privacy.is_office_url(v) if kind == "govdirectory" else privacy.is_office_channel(kind, v, label, owner_name)
        if not ok:
            stats["refused"] += 1
            return
        rows.append({"gov_id": owner_key, "state": st, "question": "general", "kind": kind, "value": v,
                     "label": label, "source": "govdirectory" if kind == "govdirectory" else "wikidata",
                     "updated_at": now, "origin": ORIGIN})
        stats["rows"] += 1

    for b in agencies.get("bodies") or []:
        if b.get("match") != "exact" or not b.get("qid"):
            continue
        key = body_key(b, ladder_keys)
        if not key:
            continue
        st, name = b["state"], b["resolved_name"]
        stats["bodies"] += 1
        add(key, st, "website", b.get("website"), "Official website", name)
        add(key, st, "email", b.get("email"), "Office mailbox", name)
        add(key, st, "phone", b.get("phone"), PHONE_LABEL, name)
        add(key, st, "govdirectory", b.get("govdirectory_url"), "Govdirectory page", name)
        for u in b.get("units") or []:
            if not u.get("label"):
                continue
            uk = SC.key_for("agency", st, u["label"])
            add(uk, st, "website", u.get("website"), "Official website", u["label"])
            add(uk, st, "email", u.get("email"), "Office mailbox", u["label"])
            add(uk, st, "phone", u.get("phone"), PHONE_LABEL, u["label"])
        for rel in b.get("related_items") or []:
            if rel.get("item_kind") == "position" and rel.get("label") and b.get("item_kind") != "position":
                pk = SC.key_for("position", st, rel["label"])
                add(pk, st, "website", rel.get("website"), "Official website", rel["label"])
                add(pk, st, "govdirectory", rel.get("govdirectory_url"), "Govdirectory page", rel["label"])
    return rows, stats


def pilot_rows(pilot: dict | None = None, now: str | None = None) -> tuple[list[dict], dict]:
    """New ``website`` rows for the pilot's ``moved`` checks: the live URL beside the stored one."""
    pilot = pilot if pilot is not None else _json(PILOT)
    now = now or db.now()
    date = (pilot.get("generated_at") or "")[:10] or "unknown"
    rows, stats = [], {"items": 0, "moved": 0, "ok": 0, "other": 0, "refused": 0}
    for it in pilot.get("items") or []:
        stats["items"] += 1
        res = it.get("result") or {}
        cls = res.get("class")
        if cls == "ok":
            stats["ok"] += 1
            continue
        if cls != "moved" or it.get("kind") != "website" or not res.get("final_url"):
            stats["other"] += 1
            continue
        stats["moved"] += 1
        url = res["final_url"].strip()
        if url.rstrip("/") == (it.get("value") or "").strip().rstrip("/") or not privacy.is_office_url(url):
            stats["refused"] += 1
            continue
        rows.append({"gov_id": it["gov_id"], "state": it["state"], "question": it.get("question") or "general",
                     "kind": "website", "value": url, "label": f"Official website (checked {date})",
                     "source": f"pilot-{date}", "updated_at": now, "origin": ORIGIN})
    return rows, stats


def load(con, log=print, dry_run: bool = False) -> dict:
    """Write the rows (``db.upsert`` on the contacts key) and return the counts."""
    a_rows, a_stats = agency_rows()
    p_rows, p_stats = pilot_rows()
    out = {"agencies": a_stats, "pilot": p_stats, "written": 0, "dry_run": dry_run}
    rows = a_rows + p_rows
    if not dry_run and rows:
        db.upsert(con, "contacts", rows)
        con.commit()
        out["written"] = len(rows)
    log(f"agencies: {a_stats['bodies']} bodies, {a_stats['rows']} rows, {a_stats['refused']} refused by the privacy "
        f"checks; pilot: {p_stats['moved']} moved sites ({len(p_rows)} new rows), {p_stats['ok']} ok, "
        f"{p_stats['other']} other; {'would write' if dry_run else 'wrote'} {len(rows)} rows")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m lexflow.municipal.agencies")
    ap.add_argument("--load", action="store_true", help="write the rows into contacts")
    ap.add_argument("--dry-run", action="store_true", help="count only")
    a = ap.parse_args(argv)
    if not a.load and not a.dry_run:
        ap.print_help()
        return 2
    con = db.connect()
    try:
        load(con, dry_run=a.dry_run or not a.load)
    finally:
        con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
