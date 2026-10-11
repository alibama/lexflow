"""Work on a few places instead of whole states, and keep checked local answers for them.

A place spec is ``<state>:<name>``, a bare state (``dc``) or a Census gov_id:

    va:charlottesville      City of Charlottesville (cities win over counties of the same name)
    md:baltimore            Baltimore City;  md:baltimore county  for the county
    dc                      the District of Columbia (the only government in the state list)

Local answers are researched per place (by Claude or a person) and stored in
``curated/places/<state>/<slug>.json``; :func:`load_local` puts them in the ``local_answers`` table
and their contacts in ``contacts``, so scoring and the dashboard use them.
"""
from __future__ import annotations

import json
import re

from .. import config, reviewers, signoff
from ..store import db
from . import states as S
from .fetch import Log
from .locus_scan import PREFIX, slug

PLACES_DIR = config.CURATED_DIR / "places"


def parse(arg: str | None) -> list[str]:
    return [p.strip() for p in (arg or "").split(",") if p.strip()]


def resolve(con, spec: str) -> list[dict]:
    spec = spec.strip()
    if re.fullmatch(r"\d{14}", spec):
        return db.rows(con, "SELECT * FROM governments WHERE gov_id=?", spec)
    state, _, name = spec.partition(":")
    st = S.normalise(state)
    govs = db.rows(con, "SELECT * FROM governments WHERE state=? ORDER BY population DESC", st)
    if not name:
        return govs[:1] if len(govs) == 1 else govs
    want = slug(name)
    county = want.endswith("_county")
    base = want.removesuffix("_county")

    def key(g):
        return slug(g["name"]) if g["kind"] == "county" else slug(PREFIX.sub("", g["name"]))
    exact = [g for g in govs if key(g) == want or (county and g["kind"] == "county" and key(g) == f"{base}_county")]
    if not exact and not county:
        cities = [g for g in govs if g["kind"] != "county" and key(g) == base]
        exact = cities or [g for g in govs if g["kind"] == "county" and key(g) == f"{base}_county"]
    if not exact:
        exact = [g for g in govs if base in key(g)][:5]
    order = {"municipality": 0, "township": 1, "county": 2}
    return sorted(exact, key=lambda g: (order.get(g["kind"], 3), -(g["population"] or 0)))[:1] if exact else []


def resolve_all(con, arg: str | None) -> list[dict]:
    out, seen = [], set()
    for spec in parse(arg):
        hits = resolve(con, spec)
        if not hits:
            raise ValueError(f"no government matches {spec!r}")
        for g in hits:
            if g["gov_id"] not in seen:
                seen.add(g["gov_id"])
                out.append(g)
    return out


def place_slug(g: dict) -> str:
    return slug(PREFIX.sub("", g["name"])) + ("_county" if g["kind"] == "county" and not
                                              g["name"].lower().endswith("county") else "")


def local_files() -> list:
    return sorted(PLACES_DIR.glob("*/*.json"))


def process_files() -> list:
    """One file per researched process: curated/places/<state>/<place>/<process>.json."""
    return sorted(PLACES_DIR.glob("*/*/*.json"))


# where a researched process quotes the state code: "Va. Code § 3.2-6524(A)", "Va. Code §§ 36-105(A), 36-114",
# "Code of Virginia § 15.2-2201", and the official publisher's section pages
CODE_CITE = {
    "va": (re.compile(r"(?:\bVa\.?\s*Code(?:\s+Ann\.)?|\bCode\s+of\s+Virginia)\s*§§?\s*((?:[\dA-Z.:()\-]+(?:,\s*|\s+and\s+|"
                      r"\s+(?:to|through)\s+|\s*&\s*)?)+)"),
           re.compile(r"law\.lis\.virginia\.gov/vacode/(?:title[\d.]+/chapter[\d.]+/section)?([\d.]+[A-Z]?-[\d.:]+)")),
    "dc": (re.compile(r"\bD\.\s?C\.\s*(?:Official\s+)?Code(?:\s+Ann\.)?\s*§§?\s*((?:[\dA-Z.:()\-]+(?:,\s*|\s+and\s+)?)+)"),
           re.compile(r"code\.dccouncil\.(?:gov|us)/us/dc/council/code/sections/([\d.:\-]+)")),
}
SECTION = re.compile(r"\d+(?:\.\d+)*[A-Z]?-\d+(?:\.\d+)*(?::\d+)?")
OFFICIAL_CODE_URL = {"va": "law.lis.virginia.gov/vacode", "dc": "code.dccouncil."}


def process_quotes(spec: dict) -> list[tuple[str, str, list[str]]]:
    """Every quote in a researched process file, with where it is and what it cites: (where, quote, cites)."""
    out = []
    for i, x in enumerate(spec.get("legal_basis") or []):
        out.append((f"legal_basis[{i}]", x.get("quote"), [x.get("citation"), x.get("url")]))
    for i, x in enumerate(spec.get("steps") or []):
        out.append((f"steps[{i}]", x.get("quote"), [x.get("source"), x.get("url")]))
    for i, x in enumerate(spec.get("fees") or []):
        out.append((f"fees[{i}]", x.get("quote"), [x.get("basis")]))
    for i, x in enumerate(spec.get("escalation") or []):
        out.append((f"escalation[{i}]", x.get("quote"), [x.get("basis")]))
    return [(w, q, [str(c) for c in cites if c]) for w, q, cites in out if isinstance(q, str) and q.strip()]


def _cited_sections(state: str, cites: list[str]) -> tuple[list[str], bool]:
    """The state code sections a quote cites, and whether it also cites something else (a web page, a city code,
    a regulation)."""
    pats = CODE_CITE.get(state)
    if not pats:
        return [], bool(cites)
    secs, other = [], False
    for c in cites:
        found = [n for m in pats[0].finditer(c) for n in SECTION.findall(m.group(1))] + pats[1].findall(c)
        secs += [n for n in found if n not in secs]
        urls = re.findall(r"https?://\S+", c)
        rest = re.sub(r"https?://\S+", "", pats[0].sub("", c))
        if any(OFFICIAL_CODE_URL[state] not in u for u in urls) or "§" in rest or \
                re.search(r"VAC(?:\d|\b)|\bRules?\b|\bCode\b|\bOrdinance\b|\bCharter\b", rest) or \
                (not found and not urls and re.search(r"[A-Za-z]{3}", rest)):
            other = True
    return secs, other


QC_VERSION = 2
_QC_MEMO: dict[tuple, dict] = {}


def state_of(spec: dict) -> str:
    """The state a process file is for, from its ``place`` ("va:staunton"); '' when it names none."""
    try:
        return S.normalise((spec.get("place") or "").partition(":")[0])
    except ValueError:
        return ""


def official_code_url(state: str, url: str) -> bool:
    """Whether ``url`` is the official publisher's page for a section of the state code, whose quotes are matched
    to Open US Law's copy of it rather than fetched."""
    return bool(state in OFFICIAL_CODE_URL and OFFICIAL_CODE_URL[state] in (url or ""))


def _unmatched_why(urls: list[str], tried: list, others: int) -> str:
    """Why lexflow's software did not match a quote that is not from the state code, in a reader's words."""
    from . import quotes as Q
    if urls:
        entry = next((e for u, e, _ in tried if u == urls[0]), None)
        got = next((ok for u, _, ok in tried if u == urls[0]), None)
        if entry is None:
            why = "the cited page has not been read by lexflow's software yet"
        elif entry.get("error"):
            why = f"the cited page could not be read ({entry['error']})"
        elif got is None:
            why = (f"{Q.describe(entry)} was checked only for the quotes this process had then, and this quote was "
                   f"not one of them")
        else:
            why = f"not found word for word in {Q.describe(entry)}"
        return why + ((", nor in the other page this process cites" if others == 1 else
                       f", nor in the {others} other pages this process cites") if others else "")
    if not others:
        return "it cites no page, and this process cites none"
    unread = sum(1 for _, e, _ in tried if e is None or e.get("error"))
    return ((f"it cites no page, and the one page this process cites does not have it word for word" if others == 1
             else f"it cites no page, and none of the {others} pages this process cites has it word for word")
            + (f" ({unread} of them could not be read)" if unread else ""))


def check_quotes(spec: dict, state: str, today: str | None = None) -> dict:
    """lexflow's software match of every quote in a researched process file.

    A quote that cites a section of the state code found in Open US Law's copy is matched to that section with the
    state models' check (validate.quote_in).  Any other quote is matched to the page it cites, as lexflow's quote
    fetch read it (lexflow/municipal/quotes.py: live, or an Internet Archive copy where the site refuses automated
    readers), and failing that to the other pages the file cites.  A quote that cites only code sections and is
    not in them is not matched.  Nothing is fetched here: a page the fetch has not read does not match.

    Returns the counts (``quotes``, ``matched``, ``by_code``, ``by_page``, ``by_archive``), every quote that did not
    match with why (``unmatched``), how each one matched (``items``), each page the file cites with when it was
    read and whether live or from the Internet Archive (``pages``), and the dates the matches were made on
    (``matched_on``: the check's date for a code quote, the day the page was read for the others).  ``hash`` is the
    file's, so a page uses the result only for the file it was made from."""
    from ..validate import quote_in
    from . import quotes as Q
    from . import statutes
    day = (today or db.now())[:10]
    cache = Q.cache_dir()
    try:
        stamp = cache.stat().st_mtime
    except OSError:
        stamp = None
    memo = (signoff.text_hash(spec), state, day, str(cache), stamp, id(statutes.load), id(statutes.section_texts))
    if memo in _QC_MEMO:
        return json.loads(json.dumps(_QC_MEMO[memo]))
    texts: dict[str, str | None] = {}

    def text_of(sec):
        if sec not in texts:
            try:
                texts[sec] = statutes.section_texts(state, [sec])[0].text
            except (KeyError, FileNotFoundError, ValueError, OSError, ImportError):
                texts[sec] = None
        return texts[sec]
    file_pages = list(dict.fromkeys(Q.key(u) for u in Q.file_urls(spec) if not official_code_url(state, u)))
    items, unmatched, pages = {}, [], {}
    n = by_code = by_live = by_archive = 0
    for where, quote, cites in process_quotes(spec):
        n += 1
        secs, also = _cited_sections(state, cites)
        found = [(sec, t) for sec in secs if (t := text_of(sec))]
        hit = next((sec for sec, t in found if quote_in(quote, t)), None)
        if hit:
            by_code += 1
            items[where] = {"by": "code", "section": hit, "on": day}
            continue
        urls = list(dict.fromkeys(Q.key(u) for u in Q.cited_urls(cites) if not official_code_url(state, u)))
        if secs and not also and not urls:
            why = (f"not found word for word in Open US Law's copy of § {found[0][0]}" if found else
                   f"§ {secs[0]} is not in Open US Law's copy of the {statutes.code_name(state)}")
            items[where] = {"by": None, "why": why, "section": secs[0]}
            unmatched.append({"where": where, "why": why})
            continue
        tried, got_url, entry = [], None, None
        for u in urls + [p for p in file_pages if p not in urls]:
            e = Q.cached(u)
            ok = Q.has(e, quote)
            tried.append((u, e, ok))
            if ok:
                got_url, entry = u, e
                break
        if got_url:
            via = "archive" if entry.get("via") == "archive" else "live"
            by_archive += via == "archive"
            by_live += via == "live"
            items[where] = {"by": via, "url": got_url, "cited": got_url in urls, "on": entry.get("fetched"),
                            "capture": entry.get("capture")}
            continue
        others = len([p for p in file_pages if p not in urls])
        why = _unmatched_why(urls, tried, others)
        items[where] = {"by": None, "why": why, "url": urls[0] if urls else None}
        unmatched.append({"where": where, "why": why, "url": urls[0] if urls else None})
    for u in list(dict.fromkeys([i["url"] for i in items.values() if i.get("url")] + file_pages)):
        e = Q.cached(u)
        pages[u] = ({"via": e.get("via"), "capture": e.get("capture"), "fetched": e.get("fetched"),
                     "error": e.get("error")} if e else {"via": None, "fetched": None, "error": "not read yet"})
    on = sorted({i["on"] for i in items.values() if i.get("by") and i.get("on")})
    out = {"version": QC_VERSION, "hash": signoff.text_hash(spec), "date": day, "code": statutes.code_name(state),
           "quotes": n, "matched": by_code + by_live + by_archive, "by_code": by_code, "by_page": by_live + by_archive,
           "by_archive": by_archive, "unmatched": unmatched, "items": items, "pages": pages, "matched_on": on}
    if len(_QC_MEMO) > 512:
        _QC_MEMO.clear()
    _QC_MEMO[memo] = out
    return json.loads(json.dumps(out))


def _ai_check(spec: dict) -> tuple[str | None, list[str]]:
    """The AI verifier's check date (``checks.date``) and the dates the file's sources were retrieved."""
    checks = spec.get("checks") if isinstance(spec.get("checks"), dict) else {}
    vdate = signoff.iso_date(checks.get("date") or checks.get("checked"))
    retrieved = sorted({d for d in (signoff.iso_date(x.get("retrieved")) for x in spec.get("sources") or []
                                    if isinstance(x, dict)) if d})
    return vdate, retrieved


def check_date_problem(spec: dict, today: str | None = None) -> str | None:
    """Why the AI verifier's check of a file that says it is verified does not cover its sources as cited (None
    when it does): it is not dated, it is dated in the future, or it is dated before a source was retrieved."""
    if not spec.get("verified"):
        return None
    vdate, retrieved = _ai_check(spec)
    day = (today or db.now())[:10]
    if not vdate:
        return "its AI check is not dated"
    if vdate > day:
        return f"its AI check is dated {vdate}, in the future"
    later = [d for d in retrieved if d > vdate]
    if later:
        return f"its AI check is dated {vdate}, before some of its sources were retrieved (the latest on {later[-1]})"
    return None


def verify_problem(spec: dict, qc: dict | None = None, state: str | None = None) -> str | None:
    """Why a researched process file cannot load as verified (None when it can).

    It loads as verified when the AI verifier passed it (``verified``), lexflow's software matched every one of its
    quotes (``check_quotes``), and either the AI check is dated on or after every source's retrieval (and not in
    the future), or the software matched every quote on or after those dates."""
    if not spec.get("verified"):
        return "the AI verifier did not pass it"
    st = state or state_of(spec)
    if not qc or qc.get("version") != QC_VERSION or qc.get("hash") != signoff.text_hash(spec):
        qc = check_quotes(spec, st)
    miss = qc.get("unmatched") or []
    if miss:
        return (f"{len(miss)} of its {qc.get('quotes')} quotes {'was' if len(miss) == 1 else 'were'} not matched by "
                f"lexflow's software")
    late = check_date_problem(spec)
    if late:
        _, retrieved = _ai_check(spec)
        on = qc.get("matched_on") or []
        if not qc.get("quotes") or not on or (retrieved and on[0] < retrieved[-1]):
            return f"{late}, and lexflow's software did not match every quote on or after that"
    return None


def is_verified(spec: dict, qc: dict | None = None, state: str | None = None) -> bool:
    """Whether a researched process file counts as verified (``verify_problem``).  ``qc`` is a stored
    ``check_quotes`` result; one for another version of the file is made again."""
    return bool(spec.get("verified")) and verify_problem(spec, qc, state) is None


def load_processes(con, govs: list[dict] | None = None, log: Log = print) -> dict:
    """Load the per-process files into place_processes, with lexflow's software match of their quotes
    (``check_quotes``, from the quote fetch's cache: nothing is fetched here), and their office contacts into
    contacts.  A file that says it is verified loads as verified only by the rule in ``verify_problem``; else it is
    loaded as not verified, with a log line that says why."""
    wanted = {g["gov_id"] for g in govs} if govs else None
    loaded, verified, contacts = 0, 0, 0
    by_place: dict[str, int] = {}
    for path in process_files():
        try:
            spec = json.loads(path.read_text(encoding="utf-8"))
        except ValueError as e:
            log(f"{path.parent.name}/{path.name}: not valid JSON ({e}); skipped")
            continue
        g = next(iter(db.rows(con, "SELECT * FROM governments WHERE gov_id=?", spec.get("gov_id") or "")), None)
        if g is None:
            hits = resolve(con, spec.get("place") or "")
            g = hits[0] if hits else None
        pid = re.sub(r"[^a-z0-9_]+", "_", (spec.get("process") or path.stem).lower()).strip("_")
        if g is None or not pid:
            log(f"{path.parent.name}/{path.name}: no government or process id; skipped")
            continue
        if wanted is not None and g["gov_id"] not in wanted:
            continue
        ts = db.now()
        qc = check_quotes(spec, g["state"], ts)
        why = verify_problem(spec, qc, g["state"]) if spec.get("verified") else None
        ok = bool(spec.get("verified")) and why is None
        if why:
            log(f"{path.parent.name}/{path.name}: {why}, so it is loaded as not verified")
        db.upsert(con, "place_processes", [{
            "gov_id": g["gov_id"], "state": g["state"], "process": pid, "title": spec.get("title"),
            "question": spec.get("question"), "category": spec.get("category"), "kind": spec.get("kind"),
            "office": spec.get("office"), "verified": int(ok), "spec": spec, "quote_check": qc, "updated_at": ts}])
        rows = [{"gov_id": g["gov_id"], "state": g["state"], "question": pid,
                 "kind": {"portal": "page", "address": "office"}.get(c.get("kind"), c.get("kind") or "page"),
                 "value": c.get("value") or c.get("url"), "label": c.get("label"), "source": "local-research",
                 "updated_at": ts} for c in spec.get("contacts") or []]
        db.upsert(con, "contacts", [r for r in rows if r["value"]])
        loaded += 1
        verified += int(ok)
        contacts += len(rows)
        by_place[g["name"]] = by_place.get(g["name"], 0) + 1
    for name, n in sorted(by_place.items()):
        log(f"{name}: {n} researched processes")
    db.bump(con)
    con.commit()
    return {"processes": loaded, "verified": verified, "process_contacts": contacts}


# words that describe how a file was drafted rather than the place: the files are worded without them
# (tests/test_place_processes.py), and a page logs any that is left (``drafting_left``)
DRAFTING_LEFT = re.compile(
    r"\bverifier\b|\bmodell?er\b|\bClaude\b|\bbrowser pane\b|\blexflow(?:'s)? (?:full-text |'va' )?index\b|"
    r"\bindex rows? \d|\bresearch (?:client|User-Agent)\b|\blexflow-research\b|\bthe research\b|\bthis run\b|"
    r"\blexflow runs?\b|\bdiscovery (?:file|run)\b|\bthe block was not\b|\bwas not (?:bypassed|circumvented)\b|"
    r"\bdid not fetch\b|\bdeclared User-Agent\b|\bresearch rules\b|\bduring (?:this )?(?:research|verification)\b",
    re.I)


def drafting_left(where: str, texts, log: Log | None = None) -> list[str]:
    """The last check on a researched process's caveats and source titles, which pages print as the file has them:
    the drafting words left in them (``DRAFTING_LEFT``), each logged once (the file needs rewording)."""
    import logging
    found = []
    for t in texts or []:
        m = DRAFTING_LEFT.search(str(t or ""))
        if m:
            found.append(m.group(0))
            (log or logging.getLogger("lexflow.places").warning)(
                f"{where}: a caveat or source title describes the drafting ({m.group(0)!r}); reword the file")
    return found


def local_row(ans: dict, spec: dict) -> dict:
    """The text of one answer of a place file, as local_answers stores it (what a reviewer of that answer signs)."""
    return {"summary": ans.get("summary"), "steps": ans.get("steps", []), "contacts": ans.get("contacts", []),
            "local_law": ans.get("local_law", []), "fees": ans.get("fees"), "caveats": ans.get("caveats", []),
            "sources": spec.get("sources", [])}


def local_signoff(ans: dict, spec: dict, row: dict, roster: dict, log: Log = print) -> dict | None:
    """The review to store with a local answer: the answer's own sign-off (text_hash of that answer) or the
    file's (text_hash of the whole file), by someone on the operator's reviewer list (``roster``), dated on or
    after the research, bound to the stored answer; else None."""
    text = signoff.row_text(row, signoff.LOCAL_TEXT)
    researched = spec.get("researched")
    who = (signoff.bound(ans.get("reviewed_by"), text, roster, not_before=researched)
           or signoff.bound(spec.get("reviewed_by"), signoff.strip_signoffs(spec), roster, not_before=researched))
    if not who and (ans.get("reviewed_by") or spec.get("reviewed_by")):
        log("reviewed_by is not a sign-off of this text (no reviewer id from the operator's list, a reviewer not on "
            "it, a typed name, no attestation, dated before the research, or a text_hash that is not this text's: "
            "`lexflow reviewer list`, `lexflow review-hash`); the page will say it is not yet reviewed")
    return signoff.bind(who, text) if who else None


def load_local(con, govs: list[dict] | None = None, log: Log = print) -> dict:
    """Load curated/places/*/*.json into local_answers and contacts (all files, or those for ``govs``)."""
    wanted = {g["gov_id"] for g in govs} if govs else None
    loaded, contacts = 0, 0
    roster = reviewers.roster(con)
    for path in local_files():
        spec = json.loads(path.read_text(encoding="utf-8"))
        hits = resolve(con, spec["place"])
        if not hits:
            log(f"{path.name}: no government matches {spec['place']!r}; skipped")
            continue
        g = hits[0]
        if wanted is not None and g["gov_id"] not in wanted:
            continue
        ts = db.now()
        for qid, ans in spec.get("answers", {}).items():
            row = {**local_row(ans, spec), "gov_id": g["gov_id"], "state": g["state"], "question": qid,
                   "built_by": spec.get("researched_by", "claude"), "verified": int(bool(spec.get("verified"))),
                   "researched": spec.get("researched"), "updated_at": ts}
            # a named person's sign-off for this answer, or for the whole file, checked against the text it was
            # given and then bound to the stored answer (lexflow/signoff.py)
            row["reviewed_by"] = local_signoff(ans, spec, row, roster,
                                               log=lambda m, p=path: log(f"{p.name}: {qid}: {m}"))
            db.upsert(con, "local_answers", [row])
            rows = []
            for c in ans.get("contacts", []):
                kind = {"portal": "page", "office": "office"}.get(c.get("kind"), c.get("kind") or "page")
                rows.append({"gov_id": g["gov_id"], "state": g["state"], "question": qid, "kind": kind,
                             "value": c.get("value") or c.get("url"), "label": c.get("label"),
                             "source": "local-research", "updated_at": ts})
            db.upsert(con, "contacts", [r for r in rows if r["value"]])
            contacts += len(rows)
            loaded += 1
        log(f"{g['name']}: {len(spec.get('answers', {}))} local answers from {path.parent.name}/{path.name}")
    db.bump(con)
    con.commit()
    return {"answers": loaded, "contacts": contacts, **load_processes(con, govs, log)}
