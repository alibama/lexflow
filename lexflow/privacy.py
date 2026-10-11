"""Office channels only: which published contacts lexflow may show (docs/design/entities-contacts.md section 5.2).

lexflow shows organisations' published channels (a website, a records page, an office address, a general office
mailbox, a main office line) and never a person's.  These are shape checks on the text of a row; none of them can
know every person's name, so each one keeps only text it can account for and refuses the rest:

* ``is_office_mailbox(address)``: the whole-token rule of section 5.2.  The local part is split into tokens (at
  ``.``, ``_``, ``-`` and ``+``, at a change from lower to upper case, and between letters and digits; digit
  tokens are ignored).  Every token must be a role word, a string that cuts into role words with nothing left over
  (``publicrecords``), the initialism of the office's own name (``mpd`` for the Metropolitan Police Department), or
  a word of the owner's own name standing beside a role word.  At least one token must be a role word or an
  initialism.  Initials come from the owner's names, and from the office name that starts the row's label only
  when that phrase is an office name (it has an office word such as department, office, division or board, and
  every other word is office vocabulary or the owner's name), so a label that is a person's name ("Jane Doe",
  "Jane Doe, FOIA Officer") gives no initials.  An initialism needs three letters or more (``MIN_INITIALS``): two
  letters are also a person's initials, so ``cc@`` is refused even for the City of Charlottesville.  Anything else
  is personal-looking (first.last, initial+surname, surname+initial, with or without digits, a role word beside a
  name) and is refused.
* ``is_office_phone(label)``: a phone number is shown only when its label names an office from a fixed vocabulary
  ("Business Licensing Division", "Clerk's Office main line").  Every word must be office vocabulary, a word of the
  owner's name, or an initialism (three letters or more) of the owner or of the office that starts the label.  An
  upper-case word is not let through as an acronym on its shape alone ("Records: JANE DOE" and "Clerk's Office -
  CC" are refused).  A label of line words only ("Phone", "Fax"), a direct-line marker ("direct", "cell",
  "personal", "home phone", "Mobile") or an office-holder's title without the word "office" ("Director", "FOIA
  Officer") is refused.
* ``office_phone_value(value)``: the phone's value itself, shown only when it is the number with nothing beside it
  but office or line words ("ext. 12"); a value with anything else ("434-555-0100 Jane Doe") is refused whole, as
  the number may be that person's line.
* ``office_label(label)``: the label of any row, kept only when every word is office or page vocabulary (the same
  test, with page words such as "portal" and "form"); otherwise None, and the page shows the row's kind instead.
* ``office_value(value)``: an office or postal value, with every piece the checks cannot account for dropped.  A
  piece (a line, or a part of one between commas, colons or dashes, or from an "Attn"/"c/o" marker on) is kept only
  when every word in it, before and after any number, is office vocabulary (titles included), address or line
  vocabulary (room, suite, P.O. box, fax, ext.), office hours (am, pm, Monday, through, appointment) or a joining
  word; or when it is a city before a state and ZIP code, a state and ZIP code, or an "Attn:"/"c/o" piece that
  names an office or a title.  Any other piece, such as a staff name before or after a room number, P.O. box or
  phone number, is dropped.  Two kinds of text are kept without being checked: a street's name between a house
  number and a street type ("123 Main St"; streets are often named after people; an address with no street type
  word, such as "100 Broadway", is dropped), and the short piece before a state and ZIP code (the city).  A name
  made only of office or address words ("Page Law") cannot be told apart by any shape check.
* ``is_office_url(url)``: a website or page link, decoded first (``%40``, ``%7E``, HTML references), refused when
  its scheme is not http or https (``javascript:``, ``vbscript:``, ``file:``, ``data:``, ``mailto:``, ``tel:``),
  when it carries an e-mail address or a ``~``, or when a segment names a person-level page (staff, people,
  profile, team, members, directory and the like).

``is_office_channel(kind, value, label, owner=...)`` applies them by kind.  A role-shaped mailbox is still not
shown until it is found on the office's own page (section 5.2, rule 5): that needs the contact check state, so the
caller applies it (``lexflow.lab.api.state_places`` hides every mailbox without such a check).
"""
from __future__ import annotations

import html
import re
from functools import lru_cache
from typing import Iterable
from urllib.parse import unquote, urlsplit

from .municipal.states import STATES

# --------------------------------------------------------------------------- vocabularies
# Office and request words.  Titles of office-holders (mayor, manager, director, attorney, ...) are left out, and
# so are short words that are also common names (cor).  Every entry has at least two letters.
ROLE_WORDS = frozenset("""
foia foil pra cpra opra ipra kora rtk righttoknow mpia pia oig ogc sunshine transparency
records record recordsrequest openrecords publicrecords request requests inquiry inquiries questions
clerk clerks info information help helpdesk contact contactus support feedback general main mail mailbox
corporations corporation corps corp business businesses licensing license licenses licence permits permit
revenue tax taxes taxation treasury finance billing payments accounts assessment assessments assessing
appeals appeal council board boards commission commissions court courts committee
public open opengov government gov city county town village borough township state commonwealth
office offices department dept division bureau agency unit services service customer customerservice
admin administration legal law ethics compliance audit privacy ombuds
planning zoning building buildings code codes enforcement inspections inspection
police fire health water utilities utility parks recreation housing elections election voter voters vote
registration filing filings ucc notary vital communications media press news webmaster web
hr humanresources human resources jobs employment careers procurement purchasing bids
""".split())

# titles of office-holders: never a role word; in a phone label only next to "office" ("Mayor's Office")
TITLES = frozenset("""
mayor manager director attorney counsel administrator supervisor commissioner treasurer assessor sheriff chief
secretary officer custodian coordinator liaison specialist registrar auditor inspector superintendent president
chair chairman chairwoman deputy assistant executive governor
""".split())

# words that name an office or its line in a phone label
PHONE_WORDS = ROLE_WORDS | frozenset("""
line lines number numbers phone telephone tel desk hotline front switchboard reception toll free non emergency
nonemergency fax section program programs center centre food safety environmental permitting operator call central
plan review facilities facility neighborhood neighborhoods development economic community consumer protection
regulatory affairs commercial residential occupancy occupation operations licensure civic district works
""".split())

# words that name only a line, not an office: a phone label made of these alone ("Phone", "Fax", "Toll free")
# names no office
LINE_WORDS = frozenset("line lines number numbers phone telephone tel fax call toll free non hotline".split())

# allowed in a phone label but naming nothing by themselves ("City Hall", "listed on the fire pages")
PHONE_FILLER = frozenset("hall listed page pages website site see also".split())

# words a phrase needs to be an office's name ("Records Management Division", "Office of the Inspector General")
OFFICE_HEADS = frozenset("""
department dept office offices division board boards bureau commission commissions agency council committee unit
authority court courts section program center centre services service administration district clerk clerks
treasury
""".split())

# further words allowed inside an office's name (never role words of a mailbox)
OFFICE_NAME_EXTRA = frozenset("""
municipal legislative legislature reference management metropolitan regional local transportation transit motor
vehicles vehicle education library libraries aging social children youth family families natural environment
conservation agriculture labor labour industry industries insurance banking securities commerce technology
innovation personnel civil rights equal opportunity comptroller controller budget judicial affairs sanitation solid
waste streets traffic engineering probate superior circuit juvenile prosecutor solicitor defender corrections
correctional
""".split())
OFFICE_NAME_WORDS = PHONE_WORDS | TITLES | OFFICE_NAME_EXTRA

# words of the link text of a records or business page ("Right to Know", "Transparency Portal", "Starting a
# Business"), and of a row's provenance ("Email on the official website", "Official website (Wikidata Q...)")
PAGE_WORDS = frozenset("""
right know freedom act acts financial form forms policy policies portal starting start application applications
submit submitting submission apply occupational access online coverage more search official make new learn
documents document renewal renewals renew how budget budgets report reports reporting get fee fees do file files
procedure procedures view receipts receipt guidelines guideline here pay payment payments transparent pdf data your
obtain cost costs accountability about click find participation employer rule rules summary use download notice
notices process email address addresses website websites census wikidata grama laws statute statutes requesting
requirements checklist mailing postal box person
""".split())
LABEL_WORDS = OFFICE_NAME_WORDS | PHONE_FILLER | PAGE_WORDS

# joining words: allowed anywhere, naming nothing
STOP = frozenset("of the and for to a an in on at by or".split())
FILLER = frozenset("is are be this that with from via if as it its also only all any per not no you we our us can "
                   "may will".split())

# a label with any of these is a person's line, whatever else it says
PERSON_MARKERS = frozenset("direct cell cellular personal private pager my".split())
# ... and these when they describe the line ("home phone", "Mobile: ..."), not a permit ("mobile food unit")
PERSON_LINE_MARKERS = frozenset("home mobile".split())
_LINE = frozenset("phone line number tel telephone".split())

# the words that end a street's name in an address ("123 Main St"): only the words between a house number and one
# of these are kept unchecked, as the street's name
STREET_TYPES = frozenset("""
street st avenue ave road rd boulevard blvd drive dr lane ln way place pl court ct square sq plaza parkway pkwy
highway hwy route rte circle cir terrace ter trail trl pike turnpike alley row loop
""".split())
# the words of an address, for office values
STREET_WORDS = STREET_TYPES | frozenset("""
north south east west n s e w
ne nw se sw p o po box drawer suite ste room rm floor fl level wing annex unit building bldg hall center centre
tower mall campus complex lobby basement ground first second third fourth fifth sixth seventh eighth ninth tenth
""".split())
# words of a phone line's number ("ext. 12", "TTY 711", "option 2")
NUMBER_WORDS = frozenset("ext extension x tty tdd option options dial".split())
# words of an office's hours ("in person 8:30 am to 4:30 pm, Monday through Friday, by appointment")
HOURS_WORDS = frozenset("""
am pm noon hours hour daily weekday weekdays monday tuesday wednesday thursday friday saturday sunday mon tue tues
wed thu thur thurs fri sat sun through thru until till except closed holidays holiday appointment appointments lunch
walk walkin
""".split())
# a number after one of these is a room, box or line number, never a house number that a street name follows
UNIT_WORDS = frozenset("""
room rm suite ste box drawer floor fl level unit apt wing building bldg no num number phone tel telephone fax
""".split()) | NUMBER_WORDS
VALUE_WORDS = LABEL_WORDS | STREET_WORDS | FILLER | NUMBER_WORDS | HOURS_WORDS

# what "City of", "County" and the like add to a government's name: left out of its core name
_NAME_FURNITURE = re.compile(r"\b(city|county|town|village|borough|township|parish|of|the|government|"
                             r"consolidated|unified|metropolitan|municipality|charter|independent)\b", re.I)


# --------------------------------------------------------------------------- tokens
def local_tokens(local: str) -> list[str]:
    """The tokens of a mailbox's local part, lower-cased, digit tokens left out.

    >>> local_tokens("CorpHelp"), local_tokens("foia.appeals"), local_tokens("kwaters77")
    (['corp', 'help'], ['foia', 'appeals'], ['kwaters'])
    """
    out = []
    for part in re.split(r"[._+\-]+", local or ""):
        # an upper-case run before a capitalised word (FOIARequests), a capitalised or lower-case word, an upper-case
        # run, or digits: so a lower-to-upper change and a letter/digit change both split
        for t in re.findall(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|\d+", part):
            if not t.isdigit():
                out.append(t.lower())
    return out


def _cut(token: str, words: frozenset, min_piece: int = 2) -> list[str] | None:
    """``token`` cut into pieces that are all in ``words`` (fewest pieces), or None when something is left over.
    Each piece has at least ``min_piece`` letters."""
    n = len(token)
    best: list[list[str] | None] = [None] * (n + 1)
    best[0] = []
    for i in range(n):
        if best[i] is None:
            continue
        for j in range(i + min_piece, n + 1):
            piece = token[i:j]
            if piece in words and (best[j] is None or len(best[i]) + 1 < len(best[j])):
                best[j] = best[i] + [piece]
    return best[n]


def _words(text: str) -> list[str]:
    return [w.lower() for w in re.findall(r"[A-Za-z]+", re.sub(r"'s\b", "", text or ""))]


# An initialism counts only with this many letters or more.  Two letters are also a person's initials: "cc@" for the
# City of Charlottesville, or "Clerk's Office - CC", could as well be a member of staff's (a conservative choice).
MIN_INITIALS = 3


def _initialisms(name: str) -> set[str]:
    """``Metropolitan Police Department`` -> {"mpd"}; ``Office of the Inspector General (OIG)`` -> {"oig", "ootig"}.
    Never one of fewer than ``MIN_INITIALS`` letters (``City of Charlottesville`` gives "coc", not "cc")."""
    out = set()
    words = re.findall(r"[A-Za-z]+", name or "")
    for keep_stop in (False, True):
        ws = [w for w in words if keep_stop or w.lower() not in STOP]
        if len(ws) >= 2:
            out.add("".join(w[0] for w in ws).lower())
    out |= {a.lower() for a in re.findall(r"\b[A-Z]{2,}\b", name or "")}
    return {i for i in out if len(i) >= MIN_INITIALS}


def _leading_office(label: str | None) -> str:
    """The phrase that starts a row's label ("Records Management Division - FOIA" -> "Records Management
    Division")."""
    return re.split(r"\s[-–—:|]\s|[,;(:]", label or "", maxsplit=1)[0].strip()


def is_office_name(phrase: str | None, owner_words: Iterable[str] = (), owner_inits: Iterable[str] = ()) -> bool:
    """Whether a phrase is an office's name: it has an office word (department, office, division, board, ...) and
    every other word is office vocabulary, a joining word, or the owner's own name or initials.  A person's name
    ("Jane Doe", "MARY SMITH Records Division") is not one.

    >>> is_office_name("Board of Municipal and Zoning Appeals"), is_office_name("Jane Doe")
    (True, False)
    """
    owner_words, owner_inits = set(owner_words), set(owner_inits)
    content = [w for w in _words(phrase or "") if w not in STOP]
    if not content or not any(w in OFFICE_HEADS for w in content):
        return False
    return all(w in OFFICE_NAME_WORDS or w in owner_words or w in owner_inits for w in content)


@lru_cache(maxsize=4096)
def _context(names: tuple[str, ...], label: str = "") -> tuple[frozenset, frozenset]:
    """(initialisms, owner words) for an owner's names (its full name, its core name, aliases) and for the office
    name that starts the row's label.  The label gives initials only when its leading phrase is an office name
    (``is_office_name``).  That phrase's length is not known ("Department of Housing and Community Development MPIA
    requests"), so each run of its first words gives an initialism ("dhcd").  None has fewer than
    ``MIN_INITIALS`` letters."""
    inits: set[str] = set()
    owner: set[str] = set()
    for name in names:
        if not name:
            continue
        core = re.sub(r"\s+", " ", _NAME_FURNITURE.sub(" ", name)).strip()
        for n in {name, core}:
            inits |= _initialisms(n)
        # only the owner's own name gives words: a label's words could include a person's name
        owner |= {w for w in _words(name) if len(w) >= 3 and w not in STOP and w not in TITLES}
    lead = _leading_office(label)
    if lead and is_office_name(lead, owner, inits):
        inits |= _initialisms(lead)
        words = [w for w in re.findall(r"[A-Za-z]+", lead) if w.lower() not in STOP]
        inits |= {"".join(w[0] for w in words[:k]).lower() for k in range(2, len(words) + 1)}
    return frozenset(i for i in inits if len(i) >= MIN_INITIALS), frozenset(owner)


def _names(owner: str | Iterable[str] | None) -> tuple[str, ...]:
    if owner is None:
        return ()
    if isinstance(owner, str):
        return (owner,)
    return tuple(n for n in owner if n)


# --------------------------------------------------------------------------- mailboxes
def mailbox_shape(address: str, owner: str | Iterable[str] | None = None, label: str | None = None) -> str:
    """``"role"`` (role-shaped) or ``"personal"`` (personal-looking) for an e-mail address, by the whole-token rule.

    ``owner`` is the office's own name (or several: its name, aliases); ``label`` is the row's label, whose leading
    phrase also gives initials when it is an office name.
    """
    local = (address or "").split("@", 1)[0].strip()
    tokens = local_tokens(local)
    if not tokens:
        return "personal"
    inits, owner_words = _context(_names(owner), label or "")
    pieces_ok = ROLE_WORDS | owner_words
    role_seen = False
    for t in tokens:
        if t in TITLES:
            return "personal"
        if t in ROLE_WORDS or t in inits:
            role_seen = True
            continue
        if t in owner_words:
            continue                        # a word of the owner's name: allowed beside a role word, never alone
        pieces = _cut(t, pieces_ok)
        if pieces is None:
            return "personal"
        role_seen = role_seen or any(p in ROLE_WORDS for p in pieces)
    return "role" if role_seen else "personal"


def is_office_mailbox(address: str, owner: str | Iterable[str] | None = None, label: str | None = None) -> bool:
    """Whether an e-mail address is role-shaped (an office mailbox) rather than personal-looking.  Role-shaped is
    necessary, not sufficient: section 5.2 rule 5 also asks that it be found on the office's own page.

    >>> is_office_mailbox("publicrecords@example.gov"), is_office_mailbox("pia.jones@example.gov")
    (True, False)
    """
    return mailbox_shape(address, owner, label) == "role"


# --------------------------------------------------------------------------- labels
def _person_line(words: list[str]) -> bool:
    """A direct-line marker, or "home"/"mobile" describing the line ("home phone", "Mobile" at the end)."""
    if any(w in PERSON_MARKERS for w in words):
        return True
    return any(w in PERSON_LINE_MARKERS and (i + 1 == len(words) or words[i + 1] in _LINE)
               for i, w in enumerate(words))


def is_office_phone(label: str | None, owner: str | Iterable[str] | None = None) -> bool:
    """Whether a phone number's label names an office line.  A number without a label is never shown, and a label
    is accepted only when every word is office vocabulary, the owner's own name, an initialism (three letters or
    more) of the owner or of the office name that starts the label, or a short joining word, and at least one word
    names an office (not only a line: "Phone" and "Fax" are refused).  An upper-case word counts only when it is one
    of those, never on its shape ("Clerk's Office - MARY SMITH" and "Clerk's Office - CC" are refused).  The number
    itself is checked by ``office_phone_value``.  A title (Director, FOIA Officer) counts only beside the word
    "office"; a direct-line marker (direct, cell, "home phone", "Mobile:") refuses the label outright.

    >>> is_office_phone("Business Licensing Division"), is_office_phone("FOIA Officer"), is_office_phone(None)
    (True, False, False)
    """
    words = _words(label or "")
    if not words or _person_line(words):
        return False
    inits, owner_words = _context(_names(owner), label or "")
    has_office = "office" in words or "offices" in words
    named = False
    for w in words:
        if w in STOP or w in owner_words or w in inits or w in PHONE_FILLER:
            continue
        if w in PERSON_LINE_MARKERS:            # "home occupation", "mobile food unit": a permit, not a line
            continue
        if w in TITLES:
            if not has_office:
                return False
            continue
        pieces = [w] if w in PHONE_WORDS else _cut(w, PHONE_WORDS)
        if pieces is None:
            return False                        # a word outside the vocabulary, such as a person's name
        named = named or any(p not in LINE_WORDS for p in pieces)
    return named


def office_label(label: str | None, owner: str | Iterable[str] | None = None) -> str | None:
    """A row's label when it can be shown: every word is office or page vocabulary ("Public Records Request",
    "Email on the official website"), a joining word, the owner's own name, or an initialism of the owner or of the
    office name that starts the label; a title only beside "office"; no direct-line marker.  Otherwise None (a
    label such as "Jane Doe, FOIA Officer" is dropped, and the row is shown under its kind).  Wikidata item ids
    ("Q12345") are ignored.

    >>> office_label("Public Records Request"), office_label("Jane Doe, FOIA Officer")
    ('Public Records Request', None)
    """
    if not label or not label.strip():
        return None
    words = _words(re.sub(r"\bQ\d+\b", " ", label))
    if not words or _person_line(words):
        return None
    inits, owner_words = _context(_names(owner), label)
    has_office = "office" in words or "offices" in words
    for w in words:
        if w in STOP or w in FILLER or w in owner_words or w in inits:
            continue
        if w in TITLES:
            if not has_office:
                return None
            continue
        if w in LABEL_WORDS or _cut(w, LABEL_WORDS) is not None:
            continue
        return None
    return label


# --------------------------------------------------------------------------- office values
_CODES = "|".join(s.upper() for s, _, _ in STATES)
_STATE_NAMES = "|".join(re.escape(n) for _, _, n in sorted(STATES, key=lambda s: -len(s[2])))
_STATE = rf"(?:(?:{_CODES})|(?i:{_STATE_NAMES}))\.?"
_ZIP = r"\d{5}(?:-\d{4})?"
_ST_ZIP = re.compile(rf"^\s*{_STATE}(?:\s+{_ZIP})?\s*$")
_CITY_ST_ZIP = re.compile(rf"^\s*[A-Za-z][A-Za-z.'\- ]{{0,40}}?\s+{_STATE}\s+{_ZIP}\s*$")
_ATTN = re.compile(r"^\s*(?:attn\.?|attention|c/o|care\s+of)\s*:?\s*", re.I)
# pieces are split at commas, bars, spaced dashes and colons (not a time's), and before an "Attn" or "c/o" marker
# inside a line ("P.O. Box 911 Attn Jane Doe")
_PART_SEP = re.compile(r"(\s*[,|]\s*|\s+[-–—]\s+|(?<!\d):(?!\d)\s*"
                       r"|\s+(?=(?i:attn\b|attention\b|c/o\b|care\s+of\b)))")
_PAREN = re.compile(r"\s*\(([^()]*)\)")
# a phone number (NANP), found in a piece before it is cut into tokens
_PHONE_NUM = re.compile(r"(?<!\d)(?:\+?1[\s.\-]*)?\(?\d{3}\)?[\s.\-]*\d{3}[\s.\-]*\d{4}(?!\d)")
# a token that is a number: digits, with at most one letter or "#" before them and two letters after ("B100",
# "#200", "x12", "605A", "2nd", "22902-1234")
_NUMBER = re.compile(r"^[#(]?[A-Za-z]?\.?\d[\d\-./]*[A-Za-z]{0,2}[).,;:]*$")
_HOUSE = re.compile(r"^\d{1,6}[A-Za-z]?(?:-\d{1,6}[A-Za-z]?)?[.,]?$")
_ORDINAL = re.compile(r"^\d{1,4}(?:st|nd|rd|th)[.,]?$", re.I)
STREET_NAME_MAX = 5         # words between a house number and its street type ("Martin Luther King Jr Blvd")


def _vocab(text: str, owner_words: frozenset) -> bool:
    """Whether every word of ``text`` is value vocabulary, a joining word or the owner's own name.  A run-together
    word ("cityhall") is cut only into pieces of three letters or more, since the address abbreviations (st, ne,
    rd, ...) would otherwise assemble names ("Wayne" = way + ne)."""
    text = re.sub(r"\b([AaPp])\.\s?[Mm]\.?", r"\1m", text or "")        # "8:30 a.m." -> "8:30 am"
    return all(w in VALUE_WORDS or w in STOP or w in owner_words or _cut(w, VALUE_WORDS, 3) is not None
               for w in _words(text))


def _value_tokens(piece: str) -> list[tuple[str, str]]:
    """A piece's tokens as (kind, text): ``phone`` (a whole phone number), ``num`` (a number token) or ``word``.  A
    token that mixes letters and digits in any other way ("Box911", "Doe123") is cut into its letter and digit
    runs, so its letters are checked as words."""
    def plain(s: str) -> list[tuple[str, str]]:
        out = []
        for t in s.split():
            if not re.search(r"\d", t):
                out.append(("word", t))
            elif _NUMBER.match(t):
                out.append(("num", t))
            else:
                out += [("num" if re.search(r"\d", r) else "word", r) for r in re.findall(r"[A-Za-z']+|[^A-Za-z']+", t)]
        return out
    toks, pos = [], 0
    for m in _PHONE_NUM.finditer(piece):
        toks += plain(piece[pos:m.start()])
        toks.append(("phone", m.group()))
        pos = m.end()
    return toks + plain(piece[pos:])


def _house_number(toks: list[tuple[str, str]], i: int) -> bool:
    """Whether token ``i`` can be a house number: a number of house shape that does not follow a phone number or a
    room, suite, box or line word ("Room 200 ..." is a room number, so no street name may follow it)."""
    kind, t = toks[i]
    if kind != "num" or not _HOUSE.match(t):
        return False
    if i == 0:
        return True
    pk, pt = toks[i - 1]
    if pk == "phone":
        return False
    if pk == "word":
        ws = _words(pt)
        return bool(ws) and not any(w in UNIT_WORDS for w in ws)
    return True                                 # after another number ("Suite 200 123 Main St")


def _street_type_after(toks: list[tuple[str, str]], i: int) -> int | None:
    """The index of the street type that ends the street name after house number ``i`` ("123 Main St": the "St"),
    at most ``STREET_NAME_MAX`` words on; None when there is none (then no word is let through as a street name)."""
    for k in range(i + 1, min(i + 2 + STREET_NAME_MAX, len(toks))):
        kind, t = toks[k]
        if kind == "word":
            ws = _words(t)
            if len(ws) == 1 and ws[0] in STREET_TYPES:
                return k
        elif not (kind == "num" and _ORDINAL.match(t)):    # "120 7th Street" has a number in its name
            return None
    return None


def _part_ok(part: str, next_part: str, owner_words: frozenset) -> bool:
    """Whether one piece of an office value can be kept (see ``office_value``).  Every word is checked, before and
    after any number, except a street's name between a house number and its street type."""
    p = part.strip()
    if not p:
        return True
    m = _ATTN.match(p)
    if m:                                       # "Attn: Records Custodian" stays; "Attn: Jane Doe" goes
        rest = p[m.end():]
        return bool(_words(rest)) and _vocab(rest, owner_words)
    if _ST_ZIP.match(p) or _CITY_ST_ZIP.match(p):
        return True
    toks = _value_tokens(p)
    if all(kind == "word" for kind, _ in toks):  # no number: office words, or a city before a state
        return _vocab(p, owner_words) or (bool(_ST_ZIP.match(next_part or "")) and len(_words(p)) <= 4)
    i = 0
    while i < len(toks):
        kind, t = toks[i]
        if _house_number(toks, i):
            end = _street_type_after(toks, i)
            if end is not None:                 # the street's name is part of the address, kept unchecked
                i = end + 1
                continue
        if kind == "word" and not _vocab(t, owner_words):
            return False                        # "Room 200 Jane Doe", "434-555-0100 Jane Doe", "123 Main St Jane Doe"
        i += 1
    return True


def _clean_line(line: str, owner_words: frozenset) -> str:
    """A line with its unaccountable pieces (and parenthesised remarks) dropped; '' when nothing is left."""
    def paren(m):
        inner = m.group(1)
        return m.group(0) if not _words(inner) or _vocab(inner, owner_words) else ""
    text = _PAREN.sub(paren, line)
    bits = _PART_SEP.split(text)
    parts, seps = bits[0::2], [""] + bits[1::2]
    # an "Attn" or "c/o" marker split off by its colon goes back with what it introduces
    merged: list[tuple[str, str]] = []
    for sep, part in zip(seps, parts):
        if merged and re.fullmatch(r"\s*(?:attn\.?|attention|c/o|care\s+of)\s*", merged[-1][1], re.I):
            merged[-1] = (merged[-1][0], merged[-1][1] + sep + part)
        else:
            merged.append((sep, part))
    out = []
    for i, (sep, part) in enumerate(merged):
        nxt = merged[i + 1][1] if i + 1 < len(merged) else ""
        if _part_ok(part, nxt, owner_words):
            out.append((sep if out else "") + part)
    return "".join(out).strip()


def office_value(value: str | None, owner: str | Iterable[str] | None = None) -> str | None:
    """An office or postal value with every piece the checks cannot account for dropped (section 5.2: "Attn: Records
    Custodian" stays; a line naming a person goes, and so does a staff name anywhere else in the value).  Lines are
    split at newlines and semicolons, and each line into pieces at commas, colons, dashes and before an "Attn" or
    "c/o" marker.  A piece is kept only when every word in it, before and after any number, is office vocabulary
    (titles and the owner's own name included), address or line vocabulary ("Room", "Suite", "P.O. Box", "fax",
    "ext."), office hours ("8:30 a.m. to 4:30 p.m., Monday through Friday") or a joining word; a run-together word
    is cut only into vocabulary pieces of three letters or more.  So "Room 200", "P.O. Box 911", "605 E Main St"
    and "Main line 434-555-0100 ext. 12" stay, and "Room 200 Jane Doe", "P.O. Box 911 Attn Jane Doe" (its Attn
    piece), "434-555-0100 Jane Doe" and "123 Main St Jane Doe" go.  A city before a state and ZIP code, and a state and ZIP code, are kept; an "Attn:" or
    "c/o" piece is kept when it names an office or a title, and a parenthesised remark when it is office
    vocabulary.  Two kinds of text are kept without knowing what they are: a street's name, the words (at most
    ``STREET_NAME_MAX``) between a house number and a street type such as St or Ave (streets are often named after
    people; an address whose street has no such type word is dropped), and a short piece just before a state and
    ZIP code, as the city.  A name made only of office or address words cannot be told apart.  The value comes back
    unchanged when nothing is dropped, and None when nothing is left.

    >>> office_value("Jane Doe, Records Custodian\\nP.O. Box 2"), office_value("City Hall Room 101 Jane Doe, Clerk")
    ('Records Custodian\\nP.O. Box 2', 'Clerk')
    """
    if not value or not value.strip():
        return None
    _, owner_words = _context(_names(owner))
    bits = re.split(r"(\r?\n|;\s*)", value)
    out, changed = [], False
    for i in range(0, len(bits), 2):
        line, sep = bits[i], bits[i + 1] if i + 1 < len(bits) else ""
        if not line.strip():
            continue
        kept = _clean_line(line, owner_words)
        changed = changed or kept != line.strip()
        if kept:
            out.append(kept + sep)
    if not changed:
        return value
    kept = "".join(out).strip().rstrip(";").strip()
    return kept or None


def office_phone_value(value: str | None, owner: str | Iterable[str] | None = None) -> str | None:
    """A phone row's value when it can be shown: it has a number, and ``office_value`` keeps all of it ("434-555-0100",
    "Main line (434) 970-3000 ext. 12").  Anything else beside the number refuses the whole value, not only that
    text: "434-555-0100 Jane Doe" or "Jane Doe: 434-555-0100" may be that person's own line.

    >>> office_phone_value("434-555-0100"), office_phone_value("434-555-0100 Jane Doe")
    ('434-555-0100', None)
    """
    if not value or len(re.findall(r"\d", value)) < 3:
        return None
    return value if office_value(value, owner) == value else None


# --------------------------------------------------------------------------- links
# a path segment of a staff, people or profile page (CivicPlus "Directory.aspx?EID=..." is a staff entry)
_PERSON_PATH = re.compile(r"(?:^|[/_.\-=&?\s])(?:staff|people|employees?|profiles?|bios?|biography|team|users?|"
                          r"members?|directory)(?:[/_.\-=&?#\s]|$)", re.I)
_SCHEME = re.compile(r"^([A-Za-z][A-Za-z0-9+.\-]*):")


def _decoded(text: str) -> str:
    """``text`` with its percent-escapes and HTML character references undone, repeatedly (``%2540`` -> ``@``)."""
    for _ in range(5):
        d = unquote(html.unescape(text))
        if d == text:
            break
        text = d
    return text


def is_office_url(url: str | None) -> bool:
    """Whether a website or page link may be shown.  The link is first decoded (percent-escapes such as ``%40`` and
    ``%7E``, and HTML character references, however often they are nested).  It is refused when it has a scheme
    other than ``http`` or ``https`` (``mailto:``, ``tel:``, ``javascript:``, ``vbscript:``, ``data:``, ``file:``,
    ``ftp:``, ...; tabs, newlines and spaces inside the scheme are ignored, as browsers ignore them), when it
    carries an e-mail address or a ``~`` anywhere (``?to=jane.doe%40example.gov``, ``/%7Ejdoe/``), or when a path,
    query or fragment segment names a person-level page (staff, people, employee(s), profile(s), bio(s), biography,
    team, user(s), member(s), directory).  A link without a scheme (``www.example.gov/foia``) is read as a host and
    path.  A refused link is left out, and the page points to the government's own website instead.

    >>> is_office_url("https://example.gov/foia"), is_office_url("https://example.gov/staff/jane-doe")
    (True, False)
    """
    raw = (url or "").strip()
    if not raw:
        return False
    u = _decoded(raw)
    m = _SCHEME.match(re.sub(r"[\x00-\x20\x7f]+", "", u))
    if m and m.group(1).lower() not in ("http", "https"):
        return False
    if "@" in u or "~" in u:
        return False
    parts = urlsplit(u if "//" in u else "//" + u)
    return not _PERSON_PATH.search(f"{parts.path}?{parts.query}#{parts.fragment}")


# the words of the source tags lexflow's writers set ("census-gus-2022", "site-scan", "wikidata", "local-research")
SOURCE_WORDS = frozenset("census gus site scan wikidata local research curated crawl import csv agency seed manual "
                         "reviewer places official page home pilot govdirectory".split())


def office_source(source: str | None) -> str | None:
    """A row's source when it can be shown: a writer's tag made of known words and digits ("census-gus-2022",
    "site-scan"), or a link that ``is_office_url`` accepts.  Otherwise None.

    >>> office_source("census-gus-2022"), office_source("jane-doe")
    ('census-gus-2022', None)
    """
    s = (source or "").strip()
    if re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+){0,5}", s):
        return s if all(p.isdigit() or p in SOURCE_WORDS for p in s.split("-")) else None
    return s if s.lower().startswith(("http://", "https://")) and is_office_url(s) else None


def is_office_channel(kind: str, value: str | None, label: str | None = None,
                      owner: str | Iterable[str] | None = None) -> bool:
    """Whether a contact row passes the shape checks: websites and pages that ``is_office_url`` accepts; office
    and postal values that ``office_value`` can keep; e-mail only when role-shaped (section 5.2 rule 5, found on the
    office's own page, is the caller's to apply); phone only with an office label and a value that
    ``office_phone_value`` keeps whole.  Any other kind (``person`` included) is refused.  The label is checked
    separately (``office_label``)."""
    if kind in ("website", "page"):
        return is_office_url(value)
    if kind in ("office", "postal"):
        return office_value(value, owner) is not None
    if kind == "email":
        return is_office_mailbox(value or "", owner, label)
    if kind == "phone":
        return is_office_phone(label, owner) and office_phone_value(value, owner) is not None
    return False
