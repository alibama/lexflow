"""The Census Bureau's Annual Survey of Public Pensions (ASPP): every state- and locally-administered defined-benefit
system, joined to the ``governments`` table so that every county, city and township maps to the public systems that
can cover its employees.

Source: the system-level "Individual Unit Files" of the ASPP (U.S. Census Bureau, public domain), one CSV per year
(``SAMPLE_YEAR, UNIT_NAME, PID6, STATE, UNIT_TYPE, ITEM_CODE, ITEM_VALUE, EIC, ISC, FINAL_WEIGHT``; the layout is
the 2022-2025 Individual Unit File Layout).  2022 is a Census of Governments year, when every system is surveyed;
2025 is the latest year, a sample in which the state systems and the largest local ones are always included.  A
system's row is its latest year (2025 when it is in the 2025 sample, else 2022), and ``years`` lists both.

**Joins.**  The unit file has no government id: ``PID6`` is the pension unit's own six-digit id (none of them is a
government's ``CENSUS_ID_PID6``).  So a local system (government type 1 county, 2 municipal, 3 township) is joined
to the government of that type in its state whose name it carries: the government's core name (``City of
Charlottesville`` -> ``charlottesville``, ``Fairfax County`` -> ``fairfax``) found as whole words in the system's
name (``CHARLOTTESVILLE RETIREMENT FUND``), the longest core winning, and a tie between two governments of that type
with the same core left unjoined (``ambiguous``).  Special-district (4) and school-district (5) systems are not
joined: those governments are not in the ``governments`` table.  A state system (type 0) is administered by the
state; it covers a local government's employees when the Census counts local active members in it (item RJ12 > 0),
or its name says it is for municipal, county, local, school or political-subdivision employees.

``pension_coverage`` holds one row per (government, system): ``how`` is ``administers`` (the government runs the
system; the name join) or ``statewide`` (a state system with local members, open to that government's employees;
whether a given employer participates is not in the Census file), with the person types the system can cover.

    python -m lexflow.benefits census [--download] [--dry-run]
"""
from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from pathlib import Path

from .. import config
from ..store import db

BASE = "https://www2.census.gov/programs-surveys/aspp/"
FILES = {2025: "datasets/2025/aspp-historical-datasets/ASPP_Unit_File_2025.csv",
         2022: "datasets/2022/aspp-historical-datasets/ASPP_Unit_File_2022.csv"}
LAYOUT = "technical-documentation/file-layouts/2022-2025/2022-2025_File_Layout.pdf"
RAW = config.RAW_DIR / "census-aspp"
YEARS = (2025, 2022)                 # latest first: a system's row is the first year that has it
SOURCE = "census-aspp"
CITATION = ("U.S. Census Bureau, Annual Survey of Public Pensions: State- and Locally-Administered Defined Benefit "
            "Data, Individual Unit Files {years} (public domain)")
GOV_TYPE = {"0": "state", "1": "county", "2": "municipal", "3": "township", "4": "special district",
            "5": "school district"}
KIND_OF_TYPE = {"1": "county", "2": "municipality", "3": "township"}     # governments.kind
ITEMS = {"RJ01": "members_total", "RJ10": "members_active", "RJ11": "members_active_state",
         "RJ12": "members_active_local", "RJ20": "beneficiaries", "RJ30": "members_inactive", "RX40": "benefits_paid"}
STATE_ABBR = re.compile(r"^([A-Z]{2})\s+")

# the Census's abbreviations in system names, read as words (display only; matching uses MATCH_WORDS)
ABBREV = {"RET": "Retirement", "RETIRE": "Retirement", "SYS": "System", "SYST": "System", "EMP": "Employees",
          "EMPL": "Employees", "EMPL.": "Employees", "EMPLS": "Employees", "EMPOYEES": "Employees",
          "TCHRS": "Teachers", "CO": "County", "TWP": "Township", "BOR": "Borough", "UNIF": "Uniformed",
          "NON": "Non", "DEPT": "Department", "ASSOC": "Association", "ASSN": "Association", "AUTH": "Authority",
          "DIST": "District", "MUNI": "Municipal", "REG": "Regional", "TRANS": "Transit", "VOL": "Volunteer",
          "VOL.": "Volunteer", "DEF": "Defined", "BEN": "Benefit", "GEN": "General", "SUPPL": "Supplemental",
          "SUPPL.": "Supplemental", "BRD": "Board", "COMM": "Commission", "PROG": "Program", "FD": "Fire Department",
          "FPD": "Fire Protection District", "NAT": "National", "SCH": "School", "ED": "Education", "&": "and",
          "MT": "Mount", "FT": "Fort", "ST": "St.", "SAINT": "Saint"}
ACRONYMS = {a.upper(): a for a in (
    "PERS", "PERA", "PERF", "IPERS", "KPERS", "APERS", "OPERS", "LACERA", "CalPERS", "CalSTRS", "SERS", "KERS",
    "CERS", "IMRF", "LOPFI", "FPPA", "VaLORS", "SPORS", "LOSAP", "AFSCME", "MTA", "FRS", "TRF", "PSERS", "MOSERS",
    "PSRS", "STRS", "TRS", "ERS", "JRS", "JRF", "EORP", "CORP", "ASHERS", "AJRS", "PJERS", "CMERS", "MFPRSI",
    "PORS", "SURS", "GARS", "IFPIF", "PARF", "LEDB", "UCRP", "PERSI", "SPRS", "ACCG", "NYCERS", "TRSL", "MSRS",
    "PSPRS", "ATU", "RTD", "WSSC", "TRA", "PFRS", "NJ", "NY", "II", "III", "IV", "DB", "DC")}
PAREN_WORDS = {"STATE", "TEACHER", "LOCAL", "SCHOOL", "PRIMARY", "POLICE", "FIRE", "GENERAL", "CLOSED", "OPEN"}
MATCH_WORDS = {"saint": "st", "ft": "fort", "mt": "mount", "twp": "township", "co": "county", "bor": "borough",
               "boro": "borough", "muni": "municipal", "sainte": "ste"}
KIND_WORDS = {"county", "city", "town", "township", "borough", "village", "parish", "of", "municipality"}
OTHER_BODY = {"suburban", "sanitary", "metropolitan", "metro", "regional", "area", "airport", "airports", "transit",
              "housing", "hospital", "port", "transportation", "utilities", "utility", "library", "community",
              "memorial", "valley", "national"}
GOV_PREFIX = re.compile(
    r"^(?:the\s+)?(?:city and borough|city and county|city-parish|consolidated government|unified government|"
    r"metropolitan government|charter township|township|city|town|village|borough|municipality|county|parish|"
    r"plantation|corporation|county of|reservation)\s+of\s+(?:the\s+)?", re.I)
GOV_SUFFIX = re.compile(r"\s+(?:county|parish|borough|census area|municipality|city|town|township|village|"
                        r"charter township)$", re.I)

# membership read from a system's name (a state system's own name, or a local one's)
MEMBERSHIP_WORDS = [
    ("teacher", r"\bTEACH|\bTCHR|\bTRS\b|STRS\b|SCHOOL|\bSCH\b|EDUCATION|\bPSERS\b|\bTRF\b|EDUCATOR"),
    ("public_safety", r"POLICE|\bFIRE|FIREFIGHTER|FIREMEN|PEACE OFFICER|LAW ENF|LAW OFFICER|SHERIFF|PATROL|"
                      r"PUBLIC SAFETY|CORRECTION|\bLOPFI\b|\bFPPA\b|\bUNIF|TROOPER|\bSPORS\b|VALORS|\bPORS\b|\bEMS\b|"
                      r"RESCUE|DETENTION|PROBATION"),
    ("judge", r"JUDGE|JUDICIA|\bJRS\b|\bJRF\b|COURT"),
    ("legislator", r"LEGISLAT|GENERAL ASSEMBLY|ELECTED OFFICIAL"),
    ("local_employee", r"MUNICIPAL|\bMUNI\b|COUNTY|LOCAL|POLITICAL SUBDIVISION|PAROCHIAL|\bCERS\b|\bIMRF\b|\bCMERS\b|"
                       r"REGIONAL"),
    ("state_employee", r"STATE EMPLOYEE|\bSTATE\b.*EMPLOYEE|\bSERS\b|\bKERS\b|\bERS\b|EMPLOYEES'? RET|"
                       r"PUBLIC EMPLOYEE|\bPERS\b|\bPERA\b|\bPERF\b|\bIPERS\b|\bKPERS\b|\bAPERS\b|HIGHWAY|"
                       r"UNIVERSITY|\(STATE\)"),
]
LOCAL_TYPES = ("teacher", "local_employee", "public_safety")
TIER = re.compile(r"\b(TIER\s+(?:[IVX]+|\d+)|PLAN\s+(?:[A-Z]|\d+|I{1,3})\b|FUND\s+(?:[A-C]|I{1,3})\b|HYBRID|"
                  r"CASH BALANCE|\bDB\b|DEFINED BENEFIT|PRE-\d{4}|\d{4} (?:ACCOUNT|FUND)|NEW HIRE)")


# ------------------------------------------------------------------------------------------------- files
def path_for(year: int) -> Path:
    return RAW / Path(FILES[year]).name


def download(log=print) -> list[Path]:
    """The unit files and the layout, once (lexflow's downloader: the project User-Agent, sizes checked)."""
    from ..municipal.fetch import download as dl
    import time
    out = []
    for year in YEARS:
        out.append(dl(BASE + FILES[year], path_for(year), log=log))
        time.sleep(1.0)
    dl(BASE + LAYOUT, RAW / Path(LAYOUT).name, log=log)
    return out


def read_units(path: Path) -> dict[str, dict]:
    """pid6 -> {name, state, type, year, items: {code: value}} from one unit file (streamed: the 2022 file has
    about 230,000 rows)."""
    units: dict[str, dict] = {}
    with open(path, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            u = units.get(r["PID6"])
            if u is None:
                u = units[r["PID6"]] = {"pid6": r["PID6"], "census_name": " ".join((r["UNIT_NAME"] or "").split()),
                                        "state": (r["STATE"] or "").strip().lower(), "type": (r["UNIT_TYPE"] or "").strip(),
                                        "year": int(r["SAMPLE_YEAR"]), "items": {}}
            code = r["ITEM_CODE"]
            if code in ITEMS and r["ITEM_VALUE"] not in ("", None):
                try:
                    u["items"][code] = int(float(r["ITEM_VALUE"]))
                except ValueError:
                    pass
    return units


def merged(paths: dict[int, Path] | None = None) -> dict[str, dict]:
    """Every system in any year, its latest year's row first; ``years`` lists the years that have it."""
    paths = paths or {y: path_for(y) for y in YEARS}
    out: dict[str, dict] = {}
    for year in sorted(paths, reverse=True):
        if not Path(paths[year]).exists():
            continue
        for pid, u in read_units(Path(paths[year])).items():
            if pid in out:
                out[pid]["years"].append(year)
                for code, v in u["items"].items():            # an older year's count where the latest has none
                    out[pid]["items"].setdefault(code, v)
                if u["items"].get("RJ12"):
                    out[pid]["local_members_years"].append(year)
            else:
                out[pid] = {**u, "years": [year], "local_members_years": [year] if u["items"].get("RJ12") else []}
    return out


# ------------------------------------------------------------------------------------------------- names
def display_name(census_name: str) -> str:
    """'AK PUBLIC EMPLOYEES RET SYSTEM (PERS-DB)' -> 'Alaska Public Employees Retirement System (PERS-DB)': the
    Census's abbreviations read as words, the state's postal code as its name.  lexflow's reading, for display;
    the Census name is kept beside it."""
    from ..municipal import states as S
    name = census_name.strip()
    m = STATE_ABBR.match(name)
    lead = ""
    if m and m.group(1).lower() in S.NAME:
        lead, name = S.NAME[m.group(1).lower()] + " ", name[m.end():]
    words, depth, prev = [], 0, None
    groups = re.findall(r"\(([^)]*)\)", name)
    short = {t for g in groups if " " not in g.strip() for t in re.split(r"[-/]", g.strip().upper())
             if t and len(t) <= 7 and t not in PAREN_WORDS}
    for w in re.split(r"(\s+|\(|\)|-|/)", name):
        if w == "(":
            depth += 1
        elif w == ")":
            depth = max(0, depth - 1)
        if not w or w.isspace() or w in "()-/":
            words.append(w)
            continue
        up = w.upper().strip(".,'’")
        if up in ACRONYMS:
            word = ACRONYMS[up]
        elif up in ABBREV:
            word = ABBREV[up]
        elif (depth and up in short) or (not re.search(r"[AEIOUY]", up) and len(up) >= 2 and up.isalpha()):
            word = w.upper()                     # a short word alone in parentheses, or no vowel: TRS, JRS, MFPRSI
        elif re.search(r"[a-z]", w):
            word = w
        else:
            word = w[:1].upper() + w[1:].lower()
        if prev is not None and word.lower() == prev.lower() and word.lower() in ("county", "city", "town"):
            continue                             # 'WASHINGTON CO COUNTY PENSION PLAN'
        words.append(word)
        prev = word
    out = lead + "".join(words)
    out = re.sub(r"(?<=\s)(Of|And|The|For|In)\b", lambda x: x.group(1).lower(), out)
    return re.sub(r"\s+", " ", out[:1].upper() + out[1:]).strip()


def tokens(text: str) -> list[str]:
    out = []
    for w in re.findall(r"[a-z0-9]+", (text or "").lower().replace("'", "")):
        out.append(MATCH_WORDS.get(w, w))
    return out


def gov_core(name: str) -> list[str]:
    """A government's name without its kind words: 'City of Charlottesville' -> ['charlottesville'],
    'Fairfax County' -> ['fairfax'], 'Township of Upper Merion' -> ['upper', 'merion']."""
    n = re.sub(r"\(.*?\)", "", name or "").strip()
    cut = GOV_PREFIX.sub("", n)
    if cut == n:                                 # 'Fairfax County'; but 'City of University City' keeps 'City'
        cut = GOV_SUFFIX.sub("", n)
    return tokens(cut)


def _find(seq: list[str], sub: list[str]) -> int:
    k = len(sub)
    for i in range(len(seq) - k + 1):
        if seq[i:i + k] == sub:
            return i
    return -1


def match_government(name: str, candidates: list[dict]) -> dict:
    """The government (of the candidates: one state, one kind) whose core name the system's name carries.
    Returns ``{gov_id, how, candidates}``; ``gov_id`` None when nothing matched or two governments tie.  A county
    the Census writes in brackets (``CLINTON FIRE RELIEF ASSOCIATION [ST LOUIS]``) narrows a tie to that county."""
    hint = re.search(r"\[([^\]]+)\]", name or "")
    county = tokens(hint.group(1)) if hint else None
    toks = tokens(re.sub(r"\[[^\]]*\]", " ", name or ""))
    hits = []
    for g in candidates:
        core = g.get("_core") or gov_core(g["name"])
        if not core:
            continue
        i = _find(toks, core)
        if i >= 0:
            after = toks[i + len(core):i + len(core) + 1]
            before = toks[max(0, i - 1):i]
            kinded = bool(set(after + before) & KIND_WORDS)
            if not kinded and set(after) & OTHER_BODY:
                continue                         # 'WASHINGTON SUBURBAN SANITARY COMMISSION': another body
            hits.append((len(core), -i, g))
    if not hits:
        return {"gov_id": None, "how": "no government of this type carries a name the system's name holds",
                "candidates": 0}
    hits.sort(key=lambda x: (x[0], x[1]), reverse=True)
    best = [h for h in hits if (h[0], h[1]) == (hits[0][0], hits[0][1])]
    if len(best) > 1 and county:
        narrowed = [h for h in best if tokens(h[2].get("county_name") or "") == county]
        best = narrowed or best
    if len(best) > 1:
        return {"gov_id": None, "how": f"ambiguous: {len(best)} governments of this type share the name "
                                       f"{' '.join(hits[0][2].get('_core') or gov_core(hits[0][2]['name']))!r}",
                "candidates": len(best), "tied": [b[2]["gov_id"] for b in best][:6]}
    g = best[0][2]
    return {"gov_id": g["gov_id"], "how": f"name: the {g['kind']} core name "
                                          f"{' '.join(g.get('_core') or gov_core(g['name']))!r} in the system's name",
            "candidates": len(hits), "gov_name": g["name"]}


# --------------------------------------------------------------------------------------------- membership
def membership(unit: dict) -> list[dict]:
    """The person types a system can cover, each with how it was read: the name's words first; for a state system
    whose name says nothing, the Census's counts of state (RJ11) and local (RJ12) active members."""
    name = unit["census_name"].upper()
    out: dict[str, str] = {}
    for kind, pat in MEMBERSHIP_WORDS:
        if re.search(pat, name):
            out[kind] = "name"
    if re.search(r"STATE POLICE|HIGHWAY PATROL|STATE PATROL|TROOPER|SPORS|VALORS|LAW OFFICERS", name):
        out.setdefault("state_employee", "name")          # a state police or state law officers' system
    items = unit.get("items") or {}
    if unit["type"] == "0":
        if not out:
            if (items.get("RJ11") or 0) > 0:
                out["state_employee"] = "Census: state active members (RJ11)"
            if (items.get("RJ12") or 0) > 0:
                out["local_employee"] = "Census: local active members (RJ12)"
        elif (items.get("RJ12") or 0) > 0 and not (set(out) & set(LOCAL_TYPES)):
            out["local_employee"] = "Census: local active members (RJ12)"
        if not out:
            out["state_employee"] = "state-administered; no membership words in the name"
    else:
        # a local system's "COUNTY" or "CITY" is its government's name, not a membership signal
        out.pop("local_employee", None)
        out.pop("state_employee", None)
        if not (set(out) & {"teacher", "public_safety", "judge", "legislator"}):
            out["local_employee"] = "locally administered"
    return [{"type": k, "how": v} for k, v in out.items()]


def tiers(census_name: str) -> list[str]:
    return list(dict.fromkeys(m.group(1).title() for m in TIER.finditer(census_name.upper())))


def covers_local(unit: dict, members: list[dict]) -> bool:
    """A state system open to local governments' employees: the Census counts local active members in it, or its
    name says it is for municipal, county, local, school or political-subdivision employees (a police or fire word
    alone does not: a state police system is for state employees)."""
    if unit["type"] != "0":
        return False
    if (unit.get("items") or {}).get("RJ12", 0) > 0 or unit.get("local_members_years"):
        return True
    return any(m["type"] in ("teacher", "local_employee") and m["how"] == "name" for m in members)


# ------------------------------------------------------------------------------------------------- build
def system_id(pid6: str) -> str:
    return f"census-pid6:{pid6}"


def curated_local(states: list[str]) -> dict[str, dict]:
    """Census unit id -> ``{covers_local, how}`` from the curated statewide-systems fixtures
    (``fixtures/benefits/systems/<st>.json``): a system the statute opens to local employers (its
    ``covers_local_source`` matched by lexflow's software), or one a curated reading says is not open to them."""
    from . import ground as G
    from . import programs as PR
    out: dict[str, dict] = {}
    for st in states:
        for e in PR.system_entries(st):
            if "covers_local" not in e:
                continue
            src = e.get("covers_local_source")
            if e["covers_local"] and not G.matched(src):
                continue                      # an opening to local employers counts only with its statute matched
            how = (f"statute ({src.get('citation') or src.get('ref')})" if G.matched(src) else "a curated reading")
            for u in e.get("census_units") or []:
                out[u] = {"covers_local": bool(e["covers_local"]), "how": how}
    return out


def build(con, units: dict[str, dict] | None = None, log=print, use_curated: bool = True) -> dict:
    """The rows of ``pension_systems`` and ``pension_coverage`` (not written)."""
    from ..municipal import states as S
    units = units if units is not None else merged()
    govs: dict[tuple[str, str], list[dict]] = defaultdict(list)
    all_govs: dict[str, list[dict]] = defaultdict(list)
    for g in db.rows(con, "SELECT gov_id, state, name, kind, county_name FROM governments"):
        g["_core"] = gov_core(g["name"])
        govs[(g["state"], g["kind"])].append(g)
        all_govs[g["state"]].append(g)
    systems, coverage, stats = [], [], defaultdict(int)
    joins = []
    ts = db.now()
    years = sorted({y for u in units.values() for y in u["years"]})
    for pid, u in sorted(units.items()):
        st = u["state"]
        if st not in S.NAME:
            stats["unknown_state"] += 1
            continue
        members = membership(u)
        level = "state" if u["type"] == "0" else "local"
        admin = {"gov_id": None, "how": None}
        if u["type"] in KIND_OF_TYPE:
            admin = match_government(u["census_name"], govs[(st, KIND_OF_TYPE[u["type"]])])
            stats["local_joined" if admin["gov_id"] else
                  ("local_ambiguous" if admin.get("candidates", 0) > 1 else "local_unjoined")] += 1
            joins.append({"pid6": pid, "state": st, "name": u["census_name"], **{k: v for k, v in admin.items()
                                                                                 if k != "tied"}})
        elif u["type"] in ("4", "5"):
            admin = {"gov_id": None, "how": f"administered by a {GOV_TYPE[u['type']]}; not in the governments table"}
            stats["special_or_school"] += 1
        else:
            admin = {"gov_id": None, "how": "administered by the state"}
            stats["state_systems"] += 1
        items = u.get("items") or {}
        row = {"id": system_id(pid), "pid6": pid, "name": display_name(u["census_name"]),
               "census_name": u["census_name"], "state": st, "level": level, "admin_type": GOV_TYPE.get(u["type"]),
               "admin_gov_id": admin.get("gov_id"), "admin_how": admin.get("how"),
               "membership": json.dumps(members), "tiers": json.dumps(tiers(u["census_name"])),
               **{col: items.get(code) for code, col in ITEMS.items()},
               "covers_local": int(covers_local(u, members)), "source": SOURCE, "year": u["years"][0],
               "years": json.dumps(sorted(u["years"])), "updated_at": ts}
        systems.append(row)
        types = [m["type"] for m in members]
        if admin.get("gov_id"):
            coverage.append({"gov_id": admin["gov_id"], "system_id": row["id"], "state": st, "how": "administers",
                             "person_types": json.dumps(types), "note": admin["how"], "updated_at": ts})
    curated = curated_local(sorted({r["state"] for r in systems if r["level"] == "state"})) if use_curated else {}
    by_state_local = defaultdict(list)
    for r in systems:
        cur = curated.get(r["id"])
        if cur is not None and bool(cur["covers_local"]) != bool(r["covers_local"]):
            r["covers_local"] = int(bool(cur["covers_local"]))
            r["admin_how"] = f"{r['admin_how']}; open to local employers: {cur['how']}"
            stats["curated_overrides"] += 1
        if r["covers_local"]:
            by_state_local[r["state"]].append(r)
    for st, rows in by_state_local.items():
        for g in all_govs.get(st, []):
            for r in rows:
                types = [m["type"] for m in json.loads(r["membership"]) if m["type"] in LOCAL_TYPES]
                cur = curated.get(r["id"])
                coverage.append({"gov_id": g["gov_id"], "system_id": r["id"], "state": st, "how": "statewide",
                                 "person_types": json.dumps(types or ["local_employee"]),
                                 "note": (f"open to local employers by {cur['how']}" if cur and cur["covers_local"] else
                                          "a state system with local members (Census RJ12) or for local employees by "
                                          "name") + ": open to this government's employees; whether it participates "
                                                    "is not in the Census file", "updated_at": ts})
    own = {c["gov_id"] for c in coverage if c["how"] == "administers"}
    covered = {c["gov_id"] for c in coverage}
    out = {"systems": systems, "coverage": coverage, "joins": joins,
           "stats": {**stats, "systems": len(systems), "years": years,
                     "state_level": sum(1 for r in systems if r["level"] == "state"),
                     "local_level": sum(1 for r in systems if r["level"] == "local"),
                     "governments": sum(len(v) for v in all_govs.values()),
                     "governments_with_own_system": len(own),
                     "governments_covered": len(covered),
                     "states_with_systems": len({r["state"] for r in systems}),
                     "states_with_local_open_state_systems": len(by_state_local),
                     "coverage_rows": len(coverage)}}
    log(json.dumps(out["stats"]))
    return out


def load(con, log=print, dry_run: bool = False, units: dict[str, dict] | None = None,
         use_curated: bool = True) -> dict:
    """Build and write both tables (replacing this source's rows), in short transactions."""
    out = build(con, units, log=log, use_curated=use_curated)
    if dry_run:
        return out["stats"]
    con.execute("DELETE FROM pension_coverage")
    con.execute("DELETE FROM pension_systems WHERE source=?", (SOURCE,))
    con.commit()
    for i in range(0, len(out["systems"]), 2000):
        db.upsert(con, "pension_systems", out["systems"][i:i + 2000])
        con.commit()
    for i in range(0, len(out["coverage"]), 5000):
        db.upsert(con, "pension_coverage", out["coverage"][i:i + 5000])
        con.commit()
    db.bump(con)
    con.commit()
    return out["stats"]


def citation(years: list[int] | None = None) -> str:
    return CITATION.format(years=", ".join(str(y) for y in sorted(years or YEARS)))
