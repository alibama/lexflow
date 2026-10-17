"""The 50 states, DC and Puerto Rico: postal code, FIPS code and name."""
from __future__ import annotations

STATES: list[tuple[str, str, str]] = [
    ("al", "01", "Alabama"), ("ak", "02", "Alaska"), ("az", "04", "Arizona"), ("ar", "05", "Arkansas"),
    ("ca", "06", "California"), ("co", "08", "Colorado"), ("ct", "09", "Connecticut"), ("de", "10", "Delaware"),
    ("dc", "11", "District of Columbia"), ("fl", "12", "Florida"), ("ga", "13", "Georgia"), ("hi", "15", "Hawaii"),
    ("id", "16", "Idaho"), ("il", "17", "Illinois"), ("in", "18", "Indiana"), ("ia", "19", "Iowa"),
    ("ks", "20", "Kansas"), ("ky", "21", "Kentucky"), ("la", "22", "Louisiana"), ("me", "23", "Maine"),
    ("md", "24", "Maryland"), ("ma", "25", "Massachusetts"), ("mi", "26", "Michigan"), ("mn", "27", "Minnesota"),
    ("ms", "28", "Mississippi"), ("mo", "29", "Missouri"), ("mt", "30", "Montana"), ("ne", "31", "Nebraska"),
    ("nv", "32", "Nevada"), ("nh", "33", "New Hampshire"), ("nj", "34", "New Jersey"), ("nm", "35", "New Mexico"),
    ("ny", "36", "New York"), ("nc", "37", "North Carolina"), ("nd", "38", "North Dakota"), ("oh", "39", "Ohio"),
    ("ok", "40", "Oklahoma"), ("or", "41", "Oregon"), ("pa", "42", "Pennsylvania"), ("ri", "44", "Rhode Island"),
    ("sc", "45", "South Carolina"), ("sd", "46", "South Dakota"), ("tn", "47", "Tennessee"), ("tx", "48", "Texas"),
    ("ut", "49", "Utah"), ("vt", "50", "Vermont"), ("va", "51", "Virginia"), ("wa", "53", "Washington"),
    ("wv", "54", "West Virginia"), ("wi", "55", "Wisconsin"), ("wy", "56", "Wyoming"), ("pr", "72", "Puerto Rico"),
]

# Wikidata items and official websites of the 52 jurisdictions (wbgetentities, 15 October 2026: every item is
# P31 state of the United States of America, except DC (capital city, federal district) and Puerto Rico
# (unincorporated territory); websites are each item's P856)
WIKIDATA: dict[str, str] = {
    "al": "Q173", "ak": "Q797", "az": "Q816", "ar": "Q1612", "ca": "Q99", "co": "Q1261", "ct": "Q779",
    "de": "Q1393", "dc": "Q61", "fl": "Q812", "ga": "Q1428", "hi": "Q782", "id": "Q1221", "il": "Q1204",
    "in": "Q1415", "ia": "Q1546", "ks": "Q1558", "ky": "Q1603", "la": "Q1588", "me": "Q724", "md": "Q1391",
    "ma": "Q771", "mi": "Q1166", "mn": "Q1527", "ms": "Q1494", "mo": "Q1581", "mt": "Q1212", "ne": "Q1553",
    "nv": "Q1227", "nh": "Q759", "nj": "Q1408", "nm": "Q1522", "ny": "Q1384", "nc": "Q1454", "nd": "Q1207",
    "oh": "Q1397", "ok": "Q1649", "or": "Q824", "pa": "Q1400", "ri": "Q1387", "sc": "Q1456", "sd": "Q1211",
    "tn": "Q1509", "tx": "Q1439", "ut": "Q829", "vt": "Q16551", "va": "Q1370", "wa": "Q1223", "wv": "Q1371",
    "wi": "Q1537", "wy": "Q1214", "pr": "Q1183",
}
WEBSITE: dict[str, str] = {
    "al": "https://www.alabama.gov", "ak": "https://alaska.gov", "az": "https://az.gov",
    "ar": "https://portal.arkansas.gov/", "ca": "https://ca.gov", "co": "https://www.colorado.gov/",
    "ct": "https://portal.ct.gov/", "de": "https://delaware.gov", "dc": "https://dc.gov/",
    "fl": "https://www.myflorida.com/", "ga": "https://georgia.gov/", "hi": "https://portal.ehawaii.gov/",
    "id": "https://www.idaho.gov", "il": "https://www.illinois.gov", "in": "https://www.in.gov",
    "ia": "https://www.iowa.gov/", "ks": "https://www.kansas.gov", "ky": "https://kentucky.gov",
    "la": "https://louisiana.gov", "me": "https://www.maine.gov", "md": "https://www.maryland.gov/",
    "ma": "https://mass.gov", "mi": "https://michigan.gov", "mn": "https://mn.gov/",
    "ms": "http://www.mississippi.gov", "mo": "https://www.mo.gov", "mt": "https://www.mt.gov/",
    "ne": "https://www.nebraska.gov/", "nv": "https://nv.gov/", "nh": "https://www.nh.gov/", "nj": "https://nj.gov",
    "nm": "https://www.newmexico.gov/", "ny": "https://www.ny.gov/", "nc": "https://www.nc.gov/",
    "nd": "https://nd.gov", "oh": "https://ohio.gov", "ok": "https://oklahoma.gov/", "or": "https://www.oregon.gov/",
    "pa": "https://www.pa.gov/", "ri": "https://www.ri.gov/", "sc": "https://www.sc.gov/", "sd": "https://sd.gov/",
    "tn": "https://www.tn.gov/", "tx": "https://texas.gov", "ut": "https://utah.gov/",
    "vt": "https://www.vermont.gov/", "va": "https://www.virginia.gov/", "wa": "https://wa.gov/",
    "wv": "https://www.wv.gov/", "wi": "https://www.wisconsin.gov/", "wy": "http://wyoming.gov",
    "pr": "https://pr.gov",
}

CODES = [s for s, _, _ in STATES]
NAME = {s: n for s, _, n in STATES}
FIPS = {s: f for s, f, _ in STATES}
BY_FIPS = {f: s for s, f, _ in STATES}
BY_NAME = {n.lower(): s for s, _, n in STATES}


def normalise(code: str) -> str:
    """Accept 'VA', 'va', '51' or 'Virginia'; return 'va'."""
    c = (code or "").strip().lower()
    if c in NAME:
        return c
    if c.zfill(2) in BY_FIPS:
        return BY_FIPS[c.zfill(2)]
    if c in BY_NAME:
        return BY_NAME[c]
    raise ValueError(f"unknown state: {code!r}")


def parse_states(arg: str | None) -> list[str]:
    """'all', '' or None -> every state; 'va,dc' -> ['va', 'dc']."""
    if not arg or arg.strip().lower() == "all":
        return list(CODES)
    return [normalise(x) for x in arg.split(",") if x.strip()]
