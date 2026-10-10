"""Every general-purpose local government in the US, from the Census of Governments 2022.

The Government Units List names 38,736 counties, municipalities and townships with an
official's title, mailing address, website (where the Census has one), population and
FIPS codes.  ``gov_id`` is the Census GID, which is stable across releases.
"""
from __future__ import annotations

import io
import re
import zipfile

from .. import config
from ..store import db
from . import states as S
from .fetch import Log, download

URL = "https://www2.census.gov/programs-surveys/gus/datasets/2022/govt_units_2022.ZIP"
ZIP = config.RAW_DIR / "census" / "govt_units_2022.ZIP"
SHEET = "General Purpose"
KIND = {"1": "county", "2": "municipality", "3": "township"}
SMALL = {"of", "and", "the", "de", "la", "du", "in", "on", "upon"}


def nice_name(raw: str, kind: str) -> str:
    """'COUNTY OF AUTAUGA' -> 'Autauga County'; 'CITY OF ST. LOUIS' -> 'City of St. Louis'."""
    words = []
    for i, w in enumerate(raw.strip().lower().split()):
        if i and w in SMALL:
            words.append(w)
        elif w.startswith("mc") and len(w) > 2:
            words.append("Mc" + w[2:].capitalize())
        else:
            words.append("-".join(p[:1].upper() + p[1:] for p in w.split("-")))
    name = " ".join(words).replace(" Dc", " DC")
    m = re.match(r"^(County|Parish|Borough|Municipality|City and Borough) of (.+)$", name)
    if kind == "county" and m:
        return f"{m.group(2)} {m.group(1)}"
    return name


def _clean_url(u) -> str | None:
    if not isinstance(u, str) or not u.strip():
        return None
    u = u.strip()
    if not re.match(r"^https?://", u, re.I):
        u = "http://" + u
    return u


def load(con, log: Log = print, progress=None) -> dict:
    import pandas as pd
    download(URL, ZIP, log=log)
    with zipfile.ZipFile(ZIP) as z:
        name = next(n for n in z.namelist() if n.lower().endswith(".xlsx"))
        log(f"reading {name} (sheet '{SHEET}')")
        df = pd.read_excel(io.BytesIO(z.read(name)), sheet_name=SHEET, dtype=str)
    df = df[df["IS_ACTIVE"].fillna("Y").str.upper() == "Y"]
    rows, contacts = [], []
    ts = db.now()
    for r in df.itertuples(index=False):
        st = S.BY_FIPS.get(str(r.FIPS_STATE).zfill(2))
        if st is None:
            continue
        kind = KIND.get(str(r.UNIT_TYPE)[:1], "other")
        county = str(r.FIPS_COUNTY).zfill(3) if isinstance(r.FIPS_COUNTY, str) else None
        website = _clean_url(r.WEB_ADDRESS)
        addr = ", ".join(x for x in (r.ADDRESS1, r.ADDRESS2, r.CITY, f"{r.STATE} {r.ZIP or ''}".strip())
                         if isinstance(x, str) and x.strip())
        pop = int(r.POPULATION) if isinstance(r.POPULATION, str) and r.POPULATION.isdigit() else None
        gid = str(r.CENSUS_ID_GIDID)
        rows.append({"gov_id": gid, "state": st, "name": nice_name(r.UNIT_NAME, kind), "kind": kind,
                     "county_fips": (S.FIPS[st] + county) if county else None,
                     "county_name": (r.COUNTY_AREA_NAME or "").title() if isinstance(r.COUNTY_AREA_NAME, str) else None,
                     "place_fips": str(r.FIPS_PLACE) if isinstance(r.FIPS_PLACE, str) else None,
                     "population": pop, "website": website, "address": addr, "source": "census-gus-2022",
                     "updated_at": ts})
        if website:
            contacts.append({"gov_id": gid, "state": st, "question": "general", "kind": "website",
                             "value": website, "label": "Official website (Census)", "source": "census-gus-2022",
                             "updated_at": ts})
        if addr:
            title = r.TITLE.title() if isinstance(r.TITLE, str) else "Main office"
            contacts.append({"gov_id": gid, "state": st, "question": "general", "kind": "postal",
                             "value": addr, "label": title, "source": "census-gus-2022", "updated_at": ts})
    log(f"{len(rows):,} governments in {len({r['state'] for r in rows})} states")
    for i in range(0, len(rows), 5000):
        db.upsert(con, "governments", rows[i:i + 5000])
        if progress:
            progress(min(1.0, (i + 5000) / len(rows)) * 0.8)
    for i in range(0, len(contacts), 5000):
        db.upsert(con, "contacts", contacts[i:i + 5000])
    db.bump(con)
    con.commit()
    kinds = {}
    for r in rows:
        kinds[r["kind"]] = kinds.get(r["kind"], 0) + 1
    return {"governments": len(rows), "kinds": kinds, "websites": sum(1 for r in rows if r["website"])}
