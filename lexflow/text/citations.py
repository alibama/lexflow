"""Find cross-references in ordinance text and resolve them to URLs / wiki pages.

Regex patterns cover what Virginia municipal codes actually write; eyecite and
citeurl are used as optional cross-checks in the tests (eyecite misses
``Va. Code §`` without "Ann."; neither knows municipal section styles).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

VA_SECTION = r"\d+(?:\.\d+)?-\d+(?:\.\d+)*(?::\d+)?"
LOCAL_SECTION = r"\d+-\d+(?:\.\d+)?(?:\([a-zA-Z0-9]+\))*"

PATTERNS: list[tuple[str, re.Pattern]] = [
    ("va-code", re.compile(
        rf"(?:Virginia Code|Va\.\s*Code(?:\s*Ann\.)?|Code of Virginia(?:,\s*1950,\s*as amended)?),?\s*(?:§§?|[Ss]ections?|[Ss]ec\.)\s*(?P<sec>{VA_SECTION})"
        rf"(?P<more>(?:\s*(?:,|;|and|through)\s*(?:§\s*)?{VA_SECTION})*)")),
    ("va-code", re.compile(
        rf"Section\s+(?P<sec>{VA_SECTION})\s+of the Code of Virginia")),
    ("va-admin", re.compile(r"(?P<sec>\d{1,2}VAC\d{1,3}-\d{1,4}-\d{1,5})(?P<sub>(?:\(\d+\))*)")),
    ("charter", re.compile(r"Charter reference\S*?.*?§\s*(?P<sec>\d+(?:\.\d+)?[A-Z]?(?:\(\d+\))?)")),
    ("federal-pl", re.compile(r"P\.L\.\s*(?P<sec>\d{2,3}-\d{1,4})")),
    ("usc", re.compile(r"(?P<title>\d+)\s+U\.S\.C\.\s*§+\s*(?P<sec>\d+[a-z]?)")),
    ("local", re.compile(
        rf"(?:City Code|County Code|this Code)?\s*(?:§§?|[Ss]ections?|[Ss]ec\.)\s*(?P<sec>{LOCAL_SECTION})"
        rf"(?P<range>\s*(?:through|to|—|-)\s*(?P<sec2>{LOCAL_SECTION}))?")),
]


@dataclass
class Citation:
    kind: str
    section: str
    text: str
    start: int
    end: int
    url: str | None = None
    wiki: str | None = None


def va_code_url(section: str) -> str:
    return f"https://law.lis.virginia.gov/vacode/{section}/"


def vac_url(section: str) -> str:
    m = re.match(r"(\d+)VAC(\d+)-(\d+)-(\d+)", section)
    if not m:
        return "https://law.lis.virginia.gov/admincode/"
    t, a, c, s = m.groups()
    return f"https://law.lis.virginia.gov/admincode/title{t}/agency{a}/chapter{c}/section{s}/"


def charter_url(locality: str) -> str:
    return f"https://law.lis.virginia.gov/charters/{locality}/"


def find_citations(text: str, jurisdiction: str = "va/charlottesville") -> list[Citation]:
    state, _, locality = jurisdiction.partition("/")
    found: list[Citation] = []
    taken: list[tuple[int, int]] = []

    def overlaps(a, b):
        return any(not (b <= s or a >= e) for s, e in taken)

    for kind, pat in PATTERNS:
        for m in pat.finditer(text):
            sec = m.group("sec")
            if overlaps(m.start(), m.end()):
                continue
            if kind == "local":
                # skip state-style numbers (62.1-44.15:46) and dates
                if re.search(r"\d+\.\d+-", sec) or ":" in sec:
                    continue
            c = Citation(kind, sec, m.group(0).strip(), m.start(), m.end())
            if kind == "va-code":
                c.url = va_code_url(sec)
            elif kind == "va-admin":
                c.url = vac_url(sec)
            elif kind == "charter":
                c.url = charter_url(locality.replace("_county", "") or locality)
            elif kind == "local":
                base = re.sub(r"\(.*$", "", sec)
                c.wiki = f"law:{state}:{locality}:{base}"
            found.append(c)
            taken.append((m.start(), m.end()))
            if kind == "va-code" and m.groupdict().get("more"):
                for extra in re.finditer(VA_SECTION, m.group("more")):
                    s2 = extra.group(0)
                    found.append(Citation(kind, s2, s2, m.start("more") + extra.start(),
                                          m.start("more") + extra.end(), url=va_code_url(s2)))
    return sorted(found, key=lambda c: c.start)
