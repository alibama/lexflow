"""Find the state statute that answers each question, with a score for how sure we are.

* ``seed``: a known section number, found in the downloaded statutes, in force, and passing
  the question's text check (score 1.0).
* ``keyword``: the best-ranked section by title, chapter and text features (score 0.4-0.8
  depending on how strong the match is).
* ``not-found`` / ``no-statutes``: nothing usable, or the state has no file in the release.

The top candidates are kept so a reviewer can see what else was close.
"""
from __future__ import annotations

import json
import re

from ..store import db
from . import statutes
from .fetch import Log
from .questions import Question


def _score_row(q: Question, title: str, chapter: str, text: str) -> float:
    s = 0.0
    if q.title_strong.search(title):
        s += 6
    elif q.title_moderate.search(title):
        s += 3
    if q.title_negative.search(title):
        s -= 6
    if q.title_moderate.search(chapter):
        s += 2
    head = text[:4000]
    if q.text_required is not None and not q.text_required.search(head):
        s -= 4
    s += 0.75 * sum(1 for p in q.text_features if p.search(head))
    if q.title_bonus is not None and q.title_bonus.search(title):
        s += 1.5
    return s


def _nc(p: re.Pattern) -> str:
    """The pattern with non-capturing groups (pandas warns about capturing ones in str.contains)."""
    return re.sub(r"\((?!\?)", "(?:", p.pattern)


def candidates(q: Question, state: str, top: int = 8) -> list[dict]:
    df = statutes.load(state)
    pre = df["section_title"].str.contains(_nc(q.title_moderate), case=False, regex=True) | \
        df["section_title"].str.contains(_nc(q.title_strong), case=False, regex=True) | \
        df["chapter_name"].str.contains(_nc(q.title_moderate), case=False, regex=True)
    sub = df[pre]
    scored = []
    for _, r in sub.iterrows():
        sc = _score_row(q, r["section_title"], r["chapter_name"], r["text"])
        if sc > 0:
            scored.append((sc, r))
    scored.sort(key=lambda x: (-x[0], len(x[1]["text"])))
    return [{"section": statutes.ref_of(state, r), "citation": r["citation"], "heading": r["section_title"],
             "chapter": r["chapter_name"], "url": r["source_url"], "score": round(sc, 2), "words": int(r["word_count"] or 0)}
            for sc, r in scored[:top]]


def locate(q: Question, state: str) -> dict:
    row = {"state": state, "question": q.id, "status": "not-found", "citation": None, "section": None, "heading": None,
           "act": None, "url": None, "method": None, "score": 0.0, "text": None, "related": "[]", "candidates": "[]"}
    if not statutes.have(state):
        row["status"] = "no-statutes"
        return row
    df = statutes.load(state)
    cands = candidates(q, state)
    row["candidates"] = json.dumps(cands)
    chosen, method, score = None, None, 0.0
    for seed in q.seeds.get(state, ()):
        hit = statutes.find(df, seed)
        for _, r in hit.iterrows():
            text = r["text"]
            if q.text_required is not None and not q.text_required.search(text):
                continue
            if q.title_negative.search(r["section_title"]) and not q.title_strong.search(r["section_title"]):
                continue
            chosen, method, score = r, "seed", 1.0
            break
        if chosen is not None:
            break
    if chosen is None and cands:
        best = cands[0]
        hit = statutes.find(df, best["section"])
        if not hit.empty and best["score"] >= 3:
            chosen, method = hit.iloc[0], "keyword"
            score = 0.8 if best["score"] >= 8 else 0.6 if best["score"] >= 5 else 0.4
    if chosen is None:
        return row
    act = None
    m = re.search(r'(?:cited as|known as)\s+(?:the\s+)?["“]([^"”]{4,120})["”]', chosen["text"])
    if m:
        act = m.group(1)
    ref = statutes.ref_of(state, chosen)
    related = [c for c in cands if c["section"] != ref][:3]
    row.update(status="found", citation=chosen["citation"], section=ref,
               heading=chosen["section_title"], url=chosen["source_url"], method=method, score=score, act=act,
               text=statutes.strip_history(chosen["text"]), related=json.dumps(related))
    return row


def run(con, q: Question, states_: list[str], log: Log = print, progress=None) -> dict:
    found = 0
    version = None
    for i, st in enumerate(states_):
        row = locate(q, st)
        if version is None:
            try:
                version = statutes.manifest(log=lambda *_: None).get("version")
            except Exception:  # noqa: BLE001 - offline is fine here
                version = None
        row["dataset_version"] = version
        db.upsert(con, "located_law", [row])
        found += row["status"] == "found"
        if row["status"] == "found":
            log(f"{st} {q.id}: {row['citation']} ({row['method']}, {row['score']:.1f}) {row['heading'][:70]}")
        else:
            log(f"{st} {q.id}: {row['status']}")
        if progress:
            progress((i + 1) / len(states_))
        con.commit()
    db.bump(con)
    con.commit()
    return {"found": found, "states": len(states_)}
