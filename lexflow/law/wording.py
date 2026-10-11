"""Time limits in the law's own words.

A model keeps a deadline as a number and a unit for the arithmetic (``{"amount": 5, "unit": "business_days"}``).
That unit is lexflow's, not the statute's: Virginia's "five working days" and "seven work days", Maryland's "10
working days" and DC's "15 days (except Saturdays, Sundays, and legal public holidays)" all become
``business_days``.  Public pages print the statute's own phrase instead.  It is found in the quotes the model
already carries, each of them checked word for word against the statute text, so nothing here is reworded:

    "within five working days"          the deadline's own quote states the period
    "an additional seven work days"
    lexflow's count: 15 + up to 10      no quote states the figure: lexflow added two periods the law does state

``describe`` gives one step's time limit; ``timer_label`` names that time limit's timer on the process map in the
same words (the compiler uses it, so the map never shows lexflow's unit); ``audit`` re-checks every curated deadline
this way and lists those whose stored unit or number the quote does not bear out.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from ..extract.segment import _amount

# what may open a time limit; a comparative ("shall not exceed", "for more than") makes a derived part "up to"
LEADS = ("within", "for not more than", "not more than", "no more than", "not later than", "no later than",
         "on or before", "at least", "before the end of", "at the end of", "not to exceed", "shall not exceed",
         "not exceed", "exceed", "for more than", "more than", "an additional", "additional", "up to", "has",
         "have", "shall have", "before", "by")
COMPARATIVE = re.compile(r"exceed|more than|up to", re.I)
UNIT_WORDS = {"hours": "hours", "days": "days", "business_days": "business days", "weeks": "weeks",
              "months": "months", "years": "years"}
PHRASE = re.compile(
    r"(?P<lead>\b(?:" + "|".join(sorted((r"\s+".join(map(re.escape, x.split())) for x in LEADS), key=len, reverse=True))
    + r")\s+(?:the\s+)?)?"
    r"(?P<amount>\b\d+|\b[a-z]+(?:-[a-z]+)?(?:\s+hundred(?:\s+(?:and\s+)?[a-z]+(?:-[a-z]+)?)?)?)"
    r"(?:st|nd|rd|th)?\s*(?:\(\d+\)\s*)?"                                   # "ten (10) days"
    r"(?P<adj>working|business|calendar|work|judicial|court)?[\s-]*"
    r"(?P<unit>days?|weeks?|months?|years?|hours?)\b"
    r"(?P<paren>\s*\((?:except|excluding|exclusive of|not counting|not including)\b[^)]*\))?", re.I)


def phrases(text: str | None) -> list[dict]:
    """Every time limit a quote states: its words exactly as written, the number, and the unit they come to."""
    out = []
    for m in PHRASE.finditer(text or ""):
        n = _amount(m.group("amount"))
        if n is None:
            continue
        unit = m.group("unit").lower().rstrip("s")
        adj = (m.group("adj") or "").lower()
        paren = m.group("paren") or ""
        no_weekends = bool(re.search(r"saturday|weekend", paren, re.I))
        if unit == "day":
            kind = "business_days" if adj in ("working", "business", "work", "judicial", "court") or no_weekends \
                else "days"
        else:
            kind = unit + "s"
        words = re.sub(r"\s+", " ", m.group(0)).strip()
        out.append({"words": words, "amount": n, "kind": kind, "adj": adj, "paren": paren.strip(),
                    "lead": re.sub(r"\s+", " ", (m.group("lead") or "")).strip().lower()})
    return out


def wording(stored_unit: str, p: dict) -> str:
    """How a found phrase compares with the stored unit: 'agrees', 'relabelled' (same count, other words: the
    stored ``business_days`` for "working days") or 'disagrees' (a different kind of unit)."""
    if p["kind"] != stored_unit:
        return "disagrees"
    if stored_unit == "business_days":
        return "agrees" if p["adj"] == "business" and not p["paren"] else "relabelled"
    if stored_unit == "days":
        return "agrees" if p["adj"] in ("", "calendar") else "relabelled"
    return "agrees"


def _quotes(facts: dict) -> list[dict]:
    """Every quote in a model's facts, with the section and subsection it cites."""
    out = []

    def walk(o):
        if isinstance(o, dict):
            if isinstance(o.get("quote"), str) and "section" in o:
                out.append(o)
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for x in o:
                walk(x)
    walk(facts or {})
    return out


def _find(amount: int, unit: str, texts: list[str]) -> tuple[dict | None, int]:
    """The first phrase in ``texts`` stating ``amount``, preferring one of the stored kind of unit; and the index
    of the text it came from."""
    hits = [(p, i) for i, t in enumerate(texts) for p in phrases(t) if p["amount"] == amount]
    same = [h for h in hits if h[0]["kind"] == unit]
    return (same or hits or [(None, -1)])[0]


def _step_texts(step: dict, facts: dict) -> list[str]:
    """Where a step's time limit can be read, in order: the deadline's own quote, the step's quote, then the other
    quotes of the model from the same subsection as the deadline's."""
    dl = step.get("deadline") or {}
    src = dl.get("source") or {}
    texts = [src.get("quote") or "", (step.get("source") or {}).get("quote") or ""]
    same = [q["quote"] for q in _quotes(facts) if q.get("section") == src.get("section")
            and (q.get("subsection") or "") == (src.get("subsection") or "")]
    return texts + [t for t in same if t not in texts]


def describe(step: dict, facts: dict | None = None) -> dict | None:
    """One step's time limit for a public page.

    Returns ``{"text", "words", "count", "parts", "wording", "in_deadline_quote"}``: ``words`` is the statute's
    phrase when a quote states the figure; otherwise ``count`` is lexflow's arithmetic ("15 + up to 10", or the
    bare figure) and ``parts`` the phrases it adds up.  ``text`` is the line to print."""
    dl = step.get("deadline")
    if not dl:
        return None
    facts = facts or {}
    amount, unit = int(dl["amount"]), dl["unit"]
    if amount == 0:
        return {"text": "no number of days in the text", "words": None, "count": None, "parts": [],
                "wording": "no figure", "in_deadline_quote": False}
    texts = _step_texts(step, facts)
    p, where = _find(amount, unit, texts)
    if p:
        return {"text": f"“{p['words']}”", "words": p["words"], "count": None, "parts": [],
                "wording": wording(unit, p), "in_deadline_quote": where == 0}
    # not stated anywhere: lexflow's sum of an earlier period and this one ("15 + up to 10")
    own = [x for t in texts[:2] for x in phrases(t) if x["kind"] == unit and x["amount"] < amount]
    for other in facts.get("steps") or []:
        if other is step or other.get("id") == step.get("id") or not other.get("deadline"):
            continue
        od = other["deadline"]
        if od["unit"] != unit or not 0 < od["amount"] < amount:
            continue
        first, _ = _find(od["amount"], unit, _step_texts(other, facts))
        for b in own:
            if first and od["amount"] + b["amount"] == amount:
                plus = "up to " if COMPARATIVE.search(b["lead"]) else ""
                count = f"{od['amount']} + {plus}{b['amount']}"
                b_words = next((t for t in texts[:2] if b["words"] in t and len(t) <= 110), b["words"])
                return {"text": f"lexflow's count: {count}, from “{first['words']}” and “{b_words}”",
                        "words": None, "count": count, "parts": [first["words"], b_words],
                        "wording": "derived", "in_deadline_quote": False}
    count = f"{amount} {UNIT_WORDS.get(unit, unit)}"
    return {"text": f"lexflow's count: {count}", "words": None, "count": count, "parts": [],
            "wording": "not stated", "in_deadline_quote": False}


NO_FIGURE = "No number of days in the text"


def timer_label(step: dict, facts: dict | None = None, *, waiting: bool = False) -> str | None:
    """The name of a time limit's timer on the process map, from the same reading as the step list: the statute's
    phrase in quotation marks (“within five working days”), "lexflow's count: 15 + up to 10" for a figure lexflow
    added up, or no number where the law gives none.  ``waiting`` is the timer that races a party's own act
    (an event-based wait): it reads "Time limit passes: “...”"."""
    d = describe(step, facts)
    if d is None:
        return None
    if d["words"]:
        text = f"“{d['words']}”"
    elif d["wording"] == "no figure":
        return "Time limit passes (no number of days in the text)" if waiting else NO_FIGURE
    else:
        text = f"lexflow's count: {d['count']}"
    return f"Time limit passes: {text}" if waiting else text


def describe_text(deadline: str | None, quote: str | None) -> str | None:
    """A deadline kept as text (an asked answer's "5 business days", or a researched process's own sentence),
    printed in the words of its quote when the quote states it, and otherwise marked as lexflow's."""
    if not deadline:
        return None
    d = re.sub(r"\s+", " ", str(deadline)).strip()
    if quote and d.lower().rstrip(".") in re.sub(r"\s+", " ", quote).lower():
        return f"“{d}”"
    m = re.fullmatch(r"(\d+) (business days|days|hours|weeks|months|years)", d)
    if m:
        unit = m.group(2).replace(" ", "_")
        p, _ = _find(int(m.group(1)), unit, [quote or ""])
        return f"“{p['words']}”" if p else f"lexflow's count: {d}"
    return f"in lexflow's words: {d}"


def audit(curated: Path) -> list[dict]:
    """Every deadline in curated/<state>/<question>.json, read this way.  A row whose ``wording`` is not 'agrees'
    (or whose figure is not in the deadline's own quote) is one where the stored unit or number is lexflow's
    and not the quote's."""
    rows = []
    for path in sorted(Path(curated).glob("*/*.json")):
        try:
            spec = json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            continue
        facts = spec.get("facts") or {}
        for s in facts.get("steps") or []:
            dl = s.get("deadline")
            if not dl:
                continue
            d = describe(s, facts)
            rows.append({"model": f"{path.parent.name}.{path.stem}", "step": s["id"], "amount": dl["amount"],
                         "unit": dl["unit"], "section": (dl.get("source") or {}).get("section"),
                         "subsection": (dl.get("source") or {}).get("subsection"),
                         "quote": (dl.get("source") or {}).get("quote"), **d})
    return rows
