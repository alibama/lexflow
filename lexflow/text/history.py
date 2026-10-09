"""Split and parse history notes ("source notes") at the end of code sections.

Formats seen in Virginia municipal codes (Municode-style):
  (Code 1976, § 16.1-5)
  (9-17-01; 3-3-08; 5-2-11)                         Charlottesville: adoption dates
  (Code 1976, §§ 17-10—17-13; 12-16-96, § 1; 9-7-21(1), § 2)
  (Ord. 14-17(1), 5-7-14, effective 7-1-14; Ord. 24-17(1), 6-5-24)   Albemarle
  (§ 17-210: § 7-7, 6-18-75, § 9, 2-11-87; ... § 17-211, Ord. 14-17(1), 5-7-14, effective 7-1-14)
Trailing editorial notes (publisher annotations) are kept separately:
  Cross reference—..., Charter reference—..., State law reference(s)—...
"""
from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field

NOTE = re.compile(r"^[*_\s]*(Cross references?|Charter references?|State law references?|Editor's note)\s*[—\-:]", re.I)
HISTORY_PARA = re.compile(r"^\(.*\)$", re.S)
DATE = re.compile(r"(?<![\d.\-])(\d{1,2})-(\d{1,2})-(\d{2}|\d{4})(?![\d\-])")
ORD = re.compile(r"\bOrd\.\s*(?:No\.\s*)?([A-Z]?-?\d{2,4}-[\w()]+(?:\(\d+\))?)")
EFFECTIVE = re.compile(r"effective\s+(\d{1,2}-\d{1,2}-\d{2,4})", re.I)
FORMER = re.compile(r"Code\s+(\d{4}),?\s*§§?\s*([\d.\-—:]+)")


def _year(y: str) -> int:
    y_i = int(y)
    if len(y) == 4:
        return y_i
    pivot = dt.date.today().year % 100
    return 2000 + y_i if y_i <= pivot else 1900 + y_i


def to_date(token: str) -> str | None:
    m = DATE.search(token)
    if not m:
        return None
    month, day, year = int(m.group(1)), int(m.group(2)), _year(m.group(3))
    try:
        return dt.date(year, month, day).isoformat()
    except ValueError:
        return None


def split_history(text: str) -> tuple[str, str | None]:
    """Peel trailing history parentheticals and editorial notes off a section body."""
    paras = [p for p in text.split("\n\n")]
    tail: list[str] = []
    while paras:
        p = paras[-1].strip()
        p_plain = p.strip("*_ ")
        if NOTE.match(p) or (HISTORY_PARA.match(p_plain) and (DATE.search(p_plain) or "Code 19" in p_plain or "Ord." in p_plain)):
            tail.insert(0, p)
            paras.pop()
            continue
        # history paragraph followed by inline editorial notes: "(...) (...)"
        if re.match(r"^\(.*\)\s*\(.*\)$", p_plain, re.S) and DATE.search(p_plain):
            tail.insert(0, p)
            paras.pop()
            continue
        break
    body = "\n\n".join(paras).strip()
    return body, ("\n\n".join(tail).strip() or None)


@dataclass
class Amendment:
    raw: str
    ordinance: str | None = None
    adopted: str | None = None
    effective: str | None = None
    former_location: str | None = None


@dataclass
class History:
    amendments: list[Amendment] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    former_codes: list[str] = field(default_factory=list)

    @property
    def last_amended(self) -> str | None:
        dates = [a.adopted for a in self.amendments if a.adopted]
        return max(dates) if dates else None

    @property
    def first_enacted(self) -> str | None:
        dates = [a.adopted for a in self.amendments if a.adopted]
        return min(dates) if dates else None


def parse_history(history: str | None) -> History:
    h = History()
    if not history:
        return h
    for para in history.split("\n\n"):
        p = para.strip().strip("*_ ")
        if NOTE.match(para) or NOTE.match(p):
            h.notes.append(p)
            continue
        for group in re.findall(r"\(([^()]*(?:\([^()]*\)[^()]*)*)\)", p):
            for m in FORMER.finditer(group):
                h.former_codes.append(f"Code {m.group(1)}, § {m.group(2)}")
            # split on ';' - each piece is one enactment / amendment record
            for piece in group.split(";"):
                piece = piece.strip()
                if not piece:
                    continue
                eff = EFFECTIVE.search(piece)
                ord_m = ORD.search(piece)
                piece_wo_eff = EFFECTIVE.sub("", piece)
                adopted = to_date(piece_wo_eff)
                if not adopted and not ord_m:
                    continue
                h.amendments.append(Amendment(
                    raw=piece,
                    ordinance=f"Ord. {ord_m.group(1)}" if ord_m else None,
                    adopted=adopted,
                    effective=to_date(eff.group(1)) if eff else None,
                ))
    return h
