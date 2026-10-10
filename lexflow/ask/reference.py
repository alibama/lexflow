"""Claude's reference answers to new questions, and the checks every one must pass.

    curated_ask/<question id>/<state>.json

    {
     "qid": "court_debt", "question": "...", "state": "va", "as_of": "2026-10-10",
     "question_type": "process | facts | mixed | yes_no | list",
     "coverage": "in_code | partial | not_in_code",
     "profile": {"groups": [["installment", "deferred payment"], ["fine", "costs"]], "negative": ["parking"],
                 "slots": ["fee", "deadline", "office"]},
     "gold_sections": [{"ref": "19.2-354", "role": "primary | supporting | definition", "why": "..."}],
     "nuggets": [{"id": "N1", "text": "...", "importance": "vital | okay", "section": "19.2-354",
                  "quote": "<word for word from that section>", "slot": "fee | deadline | office | order | yes_no | null"}],
     "slots": {"fee": [{"value": "$10", "nuggets": ["N3"]}], "deadline": [{"amount": 90, "unit": "days",
               "anchor": "...", "nuggets": ["N2"]}], "office": [...], "yes_no": {"value": "yes", "nuggets": [...]},
               "ordered_list": [{"item": "...", "nuggets": [...]}]},
     "answer": "80-250 words of plain language; every claim followed by the ids of its nuggets, e.g. [N1][N3]",
     "steps": null | <the facts schema of curated/<state>/<question>.json: actors, steps, outcomes ...>,
     "out_of_corpus": [{"kind": "regulation | court rule | contract | agency policy | federal | local", "what": "...",
                        "where": "..."}],
     "version_flags": ["19.2-354 is effective until January 1, 2027"], "local_option": "... | null",
     "reviewed_by": "...", "notes": "..."
    }
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .. import config

TYPES = {"process", "facts", "mixed", "yes_no", "list"}
COVERAGE = {"in_code", "partial", "not_in_code"}
ROLES = {"primary", "supporting", "definition"}
SLOTS = {"fee", "deadline", "office", "order", "yes_no", "amount", None}


def ask_dir(alt: bool = False) -> Path:
    """curated_ask/, or curated_ask_alt/ for independent second drafts (the Claude-vs-Claude ceiling)."""
    return config.ROOT / ("curated_ask_alt" if alt else "curated_ask")


def path(qid: str, state: str, alt: bool = False) -> Path:
    return ask_dir(alt) / qid / f"{state}.json"


def cases(alt: bool = False) -> list[tuple[str, str]]:
    return sorted((p.parent.name, p.stem) for p in ask_dir(alt).glob("*/*.json"))


def load(qid: str, state: str, alt: bool = False) -> dict:
    return json.loads(path(qid, state, alt).read_text(encoding="utf-8"))


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").replace("’", "'").replace("‘", "'").replace("“", '"')
                  .replace("”", '"').replace("–", "-").replace("—", "-")).strip().lower()


def check(spec: dict, qid: str | None = None, state: str | None = None) -> dict:
    """Every problem with a reference answer (an empty list means it is usable)."""
    from ..municipal import statutes
    problems: list[str] = []
    st = state or spec.get("state")
    if qid and spec.get("qid") != qid:
        problems.append(f"qid {spec.get('qid')!r} does not match the folder {qid!r}")
    if spec.get("state") != st:
        problems.append(f"state {spec.get('state')!r} does not match the file name {st!r}")
    if spec.get("question_type") not in TYPES:
        problems.append(f"question_type must be one of {sorted(TYPES)}")
    cov = spec.get("coverage")
    if cov not in COVERAGE:
        problems.append(f"coverage must be one of {sorted(COVERAGE)}")
    prof = spec.get("profile") or {}
    if not prof.get("groups") or not all(isinstance(g, list) and g and all(isinstance(t, str) for t in g)
                                          for g in prof["groups"]):
        problems.append("profile.groups must be a non-empty list of non-empty lists of search terms")
    texts: dict[str, str] = {}
    for g in spec.get("gold_sections") or []:
        if g.get("role") not in ROLES:
            problems.append(f"gold section {g.get('ref')}: role must be one of {sorted(ROLES)}")
        try:
            t = statutes.section_texts(st, [g["ref"]])[0]
            texts[g["ref"]] = t.text
        except Exception as e:  # noqa: BLE001
            problems.append(f"gold section {g.get('ref')}: {e}")
    if cov in ("in_code", "partial") and not spec.get("gold_sections"):
        problems.append("an in_code or partial answer needs gold_sections")
    if cov in ("partial", "not_in_code") and not spec.get("out_of_corpus"):
        problems.append("a partial or not_in_code answer must say where the rest of the law lives (out_of_corpus)")
    ids = set()
    for n in spec.get("nuggets") or []:
        nid = n.get("id")
        if not nid or nid in ids:
            problems.append(f"nugget id {nid!r} is missing or repeated")
        ids.add(nid)
        if n.get("importance") not in ("vital", "okay"):
            problems.append(f"{nid}: importance must be vital or okay")
        if n.get("slot") not in SLOTS:
            problems.append(f"{nid}: slot must be one of {sorted(x for x in SLOTS if x)} or null")
        sec = n.get("section")
        if sec not in texts:
            problems.append(f"{nid}: section {sec!r} is not one of the gold sections")
            continue
        q = norm(n.get("quote"))
        if len(q.split()) < 3:
            problems.append(f"{nid}: the quote is too short to check")
        elif q not in norm(texts[sec]):
            problems.append(f"{nid}: the quote is not word for word in {sec}: {n.get('quote', '')[:90]!r}")
    if cov in ("in_code", "partial") and not any(n.get("importance") == "vital" for n in spec.get("nuggets") or []):
        problems.append("an in_code or partial answer needs at least one vital nugget")
    quotes = {n.get("id"): norm(n.get("quote")) for n in spec.get("nuggets") or []}
    for kind, vals in (spec.get("slots") or {}).items():
        items = vals if isinstance(vals, list) else [vals]
        for v in items:
            if not isinstance(v, dict):
                problems.append(f"slot {kind}: each entry must be an object with its nuggets")
                continue
            refs = v.get("nuggets") or []
            if not refs or any(r not in ids for r in refs):
                problems.append(f"slot {kind}: cite existing nuggets ({refs})")
                continue
            for num in re.findall(r"\d[\d,.]*", str(v.get("value", "")) + " " + str(v.get("amount", ""))):
                num = num.strip(".,")
                if num and not any(has_num(num, quotes[r]) for r in refs):
                    problems.append(f"slot {kind}: {num} does not appear in its nuggets' quotes")
    answer = spec.get("answer") or ""
    words = len(answer.split())
    if cov != "not_in_code" and not 40 <= words <= 320:
        problems.append(f"answer should be 40-320 words (has {words})")
    for r in re.findall(r"\[(N\d+)\]", answer):
        if r not in ids:
            problems.append(f"answer cites {r}, which is not a nugget")
    if cov != "not_in_code" and spec.get("nuggets") and not re.search(r"\[N\d+\]", answer):
        problems.append("answer must cite its nuggets, e.g. [N1]")
    out = {"problems": problems, "sections": len(texts), "nuggets": len(ids)}
    if spec.get("steps"):
        out.update(_check_steps(spec, st, qid or spec.get("qid", "ask"), problems))
    out["ok"] = not problems
    return out


WORDNUM = {"1": "one", "2": "two", "3": "three", "4": "four", "5": "five", "6": "six", "7": "seven", "8": "eight",
           "9": "nine", "10": "ten", "12": "twelve", "14": "fourteen", "15": "fifteen", "20": "twenty", "30": "thirty",
           "45": "forty-five", "60": "sixty", "90": "ninety", "180": "one hundred eighty"}
ORDINAL = {"1": "first", "2": "second", "3": "third", "4": "fourth", "5": "fifth", "6": "sixth", "7": "seventh",
           "8": "eighth", "9": "ninth", "10": "tenth", "12": "twelfth", "14": "fourteenth", "15": "fifteenth",
           "20": "twentieth", "30": "thirtieth", "45": "forty-fifth", "60": "sixtieth", "90": "ninetieth",
           "180": "one hundred eightieth"}
# an ordinal counts only as a period ("the fifth anniversary", "the tenth day"), not as "a second offense"
ORDINAL_UNIT = r"(?:\s+(?:business|working|calendar|judicial))?\s+(?:anniversary|day|week|month|year)"


def _spelled(num: str) -> str:
    return WORDNUM.get(num, "\0")


def has_num(num: str, text: str) -> bool:
    """``num`` is in ``text`` as a whole number (not the 5 of 1995 or 45, the 2 of 19.2, the 500 of $1,500), as its
    word (not the "ten" of "sentence", the "five" of "forty-five") or as an ordinal period ("fifth anniversary")."""
    if not num:
        return False
    if re.search(rf"(?<!\d)(?<!\d[.,]){re.escape(num)}(?!\d|[.,]\d)", text):
        return True
    word, nth = WORDNUM.get(num), ORDINAL.get(num)
    return bool(word and re.search(rf"(?<![\w-]){re.escape(word)}(?!\w)", text, re.I)) or \
        bool(nth and re.search(rf"(?<![\w-]){re.escape(nth)}{ORDINAL_UNIT}", text, re.I))


def _check_steps(spec: dict, state: str, qid: str, problems: list[str]) -> dict:
    """A process answer must pass what the curated state models pass: exact quotes, schemas, lint, soundness."""
    from ..extract.ollama import check_facts
    from ..extract.schema import LegalProcessFacts
    from ..ir import Provenance
    from ..municipal import build as B
    from ..municipal import statutes
    from ..municipal.quality import assess
    refs = [g["ref"] for g in spec.get("gold_sections") or []]
    try:
        texts = statutes.section_texts(state, refs)
        facts = LegalProcessFacts.model_validate(spec["steps"])
    except Exception as e:  # noqa: BLE001
        problems.append(f"steps: {type(e).__name__}: {str(e)[:600]}")
        return {}
    text = statutes.combined_text(texts)
    bad = check_facts(facts, text)
    problems += [f"steps: {p}" for p in bad]
    if bad:
        return {"steps": len(facts.steps)}
    model = B._compile(facts, state, qid, texts, Provenance(method="gold-manual"))
    model.texts = texts
    res = assess(model, agreement=1.0)
    if not res["validated"]:
        problems.append(f"steps: the process does not validate: {res['errors'][:3]} {res['metrics']}")
    return {"steps": len(facts.steps), "quality": res["quality"], "validated": res["validated"]}


def hash_of(spec: dict) -> str:
    """A short hash of a reference's content (results record which version they were scored against)."""
    import hashlib
    return hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()[:12]
