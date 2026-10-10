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

from .. import config
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


def load_local(con, govs: list[dict] | None = None, log: Log = print) -> dict:
    """Load curated/places/*/*.json into local_answers and contacts (all files, or those for ``govs``)."""
    wanted = {g["gov_id"] for g in govs} if govs else None
    loaded, contacts = 0, 0
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
            db.upsert(con, "local_answers", [{
                "gov_id": g["gov_id"], "state": g["state"], "question": qid, "summary": ans.get("summary"),
                "steps": ans.get("steps", []), "contacts": ans.get("contacts", []), "local_law": ans.get("local_law", []),
                "fees": ans.get("fees"), "caveats": ans.get("caveats", []), "sources": spec.get("sources", []),
                "built_by": spec.get("researched_by", "claude"), "verified": int(bool(spec.get("verified"))),
                "researched": spec.get("researched"), "updated_at": ts}])
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
    return {"answers": loaded, "contacts": contacts}
