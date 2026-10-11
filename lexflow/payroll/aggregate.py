"""Headcount and pay quartiles by (state, government, agency, title) from projected payroll rows.

Input rows come from :func:`lexflow.payroll.sources.project`, so they hold only the canonical fields (agency,
title, pay, pay basis, period) and a count ``n``. The output holds counts and rounded quartiles, never a row about
a person. One output row (a *cell*) per (state, government, agency, title, period):

* ``n`` is the headcount, whatever the pay basis.
* ``pay_basis``, ``n_pay``, ``p25``, ``median`` and ``p75`` describe the cell's main pay basis (the one most of its
  people are paid on). ``other_pay`` lists the same figures for any other basis, so an hourly rate and an annual
  salary are never pooled.
* Each agency also gets an all-titles cell (``title='*'``) and each government an all-agencies cell
  (``agency='*'``), so people in small titles still count toward their office.
* Nothing is grouped by gender, race, age, dates or IDs: those fields never reach this module.

**What the counts count.** Every count and threshold below counts rows. A row is one person only for a source
whose registry entry says so (``Dataset.rows == 'person'``: at most one row per person per period, from the
publisher's own documentation). Elsewhere one person may have two rows (two jobs, appended quarters), so 11 rows
can be fewer than 11 people. Pay is therefore published only from a ``rows='person'`` source; any other source
gets headcounts of rows and no pay (``WHY['rows']``).

**Disclosure rules.** The sources publish every person's pay already; these rules are about what lexflow
republishes. No published pay figure equals the exact pay of 1 to 10 people. No union or difference of the pay
groups published from one fetch isolates 1 to 10 people. And, given the record of what earlier releases published
(``earlier``), no pay group published from this release has a headcount within 10 of one published from an earlier
release. They go further than ``payroll-research.md`` §7.3 (cell size 5), because that rule failed: with type-7
quartiles a 5-person cell published the 2nd, 3rd and 4th person's pay, rounded only to $100 a year or $0.25 an hour
(so exactly, for a round salary).

1. **Headcount** (``n``, ``n_pay``) is published for 5 or more people (``MIN_COUNT``). Below that it is ``None``,
   shown as "fewer than 5". Zero is published as 0.
2. **Pay groups of 11 or more.** Quartiles for a basis are published only when at least 11 people in the cell are
   paid on it (``MIN_PAY``), only for a basis with a known rounding step, and only from a source whose rows are
   people (above).
3. **Coarse rounding.** Quartiles are rounded to $1,000 a year, $100 a month, $10 a day and $1 an hour
   (``ROUND_TO``).
4. **No figure singles out a person.** A group's quartiles are all withheld when a rounded figure equals the exact
   pay of 1 to 10 people in the group (a rate that 11 or more share is a pay-scale step, not one person's pay), or
   when 1 to 4 people's pay lies within half a step of it (``MIN_SHARED``), since the figure would pin down so few
   people's pay.
5. **No differencing.** For one period and pay basis the published groups nest (title in agency in government).
   Every published group must hold either nobody or at least 11 people outside its published sub-groups; while one
   does not, the smallest of those sub-groups is withheld. Then every union, intersection or difference of published
   groups holds 0 or at least 11 people, so subtracting one group from another never isolates a person.
6. **One period per fetch.** Rule 5 can only work within one period: lexflow reads no IDs, so nobody can be
   matched across periods, and the same group in two periods differs by whoever joined or left (11 clerks one
   year, the same 11 and a newcomer the next: twice the second median minus the first can give the newcomer's pay).
   So when a fetch holds several periods, pay is published for the latest only (``pay_period``) and the others keep
   their headcounts. A period read from the source's period column wins over rows that have none.
7. **No differencing across releases.** The same attack works across two fetches, wherever the earlier figures
   survive (wiki history, a synced copy, a committed fixture). ``earlier`` lists every pay group lexflow has
   published from earlier releases of the source (period, basis and ``n_pay``: counts only, see
   :func:`pay_groups`). A pay group of this release is withheld when its ``n_pay`` is within 10 of any of them on
   the same basis, whatever its agency or title (a renamed office holds the same people) and equal counts included
   (one leaver and one joiner leave the count unchanged). Two groups whose sizes differ by 11 or more differ by at
   least 11 people, so a published pair of releases never isolates 1 to 10 people. The record must be kept for as
   long as any earlier figure may survive, which is for good; lexflow cannot tell a lost record from a first
   release, so whoever stores cells keeps it (``build_fixture`` carries it in the fixture's ``pay_published``).

Not covered (see ``payroll-plan.md`` §6.1):

* A figure that falls between two people's pay is a weighted mix of the two, which an insider who knows one of
  them and their ranks could use to estimate the other.
* A headcount under 5 can sometimes be worked out by subtracting published headcounts. An agency's count minus its
  titles' counts says how many people hold the other titles. A cell's ``n`` minus its ``n_pay`` says that 1 to 4
  people in it are on another pay basis or have no pay figure (for Norfolk, which has no empty pay values: in a
  temporary, part-time, retiree, sheriff or state-compensated class). One period's or release's count minus
  another's says how many joined or left. Each says how many people, never what they are paid.
* Rule 7 is only as complete as ``earlier``: a release published without passing the record is not protected.

Why a group was withheld is not published per cell, only counted per source. :func:`describe` says only what the
cell itself shows: a group under 11, a basis with no rounding step, a source whose rows are not people, or else
that a figure could single out one person, alone or set against another lexflow publishes.

``python -m lexflow.payroll.aggregate --out fixtures/payroll/sample_aggregates.json`` reads the enabled sources
once (politely, see ``sources.py``) and writes a small sample of the cells; the rows read are discarded. The pay
groups of the fixture it replaces (and of the committed fixture, and of any ``--earlier`` file) are rule 7's
``earlier``, and are carried into the new fixture.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable

import requests

from . import sources as S

MIN_COUNT = 5        # smallest headcount published
MIN_PAY = 11         # smallest group whose pay quartiles are published
MIN_SHARED = 5       # a figure's rounding band holds the pay of nobody in the group, or of at least this many
ROUND_TO = {"annual": 1000.0, "paid_year": 1000.0, "monthly": 100.0, "daily": 10.0, "hourly": 1.0}
ALL = "*"
NOT_GIVEN = "(not given)"
QUARTILES = (("p25", 0.25), ("median", 0.5), ("p75", 0.75))
PAY_KEYS = ("pay_basis", "n_pay", "p25", "median", "p75", "suppressed")
# why a pay group was withheld; counted per source, never stored per cell
WHY = {"small": f"fewer than {MIN_PAY} people", "basis": "no rounding step for the pay basis",
       "match": "a figure would equal or pin down one person's pay", "overlap": "it differs from a published group "
       f"by fewer than {MIN_PAY} people", "period": "pay is published for one period per fetch, and this is not it",
       "rows": "the source may list one person more than once, so its rows are not a count of people",
       "release": f"its headcount is within {MIN_PAY - 1} of a pay group published from an earlier release"}
# what describe() says when pay is hidden: only what the cell itself shows, never which of rules 4 to 7 applied
HIDDEN = {"small": f"lexflow shows pay only for groups of {MIN_PAY} or more people",
          "basis": "lexflow has no rounding step for that pay basis",
          "rows": "the source may list one person more than once, so lexflow cannot count the people in a group",
          "other": "lexflow never shows a figure that could single out one person, alone or set against another "
                   "it publishes for another group, period or release"}
DEFAULT_FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "payroll" / "sample_aggregates.json"

# offices a records question is usually sent to (clerks, records and FOIA units, public information)
RECORDS_OFFICE = re.compile(r"\bclerk|\brecords?\b|\bfoia\b|public information|\barchiv", re.I)

parse_pay = S.parse_pay

Key = tuple[str, str, str]           # (agency, title, period)


def clean(value) -> str:
    s = re.sub(r"\s+", " ", str(value if value is not None else "")).strip()
    if s == ALL:
        return f"{ALL} (as given)"                      # a source value never passes for a roll-up
    return s or NOT_GIVEN


def headcount(n: int) -> int | None:
    """A count as published: itself from MIN_COUNT up, 0 as 0, and None ("fewer than 5") in between."""
    return n if n == 0 or n >= MIN_COUNT else None


def _kth(pairs: list[tuple[float, int]], k: int) -> float:
    """The k-th smallest value (0-based) of a sorted list of (value, count)."""
    seen = 0
    for value, count in pairs:
        seen += count
        if k < seen:
            return value
    return pairs[-1][0]


def quantile(pairs: list[tuple[float, int]], q: float) -> float:
    """Linear interpolation between order statistics (Hyndman and Fan type 7, numpy's default), counts as weights."""
    total = sum(c for _, c in pairs)
    if not total:
        raise ValueError("no values")
    h = (total - 1) * q
    lo, hi = math.floor(h), math.ceil(h)
    a, b = _kth(pairs, lo), _kth(pairs, hi)
    return a + (h - lo) * (b - a)


def band(x: float, basis: str) -> float:
    """Round to the basis's step. Raises KeyError for a basis with no step: such pay is never published."""
    step = ROUND_TO[basis]
    return round(round(x / step) * step, 2)


def _figures(pays: Counter, basis: str | None) -> tuple[dict | None, str | None]:
    """(rounded quartiles, None) when rules 2 to 4 allow them, else (None, why)."""
    n = sum(pays.values())
    if n == 0:
        return None, None                               # nothing to withhold
    if n < MIN_PAY:
        return None, "small"
    step = ROUND_TO.get(basis or "")
    if not step:
        return None, "basis"
    pairs = sorted(pays.items())
    figs = {name: band(quantile(pairs, q), basis) for name, q in QUARTILES}
    for v in set(figs.values()):
        exact = sum(c for x, c in pairs if abs(x - v) < 0.005)
        near = sum(c for x, c in pairs if abs(x - v) <= step / 2 + 0.005)
        if 0 < exact < MIN_PAY or 0 < near < MIN_SHARED:
            return None, "match"
    return figs, None


def _parent(key: Key) -> Key | None:
    agency, title, period = key
    if title != ALL:
        return (agency, ALL, period)
    if agency != ALL:
        return (ALL, ALL, period)
    return None


def protect_overlaps(sizes: dict[Key, int], published: set[Key]) -> list[Key]:
    """Rule 5 for one period and basis. ``sizes`` is n_pay per cell; ``published`` is changed in place.

    Returns the cells withheld, in order. Each round finds a published group that holds 1 to MIN_PAY - 1 people
    outside its largest published sub-groups and withholds the smallest of those sub-groups. It ends, because each
    round withholds one group, and at worst a group stands alone (it has at least MIN_PAY people).
    """
    children: dict[Key, list[Key]] = defaultdict(list)
    for k in sizes:
        p = _parent(k)
        if p is not None and p in sizes:
            children[p].append(k)

    def cover(k: Key) -> list[Key]:                     # the largest published groups inside k
        out, stack = [], list(children.get(k, ()))
        while stack:
            c = stack.pop()
            if c in published:
                out.append(c)
            else:
                stack.extend(children.get(c, ()))
        return out

    order = sorted(sizes, key=lambda k: (k[1] != ALL, k[0] != ALL, k))     # government, agencies, titles
    withheld: list[Key] = []
    changed = True
    while changed:
        changed = False
        for k in order:
            if k not in published:
                continue
            inside = cover(k)
            rest = sizes[k] - sum(sizes[c] for c in inside)
            if 0 < rest < MIN_PAY:
                victim = min(inside, key=lambda c: (sizes[c], c))
                published.discard(victim)
                withheld.append(victim)
                changed = True
    return withheld


def _published(basis: str | None, n_pay: int, figs: dict | None) -> dict:
    out = {"pay_basis": basis, "n_pay": headcount(n_pay)}
    for name, _ in QUARTILES:
        out[name] = figs[name] if figs else None
    out["suppressed"] = figs is None
    return out


def _basis_order(basis: str) -> int:
    return S.PAY_BASES.index(basis) if basis in S.PAY_BASES else len(S.PAY_BASES)


def _period_order(label: str) -> tuple:
    """Order period labels by the numbers in them, so FY10 comes after FY9 and 2026-03-31 after 2025-03-31."""
    return tuple(int(d) for d in re.findall(r"\d+", label)), label


def pay_period(periods: Iterable[str], dated: Iterable[str] = ()) -> str | None:
    """Rule 6: the one period whose pay a fetch publishes. The latest period read from a period column, if any;
    otherwise the latest period at all (a fetch without a period column has just one)."""
    pool = set(dated) or set(periods)
    return max(pool, key=_period_order) if pool else None


def pay_groups(cells: Iterable[dict]) -> list[dict]:
    """The pay groups that published cells show pay for, as rule 7 compares them: period, basis and ``n_pay``.
    Counts only, all of them already published; no figure."""
    out = []
    for c in cells:
        for p in [{k: c.get(k) for k in PAY_KEYS}] + list(c.get("other_pay") or []):
            if not p["suppressed"] and p["n_pay"]:
                out.append({"period": c["period"], "pay_basis": p["pay_basis"], "n_pay": p["n_pay"]})
    return out


def ledger(*fixtures: dict) -> dict[str, list[dict]]:
    """Every pay group the given fixtures record as published, by source: each fixture's carried-forward
    ``pay_published`` and the pay groups of its own cells. Rule 7's ``earlier`` when a fixture is rebuilt."""
    seen: dict[str, set] = defaultdict(set)
    for fx in fixtures:
        for sid, groups in (fx.get("pay_published") or {}).items():
            seen[sid].update((g["period"], g["pay_basis"], g["n_pay"]) for g in groups)
        by_source: dict[str, list[dict]] = defaultdict(list)
        for c in fx.get("aggregates") or []:
            by_source[c["source"]].append(c)
        for sid, cells in by_source.items():
            seen[sid].update((g["period"], g["pay_basis"], g["n_pay"]) for g in pay_groups(cells))
    return {sid: [dict(zip(("period", "pay_basis", "n_pay"), t)) for t in sorted(groups)]
            for sid, groups in sorted(seen.items())}


def aggregate(rows: Iterable[dict], ds: S.Dataset, *, retrieved_at: str, withheld: Counter | None = None,
              earlier: Iterable[dict] = ()) -> list[dict]:
    """Cells keyed by (state, government, agency, title, period), with the roll-ups and rules described above.

    Pay is published for one period only (rule 6), and only from a source whose rows are people; every period
    keeps its headcounts. ``earlier`` is rule 7's record: the pay groups (dicts with ``pay_basis`` and ``n_pay``,
    as :func:`pay_groups` gives them) published from earlier releases of this source. ``withheld``, when given, is
    updated with how many pay groups each rule withheld (keys of ``WHY``).
    """
    default_period = ds.period or f"as of {retrieved_at[:10]}"
    cells: dict[Key, dict] = defaultdict(lambda: {"n": 0, "pays": defaultdict(Counter)})
    dated: set[str] = set()                             # periods read from the source's period column
    for r in rows:
        agency, title = clean(r.get("agency")), clean(r.get("title"))
        basis = r.get("pay_basis") or ds.pay_basis or "unknown"
        raw_period = r.get("period") if "period" in ds.fields else None
        if raw_period not in (None, ""):
            period = ds.period_format.format(clean(raw_period))
            dated.add(period)
        else:
            period = default_period
        n = int(r.get("n", 1))
        pay = parse_pay(r.get("pay"))
        for a, t in ((agency, title), (agency, ALL), (ALL, ALL)):
            c = cells[(a, t, period)]
            c["n"] += n
            if pay is not None:
                c["pays"][basis][pay] += n

    before: dict[str, list[int]] = defaultdict(list)    # rule 7: n_pay of pay groups from earlier releases
    for g in earlier:
        before[g["pay_basis"]].append(int(g["n_pay"]))
    why: Counter = Counter()
    figures: dict[tuple[Key, str], dict | None] = {}
    trees: dict[tuple[str, str], dict[Key, int]] = defaultdict(dict)
    shown_period = pay_period((k[2] for k in cells), dated)
    for key, c in cells.items():
        for b, pays in c["pays"].items():
            n_pay = sum(pays.values())
            if ds.rows != "person":
                figs, reason = None, "rows"                     # rows may not be people: no pay at all
            elif key[2] != shown_period:
                figs, reason = None, "period"                   # rule 6: another period of this fetch
            else:
                figs, reason = _figures(pays, b)                # rules 2 to 4
                if figs is not None and any(abs(n_pay - m) < MIN_PAY for m in before.get(b, ())):
                    figs, reason = None, "release"              # rule 7
            figures[(key, b)] = figs
            if reason:
                why[reason] += 1
            trees[(key[2], b)][key] = n_pay
    for (_, b), sizes in sorted(trees.items()):
        published = {k for k in sizes if figures[(k, b)] is not None}
        for k in protect_overlaps(sizes, published):
            figures[(k, b)] = None
            why["overlap"] += 1
    if withheld is not None:
        withheld.update(why)

    out = []
    for key in sorted(cells):
        agency, title, period = key
        c = cells[key]
        bases = sorted(c["pays"], key=lambda b: (-sum(c["pays"][b].values()), _basis_order(b), b))
        stats = [_published(b, sum(c["pays"][b].values()), figures[(key, b)]) for b in bases]
        main = stats[0] if stats else _published(ds.pay_basis, 0, None)
        out.append({"state": ds.state, "gov_id": ds.gov_id, "government": ds.government, "agency": agency,
                    "title": title, "period": period, "n": headcount(c["n"]), **main, "other_pay": stats[1:],
                    "source": ds.id, "source_url": ds.url, "licence": ds.licence, "retrieved_at": retrieved_at})
    return out


# ---- how a cell reads in an answer --------------------------------------------------------------------------

PAY_WORDS = {"annual": "annual base pay", "hourly": "hourly rate", "paid_year": "regular pay received in the year",
             "monthly": "monthly pay", "daily": "daily rate"}


def money(x: float, basis: str | None) -> str:
    return f"${x:,.0f}"                                 # every step is a whole number of dollars


def _pay_text(s: dict, counted: bool, who: str) -> str:
    b = s["pay_basis"]
    unit = " an hour" if b == "hourly" else ""
    words = PAY_WORDS.get(b, b or "pay") + (f" ({s['n_pay']:,} {who})" if counted else "")
    return (f"{words}: median about {money(s['median'], b)}{unit}, middle half about {money(s['p25'], b)} to "
            f"{money(s['p75'], b)}{unit}")


def _hidden(p: dict, people: bool) -> str:
    """Why a hidden pay group is hidden, from what the cell shows (its count, its basis, its source's rows)."""
    if not people:
        return HIDDEN["rows"]
    if p["pay_basis"] not in ROUND_TO:
        return HIDDEN["basis"]
    if p["n_pay"] is None or p["n_pay"] < MIN_PAY:
        return HIDDEN["small"]
    return HIDDEN["other"]                              # rules 4 to 7: which one is not said


def describe(cell: dict, *, source: bool = False, ds: S.Dataset | None = None) -> str:
    """One answer line for a cell. Pay appears only for groups the disclosure rules allow.

    ``ds`` is the cell's source (default: its registry entry). A count is of "staff" only when the source's rows
    are people; otherwise it is of "payroll entries", and no pay is shown even if the cell holds some (a cell
    stored before the rows rule)."""
    ds = ds or S.BY_ID.get(cell.get("source", ""))
    people = ds is not None and ds.rows == "person"
    staff, who = ("staff", "people") if people else ("payroll entries", "entries")
    where = cell["government"] if cell["agency"] == ALL else f"{cell['government']}, {cell['agency']}"
    if cell["title"] != ALL:
        where += f" ({cell['title']})"
    n = cell["n"]
    count = f"fewer than {MIN_COUNT} {staff}" if n is None else f"{n:,} {staff}"
    when = cell["period"] if cell["period"].startswith("as of") else f"in {cell['period']}"
    line = f"{where}: {count} {when}."
    main = {k: cell.get(k) for k in PAY_KEYS}
    parts = [p for p in [main] + list(cell.get("other_pay") or []) if p.get("n_pay") != 0]
    shown = [p for p in parts if not p["suppressed"] and people]
    why = "; ".join(dict.fromkeys(_hidden(p, people) for p in parts if p["suppressed"] or not people))
    if shown:
        text = "; ".join(_pay_text(p, len(parts) > 1, who) for p in shown)
        line += f" {text[0].upper()}{text[1:]}."
        if len(shown) < len(parts):
            line += f" Pay for the other groups is not shown: {why}."
    elif parts:
        line += f" Pay is not shown: {why}. The official source has it."
    else:
        line += " The source gives no pay figure for them."
    if source and ds and ds.id in S.BY_ID:
        line += f" Source: {ds.publisher}, {ds.title} ({ds.url})."
    return line


# ---- the sample fixture -------------------------------------------------------------------------------------

def sample(cells: list[dict], *, top_agencies: int = 8, titles: int = 12) -> list[dict]:
    """A small, readable subset: the government total, the largest agencies, records offices and records titles."""
    def size(c):
        return c["n"] or 0

    total = [c for c in cells if c["agency"] == ALL]
    agencies = sorted((c for c in cells if c["agency"] != ALL and c["title"] == ALL), key=lambda c: -size(c))
    picked = agencies[:top_agencies] + [c for c in agencies[top_agencies:] if RECORDS_OFFICE.search(c["agency"])]
    office_titles = sorted((c for c in cells if c["title"] != ALL and RECORDS_OFFICE.search(c["title"])),
                           key=lambda c: (-size(c), c["agency"], c["title"]))
    chosen = office_titles[:titles]
    if not any(c["suppressed"] for c in chosen):        # show what a suppressed cell looks like
        chosen += [c for c in office_titles[titles:] if c["suppressed"]][:1]
    return total + picked + chosen


def _slim(cell: dict) -> dict:
    return {k: v for k, v in cell.items() if k not in ("source_url", "licence", "retrieved_at")}


def _meta(ds: S.Dataset) -> dict:
    return {"id": ds.id, "state": ds.state, "gov_id": ds.gov_id, "government": ds.government,
            "publisher": ds.publisher, "title": ds.title, "url": ds.url, "endpoint": ds.endpoint,
            "licence": ds.licence, "cadence": ds.cadence, "person_level": ds.person_level, "fields": ds.fields,
            "never_read": list(ds.drop)}


def source_entry(ds: S.Dataset, f: S.Fetched, out: dict, earlier: Iterable[dict] = ()) -> None:
    """Add one fetched source to a fixture: its provenance and, unless the fetch was truncated, its sample cells.
    ``earlier`` is rule 7's record of the pay groups published from earlier releases of the source."""
    meta = {**_meta(ds), "query": f.query, "retrieved_at": f.retrieved_at, "requests": f.requests,
            "rows_received": f.read, "truncated": f.truncated}
    if f.truncated:                                     # incomplete groups: publish nothing from this fetch
        f.rows.clear()
        out["sources"].append({**meta, "withheld": "the row cap was reached, so the groups may be incomplete; "
                                                   "no cell from this fetch is kept"})
        return
    people = sum(int(r.get("n", 1)) for r in f.rows)    # rows; people only where ds.rows == "person"
    why: Counter = Counter()
    cells = aggregate(f.rows, ds, retrieved_at=f.retrieved_at, withheld=why, earlier=earlier)
    f.rows.clear()                                      # the projected rows are not kept
    out["sources"].append({
        **meta, "people": people, "cells": len(cells),
        "agencies": sum(1 for c in cells if c["title"] == ALL and c["agency"] != ALL),
        "headcounts_withheld": sum(1 for c in cells if c["n"] is None),
        "suppressed_cells": sum(1 for c in cells if c["suppressed"]),
        "pay_groups_withheld": {k: why.get(k, 0) for k in WHY}})
    out["aggregates"] += [_slim(c) for c in sample(cells)]


def build_fixture(ids: list[str] | None = None, *, datasets: list[S.Dataset] | None = None,
                  http: S.Http | None = None, row_cap: int = S.ROW_CAP, log=print,
                  earlier: Iterable[dict] = ()) -> dict:
    """Fetch the chosen sources once and build a fixture. ``earlier`` holds the fixtures this one follows (the one
    it replaces, the committed one): their pay groups are rule 7's record, and the new fixture carries that record
    forward in ``pay_published``, for every source, fetched this time or not."""
    http = http or S.Http(log=log)
    before = ledger(*earlier)
    out = {
        "about": "Sample aggregates of official public payroll data (lexflow.payroll): headcount and rounded pay "
                 "quartiles by government, agency and title. No names, IDs, dates or demographics were requested, "
                 "kept or written. Headcounts under min_count are blank; pay is shown only for groups of min_pay "
                 "or more, from a source with one row per person per period, rounded to the steps below, and is "
                 "withheld where a figure could single out one person, where two published groups differ by "
                 "fewer than min_pay people, or where a group's headcount is within min_pay - 1 of a pay group "
                 "published from an earlier release (pay_published, counts only); it is shown for one period per "
                 "fetch. See docs/design/payroll-plan.md, section 6.1.",
        "generated_at": S.now(), "min_count": MIN_COUNT, "min_pay": MIN_PAY, "min_shared": MIN_SHARED,
        "rounding": ROUND_TO, "sources": [], "pay_published": {}, "aggregates": []}
    chosen = datasets if datasets is not None else ([S.get(i) for i in ids] if ids else S.fetchable())
    for ds in chosen:
        try:
            f = S.fetch(ds, http, row_cap=row_cap, log=log)
        except (requests.RequestException, PermissionError, RuntimeError) as e:
            out["sources"].append({**_meta(ds), "error": str(e).split(" for url:")[0][:300]})   # no retry
            log(f"{ds.id}: {e}")
            continue
        source_entry(ds, f, out, earlier=before.get(ds.id, ()))
        s = out["sources"][-1]
        log(f"{ds.id}: " + (s["withheld"] if s.get("withheld") else f"{s['people']:,} rows, {s['cells']:,} cells"))
    out["pay_published"] = ledger({"pay_published": before, "aggregates": out["aggregates"]})
    return out


def dumps(fixture: dict) -> str:
    """Pretty JSON with one aggregate per line, so the fixture diffs well."""
    head = {k: v for k, v in fixture.items() if k != "aggregates"}
    text = json.dumps(head, indent=1, ensure_ascii=False)[:-2]
    rows = ",\n  ".join(json.dumps(c, ensure_ascii=False) for c in fixture["aggregates"])
    return f"{text},\n \"aggregates\": [\n  {rows}\n ]\n}}\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ids", help="comma-separated dataset ids (default: every enabled source)")
    ap.add_argument("--row-cap", type=int, default=S.ROW_CAP)
    ap.add_argument("--out", type=Path, help="write the sample fixture here")
    ap.add_argument("--earlier", type=Path, action="append", default=[],
                    help="an earlier fixture whose pay groups rule 7 compares with (always included: --out and the "
                         "committed fixture, when they exist)")
    a = ap.parse_args(argv)
    paths = dict.fromkeys(p.resolve() for p in [*a.earlier, *([a.out] if a.out else []), DEFAULT_FIXTURE]
                          if p.exists())
    earlier = [json.loads(p.read_text(encoding="utf-8")) for p in paths]
    fx = build_fixture(a.ids.split(",") if a.ids else None, row_cap=a.row_cap,
                       log=lambda m: print(m, file=sys.stderr), earlier=earlier)
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(dumps(fx), encoding="utf-8")
        print(f"wrote {a.out} ({len(fx['aggregates'])} aggregates)", file=sys.stderr)
    for c in fx["aggregates"]:
        print(describe(c))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
