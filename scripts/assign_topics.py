"""Topic and audience for the place processes whose category ``schema.CATEGORY_TOPIC`` does not map.

For every verified ``place_processes`` row whose category has no entry in ``CATEGORY_TOPIC`` (15 on 15 October 2026:
courts_legal, permits_construction, zoning_land_use, health_social_services), the decision model
(``lexflow.extract.decide``, ``tev1:0.8b`` through ``/v1/systemone``, or the chat fallback) is asked two ``choice``
questions from the title, the question and the summary: the topic over ``schema.VOCAB["topic"]`` and the audience
over ``schema.VOCAB["audience"]``.  The answers go to ``fixtures/places/topics.json``:

    {"<gov_id>/<process>": {"topic": "courts", "topic_confidence": 0.93, "audience": "resident",
                            "audience_confidence": 0.71, "confidence": 0.71, "model": "tev1:0.8b",
                            "date": "2026-10-15", "accepted": false}, ...}

``confidence`` is the lower of the two.  ``graph.py`` uses a field only when a person set ``accepted`` to true or
the model's confidence for it is at least ``graph.TOPIC_CONFIDENCE`` (0.9); an ``accepted`` flag already in the file
is kept when the model's answers are unchanged.  The database is read only (one short read-only connection); the
wiki is not touched.  The ``_note`` and ``_generated`` keys of the file are not entries.

    python scripts/assign_topics.py [--db PATH] [--url http://lexflow-ollama2:11434] [--model tev1:0.8b] [--out PATH]
                                    [--no-cache] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lexflow import config  # noqa: E402
from lexflow.extract import decide as DEC  # noqa: E402
from lexflow.publish import schema as SC  # noqa: E402

OUT = ROOT / "fixtures" / "places" / "topics.json"
QUESTIONS = {
    "topic": {"type": "choice", "instructions": "What is this local government process about? Pick the topic that "
                                                "fits best.", "criteria": {v.slug: v.description for v in SC.VOCAB["topic"]}},
    "audience": {"type": "choice", "instructions": "Who is this process for? Pick the audience that fits best.",
                 "criteria": {v.slug: v.description for v in SC.VOCAB["audience"]}},
}


def unmapped(db_path: Path | str | None = None) -> list[dict]:
    """The verified place processes whose category CATEGORY_TOPIC does not map, read-only."""
    path = Path(db_path or config.DB_PATH)
    con = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True, timeout=5)
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute("SELECT gov_id, process, state, category, title, question, spec FROM place_processes "
                           "WHERE verified=1 ORDER BY gov_id, process").fetchall()
    finally:
        con.close()
    out = []
    for r in rows:
        spec = json.loads(r["spec"] or "{}") if isinstance(r["spec"], str) else (r["spec"] or {})
        category = r["category"] or spec.get("category") or ""
        if category in SC.CATEGORY_TOPIC:
            continue
        out.append({"gov_id": r["gov_id"], "process": r["process"], "state": r["state"], "category": category,
                    "title": r["title"] or spec.get("title") or r["process"], "question": r["question"] or "",
                    "summary": spec.get("summary") or ""})
    return out


def state_of(p: dict) -> dict:
    return {"Title": p["title"], "Question": p["question"], "Summary": " ".join((p["summary"] or "").split())[:1200]}


def assign(rows: list[dict], decider: DEC.Decider, log=print) -> dict[str, dict]:
    today = time.strftime("%Y-%m-%d")
    out = {}
    for p in rows:
        key = f"{p['gov_id']}/{p['process']}"
        res = decider.decide(state_of(p), QUESTIONS)
        a = res["answers"]
        t, au = a["topic"], a["audience"]
        tc = None if t.get("confidence") is None else round(float(t["confidence"]), 4)
        ac = None if au.get("confidence") is None else round(float(au["confidence"]), 4)
        confs = [c for c in (tc, ac) if c is not None]
        entry = {"topic": t.get("choice"), "topic_confidence": tc,
                 "audience": au.get("choice"), "audience_confidence": ac,
                 "confidence": min(confs) if confs else None, "model": res.get("model") or decider.model,
                 "date": today, "accepted": False, "category": p["category"], "title": p["title"]}
        out[key] = entry
        log(f"{key} [{p['category']}] {p['title'][:60]!r}: topic {entry['topic']} ({_fmt(entry['topic_confidence'])}), "
            f"audience {entry['audience']} ({_fmt(entry['audience_confidence'])}){' [cached]' if res.get('cached') else ''}")
    return out


def _fmt(c) -> str:
    return "-" if c is None else f"{c:.2f}"


def merge(old: dict, new: dict) -> dict:
    """``new`` with the ``accepted`` flag of ``old`` kept where topic and audience are unchanged."""
    for key, entry in new.items():
        prev = old.get(key) if isinstance(old.get(key), dict) else None
        if prev and prev.get("accepted") is True and prev.get("topic") == entry["topic"] \
                and prev.get("audience") == entry["audience"]:
            entry["accepted"] = True
    return new


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--db", help=f"the lexflow database (default {config.DB_PATH})")
    ap.add_argument("--url", help=f"the Ollama that serves decisions (default {config.DECIDE_URL})")
    ap.add_argument("--model", help=f"the decision model (default {config.DECIDE_MODEL})")
    ap.add_argument("--out", help=f"where to write (default {OUT})")
    ap.add_argument("--no-cache", action="store_true", help="ask the model again even for cached states")
    ap.add_argument("--dry-run", action="store_true", help="print the assignments and write nothing")
    args = ap.parse_args(argv)
    rows = unmapped(args.db)
    print(f"{len(rows)} verified place processes with an unmapped category", file=sys.stderr)
    if not rows:
        return 0
    decider = DEC.Decider(args.model, base_url=args.url, cache=not args.no_cache)
    b = decider.backend
    print(f"backend: {b['kind']} ({b['model']}) at {decider.base_url}", file=sys.stderr)
    if b["kind"] == "none":
        print("no decision model and no chat model pulled there: nothing to ask", file=sys.stderr)
        return 1
    new = assign(rows, decider, log=lambda s: print(s, file=sys.stderr))
    out = Path(args.out) if args.out else OUT
    old = {}
    if out.exists():
        try:
            old = json.loads(out.read_text(encoding="utf-8"))
        except ValueError:
            old = {}
    entries = merge(old, new)
    data = {"_note": "Topic and audience of the verified place processes whose category schema.CATEGORY_TOPIC does "
                     "not map, chosen by a decision model (scripts/assign_topics.py) from the title, question and "
                     "summary. graph.py uses a field only when accepted is true or its confidence is at least "
                     f"{0.9}; set accepted to true after checking an entry.",
            "_generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **dict(sorted(entries.items()))}
    if args.dry_run:
        print(json.dumps(data, indent=1, ensure_ascii=False))
        return 0
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    sure = sum(1 for e in entries.values() if (e.get("confidence") or 0) >= 0.9)
    print(f"{len(entries)} entries written to {out}; {sure} with both confidences >= 0.9; decider stats "
          f"{decider.stats}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
