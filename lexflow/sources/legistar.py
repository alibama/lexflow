"""How laws were actually processed: Legistar matter histories -> event log -> conformance.

Albemarle County runs Legistar (``webapi.legistar.com/v1/albemarle``, no token).  In
practice one ordinance's life is split across separate matters - a consent-agenda
item that schedules the public hearing, then a "Public Hearing ..." matter that is
adopted or deferred - so cases are rebuilt by linking matters on their titles.

As-written reference: Va. Code § 15.2-1427 (counties: two newspaper notices, the first
no more than 28 days and the second at least 7 days before the meeting; emergency
ordinances may skip notice but lapse after 60 days unless re-adopted).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

import requests

BASE = "https://webapi.legistar.com/v1/{client}"

AS_WRITTEN = [
    ("authorize", "Board authorizes advertisement / schedules hearing"),
    ("notice_1", "First newspaper notice (no more than 28 days before)"),
    ("notice_2", "Second newspaper notice (at least 7 days before)"),
    ("meeting", "Public meeting / hearing"),
    ("decide", "Adopt (majority of those present and voting) or defer"),
]
ACTION_MAP = {"scheduled with the consent agenda": "authorize", "approved": "authorize",
              "adopted": "decide", "deferred": "decide", "denied": "decide", "tabled": "decide"}


@dataclass
class Legistar:
    client: str
    timeout: int = 30

    def get(self, path: str, **params):
        r = requests.get(f"{BASE.format(client=self.client)}/{path}", params=params, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def ordinances(self, top: int = 1000):
        return self.get("matters", **{"$top": top, "$filter": "MatterTypeName eq 'Ordinance'",
                                      "$orderby": "MatterId desc"})

    def histories(self, matter_id: int):
        return self.get(f"matters/{matter_id}/histories")


_PREFIX = re.compile(r"^(request to |authorize |schedule |public hearing (to consider |for |to )?|"
                     r"a public hearing (to consider |for |to )?|the adoption of )+", re.I)


def subject(title: str) -> str:
    t = title.lower().strip()
    for _ in range(4):
        t = _PREFIX.sub("", t).strip()
    t = re.sub(r"\b(an|a|the|to|for|of|consider|adoption|ordinance|public|hearing)\b", " ", t)
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def _sim(a: str, b: str) -> float:
    sa, sb = set(a.split()), set(b.split())
    return len(sa & sb) / len(sa | sb) if sa | sb else 0.0


@dataclass
class Case:
    case_id: str
    matters: list[int] = field(default_factory=list)
    title: str = ""
    events: list[dict] = field(default_factory=list)

    @property
    def trace(self) -> list[str]:
        return [e["activity"] for e in sorted(self.events, key=lambda e: e["time"])]


def build_cases(matters: list[dict], histories: dict[str, list[dict]], threshold: float = 0.5) -> list[Case]:
    """Link 'schedule hearing' matters to the later 'public hearing' matter about the same subject."""
    ms = sorted(matters, key=lambda m: m["MatterId"])
    cases: list[Case] = []
    for m in ms:
        subj = subject(m["MatterTitle"])
        target = None
        for c in cases:
            if _sim(subject(c.title), subj) >= threshold and len(c.matters) < 3:
                target = c
                break
        if target is None:
            target = Case(case_id=f"case-{m['MatterFile']}", title=m["MatterTitle"])
            cases.append(target)
        target.matters.append(m["MatterId"])
        for h in histories.get(str(m["MatterId"]), []):
            target.events.append({"case": target.case_id, "matter": m["MatterId"],
                                  "activity": h["MatterHistoryActionName"].lower(),
                                  "time": h["MatterHistoryActionDate"][:10],
                                  "resource": h["MatterHistoryActionBodyName"],
                                  "consent": bool(h.get("MatterHistoryConsent"))})
    return cases


def event_log(cases: list[Case]):
    import pandas as pd
    rows = [{"case:concept:name": e["case"], "concept:name": e["activity"],
             "time:timestamp": pd.Timestamp(e["time"]), "org:resource": e["resource"]}
            for c in cases for e in c.events]
    return pd.DataFrame(rows).sort_values(["case:concept:name", "time:timestamp"])


@dataclass
class Conformance:
    cases: int
    complete_cases: int
    variants: dict[str, int]
    days_authorize_to_decision: list[int]
    observable_steps: list[str]
    unobservable_steps: list[str]
    findings: list[str]


def conformance(cases: list[Case]) -> Conformance:
    variants: dict[str, int] = {}
    gaps, complete = [], 0
    for c in cases:
        key = " → ".join(c.trace) or "(no history rows)"
        variants[key] = variants.get(key, 0) + 1
        steps = [ACTION_MAP.get(a) for a in c.trace]
        times = sorted(c.events, key=lambda e: e["time"])
        if "authorize" in steps and "decide" in steps:
            complete += 1
            t0 = next(e["time"] for e in times if ACTION_MAP.get(e["activity"]) == "authorize")
            t1 = next(e["time"] for e in times if ACTION_MAP.get(e["activity"]) == "decide")
            gaps.append((date.fromisoformat(t1) - date.fromisoformat(t0)).days)
    observable = sorted({ACTION_MAP[a] for c in cases for a in c.trace if a in ACTION_MAP})
    unobservable = [k for k, _ in AS_WRITTEN if k not in observable]
    findings = []
    if "notice_1" in unobservable:
        findings.append("Newspaper notices required by Va. Code § 15.2-1427(F) leave no trace in Legistar; "
                        "compliance cannot be checked from this data alone (needs ad affidavits).")
    if gaps and min(gaps) < 7:
        findings.append("Some decisions came less than 7 days after authorization - check notice timing.")
    if any(c.trace == ["adopted"] for c in cases):
        findings.append("Adopted ordinances with no linked scheduling matter (link by title failed or step missing).")
    findings.append("MatterEnactmentNumber is empty, so adopted ordinances cannot be joined to the code's "
                    "history notes (e.g. 'Ord. 24-17(1)') without text matching.")
    return Conformance(len(cases), complete, variants, gaps, observable, unobservable, findings)
