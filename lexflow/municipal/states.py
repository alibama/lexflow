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
