"""Rebuild whole code sections from LOCUS chunks.

LOCUS rows are heading-split OCR chunks.  Problems this module repairs, each
recorded as a flag on the rebuilt section so reviewers can see it:

* ``subsection-row``      - a chunk is a subsection (``A. ...``) of the section before it
* ``page-head-row``       - a running head became the chunk header (``# ALBEMARLE COUNTY CODE``)
* ``header-as-content``   - the chunk header carries body text (``F. Judicial review. A final ...``)
* ``header-mismatch``     - header names one section, content holds others (``Sec. 17-37`` row with 17-1..17-7)
* ``missing-subsection``  - lettered/numbered subsections skip a value (A..D, F -> E missing)
* ``page-furniture``      - supplement footers / page numbers / running heads removed
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .clean import clean_text
from .history import split_history

SEC_HEAD = re.compile(
    r"^#*\s*(?:\*\*)?\s*(?:Sec(?:tion)?s?\.?|§)\s*(?P<num>\d+(?:\.\d+)?[-.]\d+(?:\.\d+)*(?::\d+)?[A-Za-z]?)"
    r"(?:,\s*\d+[-.\d]*)*\.?\s*(?P<title>.*?)(?:\*\*)?\s*$")
DOTTED_HEAD = re.compile(r"^#*\s*(?P<num>\d+\.\d+\.\d+)\s+(?P<title>.+)$")
SUB_HEAD = re.compile(r"^#*\s*(?P<label>[A-Z]|\d{1,2}|\([a-z0-9]{1,3}\))\.?\s+(?P<rest>[A-Z].*)$")
EMBEDDED = re.compile(r"^\*\*Sec\.\s*(?P<num>\d+[-.]\d+(?:\.\d+)?)\.\s*(?P<title>.*?)\*\*\s*$", re.M)


@dataclass
class Section:
    number: str
    title: str
    code: str
    jurisdiction: str
    text: str = ""
    history: str | None = None
    rows: list[int] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    subsections: list[str] = field(default_factory=list)

    def add(self, chunk: str, row: int | None = None):
        chunk = chunk.strip()
        if chunk:
            self.text = (self.text + "\n\n" + chunk).strip()
        if row is not None and row not in self.rows:
            self.rows.append(row)


def parse_header(header: str) -> dict:
    h = header.strip()
    bare = re.sub(r"^#+\s*", "", h)
    m = SEC_HEAD.match(h) or DOTTED_HEAD.match(h)
    if m:
        title = m.group("title").strip()
        return {"kind": "section", "number": m.group("num"), "title": title.rstrip(".") + ("." if title else "")}
    if re.fullmatch(r"[A-Z][A-Z ,&'—\-]+", bare) and len(bare.split()) <= 6:
        return {"kind": "page-head", "text": bare}
    m = SUB_HEAD.match(h)
    if m:
        rest = m.group("rest").strip()
        # "D. Conduct of hearing. The hearing will be..." -> title + body
        parts = re.split(r"(?<=\.)\s+", rest, maxsplit=1)
        title = parts[0]
        body = parts[1] if len(parts) > 1 else ""
        return {"kind": "subsection", "label": m.group("label").strip("()"), "title": title, "body": body}
    return {"kind": "other", "text": bare}


def _expected_sequence(labels: list[str]) -> list[str]:
    missing = []
    letters = [l for l in labels if len(l) == 1 and l.isalpha() and l.isupper()]
    for a, b in zip(letters, letters[1:]):
        for code in range(ord(a) + 1, ord(b)):
            missing.append(chr(code))
    return missing


def resegment(rows: list[dict], code: str, jurisdiction: str) -> list[Section]:
    """Rebuild sections from LOCUS rows (dicts with row/header/content), in row order."""
    sections: list[Section] = []
    current: Section | None = None
    for r in sorted(rows, key=lambda x: x["row"]):
        head = parse_header(r["header"])
        content, removed = clean_text(r["content"])
        embedded = list(EMBEDDED.finditer(content))
        if head["kind"] == "section" and embedded and not re.search(
                re.escape(head["number"]), content[: embedded[0].start()] if embedded else content):
            # header-mismatch: trust the headings embedded in the content
            pre = content[: embedded[0].start()].strip()
            if pre:
                orphan = Section(f"{head['number']}?", "(text not attributable to a section)", code, jurisdiction)
                orphan.add(pre, r["row"])
                orphan.flags.append(f"unattributed-text:row {r['row']}")
                sections.append(orphan)
            for i, em in enumerate(embedded):
                end = embedded[i + 1].start() if i + 1 < len(embedded) else len(content)
                current = Section(em.group("num"), em.group("title").strip(), code, jurisdiction)
                current.add(content[em.end():end], r["row"])
                current.flags.append(f"header-mismatch:row {r['row']} header says {head['number']}")
                if removed:
                    current.flags.append("page-furniture")
                sections.append(current)
            continue
        if head["kind"] == "section":
            current = Section(head["number"], head["title"], code, jurisdiction)
            sections.append(current)
            if re.match(r"^Secs?\.\s*\d", content) and head["number"] not in content:
                current.flags.append(f"header-mismatch:row {r['row']} content: {content[:40]}")
            current.add(content, r["row"])
        elif head["kind"] == "subsection" and current is not None:
            current.subsections.append(head["label"])
            if head["body"]:
                current.flags.append(f"header-as-content:{head['label']}")
            current.add(f"{head['label']}. {head['title']} {head['body']}".strip() + ("\n\n" + content if content else ""),
                        r["row"])
        elif head["kind"] == "page-head" and current is not None:
            current.flags.append(f"page-head-row:{r['row']}")
            current.add(content, r["row"])
        elif current is not None:
            current.add(content, r["row"])
        else:
            continue
        if removed and "page-furniture" not in current.flags:
            current.flags.append("page-furniture")
    for s in sections:
        # glue paragraphs split across chunk boundaries (C.1 ... page head ... C.2)
        s.text, _ = clean_text(s.text)
        s.text, s.history = split_history(s.text)
        missing = _expected_sequence(s.subsections)
        for label in missing:
            s.flags.append(f"missing-subsection:{label}")
    return sections
