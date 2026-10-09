"""Local ordinances from LOCUS-v1: which governments have local law on each question.

LOCUS is used to *find* local provisions, not to cite them (CC BY-NC 4.0, no source URLs,
machine-made labels).  Only small columns are read, with a filter on ``state`` that
parquet row-group statistics turn into ranged reads of the matching row groups.
"""
from __future__ import annotations

import hashlib
import re

from ..store import db
from . import states as S
from .fetch import Log
from .questions import QUESTIONS

DATASET = "LocalLaws/LOCUS-v1"
COLUMNS = ["state", "city", "county", "header", "function", "topic"]
PREFIX = re.compile(r"^(city|town|village|borough|township|city and borough|charter township|unified government|"
                    r"consolidated government|metropolitan government|municipality|plantation|corporation) of\s+", re.I)


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def gov_keys(con, state: str) -> dict[str, str]:
    """LOCUS slug -> gov_id ('albemarle_county' -> county, 'charlottesville' -> city)."""
    keys: dict[str, str] = {}
    for g in db.rows(con, "SELECT gov_id, name, kind FROM governments WHERE state=?", state):
        if g["kind"] == "county":
            base = slug(g["name"])
            variants = [base, base.replace("_", "")]
        else:
            m = PREFIX.match(g["name"])
            base = slug(PREFIX.sub("", g["name"]))
            kind = slug(m.group(1)) if m else ""
            variants = [base, f"{base}_{kind}" if kind else base, base.replace("_", "")]
        for v in list(variants):
            if v.startswith("st_"):
                variants.append("saint_" + v[3:])
        for v in variants:
            keys.setdefault(v, g["gov_id"])
    return keys


def read_state(state: str, log: Log = print):
    import pyarrow.dataset as ds
    from huggingface_hub import HfFileSystem
    fs = HfFileSystem()
    files = sorted(fs.glob(f"datasets/{DATASET}/data/*.parquet"))
    log(f"LOCUS: {len(files)} shards; reading rows for {S.NAME[state]}")
    dataset = ds.dataset(files, filesystem=fs, format="parquet")
    return dataset.to_table(filter=ds.field("state") == state, columns=COLUMNS).to_pylist()


def run(con, state: str, log: Log = print, rows: list[dict] | None = None) -> dict:
    rows = rows if rows is not None else read_state(state, log)
    keys = gov_keys(con, state)
    out, unmatched, ts = [], set(), db.now()
    for r in rows:
        place = r.get("city") or r.get("county")
        if not place:
            continue
        gid = keys.get(place)
        if gid is None:
            unmatched.add(place)
            continue
        header = r.get("header") or ""
        for q in QUESTIONS.values():
            hit = q.local_header and q.local_header.search(header)
            topical = q.id == "business" and r.get("topic") == "Business" and r.get("function") in ("Process", "Rules")
            if not (hit or (topical and re.search(r"licen[cs]|permit|registration", header, re.I))):
                continue
            score = 1.0 if (hit and r.get("function") == "Process") else 0.7 if hit else 0.4
            out.append(dict(gov_id=gid, state=state, question=q.id, source="locus",
                            ref=f"{place}:{hashlib.sha1(header.encode()).hexdigest()[:12]}",
                            header=header.lstrip("# ")[:300], function=r.get("function"), topic=r.get("topic"),
                            score=score, updated_at=ts))
    # retire earlier matches first (score 0 rather than DELETE, so the change reaches Turso too)
    con.execute("UPDATE local_law SET score=0, updated_at=? WHERE state=? AND source='locus' AND score > 0",
                (ts, state))
    db.upsert(con, "local_law", out)
    db.upsert(con, "scans", [{"source": "locus", "state": state, "rows": len(rows), "matched": len(out),
                              "status": "done", "scanned_at": ts}], keys=("source", "state"), stamp=False)
    db.bump(con)
    con.commit()
    govs = len({o["gov_id"] for o in out})
    log(f"{S.NAME[state]}: {len(rows):,} LOCUS rows, {len(out)} local provisions in {govs} governments"
        + (f"; {len(unmatched)} LOCUS places not matched to Census names" if unmatched else ""))
    return {"rows": len(rows), "provisions": len(out), "governments": govs, "unmatched": sorted(unmatched)[:20]}
