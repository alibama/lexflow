"""Remove page furniture that OCR left inside LOCUS chunks and re-join split paragraphs.

Observed in LOCUS-v1 (Charlottesville / Albemarle rows):
  * supplement footers  ``Supp. No. 40 985`` / ``Supp. No. 4      17-24``
  * bare page numbers   ``986``
  * running heads       ``NOISE CONTROL`` / ``CHARLOTTESVILLE CITY CODE`` / ``§ 16-9`` / ``$ 16-9``
  * page-turn notes     ``[The next page is 1033]``
  * sentences broken across a page (``between the hours of 10:00`` ... ``p.m. and 6:00 a.m.``)
"""
from __future__ import annotations

import re

FURNITURE = [
    re.compile(r"^\s*Supp\.\s*No\.\s*\d+(\s+[\w\-.]+)?\s*$"),
    re.compile(r"^\s*\d{1,4}\s*$"),
    re.compile(r"^\s*[§$]{1,2}\s*\d+[\w\-.:]*\s*$"),
    re.compile(r"^\s*\[The next page is [\w\-.]+\]\s*$", re.I),
]
RUNNING_HEAD = re.compile(r"^\s*[A-Z][A-Z ,&'—\-]{2,58}[A-Z]\s*$")
TERMINAL = tuple('.;:)"”]!?') + ("*",)


def _is_furniture(line: str) -> bool:
    return any(p.match(line) for p in FURNITURE)


def clean_text(text: str, extra_heads: tuple[str, ...] = ()) -> tuple[str, list[str]]:
    """Return (clean text, list of removed lines)."""
    lines = text.replace("\r\n", "\n").split("\n")
    furniture_idx = {i for i, ln in enumerate(lines) if _is_furniture(ln)}
    removed_idx = set(furniture_idx)
    for i, ln in enumerate(lines):
        if ln.strip() in extra_heads:
            removed_idx.add(i)
            continue
        if RUNNING_HEAD.match(ln) and len(ln.split()) <= 6:
            # only treat ALL-CAPS lines as running heads when they sit next to other furniture
            near = any(j in furniture_idx for j in range(i - 3, i + 4) if j != i)
            if near:
                removed_idx.add(i)
    removed = [lines[i] for i in sorted(removed_idx) if lines[i].strip()]
    kept = [ln for i, ln in enumerate(lines) if i not in removed_idx]
    out = "\n".join(kept)
    out = re.sub(r"[ \t]+\n", "\n", out)
    out = re.sub(r"\n{3,}", "\n\n", out).strip()
    # re-join paragraphs split by a page break: no terminal punctuation + lowercase continuation
    paras = out.split("\n\n")
    joined: list[str] = []
    for p in paras:
        if joined and not joined[-1].rstrip().endswith(TERMINAL) and p[:1].islower():
            joined[-1] = joined[-1].rstrip() + " " + p.lstrip()
        elif joined and not joined[-1].rstrip().endswith(TERMINAL) and re.match(r"^[a-z]", p.strip()):
            joined[-1] = joined[-1].rstrip() + " " + p.strip()
        else:
            joined.append(p)
    return "\n\n".join(joined), removed
