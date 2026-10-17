"""Wikidata suggestions for the schema's vocabulary items and the classes without a QID, for the operator to
review (docs/design/wikibase-schema.md section 8).

``targets()`` lists every item of ``schema.VOCAB`` (topics, audiences, review statuses, time units, reference
types, step kinds, unit levels, escalation types, determination methods, the currency) and every class of
``schema.CLASSES`` that has no ``wikidata`` yet.  ``suggest(term)`` searches Wikidata read-only
(``wbsearchentities`` then ``wbgetentities`` for the hits and for the labels of their classes; ``User-Agent:
lexflow-research/0.1``; at most one request a second) and runs the suggestion classifier of
``lexflow.law.terms`` (``link``: the survey-fitted logistic model) over the candidates.  ``build()`` writes
``fixtures/entities/vocab_links.json``::

    {key: {"qid", "label", "description", "relation": "exact" | "close" | "broad", "p", "reviewed": false,
           "term", "alternatives": [{qid, label, description, p}]}}

``relation`` is ``exact`` when the item's label or an alias is the term (singular or plural), ``broad`` when the
item's label is a proper part of the term (``day`` for "calendar days": the item is the broader concept), else
``close``.  Nothing here is a match until a person sets ``reviewed`` to true.  ``get(key)`` reads one entry;
``writable(key)`` is the QID the graph may write as ``exact match`` later: relation ``exact`` and ``p`` at least
``WRITE_P`` (0.9).  The hook for ``graph.Build`` (three lines, where a vocabulary or class item is made)::

    from . import vocab_links
    qid = vocab_links.writable(key)
    if qid: self.claim(it, "exact match", url(SC.WIKIDATA_ENTITY + qid))
"""
from __future__ import annotations

import argparse
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from .. import config
from . import schema as SC

API = "https://www.wikidata.org/w/api.php"
USER_AGENT = "lexflow-research/0.1"
PATH = config.ROOT / "fixtures" / "entities" / "vocab_links.json"
WRITE_P = 0.9
KEEP_P = 0.2                     # below this the best candidate is not even listed as a suggestion
_last = 0.0
_cache: dict = {}


def targets() -> list[dict]:
    """``[{key, label, description, kind}]``: every vocabulary item, then every class without a QID."""
    out = []
    for set_, items in SC.VOCAB.items():
        for v in items:
            out.append({"key": SC.key_for("vocab", set_, v.slug), "label": v.label, "description": v.description,
                        "kind": f"vocab:{set_}"})
    for c in SC.CLASSES:
        if not c.wikidata:
            out.append({"key": SC.key_for("class", c.slug), "label": c.label,
                        "description": c.description, "kind": "class"})
    return out


# ------------------------------------------------------------------------------------------ read-only Wikidata
def _throttle() -> None:
    global _last
    wait = _last + INTERVAL - time.monotonic()
    if wait > 0:
        time.sleep(wait)
    _last = time.monotonic()


INTERVAL = 2.0                   # seconds between requests (Wikidata answered 429 at one a second on 16 Oct 2026)


def _get(params: dict, session=None, timeout: float = 30, tries: int = 4) -> dict:
    """One API call, at most one every ``INTERVAL`` seconds; a 429 waits for ``Retry-After`` (at least 30 s) and
    tries again, up to ``tries`` times."""
    http = session or requests
    for attempt in range(tries):
        _throttle()
        r = http.get(API, params={**params, "format": "json"}, headers={"User-Agent": USER_AGENT}, timeout=timeout)
        if r.status_code == 429 and attempt + 1 < tries:
            try:
                wait = max(30.0, float(r.headers.get("Retry-After", "30")))
            except ValueError:
                wait = 30.0
            time.sleep(min(wait, 120.0))
            continue
        r.raise_for_status()
        return r.json()
    raise requests.HTTPError("429 after retries")


def _singular(term: str) -> str:
    t = term.strip()
    if t.endswith("ies") and len(t) > 4:
        return t[:-3] + "y"
    if t.endswith("s") and not t.endswith("ss") and len(t) > 3:
        return t[:-1]
    return t


def search(term: str, limit: int = 8, session=None) -> list[dict]:
    """Candidates in the shape ``lexflow.law.terms.candidate_features`` reads, for the term and its singular."""
    from ..law import terms as T
    ids: list[str] = []
    for q in dict.fromkeys([term, _singular(term)]):
        hits = _get({"action": "wbsearchentities", "search": q, "language": "en", "uselang": "en", "type": "item",
                     "limit": limit}, session).get("search", [])
        for h in hits:
            if h.get("id") and h["id"] not in ids:
                ids.append(h["id"])
    if not ids:
        return []
    ents = _get({"action": "wbgetentities", "ids": "|".join(ids[:16]), "languages": "en|mul",
                 "props": "labels|descriptions|aliases|claims|sitelinks"}, session).get("entities", {})
    class_ids: list[str] = []
    for e in ents.values():
        for p in ("P31", "P279", "P17", "P1001"):
            for c in (e.get("claims") or {}).get(p, []):
                v = ((c.get("mainsnak") or {}).get("datavalue") or {}).get("value")
                if isinstance(v, dict) and v.get("id") and v["id"] not in class_ids:
                    class_ids.append(v["id"])
    labels: dict[str, str] = {}
    for i in range(0, min(len(class_ids), 100), 50):
        got = _get({"action": "wbgetentities", "ids": "|".join(class_ids[i:i + 50]), "languages": "en",
                    "props": "labels"}, session).get("entities", {})
        for qid, e in got.items():
            lab = ((e.get("labels") or {}).get("en") or {}).get("value")
            if lab:
                labels[qid] = lab
    return [T.candidate_from_entity(qid, ents[qid], labels, rank=i + 1) for i, qid in enumerate(ids) if qid in ents]


# -------------------------------------------------------------------------------------------- classification
def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", (s or "").lower()).strip()


def relation(term: str, cand: dict) -> str:
    """``exact`` (label or alias is the term, singular or plural), ``broad`` (the label is a proper part of the
    term), else ``close``."""
    t = _norm(term)
    names = [_norm(cand.get("label") or "")] + [_norm(a) for a in cand.get("aliases") or []]
    forms = {t, _norm(_singular(term)), t + "s"}
    if any(n and (n in forms or _norm(_singular(n)) in forms) for n in names):
        return "exact"
    lab = names[0]
    tw, lw = {_singular(w) for w in t.split()}, {_singular(w) for w in lab.split()}
    if lw and lw < tw:
        return "broad"
    return "close"


def suggest(term: str, candidates: list[dict] | None = None, session=None) -> dict:
    """The classifier's suggestion for one term: the best candidate (when its probability is at least
    ``KEEP_P``), its relation and probability, and the next alternatives."""
    from ..law import terms as T
    cands = candidates if candidates is not None else search(term, session=session)
    if not cands:
        return {"qid": None, "label": None, "description": None, "relation": None, "p": 0.0, "alternatives": []}
    model = T.default_model()
    rows = [T.candidate_features(term, c, rank=c.get("rank") or i + 1, peers=cands) for i, c in enumerate(cands)]
    ps = [0.0 if T.unlinkable(c) else p for c, p in zip(cands, T.predict(model, rows))]
    order = sorted(range(len(cands)), key=lambda i: -ps[i])
    best = order[0]
    alts = [{"qid": cands[i]["qid"], "label": cands[i].get("label"), "description": cands[i].get("description"),
             "p": round(ps[i], 3)} for i in order[1:4] if ps[i] >= KEEP_P]
    if ps[best] < KEEP_P:
        return {"qid": None, "label": None, "description": None, "relation": None, "p": round(ps[best], 3),
                "alternatives": alts}
    c = cands[best]
    return {"qid": c["qid"], "label": c.get("label"), "description": c.get("description"),
            "relation": relation(term, c), "p": round(ps[best], 3), "alternatives": alts}


def build(path: Path | str | None = None, log=print, session=None, only: list[str] | None = None,
          resume: bool = False) -> dict:
    """Suggest for every target and write the file (entries a person has reviewed are kept as they are; with
    ``resume`` so is every entry already there).  The file is saved after each item, so a run cut short keeps
    what it found."""
    out_path = Path(path) if path else PATH
    data = load(out_path)
    data = {k: v for k, v in data.items() if not k.startswith("_")}
    todo = [t for t in targets() if not only or t["key"] in only]
    n = 0
    for t in todo:
        prev = data.get(t["key"])
        if prev and (prev.get("reviewed") or resume):
            continue
        try:
            s = suggest(t["label"], session=session)
        except requests.RequestException as e:
            log(f"{t['key']}: {e}")
            continue
        data[t["key"]] = {"term": t["label"], "kind": t["kind"], **s, "reviewed": False}
        n += 1
        log(f"{t['key']}: {s['qid']} {s['label']!r} {s['relation']} p={s['p']}")
        _save(out_path, data)
    _save(out_path, data)
    log(f"{n} suggestions written to {out_path}")
    return data


def _save(out_path: Path, data: dict) -> None:
    data["_meta"] = {"built": datetime.now(timezone.utc).strftime("%Y-%m-%d"), "classifier": "lexflow.law.terms.link",
                     "source": "Wikidata wbsearchentities + wbgetentities, read-only", "write_p": WRITE_P,
                     "note": "suggestions for review; nothing is a match until reviewed is true"}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    _cache.clear()


# ---------------------------------------------------------------------------------------------------- reading
def load(path: Path | str | None = None) -> dict:
    p = Path(path) if path else PATH
    key = str(p)
    stamp = p.stat().st_mtime if p.exists() else -1
    if key not in _cache or _cache[key][0] != stamp:
        try:
            data = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
        except ValueError:
            data = {}
        _cache[key] = (stamp, data)
    return _cache[key][1]


def get(key: str, path: Path | str | None = None) -> dict | None:
    """The suggestion for one key (``lexflow:vocab:topic:courts``), or None."""
    e = load(path).get(key)
    return e if isinstance(e, dict) and not key.startswith("_") else None


def writable(key: str, path: Path | str | None = None) -> str | None:
    """The QID the graph may write as ``exact match``: relation exact and p at least ``WRITE_P``."""
    e = get(key, path)
    if e and e.get("qid") and e.get("relation") == "exact" and (e.get("p") or 0) >= WRITE_P:
        return e["qid"]
    return None


def summary(path: Path | str | None = None) -> list[dict]:
    """Rows for the docs: key, term, qid, label, relation, p, reviewed."""
    data = load(path)
    return [{"key": k, **{f: v.get(f) for f in ("term", "qid", "label", "relation", "p", "reviewed")}}
            for k, v in sorted(data.items()) if not k.startswith("_")]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m lexflow.publish.vocab_links")
    ap.add_argument("--build", action="store_true", help="search Wikidata (read-only, 1 req/s) and write the file")
    ap.add_argument("--only", nargs="*", help="keys to redo")
    ap.add_argument("--resume", action="store_true", help="keep the entries already in the file")
    ap.add_argument("--table", action="store_true", help="print the file as a Markdown table")
    a = ap.parse_args(argv)
    if a.build:
        build(only=a.only, resume=a.resume)
    if a.table or not a.build:
        print("| Key | Term | Wikidata | Relation | p |\n|---|---|---|---|---|")
        for r in summary():
            q = f"[{r['qid']}](https://www.wikidata.org/wiki/{r['qid']}) {r['label'] or ''}" if r["qid"] else "–"
            print(f"| `{r['key']}` | {r['term']} | {q} | {r['relation'] or '–'} | {r['p'] if r['p'] is not None else '–'} |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
