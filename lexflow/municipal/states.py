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


# ---------------------------------------------------------------------- countries
# National jurisdictions beside the states.  A country's key is its ISO 3166-1 alpha-3 code in lower case, so it never
# collides with a two-letter postal code (``co`` Colorado vs Colombia, ``de``, ``in``, ``md``, ``pa`` ...): the key
# names its index (data/index/statutes_jpn.sqlite), its wiki items (lexflow:code:jpn, lexflow:jurisdiction:jpn) and
# its entry in the dashboard's pickers.  ``iso2`` is kept for the ELI IRIs (/eli/jp/...).  The adapters and their
# verified sources are lexflow/corpus/countries/ (docs/design/global-sources.md); only countries whose law lexflow
# holds are listed here.  The lists above stay the 52 US jurisdictions: code that walks them (open-us-law, Census,
# CourtListener) never meets a country.
COUNTRIES: list[dict] = [
    {"code": "jpn", "iso2": "jp", "name": "Japan", "wikidata": "Q17", "languages": ["ja"],
     "names": {"ja": "日本"}, "descriptions": {"ja": "国（lexflow の法域）"},
     "code_label": {"ja": "日本の法令", "en": "Laws of Japan"},
     "code_description": {"ja": "e-Gov法令検索に収録された現行の法令"}, "website": "https://laws.e-gov.go.jp/",
     "source": "e-Gov 法令検索 (Digital Agency)"},
    {"code": "bra", "iso2": "br", "name": "Brazil", "wikidata": "Q155", "languages": ["pt"],
     "names": {"pt": "Brasil"}, "descriptions": {"pt": "país (jurisdição do lexflow)"},
     "code_label": {"pt": "Legislação federal brasileira", "en": "Federal legislation of Brazil"},
     "code_description": {"pt": "Constituição, emendas constitucionais, leis complementares, leis ordinárias e "
                                "decretos-leis federais compilados no Normas.leg.br"},
     "website": "https://normas.leg.br/",
     "official_sites": ["https://normas.leg.br/", "https://legis.senado.leg.br/dadosabertos/",
                        "https://www.lexml.gov.br/", "https://www.planalto.gov.br/ccivil_03/"],
     "source": "Normas.leg.br (Congresso Nacional) and Senado Federal open data", "aliases": ["brasil"]},
    # Australia, three of its states (subnational keys <alpha-3>-<abbr>, ``parent`` the country) and Romania, whose
    # law the country adapters pull (docs/design/global-sources.md §9); Wikidata items verified read-only against
    # Special:EntityData on 22 October 2026 (Q34366, Q35715, Q3206: P31 state of Australia, P17 Australia)
    {"code": "aus", "iso2": "au", "name": "Australia", "wikidata": "Q408", "languages": ["en"],
     "code_label": {"en": "Commonwealth Acts (Federal Register of Legislation)"},
     "code_description": {"en": "Commonwealth Acts in force, current compilations"},
     "website": "https://www.legislation.gov.au/", "source": "Federal Register of Legislation (Office of Parliamentary "
     "Counsel)"},
    {"code": "aus-tas", "iso2": "au-tas", "iso3166_2": "AU-TAS", "parent": "aus", "name": "Tasmania",
     "wikidata": "Q34366", "languages": ["en"], "code_label": {"en": "Tasmanian Acts (Tasmanian Legislation Online)"},
     "website": "https://www.legislation.tas.gov.au/", "source": "Tasmanian Legislation Online"},
    {"code": "aus-sa", "iso2": "au-sa", "iso3166_2": "AU-SA", "parent": "aus", "name": "South Australia",
     "wikidata": "Q35715", "languages": ["en"],
     "code_label": {"en": "South Australian Acts (Legislative Database, DataSA)"},
     "website": "https://www.legislation.sa.gov.au/", "source": "Legislative Database Update Package (XML), DataSA"},
    {"code": "aus-wa", "iso2": "au-wa", "iso3166_2": "AU-WA", "parent": "aus", "name": "Western Australia",
     "wikidata": "Q3206", "languages": ["en"],
     "code_label": {"en": "Western Australian Acts (Western Australian Legislation)"},
     "website": "https://www.legislation.wa.gov.au/", "source": "Western Australian Legislation"},
    {"code": "rou", "iso2": "ro", "name": "Romania", "wikidata": "Q218", "languages": ["ro"],
     "names": {"ro": "România"}, "descriptions": {"ro": "țară (jurisdicție lexflow)"},
     "code_label": {"ro": "Legislația României", "en": "Legislation of Romania"},
     "website": "https://legislatie.just.ro/", "source": "Portal Legislativ (Ministerul Justiției), FreeWebService"},
]
COUNTRY = {c["code"]: c for c in COUNTRIES}
COUNTRY_CODES = [c["code"] for c in COUNTRIES]
COUNTRY_NAME = {c["code"]: c["name"] for c in COUNTRIES}
COUNTRY_BY_ALIAS = {**{c["iso2"]: c["code"] for c in COUNTRIES}, **{c["name"].lower(): c["code"] for c in COUNTRIES}}
# every jurisdiction lexflow answers for, states first
JURISDICTION_NAME: dict[str, str] = {**NAME, **COUNTRY_NAME}


def is_country(code: str) -> bool:
    return (code or "").strip().lower() in COUNTRY


def name_of(code: str) -> str:
    """The name of a state or a country (``va`` -> Virginia, ``jpn`` -> Japan); the code itself when unknown."""
    c = (code or "").strip().lower()
    return JURISDICTION_NAME.get(c, code)


def normalise_any(code: str) -> str:
    """``normalise`` for a state, or a country's key from its key, alpha-2 code or name (``JPN``, ``Japan``); a bare
    ``jp`` is Japan only because no state has that code."""
    c = (code or "").strip().lower()
    if c in COUNTRY:
        return c
    try:
        return normalise(c)
    except ValueError:
        if c in COUNTRY_BY_ALIAS:
            return COUNTRY_BY_ALIAS[c]
        raise ValueError(f"unknown state or country: {code!r}") from None


def parse_jurisdictions(arg: str | None) -> list[str]:
    """``parse_states`` that also accepts country keys: 'all' -> every state (countries are named explicitly)."""
    if not arg or arg.strip().lower() == "all":
        return list(CODES)
    return [normalise_any(x) for x in arg.split(",") if x.strip()]
