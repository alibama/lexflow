"""Who to contact: Wikidata (the data behind govdirectory.org), a CSV import, and the contact ladder.

Contact levels, best first (scores live in :mod:`lexflow.municipal.method`):

* ``page``    - a records page (or business-licence page) on the government's own site,
                or a records-specific email such as foia@ / records@ / clerk@
* ``direct``  - a general email address or phone number
* ``website`` - an official website only
* ``postal``  - only the Census mailing address and an official's title
* ``none``
"""
from __future__ import annotations

import csv
import re
import time

import requests

from .. import config
from ..store import db
from . import states as S
from .fetch import Log

SPARQL = "https://query.wikidata.org/sparql"
LEVELS = ["none", "postal", "website", "direct", "page"]
RECORDS_EMAIL = re.compile(r"^(foia|records?|publicrecords|public\.?records|opra|cpra|clerk|townclerk|cityclerk|"
                           r"countyclerk|recordsrequest|records\.?request|rtk|righttoknow|openrecords)\b", re.I)
BUSINESS_EMAIL = re.compile(r"^(business|bpol|license|licensing|revenue|commissioner|tax)", re.I)

COUNTY_QUERY = """
SELECT ?item ?fips ?website ?email ?phone WHERE {
  ?item wdt:P882 ?fips . FILTER(STRSTARTS(?fips, "%(fips)s"))
  OPTIONAL { ?item wdt:P856 ?website }
  OPTIONAL { ?item wdt:P968 ?email }
  OPTIONAL { ?item wdt:P1329 ?phone }
}"""
# FIPS 55-3 codes are stored as "<state>-<place>", e.g. "51-14968" for Charlottesville
PLACE_QUERY = """
SELECT ?item ?place ?website ?email ?phone WHERE {
  ?item wdt:P774 ?place . FILTER(STRSTARTS(?place, "%(fips)s-"))
  OPTIONAL { ?item wdt:P856 ?website }
  OPTIONAL { ?item wdt:P968 ?email }
  OPTIONAL { ?item wdt:P1329 ?phone }
}"""


def _sparql(query: str, log: Log, tries: int = 3) -> list[dict]:
    for attempt in range(tries):
        try:
            r = requests.get(SPARQL, params={"query": query, "format": "json"}, timeout=90,
                             headers={"User-Agent": config.USER_AGENT, "Accept": "application/sparql-results+json"})
            if r.status_code == 429:
                time.sleep(int(r.headers.get("Retry-After", "30")))
                continue
            r.raise_for_status()
            return [{k: v["value"] for k, v in b.items()} for b in r.json()["results"]["bindings"]]
        except requests.RequestException as e:
            log(f"Wikidata query failed ({e}); retrying" if attempt + 1 < tries else f"Wikidata query failed: {e}")
            time.sleep(5 * (attempt + 1))
    return []


def wikidata(con, state: str, log: Log = print) -> dict:
    govs = db.rows(con, "SELECT gov_id, kind, county_fips, place_fips FROM governments WHERE state=?", state)
    by_county = {g["county_fips"]: g["gov_id"] for g in govs if g["kind"] == "county"}
    by_place = {g["place_fips"]: g["gov_id"] for g in govs if g["kind"] != "county" and g["place_fips"]}
    results = _sparql(COUNTY_QUERY % {"fips": S.FIPS[state]}, log)
    results += _sparql(PLACE_QUERY % {"fips": S.FIPS[state]}, log)
    contacts, qids, ts = [], {}, db.now()
    for b in results:
        if "fips" in b:
            gid = by_county.get(b["fips"])
        else:
            gid = by_place.get(b.get("place", "").split("-")[-1])
        if not gid:
            continue
        qid = b["item"].rsplit("/", 1)[-1]
        qids[gid] = qid
        if b.get("website"):
            contacts.append(dict(gov_id=gid, state=state, question="general", kind="website", value=b["website"],
                                 label=f"Official website (Wikidata {qid})", source="wikidata", updated_at=ts))
        if b.get("email"):
            email = b["email"].removeprefix("mailto:")
            contacts.append(dict(gov_id=gid, state=state, question="general", kind="email", value=email,
                                 label=f"Email (Wikidata {qid})", source="wikidata", updated_at=ts))
            if RECORDS_EMAIL.match(email):
                contacts.append(dict(gov_id=gid, state=state, question="records", kind="email", value=email,
                                     label="Records email (Wikidata)", source="wikidata", updated_at=ts))
        if b.get("phone"):
            contacts.append(dict(gov_id=gid, state=state, question="general", kind="phone", value=b["phone"],
                                 label=f"Phone (Wikidata {qid})", source="wikidata", updated_at=ts))
    db.upsert(con, "contacts", contacts)
    con.executemany("UPDATE governments SET wikidata=?, updated_at=? WHERE gov_id=?",
                    [(q, ts, g) for g, q in qids.items()])
    db.bump(con)
    con.commit()
    log(f"{S.NAME[state]}: Wikidata matched {len(qids)} of {len(govs)} governments, {len(contacts)} contact rows")
    return {"matched": len(qids), "contacts": len(contacts)}


def import_csv(con, path, log: Log = print) -> int:
    """Columns: gov_id, question (general|records|business), kind (website|email|phone|page|office|person),
    value, label (optional).  Use this to bring in govenator or any hand-made list."""
    rows, ts = [], db.now()
    states = {g["gov_id"]: g["state"] for g in db.rows(con, "SELECT gov_id, state FROM governments")}
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            gid = (r.get("gov_id") or "").strip()
            if gid not in states or not r.get("value"):
                continue
            rows.append(dict(gov_id=gid, state=states[gid], question=(r.get("question") or "general").strip(),
                             kind=(r.get("kind") or "website").strip(), value=r["value"].strip(),
                             label=(r.get("label") or "").strip() or None, source="csv-import", updated_at=ts))
    db.upsert(con, "contacts", rows)
    db.bump(con)
    con.commit()
    log(f"imported {len(rows)} contact rows from {path}")
    return len(rows)


def level(contacts: list[dict], question: str) -> str:
    """Best contact level one government has for one question."""
    kinds_q = {(c["question"], c["kind"]) for c in contacts}
    if (question, "page") in kinds_q or (question, "email") in kinds_q or (question, "person") in kinds_q \
            or (question, "office") in kinds_q:
        return "page"
    if ("general", "email") in kinds_q or ("general", "phone") in kinds_q or (question, "phone") in kinds_q:
        return "direct"
    if ("general", "website") in kinds_q:
        return "website"
    if ("general", "postal") in kinds_q:
        return "postal"
    return "none"
