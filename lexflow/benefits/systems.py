"""The statewide retirement systems: each state's state-administered systems (from ``pension_systems``), the section
of the state's code that creates each one (searched in the statute index), the body that administers it (with its
Wikidata id where an exact match exists) and its official website.

``find(state)`` groups a state's Census units into systems (``VIRGINIA RETIREMENT SYSTEM (STATE)``, ``(TEACHER)`` and
``(POLITICAL SUBDIVISIONS)`` are one system, the Virginia Retirement System, with three plans), searches the state's
index for each system's name (with and without the state's name), and keeps the sentence of the best section that
establishes, creates or continues the system (``There is a State Retirement and Pension System of Maryland``, "the
General Assembly hereby establishes the Virginia Retirement System").  The quote is cut from the index text itself,
so it matches by construction; the choice of section is lexflow's and is marked ``found_by: search`` until a person
reviews it (``reviewed``).  ``wikidata(name, state)`` asks Wikidata read-only (``wbsearchentities`` then
``wbgetentities``, the lexflow-research User-Agent, one request every two seconds) and keeps a match only when the
item's label or an alias is the system's name and the item is about the state (its description or a claim names
the state, or its official website is a state domain); its official website (P856) comes with it.

``build()`` gives the automatic first pass for a set of states (``python -m lexflow.benefits.research units <st>``
prints it); the curated per-state files ``fixtures/benefits/systems/<st>.json`` are what lexflow uses, and
``wikidata_all`` adds exact Wikidata matches for their systems (``python -m lexflow.benefits wikidata --write``).
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

from .. import config
from ..store import db
from . import census as C

PATH = config.ROOT / "fixtures" / "benefits" / "state_systems.json"
ESTABLISH = re.compile(
    r"\b(?:(?:is|are)\s+(?:hereby\s+)?(?:established|created|continued|constituted|organized)|hereby\s+(?:establishes|"
    r"creates|continues)|there\s+(?:is|are|shall\s+be)\s+(?:hereby\s+)?(?:created|established|a|an)\b|shall\s+be\s+"
    r"(?:known|continued|designated)\s+as|is\s+the\s+successor)", re.I)
HEADING_HINT = re.compile(r"establish|creat|continu|name|title|short title|organization|purpose", re.I)
QUALIFIERS = re.compile(
    r"\b(?:fund\s+[a-c]|fund\s+i{1,3}|tier\s+\w+|plan\s+[a-z0-9]+|db|dc|db plan|defined benefit(?: program| plan|"
    r" component)?|division pension|pension plan|program|account|pre-\d{4}|\d{4} account|\d{4}|closed|"
    r"hybrid db component|cost-sharing|special fund|new hire pension plans)\b", re.I)
SENT = re.compile(r"(?<=[.;:])\s+(?=[\"“(A-Z0-9])|\n+")


def _norm_tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", (text or "").lower().replace("'", "").replace("’", ""))


def core_name(display: str, state: str) -> str:
    """'Virginia Retirement System (Political Subdivisions)' -> 'Virginia Retirement System'; 'CalPERS Public
    Employees' Retirement Fund A' -> 'Public Employees Retirement Fund'."""
    n = re.sub(r"\([^)]*\)", " ", display or "")
    n = re.sub(r"\b(CalPERS|CalSTRS|PERSI|FRS|PERA|FPPA)\b", " ", n)
    n = re.sub(r"\s+-\s+.*$", " ", n)
    n = QUALIFIERS.sub(" ", n)
    return re.sub(r"\s+", " ", n).strip(" -,")


def phrases(display: str, state: str) -> list[str]:
    """The names to search for, most specific first: with the state's name, without it, in the statute's usual
    orders ('Teachers Retirement System of Georgia', 'Employees' Retirement System of the State of Maryland'), and
    a 'Retirement and Pension Systems' name split into its two systems."""
    from ..municipal import states as S
    name = S.NAME.get(state, "")
    core = core_name(display, state)
    core = re.sub(rf"(?:of\s+)?{state.upper()}$", f"of {name}", core).strip()
    core = re.sub(r"^Nys", "New York State", core)
    bases = [core]
    m = re.match(r"(.*)Retirement and Pension Systems?$", core)
    if m:
        bases = [f"{m.group(1)}Retirement System", f"{m.group(1)}Pension System"]
    out = []
    for b in bases:
        if re.search(r"Retirement$", b):
            b = b + " System"
        bare = re.sub(rf"^{re.escape(name)}\s+|\s+of\s+(?:the\s+State\s+of\s+)?{re.escape(name)}$", "", b,
                      flags=re.I).strip()
        out += [b, bare, f"{bare} of the State of {name}", f"{bare} of {name}"]
    return [p for p in dict.fromkeys(out) if len(_norm_tokens(p)) >= 2]


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in SENT.split(text or "") if s and s.strip()]


def _contains(sentence: str, phrase: str) -> bool:
    s, p = _norm_tokens(sentence), _norm_tokens(phrase)
    return any(s[i:i + len(p)] == p for i in range(len(s) - len(p) + 1)) if p else False


BEFORE = {"there", "establishes", "creates", "continues", "establish", "create", "continue"}
AFTER_VERB = {"established", "created", "continued", "constituted", "organized", "known", "designated"}


def establishes(sentence: str, phrase: str) -> bool:
    """The sentence establishes, creates or continues the system itself (not a fund, a DROP or a plan of it): the
    name comes right after 'There is a', 'hereby establishes the' ..., or right before 'is (hereby) established'."""
    s, p = _norm_tokens(sentence), _norm_tokens(phrase)
    for i in range(len(s) - len(p) + 1):
        if s[i:i + len(p)] != p:
            continue
        pre = s[max(0, i - 4):i]
        post = s[i + len(p):i + len(p) + 8]
        if set(pre) & BEFORE and (not pre or pre[-1] in ("a", "an", "the", "is", "are") or pre[-1] in BEFORE):
            return True
        if post[:1] and post[0] in ("is", "are", "shall") and set(post[:5]) & AFTER_VERB:
            return True
        if post[:1] and post[0] in ("is", "are") and post[1:3] == ["hereby", "established"]:
            return True
    return False


def _window(sentence: str, phrase: str, words: int = 55) -> str:
    """At most ``words`` words of the sentence around the phrase and the establishing words (contiguous, verbatim)."""
    toks = sentence.split()
    if len(toks) <= words:
        return sentence
    low = [re.sub(r"[^a-z0-9]", "", t.lower()) for t in toks]
    first = _norm_tokens(phrase)[0] if _norm_tokens(phrase) else ""
    i = next((k for k, t in enumerate(low) if t == first), 0)
    a = max(0, i - 10)
    return " ".join(toks[a:a + words])


def best_section(state: str, display: str) -> dict | None:
    """The section that most likely creates the system, and its establishing sentence (cut from the index text)."""
    from ..ask import index as I
    if not I.ready(state):
        return None
    cands = []
    for rank, ph in enumerate(phrases(display, state)):
        rows = I.search(state, I.phrase(ph) or "", limit=40)
        for r in rows:
            full = I.by_id(state, r["id"], with_text=True) or {}
            text = full.get("text") or ""
            for s in _sentences(text):
                if not _contains(s, ph):
                    continue
                est = bool(ESTABLISH.search(s)) and establishes(s, ph)
                means = bool(re.search(r"\bmeans\b", s)) and s.find(ph.split()[0]) < 40
                if not (est or means):
                    continue
                score = (3 if est else 1) + (2 if HEADING_HINT.search(r.get("title") or "") else 0) \
                    + (1 if _contains(r.get("title") or "", ph) else 0) - rank * 0.5 - (r["id"] / 1e7)
                cands.append((score, r, s, ph, est))
        if any(c[4] for c in cands):
            break
    if not cands:
        return None
    score, r, s, ph, est = max(cands, key=lambda c: c[0])
    return {"kind": "statute", "state": state, "ref": r["ref"], "citation": r["citation"], "url": r["url"],
            "quote": _window(s, ph), "found_by": "search", "searched": ph,
            "establishes": est, "heading": r.get("title")}


# --------------------------------------------------------------------------------------------- Wikidata
def _same(a: str, b: str) -> bool:
    return _norm_tokens(a) == _norm_tokens(b)


def wikidata(name: str, state: str) -> dict | None:
    """An exact Wikidata match for a system's name in a state, with its official website (P856), or None."""
    from ..municipal import states as S
    from ..publish import vocab_links as VL
    sname = S.NAME.get(state, "")
    hits = VL._get({"action": "wbsearchentities", "search": name, "language": "en", "uselang": "en", "type": "item",
                    "limit": 8}).get("search", [])
    ids = [h["id"] for h in hits if h.get("id")]
    if not ids:
        return None
    ents = VL._get({"action": "wbgetentities", "ids": "|".join(ids), "languages": "en",
                    "props": "labels|aliases|descriptions|claims"}).get("entities", {})
    for qid in ids:
        e = ents.get(qid) or {}
        label = ((e.get("labels") or {}).get("en") or {}).get("value") or ""
        aliases = [a["value"] for a in (e.get("aliases") or {}).get("en", [])]
        if not any(_same(x, name) for x in [label] + aliases):
            continue
        desc = ((e.get("descriptions") or {}).get("en") or {}).get("value") or ""
        sites = [((c.get("mainsnak") or {}).get("datavalue") or {}).get("value") for c in
                 (e.get("claims") or {}).get("P856", [])]
        sites = [s for s in sites if isinstance(s, str)]
        about_state = (sname.lower() in (desc + " " + label).lower()) or any(
            re.search(rf"\.{state}\.(gov|us)\b|{state}\.gov\b", s or "") for s in sites)
        if not about_state:
            continue
        return {"qid": qid, "label": label, "description": desc, "website": sites[0] if sites else None,
                "match": "exact", "checked": db.now()[:10]}
    return None


# --------------------------------------------------------------------------------------------- build
def state_units(con, states: list[str] | None = None) -> dict[str, list[dict]]:
    sql = "SELECT * FROM pension_systems WHERE level='state'" + (
        f" AND state IN ({','.join('?' * len(states))})" if states else "") + " ORDER BY state, name"
    out: dict[str, list[dict]] = defaultdict(list)
    for r in db.rows(con, sql, *(states or [])):
        out[r["state"]].append(r)
    return out


def group(units: list[dict], state: str) -> list[dict]:
    """Census units -> systems, by their core name."""
    by: dict[str, dict] = {}
    for u in units:
        key = " ".join(_norm_tokens(core_name(u["name"], state)))
        g = by.setdefault(key, {"name": core_name(u["name"], state), "units": []})
        g["units"].append({"id": u["id"], "census_name": u["census_name"], "plan": u["name"],
                           "membership": [m["type"] for m in json.loads(u["membership"] or "[]")],
                           "covers_local": bool(u["covers_local"]), "members_active": u["members_active"],
                           "beneficiaries": u["beneficiaries"]})
    return list(by.values())


def load() -> dict:
    try:
        return json.loads(PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"_about": "", "states": {}}


def build(con, states: list[str] | None = None, with_wikidata: bool = False, log=print) -> dict:
    """The state_systems fixture for these states (curated states are kept as they are)."""
    from ..municipal import states as S
    doc = load()
    doc["_about"] = ("Statewide retirement systems (lexflow.benefits.systems): Census units grouped into systems, "
                     "each with the section that creates it as found by search in the statute index (found_by: "
                     "search; not reviewed unless reviewed: true), the administering body and its Wikidata match "
                     "(exact only). Curated entries (curated: true) are a person's or Claude's reading, every "
                     "quote matched by lexflow's software.")
    doc["as_of"] = db.now()[:10]
    out = doc.setdefault("states", {})
    for st, units in state_units(con, states).items():
        have = out.get(st) or {}
        if have.get("curated"):
            log(f"{st}: curated, kept")
            continue
        systems = []
        for g in group(units, st):
            src = best_section(st, g["units"][0]["plan"]) if True else None
            body = {"name": g["name"], "wikidata": None, "website": None}
            old = next((s for s in have.get("systems") or [] if s.get("name") == g["name"]), None)
            if old and (old.get("body") or {}).get("wikidata"):
                body = old["body"]
            elif with_wikidata:
                try:
                    wd = wikidata(g["name"], st)
                except Exception as e:  # noqa: BLE001 - Wikidata down: no match recorded
                    wd, body["wikidata_error"] = None, f"{type(e).__name__}"
                if wd:
                    body.update(wikidata=wd["qid"], wikidata_label=wd["label"], website=wd["website"])
            systems.append({"name": g["name"], "units": g["units"], "statute": src, "body": body,
                            "membership": sorted({m for u in g["units"] for m in u["membership"]}),
                            "covers_local": any(u["covers_local"] for u in g["units"]), "reviewed": False})
        out[st] = {"state": st, "name": S.NAME.get(st), "curated": False, "systems": systems}
        found = sum(1 for s in systems if s["statute"])
        log(f"{st}: {len(systems)} systems, {found} with a section found"
            + (f", {sum(1 for s in systems if s['body'].get('wikidata'))} on Wikidata" if with_wikidata else ""))
    doc["states"] = dict(sorted(out.items()))
    return doc


def write(doc: dict, path: Path | None = None) -> None:
    (path or PATH).write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------------- Wikidata for the curated bodies
WIKIDATA_PATH = config.ROOT / "fixtures" / "benefits" / "wikidata_bodies.json"


def wikidata_all(states: list[str] | None = None, write: bool = False, log=print) -> dict:
    """Exact Wikidata matches for every curated system (``fixtures/benefits/systems/<st>.json``): the system's name,
    then its body's name, then the name with the state's ("Teachers' Retirement System of Georgia").  Read-only,
    one request every two seconds.  Writes ``fixtures/benefits/wikidata_bodies.json`` (``{state: {system name:
    {qid, label, description, website, match, checked, searched}}}``) with ``write``; entries already there are kept
    (a QID is asked once)."""
    from ..municipal import states as S
    from . import programs as PR
    try:
        have = json.loads(WIKIDATA_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        have = {}
    have.pop("_about", None)
    stats = {"systems": 0, "matched": 0, "asked": 0}
    for st in states or PR.states_with("systems"):
        doc = json.loads((PR.SYSTEMS_DIR / f"{st}.json").read_text(encoding="utf-8"))
        got = have.setdefault(st, {})
        for e in doc.get("systems") or []:
            name = e.get("name")
            stats["systems"] += 1
            if name in got:
                stats["matched"] += bool(got[name].get("qid"))
                continue
            tries = [name, (e.get("body") or {}).get("name"), f"{name} of {S.NAME.get(st, '')}"]
            found = None
            for t in [x for x in dict.fromkeys(tries) if x]:
                stats["asked"] += 1
                try:
                    found = wikidata(t, st)
                except Exception as ex:  # noqa: BLE001 - Wikidata down: try again another day
                    log(f"{st}: {t}: {type(ex).__name__}")
                    found = None
                    break
                if found:
                    found["searched"] = t
                    break
            got[name] = found or {"qid": None, "checked": db.now()[:10], "searched": tries[0]}
            stats["matched"] += bool(found)
            log(f"{st}: {name}: {found['qid'] if found else 'no exact match'}")
        if write:
            WIKIDATA_PATH.write_text(json.dumps({"_about": "Exact Wikidata matches for the statewide retirement "
                                                 "systems (lexflow.benefits.systems.wikidata_all): the item's label or "
                                                 "an alias is the name searched and the item is about the state. "
                                                 "Read-only; nothing was written to Wikidata.", **dict(sorted(have.items()))},
                                                indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return stats


def wikidata_of(state: str, name: str) -> dict | None:
    try:
        have = json.loads(WIKIDATA_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    hit = (have.get(state) or {}).get(name)
    return hit if hit and hit.get("qid") else None
