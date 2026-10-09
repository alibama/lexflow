"""SearXNG (self-hosted metasearch) for finding the law around a provision.

Enable JSON in settings.yml (``search.formats: [html, json]``); keep the limiter off for
the pipeline's own IP or list it in ``pass_ip`` - the limiter flags python-requests as a bot.
Used for: resolving cited state law, finding the adopting ordinance / minutes for a history
note, case law that construes a section, and the publisher page to "recurse to the original".
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import requests

from ..ir import SectionText
from ..text.citations import find_citations
from ..text.history import parse_history

KINDS = [
    ("va-code", re.compile(r"law\.lis\.virginia\.gov/vacode/")),
    ("va-admin-code", re.compile(r"law\.lis\.virginia\.gov/admincode/")),
    ("va-charter", re.compile(r"law\.lis\.virginia\.gov/charters/")),
    ("municipal-code", re.compile(r"library\.municode\.com|ecode360\.com|codelibrary\.amlegal\.com")),
    ("legislation", re.compile(r"legistar\.com|civicclerk\.com|boarddocs\.com|primegov\.com")),
    ("minutes-records", re.compile(r"weblink\.|laserfiche|/DocumentCenter/")),
    ("case-law", re.compile(r"courtlistener\.com|casetext\.com|law\.justia\.com/cases|vacourts\.gov")),
    ("government", re.compile(r"\.gov(/|$)|albemarle\.org|charlottesville\.gov")),
]


def classify(url: str) -> str:
    for kind, pat in KINDS:
        if pat.search(url):
            return kind
    return "other"


@dataclass
class SearX:
    base_url: str = "http://localhost:8080"
    timeout: int = 20
    user_agent: str = "lexflow/0.3 (+https://lexipedia.xyz)"

    def search(self, q: str, *, categories: str | None = None, engines: str | None = None,
               language: str = "en", pageno: int = 1, time_range: str | None = None) -> list[dict]:
        params = {"q": q, "format": "json", "language": language, "pageno": pageno}
        if categories:
            params["categories"] = categories
        if engines:
            params["engines"] = engines
        if time_range:
            params["time_range"] = time_range
        r = requests.get(f"{self.base_url.rstrip('/')}/search", params=params, timeout=self.timeout,
                         headers={"User-Agent": self.user_agent, "Accept": "application/json"})
        if r.status_code == 403:
            raise RuntimeError("SearXNG returned 403: add 'json' to search.formats in settings.yml")
        r.raise_for_status()
        out = []
        for item in r.json().get("results", []):
            out.append({"title": item.get("title", ""), "url": item.get("url", ""),
                        "snippet": item.get("content", ""), "engine": item.get("engine", ""),
                        "kind": classify(item.get("url", ""))})
        return out


def queries_for(section: SectionText, jurisdiction_name: str) -> list[dict]:
    """Search plan for one provision: what to look up and which result kind answers it."""
    plan = [{"purpose": "official text of this section", "want": "municipal-code",
             "q": f'"{section.section}" "{section.title.rstrip(".")}" {jurisdiction_name} code'}]
    for c in find_citations(section.text, section.jurisdiction):
        if c.kind == "va-code":
            plan.append({"purpose": f"cited state statute {c.section}", "want": "va-code",
                         "q": f'"{c.section}" site:law.lis.virginia.gov'})
        elif c.kind == "va-admin":
            plan.append({"purpose": f"cited regulation {c.section}", "want": "va-admin-code",
                         "q": f'"{c.section}" site:law.lis.virginia.gov'})
    hist = parse_history(section.history)
    for a in hist.amendments[-3:]:
        if a.ordinance:
            plan.append({"purpose": f"adopting {a.ordinance} ({a.adopted})", "want": "legislation",
                         "q": f'"{a.ordinance}" {jurisdiction_name} board minutes'})
    plan.append({"purpose": "court decisions construing this section", "want": "case-law",
                 "q": f'"{section.code}" "{section.section}"'})
    return plan
