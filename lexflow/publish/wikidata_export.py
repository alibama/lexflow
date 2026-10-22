"""lexflow's laws against Wikidata, read-only, and QuickStatements that only add what existing items lack.

Nothing here writes to Wikidata or to the Lexipedia Wikibase.  ``reconcile`` reads query.wikidata.org and the
Wikidata API (lexflow's research user agent, at most one request a second, backing off on 429 and 503; answers are
cached under ``data/cache/wikidata/``) and records what it finds in the local table ``wikidata_laws``; ``qs`` writes
QuickStatements V1 batches to ``out/wikidata/jpn-*.qs`` for the operator to review and run under his own account,
after a Wikidata bot request (docs/design/wikidata-laws.md §6 has the drafts).

**Japan.**  Each law of the index (8,981 in force) and of the API v2 law list (9,567 with the repealed and the not
yet in force) is looked for on Wikidata four ways, in this order of trust:

1. ``P8610`` (e-GOV law ID) equal to the law_id;
2. ``P8550`` (law identifier) equal to the law number, compared by ``japan.law_num_key`` (平成5年法律第88号, the
   spelling Wikidata uses, against e-Gov's 平成五年法律第八十八号), on an item whose country is Japan;
3. the jawiki article: an item whose Japanese Wikipedia sitelink is the law's title (or ``<title> (日本)``), when the
   item is an instance of a legal act, statute, law or a subclass of one;
4. the Japanese label equal to the title, on an item of such a class whose country is Japan.

Matches 1-3 are ``confident`` when exactly one item matches and the item carries no other law's e-GOV law ID or law
identifier; 4 is reported only.  Only confident matches reach the QuickStatements and the Lexipedia ``Wikidata item
ID`` claims (``graph.Build._wikidata_laws``).  For every matched item the report says which of ``P8610 P8550 P7588
P7589 P953 P2567`` it lacks.

**United States.**  The items of each state's code and of the named acts lexflow models (the heading of a unit that
ends in "Act", "Law" or "Code"), found by English label or alias among the Wikidata items that apply to the state.
**Australia.**  ``P2461`` (ComLaw ID) against the title ids of the Federal Register of Legislation list lexflow holds.

**QuickStatements.**  One file per property, each statement with the references ``S854`` (the e-Gov page), ``S813``
(the date lexflow fetched the bulk download) and ``S248`` (e-Gov法令検索, ``EGOV_QID``): ``P8610``, ``P8550``,
``P7589`` (date of promulgation), ``P7588`` (effective date, only for a law whose indexed revision is its original
text, since e-Gov gives the enforcement date of the version in force, not of the law), ``P953`` (with qualifier
``P407`` Japanese) and ``P2567`` (amended by, only where both laws have a confident item; qualifier ``P585``, the
amending law's promulgation).  A statement is written only when the item has no value for the property at all
(for ``P2567``: not that value), so no existing statement, label or description is touched, and no item is created.

    python -m lexflow.publish.wikidata_export reconcile [--only jpn,us,aus]
    python -m lexflow.publish.wikidata_export qs [--out out/wikidata]
    python -m lexflow.publish.wikidata_export report
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import sys
import time
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable

from .. import config
from ..store import db

UA = "lexflow-research/0.1 (https://github.com/alibama/lexflow)"
SPARQL = "https://query.wikidata.org/sparql"
API = "https://www.wikidata.org/w/api.php"
CACHE = config.DATA_DIR / "cache" / "wikidata"
OUT = config.ROOT / "out" / "wikidata"
PACE = 1.0                                  # seconds between requests (the brief's limit)
EGOV_QID = "Q48746885"                      # e-Gov法令検索 (read 22 October 2026 by its ja/en labels)
JAPAN, JAPANESE = "Q17", "Q5287"
JAPAN_COUNTRIES = {"Q17", "Q188712"}        # Japan, and the Empire of Japan that prewar laws' items name
FRL_QID = "Q57686106"                       # the Federal Register of Legislation
# what a law item is an instance of (directly or through subclasses): legal act, statute, law, act of parliament
LAW_CLASSES = ("Q1864008", "Q820655", "Q7748", "Q11204", "Q2135465")
LAW_CLASS_ROOTS = ("Q1864008", "Q820655")   # legal act, statute: P31/P279* must reach one of these
CHECK_PROPS = ("P8610", "P8550", "P7588", "P7589", "P953", "P2567")
BATCH = 250                                 # VALUES per SPARQL query
Log = Callable[[str], None]

TABLE = """CREATE TABLE IF NOT EXISTS wikidata_laws (
  jurisdiction TEXT NOT NULL,
  law_key TEXT NOT NULL,
  qid TEXT NOT NULL,
  method TEXT NOT NULL,
  confident INTEGER NOT NULL,
  label TEXT,
  has TEXT,
  conflict TEXT,
  checked TEXT,
  PRIMARY KEY (jurisdiction, law_key, qid)
);"""


# --------------------------------------------------------------------------- the read-only client
class Client:
    """GETs (and SPARQL POSTs, which only read) to Wikidata with lexflow's research user agent, one a second,
    cached by the request's digest; backs off on 429 and 503 as the answer's Retry-After says (else 30 s, doubling)."""

    def __init__(self, cache: Path | None = CACHE, pace: float = PACE, log: Log = print, session=None):
        import requests
        self.cache, self.pace, self.log = cache, pace, log
        self.session = session or requests.Session()
        self.session.headers["User-Agent"] = UA
        self.last = 0.0
        self.requests = 0
        self.cached = 0

    def _wait(self):
        d = self.last + self.pace - time.time()
        if d > 0:
            time.sleep(d)
        self.last = time.time()

    def _cached(self, kind: str, payload: str):
        if self.cache is None:
            return None, None
        p = self.cache / f"{kind}-{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:24]}.json"
        if p.exists():
            try:
                self.cached += 1
                return p, json.loads(p.read_text(encoding="utf-8"))
            except ValueError:
                pass
        return p, None

    def _send(self, method: str, url: str, **kw) -> dict:
        wait = 30
        for attempt in range(6):
            self._wait()
            r = self.session.request(method, url, timeout=180, **kw)
            self.requests += 1
            if r.status_code in (429, 503):
                retry = r.headers.get("Retry-After")
                pause = int(retry) if retry and retry.isdigit() else wait
                self.log(f"wikidata: HTTP {r.status_code}, waiting {pause} s")
                time.sleep(pause)
                wait *= 2
                continue
            r.raise_for_status()
            return r.json()
        raise RuntimeError(f"wikidata: gave up after 6 attempts on {url}")

    def sparql(self, query: str) -> list[dict]:
        """The bindings of a SELECT, as ``{var: value}`` (entity IRIs shortened to their Q/P id)."""
        path, data = self._cached("sparql", query)
        if data is None:
            data = self._send("POST", SPARQL, data={"query": query, "format": "json"},
                              headers={"Accept": "application/sparql-results+json"})
            if path is not None:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        out = []
        for b in data.get("results", {}).get("bindings", []):
            out.append({k: _short(v.get("value", "")) for k, v in b.items()})
        return out

    def entities(self, qids: Iterable[str], props: str = "claims|labels|sitelinks") -> dict[str, dict]:
        """``wbgetentities`` for some items, 50 a request (claims, labels, sitelinks)."""
        qids = sorted(set(qids))
        out: dict[str, dict] = {}
        for i in range(0, len(qids), 50):
            chunk = "|".join(qids[i:i + 50])
            params = {"action": "wbgetentities", "ids": chunk, "props": props, "languages": "ja|en",
                      "sitefilter": "jawiki|enwiki", "format": "json"}
            path, data = self._cached("api", json.dumps(params, sort_keys=True))
            if data is None:
                data = self._send("GET", API, params=params)
                if path is not None:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            out.update({q: e for q, e in (data.get("entities") or {}).items() if "missing" not in e})
        return out


def _short(v: str) -> str:
    return v.rsplit("/", 1)[-1] if v.startswith("http://www.wikidata.org/entity/") else v


def _lit(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def claim_values(entity: dict, pid: str) -> list:
    """The main values of an item's statements for one property (ids for items, ``+YYYY-MM-DD...`` for times)."""
    out = []
    for s in (entity.get("claims") or {}).get(pid, []):
        dv = (s.get("mainsnak") or {}).get("datavalue") or {}
        v = dv.get("value")
        if isinstance(v, dict):
            v = v.get("id") or v.get("time") or v.get("text") or v.get("amount")
        if v is not None:
            out.append(v)
    return out


def norm_title(s: str) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", s or ""))


# --------------------------------------------------------------------------- Japan
def jpn_laws(con=None) -> dict[str, dict]:
    """law_id -> {title, law_num, promulgated, enforced, revision_id, in_force}: the index's laws and the API list's."""
    from ..corpus import countries as CT
    from ..corpus.countries import japan as J
    out: dict[str, dict] = {}
    for x in CT.laws("jpn"):
        out[x["law_id"]] = {"title": x["title"], "law_num": x["law_num"], "promulgated": x["promulgated"],
                            "enforced": x["enforced"], "revision_id": x["revision_id"], "in_force": True,
                            "url": x["url"]}
    for law_id, e in J.law_list().items():
        out.setdefault(law_id, {"title": e.get("law_title") or "", "law_num": e.get("law_num") or "",
                                "promulgated": e.get("promulgation_date"), "enforced": None,
                                "revision_id": e.get("law_revision_id"), "in_force": False,
                                "url": J.PAGE_URL.format(id=law_id)})
    return out


def reconcile_jpn(client: Client, laws: dict[str, dict], log: Log = print) -> dict:
    """The four lookups of the module docstring; returns ``{"matches": {law_id: [match]}, "entities": {qid: e}}``."""
    from ..corpus.countries import japan as J
    by_num = defaultdict(list)
    for law_id, x in laws.items():
        k = J.law_num_key(x["law_num"])
        if k:
            by_num[k].append(law_id)
    by_title = defaultdict(list)
    for law_id, x in laws.items():
        by_title[norm_title(x["title"])].append(law_id)
    cand: dict[str, dict[str, set]] = defaultdict(lambda: defaultdict(set))     # law_id -> qid -> methods
    # 1. P8610
    rows = client.sparql("SELECT ?item ?v WHERE { ?item wdt:P8610 ?v }")
    p8610 = defaultdict(set)
    for r in rows:
        p8610[r["v"]].add(r["item"])
        if r["v"] in laws:
            cand[r["v"]][r["item"]].add("P8610")
    log(f"jpn: {len(rows):,} P8610 statements on Wikidata, {sum(1 for v in p8610 if v in laws):,} of lexflow's laws")
    # 2. P8550 on Japanese items, or written as a Japanese era number
    rows = client.sparql("SELECT ?item ?v ?c WHERE { ?item wdt:P8550 ?v . OPTIONAL { ?item wdt:P17 ?c } "
                         "FILTER(REGEX(?v, '^(明治|大正|昭和|平成|令和)')) }")
    p8550 = defaultdict(set)
    for r in rows:
        k = J.law_num_key(r["v"])
        if not k or (r.get("c") is not None and r["c"] not in JAPAN_COUNTRIES):
            continue
        p8550[r["item"]].add(k)
        for law_id in by_num.get(k, []):
            cand[law_id][r["item"]].add("P8550")
    log(f"jpn: {len(rows):,} era-style P8550 statements on Wikidata")
    # 3. jawiki sitelinks; 4. ja labels
    titles = sorted(t for t in {x["title"] for x in laws.values()} if t)
    variants = titles + [f"{t} (日本)" for t in titles]
    for i in range(0, len(variants), BATCH):
        vals = " ".join(_lit(t) + "@ja" for t in variants[i:i + BATCH])
        q = ("SELECT ?item ?t WHERE { VALUES ?t { " + vals + " } ?a schema:about ?item ; "
             "schema:isPartOf <https://ja.wikipedia.org/> ; schema:name ?t }")
        for r in client.sparql(q):
            t = norm_title(re.sub(r" \(日本\)$", "", r["t"]))
            for law_id in by_title.get(t, []):
                cand[law_id][r["item"]].add("jawiki")
    for i in range(0, len(titles), BATCH):
        vals = " ".join(_lit(t) + "@ja" for t in titles[i:i + BATCH])
        q = "SELECT ?item ?t WHERE { VALUES ?t { " + vals + " } ?item rdfs:label ?t }"
        for r in client.sparql(q):
            for law_id in by_title.get(norm_title(r["t"]), []):
                cand[law_id][r["item"]].add("label")
    qids = sorted({q for m in cand.values() for q in m})
    log(f"jpn: {len(cand):,} laws with a candidate, {len(qids):,} items to check")
    lawish = law_items(client, qids)
    ents = client.entities(qids)
    matches: dict[str, list[dict]] = {}
    for law_id, m in cand.items():
        x = laws[law_id]
        out = []
        for qid, methods in m.items():
            e = ents.get(qid) or {}
            ids = set(claim_values(e, "P8610"))
            nums = {J.law_num_key(v) for v in claim_values(e, "P8550")}
            countries = set(claim_values(e, "P17")) | set(claim_values(e, "P1001"))
            conflict = []
            if ids and law_id not in ids:
                conflict.append("P8610 " + ",".join(sorted(ids)))
            key = J.law_num_key(x["law_num"])
            if {n for n in nums if n} and key not in nums:
                conflict.append("P8550 " + ",".join(sorted(n for n in nums if n)))
            if countries and not countries & JAPAN_COUNTRIES:
                conflict.append("country " + ",".join(sorted(countries)))
            method = next(k for k in ("P8610", "P8550", "jawiki", "label") if k in methods)
            ok_class = qid in lawish
            if method in ("jawiki", "label") and not ok_class:
                continue                        # an article about the field of law, a person, a book ...
            if method == "label" and not countries & JAPAN_COUNTRIES:
                continue
            out.append({"qid": qid, "method": method, "methods": sorted(methods), "conflict": "; ".join(conflict),
                        "label": ((e.get("labels") or {}).get("ja") or {}).get("value"), "law_class": ok_class,
                        "has": [p for p in CHECK_PROPS if claim_values(e, p)]})
        if out:
            matches[law_id] = out
    # confidence: the best method finds exactly one item, which has no conflicting identifier or country and which
    # no other law's identifier or jawiki article also finds
    rank = {"P8610": 0, "P8550": 1, "jawiki": 2, "label": 3}
    item_laws = Counter(m["qid"] for ms in matches.values() for m in ms if m["method"] != "label")
    for law_id, ms in matches.items():
        for m in ms:
            m["confident"] = 0
        best = min(rank[m["method"]] for m in ms)
        top = [m for m in ms if rank[m["method"]] == best]
        if best < 3 and len(top) == 1 and not top[0]["conflict"] and item_laws[top[0]["qid"]] == 1:
            top[0]["confident"] = 1
    return {"matches": matches, "entities": ents}


def law_items(client: Client, qids: list[str]) -> set[str]:
    """The items among ``qids`` that are an instance of a legal act or statute, or of a subclass of one."""
    out: set[str] = set()
    roots = " ".join(f"wd:{q}" for q in LAW_CLASS_ROOTS)
    for i in range(0, len(qids), BATCH):
        vals = " ".join(f"wd:{q}" for q in qids[i:i + BATCH])
        q = ("SELECT DISTINCT ?item WHERE { VALUES ?item { " + vals + " } VALUES ?root { " + roots + " } "
             "?item wdt:P31/wdt:P279* ?root }")
        out |= {r["item"] for r in client.sparql(q)}
    return out


def store(con, jurisdiction: str, matches: dict[str, list[dict]]) -> int:
    con.executescript(TABLE)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with con:
        con.execute("DELETE FROM wikidata_laws WHERE jurisdiction=?", (jurisdiction,))
        con.executemany("INSERT OR REPLACE INTO wikidata_laws VALUES (?,?,?,?,?,?,?,?,?)",
                        [(jurisdiction, law_id, m["qid"], m["method"], m.get("confident", 0), m.get("label"),
                          ",".join(m.get("has") or []), m.get("conflict") or None, now)
                         for law_id, ms in matches.items() for m in ms])
    return sum(len(ms) for ms in matches.values())


def summary_jpn(laws: dict[str, dict], matches: dict[str, list[dict]], amended: set[str]) -> dict:
    """The counts the brief asks for, for the laws in force and for all the listed ones."""
    out = {}
    for scope, ids in (("in_force", [k for k, x in laws.items() if x["in_force"]]), ("listed", list(laws))):
        found = [k for k in ids if k in matches]
        conf = [k for k in ids if any(m.get("confident") for m in matches.get(k, []))]
        best = {k: next((m for m in matches[k] if m.get("confident")), matches[k][0]) for k in found}
        lacks = {p: sum(1 for k in conf if p not in best[k]["has"]) for p in CHECK_PROPS}
        lacks["P2567 (lexflow knows an amendment)"] = sum(1 for k in conf if "P2567" not in best[k]["has"]
                                                          and k in amended)
        out[scope] = {"laws": len(ids), "with_item": len(found), "confident": len(conf),
                      "by_method": dict(Counter(best[k]["method"] for k in found)),
                      "conflicts": sum(1 for k in found if best[k]["conflict"]),
                      "confident_lacking": lacks, "without_item": len(ids) - len(found)}
    return out


# --------------------------------------------------------------------------- the United States
def reconcile_us(client: Client, con, log: Log = print) -> dict:
    """The code item of each state lexflow holds and the named acts it models, by English label or alias among
    Wikidata's items for the state (instances of a legal act, statute or code of law, or a subclass)."""
    from ..municipal import states as S
    from . import graph
    names: dict[str, set[str]] = defaultdict(set)              # state -> names lexflow has (codes, named acts)
    codes: dict[str, set[str]] = defaultdict(set)              # state -> the code items' labels among them
    try:
        items = graph.build(con, states=list(S.CODES), drafts=False, log=lambda *_: None)
    except Exception as e:  # noqa: BLE001 - a broken build: no US names
        log(f"us: graph build failed: {e}")
        items = []
    for it in items:
        kind = it.key.split(":")[1] if ":" in it.key else ""
        st = it.key.split(":")[2] if it.key.count(":") >= 2 else ""
        if st not in S.NAME:
            continue
        if kind == "code" and it.key.count(":") == 2:
            names[st].add(it.label)
            codes[st].add(it.label)
        heading = next((c.value.value for c in it.claims if c.prop == "heading text"), "")
        if kind == "unit" and re.search(r"\b(Act|Law|Code)\b\s*\.?$", heading or ""):
            names[st].add(heading.strip(" ."))
    states = sorted(names)
    found: dict[str, dict[str, str]] = defaultdict(dict)
    roots = "wd:Q1864008 wd:Q820655 wd:Q922203"
    by_state = defaultdict(lambda: defaultdict(set))
    for st in states:                               # one query a state keeps each one small
        q_state = S.WIKIDATA.get(st)
        if not q_state:
            continue
        q = ("SELECT DISTINCT ?item ?l WHERE { VALUES ?root { " + roots + " } "
             "{ ?item wdt:P1001 wd:" + q_state + " } UNION { ?item wdt:P131 wd:" + q_state + " } "
             "?item wdt:P31/wdt:P279* ?root . { ?item rdfs:label ?l } UNION { ?item skos:altLabel ?l } "
             "FILTER(LANG(?l) = 'en') }")
        for r in client.sparql(q):
            by_state[st][_norm_en(r["l"])].add(r["item"])
    out = {"states": len(states), "names": sum(len(v) for v in names.values()), "matched": 0, "codes": 0,
           "codes_matched": 0, "acts": 0, "acts_matched": 0, "by_state": {}}
    for st in states:
        got = {}
        state = S.NAME[st]
        for n in sorted(names[st]):
            is_code = n in codes[st]
            tries = [_norm_en(n), *_code_variants(state)] if is_code else _act_variants(n, state)
            hit = next((by_state[st][t] for t in tries if by_state[st].get(t)), None)
            out["codes" if is_code else "acts"] += 1
            if hit:
                got[n] = sorted(hit)[0]
                out["codes_matched" if is_code else "acts_matched"] += 1
        found[st] = got
        out["matched"] += len(got)
        out["by_state"][st] = {"names": sorted(names[st]), "matched": got,
                               "wikidata_items_for_state": len({q for v in by_state[st].values() for q in v})}
    return out


def _code_variants(state: str) -> list[str]:
    """The names a state's code goes by on Wikidata (Code of Virginia, Florida Statutes, General Laws of
    Massachusetts ...), normalised."""
    forms = ["code of {s}", "{s} code", "{s} statutes", "{s} revised statutes", "revised statutes of {s}",
             "{s} compiled statutes", "{s} general statutes", "general statutes of {s}", "general laws of {s}",
             "{s} consolidated laws", "consolidated laws of {s}", "official code of {s}", "revised code of {s}",
             "{s} code annotated", "code of laws of {s}", "{s} code of laws", "laws of {s}", "{s} codes",
             "{s} statutes annotated", "{s} revised code", "{s} official code"]
    return [_norm_en(f.format(s=state)) for f in forms]


def _act_variants(name: str, state: str) -> list[str]:
    """A named act with and without a leading "The" and the state's name (The Virginia Freedom of Information Act,
    Virginia Freedom of Information Act, Freedom of Information Act)."""
    base = re.sub(r"^the\s+", "", name.strip(), flags=re.I)
    bare = re.sub(rf"^{re.escape(state)}\s+", "", base, flags=re.I)
    return list(dict.fromkeys(_norm_en(x) for x in (name, base, f"{state} {bare}", bare)))


def _norm_en(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


# --------------------------------------------------------------------------- Australia
def reconcile_aus(client: Client, log: Log = print) -> dict:
    """``P2461`` (ComLaw ID) against the title ids of the Federal Register of Legislation list lexflow holds."""
    path = config.RAW_DIR / "countries" / "aus" / "list.jsonl"
    acts = {}
    if path.exists():
        for ln in path.read_text(encoding="utf-8").splitlines():
            if ln.strip():
                e = json.loads(ln)
                acts[e["title_id"]] = e
    rows = client.sparql("SELECT ?item ?v WHERE { ?item wdt:P2461 ?v }")
    by_id = defaultdict(set)
    for r in rows:
        by_id[r["v"].strip().upper()].add(r["item"])
    hit = {t: sorted(by_id[t]) for t in acts if t in by_id}
    principal = [t for t, e in acts.items() if e.get("principal")]
    fetched = set()
    progress = config.RAW_DIR / "countries" / "aus" / "progress.jsonl"
    if progress.exists():
        for ln in progress.read_text(encoding="utf-8").splitlines():
            try:
                e = json.loads(ln)
            except ValueError:
                continue
            if e.get("status") == "ok":
                fetched.add(e.get("title_id"))
    return {"wikidata_p2461_statements": len(rows), "acts_listed": len(acts), "principal": len(principal),
            "acts_with_item": len(hit), "principal_with_item": sum(1 for t in principal if t in hit),
            "fetched_acts": len(fetched), "fetched_with_item": sum(1 for t in fetched if t in hit),
            "several_items": sum(1 for v in hit.values() if len(v) > 1)}


# --------------------------------------------------------------------------- QuickStatements
GREGORIAN_FROM = "1873-01-01"           # Japan's dates before 明治6年 are lunar-calendar dates e-Gov writes unconverted


def qs_time(date: str | None) -> str | None:
    """A QuickStatements day-precision time, or None for no date and for a Japanese date before the Gregorian
    calendar's adoption (明治5年12月3日 became 1 January 1873), which e-Gov gives in the old calendar."""
    s = (date or "")[:10]
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", s) or s < GREGORIAN_FROM:
        return None
    return f"+{s}T00:00:00Z/11"


def qs_refs(url: str, retrieved: str) -> list[str]:
    out = ["S854", _lit(url)]
    t = qs_time(retrieved)
    if t:
        out += ["S813", t]
    out += ["S248", EGOV_QID]
    return out


def build_qs(laws: dict[str, dict], matches: dict[str, list[dict]], entities: dict[str, dict],
             amendments: list[dict], retrieved: str) -> dict[str, list[str]]:
    """The QuickStatements lines per property (see the module docstring), only for confident matches and only
    where the item lacks the property (``P2567``: the value)."""
    from ..corpus.countries import japan as J
    qid_of = {k: next(m["qid"] for m in ms if m.get("confident")) for k, ms in matches.items()
              if any(m.get("confident") for m in ms)}
    amended = {r["law_key"] for r in amendments if r["kind"] == "amended"}
    out: dict[str, list[str]] = {p: [] for p in ("P8610", "P8550", "P7589", "P7588", "P953", "P2567")}
    note = "/* e-Gov法令検索 (Digital Agency) via lexflow reconciliation */"
    for law_id in sorted(qid_of):
        q, x = qid_of[law_id], laws[law_id]
        e = entities.get(q) or {}
        page = x.get("url") or J.PAGE_URL.format(id=law_id)
        refs = qs_refs(page, retrieved)
        if not claim_values(e, "P8610"):
            out["P8610"].append("\t".join([q, "P8610", _lit(law_id), *refs, note]))
        parsed = J.parse_law_num(x["law_num"])
        key = J.law_num_key(x["law_num"]) if parsed and parsed["num"] is not None else ""   # 明治三十三年勅令: no number
        if key and not claim_values(e, "P8550"):
            out["P8550"].append("\t".join([q, "P8550", _lit(key), *refs, note]))
        t = qs_time(x.get("promulgated"))
        if t and not claim_values(e, "P7589"):
            out["P7589"].append("\t".join([q, "P7589", t, *refs, note]))
        # the effective date of the law itself: known only when the indexed revision is the original text
        rev = (x.get("revision_id") or "").split("_")
        original = x.get("in_force") and len(rev) == 3 and not rev[2].strip("0") and law_id not in amended
        t = qs_time(x.get("enforced")) if original else None
        if t and not claim_values(e, "P7588"):
            out["P7588"].append("\t".join([q, "P7588", t, *refs, note]))
        if not claim_values(e, "P953"):
            out["P953"].append("\t".join([q, "P953", _lit(page), "P407", JAPANESE, *refs, note]))
    seen = set()
    # a row that knows the amending law's promulgation first (the zip's revision rows know only the enforcement)
    for r in sorted(amendments, key=lambda r: (r.get("date_kind") != "promulgated", r["law_key"], r["amending_key"] or "")):
        if r["kind"] != "amended" or not r["amending_key"]:
            continue
        a, b = qid_of.get(r["law_key"]), qid_of.get(r["amending_key"])
        if not a or not b or (a, b) in seen or b in claim_values(entities.get(a) or {}, "P2567"):
            continue
        seen.add((a, b))
        line = [a, "P2567", b]
        t = qs_time(r["date"]) if r["date_kind"] == "promulgated" else None
        if t:
            line += ["P585", t]
        page = laws[r["law_key"]].get("url") or J.PAGE_URL.format(id=r["law_key"])
        out["P2567"].append("\t".join(line + qs_refs(page, r.get("retrieved") or retrieved) + [note]))
    return out


QS_NAMES = {"P8610": "e-GOV law ID", "P8550": "law identifier", "P7589": "date of promulgation",
            "P7588": "effective date", "P953": "full work available at URL", "P2567": "amended by"}


def write_qs(lines: dict[str, list[str]], out_dir: Path, *, retrieved: str, summary: dict) -> dict[str, int]:
    """``out_dir/jpn-<property>.qs``, each with a header of ``#`` lines (delete them before pasting into
    QuickStatements, ``grep -v '^#'``) that says what the batch adds, how many statements and from what."""
    out_dir.mkdir(parents=True, exist_ok=True)
    counts = {}
    for pid, ls in lines.items():
        name = QS_NAMES[pid]
        items = len({ln.split("\t", 1)[0] for ls_ in [ls] for ln in ls_})
        head = [f"# lexflow QuickStatements V1 batch: add {pid} ({name}) to existing Wikidata items for Japanese laws",
                f"# statements: {len(ls)} on {items} items; generated "
                f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')} from e-Gov法令検索 (bulk XML retrieved {retrieved})",
                "# every statement carries S854 (the e-Gov page), S813 (retrieved) and S248 Q48746885 (e-Gov法令検索)",
                "# only items matched by an identifier or their jawiki article, only where the item has no "
                f"{pid}" + (" statement with this value" if pid == "P2567" else " statement") +
                "; no labels, no existing statements, no new items",
                "# review, then run under your own account after the bot request (docs/design/wikidata-laws.md §6); "
                "strip these lines first: grep -v '^#'",
                f"# laws in force {summary.get('in_force', {}).get('laws', 0)}, with a confident item "
                f"{summary.get('in_force', {}).get('confident', 0)}"]
        (out_dir / f"jpn-{pid.lower()}.qs").write_text("\n".join(head + ls) + "\n", encoding="utf-8")
        counts[pid] = len(ls)
    return counts


# --------------------------------------------------------------------------- the run
def run(con, *, only: set[str] | None = None, out_dir: Path | None = None, client: Client | None = None,
        log: Log = print) -> dict:
    only = only or {"jpn", "us", "aus"}
    client = client or Client(log=log)
    out_dir = out_dir or OUT
    report: dict = {"generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "user_agent": UA}
    if "jpn" in only:
        from ..corpus.countries import japan as J
        laws = jpn_laws(con)
        res = reconcile_jpn(client, laws, log)
        store(con, "jpn", res["matches"])
        try:
            amendments = db.rows(con, "SELECT * FROM law_amendments WHERE jurisdiction='jpn'")
        except sqlite3.Error:
            amendments = []
        amended = {r["law_key"] for r in amendments if r["kind"] == "amended"}
        report["jpn"] = summary_jpn(laws, res["matches"], amended)
        retrieved = ((J.manifest().get("bulk") or {}).get("fetched") or "")[:10]
        lines = build_qs(laws, res["matches"], res["entities"], amendments, retrieved)
        report["jpn"]["quickstatements"] = write_qs(lines, out_dir, retrieved=retrieved, summary=report["jpn"])
        review = [{"law_id": k, "title": laws[k]["title"], **m} for k, ms in sorted(res["matches"].items())
                  for m in ms if not m.get("confident")]
        (out_dir / "jpn-review.json").write_text(json.dumps(review, ensure_ascii=False, indent=1), encoding="utf-8")
        report["jpn"]["review_rows"] = len(review)
    if "us" in only:
        report["us"] = reconcile_us(client, con, log)
    if "aus" in only:
        report["aus"] = reconcile_aus(client, log)
    report["requests"], report["cached"] = client.requests, client.cached
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "reconcile-report.json"
    try:                                            # a partial run (qs, --only) keeps the other jurisdictions' parts
        old = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        old = {}
    path.write_text(json.dumps({**old, **report}, ensure_ascii=False, indent=1), encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m lexflow.publish.wikidata_export", description=__doc__.split("\n\n")[0])
    ap.add_argument("action", choices=["reconcile", "qs", "report"], help="reconcile and qs both read Wikidata "
                                                                          "(cached) and write out/wikidata/")
    ap.add_argument("--only", help="comma-separated: jpn,us,aus (default all)")
    ap.add_argument("--out", help=f"output directory (default {OUT})")
    args = ap.parse_args(argv)
    log = lambda *a: print(*a, file=sys.stderr, flush=True)       # noqa: E731
    if args.action == "report":
        p = Path(args.out or OUT) / "reconcile-report.json"
        print(p.read_text(encoding="utf-8") if p.exists() else "{}")
        return 0
    con = db.connect()
    try:
        only = {s.strip() for s in args.only.split(",")} if args.only else None
        if args.action == "qs":
            only = {"jpn"}
        report = run(con, only=only, out_dir=Path(args.out) if args.out else None, log=log)
    finally:
        con.close()
    print(json.dumps(report, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
