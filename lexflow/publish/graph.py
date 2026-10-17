"""A neutral, in-memory build of everything docs/design/wikibase-schema.md section 4 describes, with no wiki ids.

``build(con)`` reads the live database and the fixtures and returns ``Item`` objects whose claims name properties
by LABEL and other items by KEY (``Value(kind='item', value='lexflow:…')``); vocabulary and class targets are keys
too.  ``qs.py`` turns them into QuickStatements and ``rdf.py`` into Turtle, resolving keys to ids there.  Nothing
here writes anywhere or touches the network.

Sources: the statute indexes (path, act_id, effective dates, headings) for codes, units and sections;
``process_models`` (reviewed and agreed in full, single as drafts); ``fixtures/authority/ladders.json`` for rungs
and bodies; ``fixtures/entities/agencies.json`` for agencies (exact, kind-checked matches only);
``caselaw.COURTS`` for courts, named from ``fixtures/entities/courts.json``; ``place_processes`` verified rows for
local processes, with ``fixtures/places/topics.json`` for the topic and audience of those whose category
``schema.CATEGORY_TOPIC`` does not map; ``contacts`` for office channels, after ``lexflow.privacy``; ``case_law``
for court decisions; ``states.py`` for the jurisdictions.  With ``LEXFLOW_DECIDE=1`` the decision model
(``extract/decide.py``) gives a local step its kind where the file gives none and the model is sure.

Rules kept here: every claim made from a quote carries the grounding reference of section 4.6 (source section or
URL, pinpoint, quoted text, determination method); words from ``quotes.NO_REPRINT`` hosts never enter a Value;
no Value carries a personal-looking mailbox; labels and descriptions are at most 250 characters and strings 400;
the result is in sorted key order so re-runs diff cleanly.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Literal

from .. import config, privacy
from ..extract import decide as DEC
from ..municipal import states as S
from ..municipal.caselaw import COURTS
from ..municipal.questions import QUESTIONS
from ..municipal import quotes as QT
from ..store import db
from . import schema as SC

Log = Callable[[str], None]
# fixtures/places/topics.json: a decision model's topic and audience for the place processes whose category
# CATEGORY_TOPIC does not map (scripts/assign_topics.py); an entry is used when a person accepted it or the model's
# confidence reached this
TOPIC_CONFIDENCE = 0.9
ValueKind = Literal["item", "string", "url", "time", "quantity", "monolingual", "external-id"]


@dataclass
class Value:
    kind: ValueKind
    value: str
    unit: str | None = None               # quantity: the unit item's key
    lang: str | None = None               # monolingual: the language
    precision: int = 11                   # time: 11 day, 10 month, 9 year

    def sig(self) -> tuple:
        return (self.kind, self.value, self.unit, self.lang, self.precision)


@dataclass
class Claim:
    prop: str                             # property LABEL, never an id
    value: Value
    qualifiers: list[tuple[str, Value]] = field(default_factory=list)
    references: list[list[tuple[str, Value]]] = field(default_factory=list)


@dataclass
class Item:
    key: str
    label: str
    description: str
    aliases: list[str]
    cls: str | None                       # class key, or the label of an existing class item (Q7 ...)
    claims: list[Claim]
    exists: bool                          # wikibase_items already holds the key: the writer updates


def by_kind(items: list[Item]) -> dict[str, list[Item]]:
    out: dict[str, list[Item]] = {}
    for it in items:
        out.setdefault(SC.kind_of(it.key), []).append(it)
    return out


# --------------------------------------------------------------------------- values


def _cut(s: str, n: int) -> str:
    s = re.sub(r"\s+", " ", (s or "")).strip()
    return s if len(s) <= n else s[:n - 1].rstrip() + "…"


def item(key: str) -> Value:
    return Value("item", key)


def string(s: str) -> Value:
    return Value("string", _cut(s, SC.STRING_MAX))


def url(u: str) -> Value:
    return Value("url", (u or "").strip())


def ext(s: str) -> Value:
    return Value("external-id", str(s).strip())


def mono(s: str, lang: str = "en") -> Value:
    return Value("monolingual", _cut(s, SC.STRING_MAX), lang=lang)


def quantity(n, unit: str | None = None) -> Value:
    v = f"{n:g}" if isinstance(n, float) else str(n)
    return Value("quantity", v, unit=unit)


def time(date: str | None) -> Value | None:
    """``2026-10-10``, ``2026-10-10T12:00:00Z`` or ``2026`` -> a time value with the right precision."""
    s = (date or "").strip()[:10]
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return Value("time", s, precision=11)
    if re.fullmatch(r"\d{4}-\d{2}", s):
        return Value("time", s + "-00", precision=10)
    if re.fullmatch(r"\d{4}", s):
        return Value("time", s + "-00-00", precision=9)
    return None


_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_URL = re.compile(r"^(?:https?://[^\s/?#]+[^\s]*|mailto:[^\s@]+@[^\s@]+)$", re.I)
_CITE = re.compile(r"§|\bILCS\b|\bRCW\b|\bStat\.|\bCode\b")


def personal_mailbox(text: str | None, owner=None) -> str | None:
    """The first personal-looking mailbox in a text (``privacy.is_office_mailbox`` refuses it), or None."""
    for m in _EMAIL.findall(text or ""):
        if not privacy.is_office_mailbox(m, owner):
            return m
    return None


_ARCHIVE = re.compile(r"^https?://web\.archive\.org/web/[^/]+/(https?://.*)$", re.I)


def no_reprint(source_url: str | None) -> bool:
    """Whether words read from ``source_url`` may not be written: the page's host is in ``quotes.NO_REPRINT``, or
    the page is an Internet Archive capture of such a host (the words are still that site's)."""
    u = (source_url or "").strip()
    if not u:
        return False
    m = _ARCHIVE.match(u)
    return bool(QT.policy(u) or (m and QT.policy(m.group(1))))


def first_url(text: str | None) -> str | None:
    """The first absolute http(s) URL in a text (``Albemarle County Code § 15-501; https://…pdf`` -> the URL)."""
    m = re.search(r"https?://[^\s<>\"']+", text or "")
    return m.group(0).rstrip(".,;)") if m else None


_BASIS = re.compile(r"^[^\d§]{0,60}?§*\s*(\d[\w.\-/]*?)((?:\s*\([^()]{1,8}\))*)(?=[\s;,:)]|$)")


def basis_slug(basis: str | None) -> str:
    """The ``<section-slug>`` of a local rung's key from a researched process's free-text ``basis``: the leading
    section number with its pinpoints, lower-cased (``58.1-3984(A) (circuit court; https://…)`` ->
    ``58.1-3984-a``, ``12VAC30-110-160`` -> ``12vac30-110-160``); ``local`` when the basis starts with no number
    (a page, a policy, a notice)."""
    b = (basis or "").replace("�", "§").strip()
    if not b or _URL.match(b):
        return "local"
    m = _BASIS.match(b)
    if not m:
        return "local"
    pins = [p.strip().lower() for p in _PIN.findall(m.group(2) or "")]
    parts = [m.group(1).lower().rstrip(".")] + [re.sub(r"[^a-z0-9.]+", "-", p).strip("-") for p in pins]
    return "-".join(p for p in parts if p) or "local"


_PIN = re.compile(r"\(([^()]+)\)")


def vocab(set_: str, slug_: str) -> Value:
    return item(SC.vocab_key(set_, slug_))


def cls(slug_: str) -> str:
    return SC.class_key(slug_)


# --------------------------------------------------------------------------- text helpers

_WORDS = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
          "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
          "sixteen": 16, "eighteen": 18, "twenty": 20, "twenty-one": 21, "twenty-four": 24, "thirty": 30,
          "forty": 40, "forty-five": 45, "forty-eight": 48, "sixty": 60, "seventy-two": 72, "ninety": 90,
          "one hundred twenty": 120, "one hundred eighty": 180}
_ORDINALS = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6, "seventh": 7, "eighth": 8,
             "ninth": 9, "tenth": 10, "eleventh": 11, "fourteenth": 14, "fifteenth": 15, "twentieth": 20,
             "thirtieth": 30}
_NUMBER = r"(\d+|" + "|".join(re.escape(w) for w in sorted(list(_WORDS) + list(_ORDINALS), key=len, reverse=True)) + r")"
_LEAD = r"(within|in|no later than|not later than|no more than|not more than|up to|after|at least|not less than)"
_QUAL = r"(business|working|work|calendar)?"
_UNIT = r"(days?|hours?|weeks?|months?|years?)"
_FROM = r"(of|after|from|following|before|prior to|preceding)"
_ANCHOR = r"(?:\s+" + _FROM + r"\s+([^.;:]{3,120}))?"
# "within 30 days of X", "no later than 10 business days after X", "not later than 45 days before X"
_LIMIT = re.compile(r"\b" + _LEAD + r"\s+(?:the\s+)?" + _NUMBER + r"\s*(?:\(\d+\)\s*)?" + _QUAL + r"[\s-]*" +
                    _UNIT + r"\b" + _ANCHOR, re.I)
# no lead word: "5 working days", "10 business days after X", "the third day after the election" (a count of
# plain days with no anchor word after it is not read: "4 months of age" is no limit)
_BARE = re.compile(r"\b(?:the\s+)?" + _NUMBER + r"(?:st|nd|rd|th)?\s*(?:\(\d+\)\s*)?" + _QUAL + r"[\s-]*" + _UNIT +
                   r"\b" + _ANCHOR, re.I)
_NEXT_DAY = re.compile(r"\b(?:the\s+)?(?:next|following)\s+(business|working|work|calendar)?\s*day\b", re.I)
_MONEY = re.compile(r"\$\s?(\d{1,3}(?:,\d{3})*|\d+)(?:\.(\d{1,2}))?")
_CENTS = re.compile(r"\b(\d+|[a-z]+(?:-[a-z]+)?)\s+(cents?|dollars?)\b", re.I)
# a fee of nothing: "No fee", "No license tax", "Free", "None"; never "None stated" or "No late penalties"
_NO_FEE = re.compile(r"^\s*(?:no\s+(?:\w+\s+){0,2}(?:fees?|tax|charge|cost|costs)|none|free(?:\s+of\s+charge)?|"
                     r"no\s+charge|without\s+charge|at\s+no\s+cost|nothing)\b(?:\s*[(.;,:]|\s*$|\s+(?:for|when|if|unless|"
                     r"to|while|in|on|at|under|where|except|other|allowed|once|after|before|until|during|only|with)\b)", re.I)


def _amount(word: str) -> int | None:
    w = re.sub(r"\s+", " ", word.lower().strip())
    if w.isdigit():
        return int(w)
    return _WORDS.get(w, _ORDINALS.get(w))


def _unit_slug(qual: str | None, unit: str) -> str:
    qual, unit = (qual or "").lower(), unit.lower().rstrip("s")
    if unit == "day":
        return {"business": "business-days", "working": "working-days", "work": "work-days"}.get(qual, "calendar-days")
    return unit + "s"


def _anchor(s: str | None) -> str | None:
    """The event a limit runs from, without a trailing remark or citation (``receiving a request (USBC § 119``
    -> ``receiving a request``)."""
    a = re.split(r"\s+\(", (s or "").strip(), maxsplit=1)[0].strip(" ,")
    return a or None


def parse_limit(text: str | None) -> tuple[int, str, str | None] | None:
    """A local deadline text as ``(amount, time-unit slug, counted from)``: ``"within three business days of
    receiving a request"`` -> ``(3, 'business-days', 'receiving a request')``; ``"no later than 10 business days
    after the hearing"`` -> ``(10, 'business-days', 'the hearing')``; ``"5 working days"`` -> ``(5,
    'working-days', None)``; ``"the next business day"`` -> ``(1, 'business-days', None)``.  None when the text
    sets no such limit (a calendar date, "by the due date", "not stated")."""
    t = text or ""
    m = _LIMIT.search(t)
    if m:
        amount = _amount(m.group(2))
        if amount is not None:
            return amount, _unit_slug(m.group(3), m.group(4)), _anchor(m.group(6))
    for m in _BARE.finditer(t):
        amount = _amount(m.group(1))
        if amount is None:
            continue
        qual, anchor_word = m.group(2), (m.group(4) or "").lower()
        if qual or anchor_word in ("after", "from", "following", "before", "prior to", "preceding"):
            return amount, _unit_slug(qual, m.group(3)), _anchor(m.group(5))
    m = _NEXT_DAY.search(t)
    if m:
        return 1, _unit_slug(m.group(1), "day"), None
    return None


def parse_fee(text: str | None) -> tuple[str, str | None] | None:
    """A local fee text as ``(amount in dollars, fee basis)``: ``"$75"`` -> ``("75", None)``; ``"$25 per year"``
    -> ``("25", "$25 per year")``; ``"$0.50 per $100 of value"`` -> ``("0.50", "$0.50 per $100 of value")``;
    ``"$20 if paid within 96 hours; $40 after"`` -> ``("20", <the whole text>)``; ``"ten cents per page"`` ->
    ``("0.10", "ten cents per page")``; ``"No fee"`` -> ``("0", "No fee")``.  None when no amount can be read: a
    percentage, "the fine on the ticket", "not stated" (``"None stated"`` is not a fee of nothing)."""
    t = (text or "").strip()
    if not t:
        return None
    m = _MONEY.search(t)
    if m:
        amount = m.group(1).replace(",", "") + (f".{m.group(2)}" if m.group(2) else "")
        basis = t if t.replace(" ", "") not in (f"${amount}", f"${m.group(1)}") else None
        return amount, basis
    m = _CENTS.search(t)
    if m:
        n = _amount(m.group(1))
        if n is not None:
            amount = f"{n / 100:.2f}" if m.group(2).lower().startswith("cent") else str(n)
            return amount, t
    if _NO_FEE.match(t):
        return "0", t
    return None


# --------------------------------------------------------------------------- the build


class Build:
    def __init__(self, con, *, states=None, places=None, drafts=True, log: Log = print, decider=None):
        self.con, self.log = con, log
        self.states = sorted(S.normalise(s) for s in states) if states else None
        self.places = set(places or ())
        self.drafts = drafts
        # the decision model for the kind of a local step the file leaves without one: the one given (tests), else
        # the shared one when LEXFLOW_DECIDE=1 and a backend is pulled, else none (no step kind claim, as before)
        self.decider = decider if decider is not None else DEC.shared()
        self.items: dict[str, Item] = {}
        self.existing: set[str] = {r["key"] for r in db.rows(con, "SELECT key FROM wikibase_items")}
        self.rows: dict[tuple[str, str], dict | None] = {}        # (state, ref) -> index row
        self.sec_key: dict[tuple[str, int], str] = {}             # (state, index id) -> section key
        self.sections: dict[str, tuple[str, dict]] = {}           # section key -> (state, row)
        self.roots_done: set[str] = set()
        self.actor_body: dict[tuple[str, str, str], str] = {}     # (state, question, actor) -> body key
        self.body_by_qid: dict[str, str] = {}
        self.ladders = _json(config.ROOT / "fixtures" / "authority" / "ladders.json")
        self.agencies = _json(config.ROOT / "fixtures" / "entities" / "agencies.json")
        # CourtListener court id -> the ladder body's key for the same court (fixtures/entities/court_keys.json)
        self.court_keys: dict[str, str] = {k: v["key"] for k, v in
                                           (_json(config.ROOT / "fixtures" / "entities" / "court_keys.json")
                                            .get("courts") or {}).items() if v.get("key")}
        # CourtListener court id -> {name, jurisdiction, url} (fixtures/entities/courts.json, scripts/fetch_courts.py)
        self.court_names: dict[str, dict] = {k: v for k, v in
                                             (_json(config.ROOT / "fixtures" / "entities" / "courts.json")
                                              .get("courts") or {}).items() if v.get("name")}
        # state -> slug -> {name, description, match, actors} (fixtures/entities/office_types.json)
        self.office_type_specs: dict[str, dict] = {k: v for k, v in
                                                   _json(config.ROOT / "fixtures" / "entities" / "office_types.json").items()
                                                   if isinstance(v, dict) and k in S.NAME}
        self.office_types: dict[str, list[tuple[str, list, set]]] = {}   # state -> [(key, patterns, actor ids)]
        self._postal: dict[str, set[str]] = {}                    # item key -> normalised addresses written
        # "<gov_id>/<process>" -> the decided topic and audience (fixtures/places/topics.json)
        self.topics: dict[str, dict] = {k: v for k, v in _json(config.ROOT / "fixtures" / "places" / "topics.json").items()
                                        if isinstance(v, dict) and not k.startswith("_")}
        # the class items the wiki holds (Q7 ...) exist whatever key they carry: their canonical key and the
        # label-form key an earlier loader wrote both name the same item (schema.LEGACY_CLASS_KEYS)
        for c in SC.CLASSES:
            if c.qid:
                self.existing.add(SC.key_for("class", c.slug))
        self.gaps: dict[str, int] = {}
        self.rung_steps: dict[str, list[str]] = {}                # step key -> rung keys
        # units and codes: what each holds (_describe_units)
        self.unit_info: dict[str, dict] = {}                      # unit or code key -> el, chain, kind, level, heading
        self.unit_sections: dict[str, dict[str, tuple]] = {}      # key -> sort key -> (sort key, number, heading)
        self.children: dict[str, dict[str, str]] = {}             # key -> direct child key -> level
        # unit key -> {name, source, retrieved}: fixtures/law/unit_headings.json (lexflow/law/headings.py), optional
        self.unit_headings: dict[str, dict] = _unit_headings()

    # ---- bookkeeping
    def gap(self, what: str, n: int = 1):
        self.gaps[what] = self.gaps.get(what, 0) + n

    def want(self, state: str) -> bool:
        return self.states is None or state in self.states

    def add(self, key: str, label: str, description: str, cls_: str | None, aliases=()) -> Item:
        it = self.items.get(key)
        if it is None:
            it = Item(key, _cut(self._no_mailbox(label), SC.LABEL_MAX),
                      _cut(self._no_mailbox(description), SC.DESCRIPTION_MAX), [], cls_, [], key in self.existing)
            self.items[key] = it
        for a in aliases:
            a = _cut(self._no_mailbox(a), SC.LABEL_MAX)
            if a and a != it.label and a not in it.aliases:
                it.aliases.append(a)
        return it

    def _no_mailbox(self, text: str) -> str:
        """A label, description or alias with any e-mail address removed: a term names a thing, never a channel
        (channels are claims, after the privacy checks), and a person's mailbox must never reach the wiki."""
        if "@" not in (text or ""):
            return text or ""
        self.gap("mailboxes removed from labels and descriptions")
        out = _EMAIL.sub("", text)
        return re.sub(r"\(\s*\)|\[\s*\]", "", out)

    def claim(self, it: Item, prop: str, value: Value | None, qualifiers=(), references=()) -> Claim | None:
        if value is None:
            return None
        if prop not in SC.ALL_PROPERTY_LABELS:
            raise KeyError(f"unknown property {prop!r}")
        if not self._clean(value, it):
            return None
        quals = [(q, v) for q, v in qualifiers if v is not None and self._clean(v, it)]
        refs = [[(q, v) for q, v in ref if v is not None and self._clean(v, it)] for ref in references]
        refs = [r for r in refs if r]
        sig = (prop, value.sig(), tuple((q, v.sig()) for q, v in quals))
        for c in it.claims:
            if (c.prop, c.value.sig(), tuple((q, v.sig()) for q, v in c.qualifiers)) == sig:
                for r in refs:
                    if r not in c.references:
                        c.references.append(r)
                return c
        c = Claim(prop, value, quals, refs)
        it.claims.append(c)
        return c

    def _clean(self, v: Value, it: Item) -> bool:
        """No personal-looking mailbox in any value; a ``mailto:`` must be an office mailbox; a URL value is an
        absolute http(s) or mailto IRI (a citation or a bare host in a URL field is dropped, with a log line)."""
        if v.kind in ("string", "monolingual", "url", "external-id"):
            bad = personal_mailbox(v.value)
            if bad:
                self.gap("values dropped: personal-looking mailbox")
                return False
        if v.kind == "url" and not _URL.match(v.value):
            self.gap("values dropped: not an absolute http(s) or mailto URL")
            self.log(f"{it.key}: URL value dropped (not an absolute URL): {v.value[:80]!r}")
            return False
        return True

    def ground(self, section_key: str | None, pinpoint: str | None, quote: str | None, *, source_url=None,
               method: str = "curated", retrieved: str | None = None) -> list[tuple[str, Value]]:
        """The grounding reference of section 4.6.  Words from a NO_REPRINT host are never put in a Value: the
        reference then carries the URL and no quoted text."""
        ref: list[tuple[str, Value]] = []
        if section_key:
            ref.append(("source section", item(section_key)))
        if source_url and _URL.match(source_url) and privacy.is_office_url(source_url):
            ref.append(("source URL", url(source_url)))
        if pinpoint:
            ref.append(("pinpoint", string(pinpoint)))
        if quote and not no_reprint(source_url):
            ref.append(("quoted text", string(quote)))
        elif quote:
            self.gap("quotes withheld (NO_REPRINT host)")
        if retrieved and time(retrieved):
            ref.append(("retrieved", time(retrieved)))
        ref.append(("determination method", vocab("determination-method", method)))
        return ref

    # ---- the statute index
    def row(self, state: str, ref: str) -> dict | None:
        k = (state, ref)
        if k not in self.rows:
            from ..ask import index as I
            try:
                hits = I.lookup(state, ref) if I.ready(state) else []
            except Exception as e:  # noqa: BLE001 - a missing or locked index: no law for this state
                self.log(f"{state}: index lookup failed for {ref!r}: {e}")
                hits = []
            self.rows[k] = hits[0] if hits else None
        return self.rows[k]

    def section(self, state: str, ref: str, *, mint: bool = True) -> str | None:
        """The key of a section, minting it when the index knows the section: the key wikibase_items holds for
        this (state, ref), else the key another ref of the same index row got, else ``lexflow:statute:<st>:<the
        index's ref>``."""
        given = SC.key_for("statute", state, ref)
        if given in self.sections:
            return given
        r = self.row(state, ref)
        if r is None:
            if given in self.existing:
                self.sections[given] = (state, {})
                self.gap("sections not in the index (kept bare)")
                return given
            self.gap("sections not in the index")
            return None
        rid = (state, r["id"])
        if rid in self.sec_key:
            return self.sec_key[rid]
        key = given if given in self.existing else SC.key_for("statute", state, r["ref"])
        if not mint:
            return key
        self.sec_key[rid] = key
        self.sections[key] = (state, r)
        return key

    # ---- vocabularies and classes
    def vocabularies(self):
        for c in SC.CLASSES:
            if c.qid:
                # exists on the wiki (referred to by label); the update pass gives it its canonical key and, where
                # the old loader wrote the label form, that key too as an alias, so nothing is duplicated
                it = self.add(SC.key_for("class", c.slug), c.label, c.description, None)
                self.claim(it, "legal identifier", ext(it.key))
                legacy = SC.legacy_class_key(c.slug)
                if legacy != it.key and (legacy in self.existing or legacy in SC.LEGACY_CLASS_KEYS.values()):
                    self.claim(it, "legal identifier", ext(legacy))
                continue
            it = self.add(SC.key_for("class", c.slug), c.label, c.description, None)
            if c.subclass_of:
                self.claim(it, "subclass of", item(cls(c.subclass_of)))
            if c.wikidata:
                self.claim(it, "exact match", url(SC.WIKIDATA_ENTITY + c.wikidata))
                self.claim(it, "Wikidata item ID", ext(c.wikidata))
        for set_, entries in SC.VOCAB.items():
            for v in entries:
                self.add(SC.key_for("vocab", set_, v.slug), v.label, v.description, cls(set_))

    # ---- jurisdictions
    def jurisdictions(self):
        for st, _, name in S.STATES:
            if not self.want(st):
                continue
            it = self.add(SC.key_for("jurisdiction", st), name, "US state or district (lexflow jurisdiction)",
                          cls("jurisdiction"))
            q = S.WIKIDATA.get(st)
            if q:
                self.claim(it, "Wikidata item ID", ext(q))
                self.claim(it, "exact match", url(SC.WIKIDATA_ENTITY + q))
            w = S.WEBSITE.get(st)
            if w and privacy.is_office_url(w):
                self.claim(it, "official website", url(w))

    # ---- law
    def seed_sections(self):
        """Every statute key on the wiki keeps its key: resolve them first, so a model, rung or local process
        that cites the same section under another spelling finds the existing key."""
        for key in sorted(self.existing):
            if key.startswith("lexflow:statute:"):
                _, _, st, ref = key.split(":", 3)
                if self.want(st):
                    self.section(st, ref)

    def law(self):
        """Items for every section in the build (the wiki's, the models', the rungs' and the local processes'),
        their units and codes, the follows chain and the references between them."""
        for key in sorted(self.sections):
            self._section_item(key)
        self._describe_units()                            # after every section is placed under its units
        # follows: the previous built section of the same unit, in sort order
        by_parent: dict[str, list[tuple[str, str]]] = {}
        for key, (st, r) in self.sections.items():
            if r:
                by_parent.setdefault(_parent_key(st, r), []).append((SC.sort_key(r["act_id"]), key))
        for sibs in by_parent.values():
            sibs.sort()
            for (_, prev), (_, nxt) in zip(sibs, sibs[1:]):
                self.claim(self.items[nxt], "follows", item(prev))
        self._references()

    def _section_item(self, key: str):
        st, r = self.sections[key]
        if not r:
            it = self.add(key, key.rsplit(":", 1)[-1], f"{S.NAME[st]} statute (not in the index)", cls("statute"))
            self.claim(it, "applies to jurisdiction", item(SC.key_for("jurisdiction", st)))
            return
        heading = (r.get("original_title") or "").strip() or (r.get("title") or "").strip()
        it = self.add(key, r["citation"], heading or f"{S.NAME[st]} statute", cls("statute"))
        self.claim(it, "citation", string(r["citation"]))
        if r.get("url") and privacy.is_office_url(r["url"]):
            self.claim(it, "official text", url(r["url"]))
        self.claim(it, "applies to jurisdiction", item(SC.key_for("jurisdiction", st)))
        self.claim(it, "unit level", vocab("unit-level", "section"))
        self.claim(it, "section number", string(r["section_number"] or r["ref"]))
        self.claim(it, "sort key", string(SC.sort_key(r["act_id"])))
        self.claim(it, "act identifier", ext(r["act_id"]))
        if heading:
            self.claim(it, "heading text", mono(heading))
        else:
            self.gap("sections without a heading")
        self.claim(it, "effective date", time(r.get("effective_from")))
        self.claim(it, "effective until", time(r.get("effective_until")))
        parent = self._units(st, r)
        if parent:
            self.claim(it, "part of", item(parent))

    def _units(self, st: str, r: dict) -> str | None:
        """The code, sub-code and unit items above a section, from its path and act_id; the parent's key."""
        toks = SC.unit_tokens(r["act_id"])
        elems = [e for e in (r.get("path") or "").split(" / ") if e]
        if not toks:
            return None
        if len(elems) != len(toks) + 1:
            # Utah's "Chapter 48-3a" is one act_id token with its section: name the units from the tokens
            self.gap("sections whose path and act_id disagree")
            elems = [elems[0] if elems else f"{S.NAME[st]} Code"] + [_token_name(t) for t in toks]
        jur = item(SC.key_for("jurisdiction", st))
        code_key = SC.key_for("code", st)
        code = self.add(code_key, elems[0], f"The code of laws of {S.NAME[st]}", cls("legal-code"))
        self.claim(code, "applies to jurisdiction", jur)
        self.claim(code, "unit level", vocab("unit-level", "code"))
        short = (r["citation"].rsplit("§", 1)[0].strip(" ,") if "§" in r["citation"] else elems[0])
        heading = (r.get("original_title") or "").strip() or (r.get("title") or "").strip()
        sec = (SC.sort_key(r["act_id"]), str(r.get("section_number") or r["ref"]), heading)
        self.unit_info.setdefault(code_key, {"el": elems[0], "chain": "", "code": elems[0], "state": st, "kind": "code"})
        self._place(code_key, sec)
        parent = code_key
        labels: list[str] = []
        for i, (tok, el) in enumerate(zip(toks[:-1], elems[1:-1])):
            if tok[:1] in ("C", "A") and tok[1:].isalpha():          # a named code inside the state's codes
                key = SC.key_for("code", st, tok[1:])
                sub = self.add(key, short, f"{el} of the {elems[0]}", cls("legal-code"))
                self.claim(sub, "applies to jurisdiction", jur)
                self.claim(sub, "unit level", vocab("unit-level", "code"))
                self.claim(sub, "part of", item(code_key))
                self.claim(sub, "act identifier", ext(SC.unit_prefix(r["act_id"], i + 1)))
                self.unit_info.setdefault(key, {"el": el, "chain": f"the {elems[0]}", "code": elems[0], "state": st,
                                                "kind": "code"})
                self.children.setdefault(parent, {})[key] = "code"
                self._place(key, sec)
                parent = key
                continue
            prefix = SC.unit_prefix(r["act_id"], i + 1)
            key = SC.key_for("unit", st, prefix)
            level = SC.unit_level(el, tok)
            chain = f"{short} {', '.join(labels)}" if labels else f"the {elems[0]}"
            labels.append(el)
            unit = self.add(key, f"{short} {', '.join(labels)}", f"{el} of {chain}", cls("statutory-unit"))
            self.claim(unit, "applies to jurisdiction", jur)
            self.claim(unit, "part of", item(parent))
            if level:
                self.claim(unit, "unit level", vocab("unit-level", level))
            else:
                self.gap(f"units of unknown level ({el})")
                self.log(f"{key}: no unit level for {el!r} (token {tok!r}); written as a statutory unit without one")
            self.claim(unit, "sort key", string(SC.sort_key(prefix)))
            self.claim(unit, "act identifier", ext(prefix))
            name = (self.unit_headings.get(key) or {}).get("name") or self._unit_name(st, " / ".join(elems[:i + 2]))
            if name:
                self.claim(unit, "heading text", mono(name))
            else:
                self.gap("units without a heading")
            self.unit_info.setdefault(key, {"el": el, "chain": chain, "code": elems[0], "state": st, "kind": "unit",
                                            "level": level, "heading": name})
            self.children.setdefault(parent, {})[key] = level or "unit"
            self._place(key, sec)
            parent = key
        return parent

    def _place(self, key: str, sec: tuple[str, str, str]) -> None:
        """Record that the build places section ``sec`` (sort key, number, heading) under the unit or code ``key``."""
        self.unit_sections.setdefault(key, {})[sec[0]] = sec

    def _describe_units(self) -> None:
        """Every statutory unit's description says where it sits and what it holds, and every code's what lexflow
        cites of it (the coordinator's request of 15 October 2026: "Article 2 of the A.R.S." said nothing):

        * unit: ``[<heading> — ]<Article 2> of <A.R.S. Title 39, Chapter 1>; holds §§ 39-121 to 39-128, 8 sections
          (first: Definitions)``: the parent chain from the path, the lowest and highest section the build places
          under it (the count when more than two), and the first section's heading;
        * code: ``Code of <State>: N titles, M sections cited by lexflow`` (the level word of its direct children);
          a named code inside the state's codes: ``<Government Code> of the <California Codes>: ...``.

        Deterministic: sections are ordered by sort key, and the result depends only on the build's own sections."""
        for key, info in sorted(self.unit_info.items()):
            it = self.items.get(key)
            if it is None:
                continue
            secs = [self.unit_sections[key][k] for k in sorted(self.unit_sections.get(key, {}))]
            if info["kind"] == "code":
                kids = self.children.get(key, {})
                levels = {lv for lv in kids.values()}
                word = (next(iter(levels)) if len(levels) == 1 else "unit")
                word = word if word != "code" else "code"
                n, m = len(kids), len(secs)
                head = f"Code of {S.NAME[info['state']]}" if not info["chain"] else f"{info['el']} of {info['chain']}"
                it.description = _cut(f"{head}: {n} {_plural(word, n)}, {m} {_plural('section', m)} cited by lexflow",
                                      SC.DESCRIPTION_MAX)
                continue
            base = f"{info['el']} of {info['chain']}"
            holds = ""
            if secs:
                lo, hi = secs[0][1], secs[-1][1]
                rng = f"§ {lo}" if len(secs) == 1 else f"§§ {lo} to {hi}"
                if len(secs) > 2:
                    rng += f", {len(secs)} sections"
                first = secs[0][2]
                holds = f"; holds {rng}" + (f" (first: {_cut(first, 80)})" if first else "")
            heading = info.get("heading")
            lead = f"{heading} — " if heading and heading.lower() != info["el"].lower() else ""
            it.description = _cut(lead + base + holds, SC.DESCRIPTION_MAX)

    def _unit_name(self, st: str, path: str) -> str | None:
        names = self.__dict__.setdefault("_unit_names", {})
        if st not in names:
            names[st] = {}
            try:
                from ..law import xref
                tab = xref.table(st)
                if tab:
                    for e in tab.names.values():
                        if e.get("unit") and e.get("name"):
                            names[st].setdefault(e["unit"], e["name"])
            except Exception as e:  # noqa: BLE001 - no index, no names
                self.log(f"{st}: unit names unavailable: {e}")
        return names[st].get(path)

    def _references(self):
        """references between built sections, with the reference type from lexflow.law.xref."""
        try:
            from ..law import xref
        except Exception:  # noqa: BLE001
            return
        for key in sorted(self.sections):
            st, r = self.sections[key]
            if not r:
                continue
            try:
                edges = xref.edges(st, r)
            except Exception as e:  # noqa: BLE001 - a parse problem is not a build problem
                self.log(f"{key}: references not read: {e}")
                continue
            seen = set()
            for e in edges:
                target = self.sec_key.get((st, e["target"]))
                if not target or target == key or (target, e["role"]) in seen:
                    continue
                seen.add((target, e["role"]))
                role = e["role"] if SC.key_for("vocab", "reference-type", e["role"]) in SC.VOCAB_BY_KEY else "other"
                quals = [("reference type", vocab("reference-type", role))]
                if e.get("pinpoint"):
                    quals.append(("pinpoint", string(e["pinpoint"])))
                self.claim(self.items[key], "references", item(target), quals)

    # ---- bodies
    def root(self, st: str) -> str:
        key = SC.key_for("agency", st, "government")
        if key not in self.items:
            it = self.add(key, f"{S.NAME[st]} state government", f"The government of {S.NAME[st]} (root of its "
                          "agencies)", cls("government-agency"))
            self.claim(it, "applies to jurisdiction", item(SC.key_for("jurisdiction", st)))
        return key

    def bodies(self):
        self._agencies_fixture()
        self._ladder_bodies()
        self._office_types()
        self._courts()
        pp = self.add(SC.PRIVATE_PARTY, "private party", "The person or business a process serves: a requester, "
                      "applicant, registered agent or incorporator; never a named individual.", cls("legal-role"))
        del pp

    def _agencies_fixture(self):
        exact = [b for b in self.agencies.get("bodies", []) if b.get("match") == "exact" and b.get("qid")]
        ladder_keys = {b["qid"]: b["key"] for b in self.ladders.get("bodies", {}).values()
                       if b.get("qid") and b.get("qid_status") == "exact" and b.get("key")}
        for b in sorted(exact, key=lambda b: (b["state"], b["resolved_name"] or "")):
            st, name, kind = b["state"], b["resolved_name"], b.get("item_kind")
            if not self.want(st) or not name:
                continue
            if kind == "position":
                key = SC.key_for("position", st, name)
                it = self.add(key, name, f"Position in {S.NAME[st]}", cls("position"))
            else:
                key = ladder_keys.get(b["qid"]) or SC.key_for("agency", st, name)
                if SC.kind_of(key) != "agency":
                    key = SC.key_for("agency", st, name)
                it = self.add(key, name, f"{'Court' if kind == 'court' else 'Government agency'} of {S.NAME[st]}",
                              cls("court" if kind == "court" else "government-agency"))
                self.claim(it, "part of", item(self.root(st)))
            self.claim(it, "applies to jurisdiction", item(SC.key_for("jurisdiction", st)))
            if kind in ("organisation", "court", "position"):           # kind-checked: untyped gets no QID
                self.claim(it, "Wikidata item ID", ext(b["qid"]))
                self.claim(it, "exact match", url(SC.WIKIDATA_ENTITY + b["qid"]))
                self.body_by_qid[b["qid"]] = key
            else:
                self.gap("fixture QIDs left off (untyped item)")
            if b.get("website") and privacy.is_office_url(b["website"]):
                self.claim(it, "official website", url(b["website"]))
            if b.get("govdirectory_url") and privacy.is_office_url(b["govdirectory_url"]):
                self.claim(it, "described at URL", url(b["govdirectory_url"]))
            if b.get("email") and privacy.is_office_mailbox(b["email"], name):
                self.claim(it, "email address", url("mailto:" + b["email"].strip()))
            for u in b.get("units") or []:
                if not u.get("label"):
                    continue
                uk = SC.key_for("agency", st, u["label"])
                unit = self.add(uk, u["label"], f"Unit of the {name}", cls("organizational-unit"))
                self.claim(unit, "part of", item(key))
                self.claim(unit, "applies to jurisdiction", item(SC.key_for("jurisdiction", st)))
                if u.get("qid"):
                    self.claim(unit, "Wikidata item ID", ext(u["qid"]))
                if u.get("website") and privacy.is_office_url(u["website"]):
                    self.claim(unit, "official website", url(u["website"]))
            for rel in b.get("related_items") or []:
                if rel.get("item_kind") == "position" and rel.get("label") and kind != "position":
                    pk = SC.key_for("position", st, rel["label"])
                    pos = self.add(pk, rel["label"], f"Position in {S.NAME[st]}", cls("position"))
                    self.claim(pos, "position in", item(key))
                    self.claim(pos, "applies to jurisdiction", item(SC.key_for("jurisdiction", st)))
                    if rel.get("qid"):
                        self.claim(pos, "Wikidata item ID", ext(rel["qid"]))
                    self.claim(it, "head position", item(pk))
            for q, actor in _actors_of(b.get("source") or ""):
                self.actor_body[(st, q, actor)] = key

    def _ladder_bodies(self):
        for ref, b in sorted(self.ladders.get("bodies", {}).items()):
            key, kind = b.get("key"), (b.get("kind") or "")
            if not key or key == SC.PRIVATE_PARTY:
                continue
            k = SC.kind_of(key)
            st = key.split(":")[2]
            if st not in S.NAME or not self.want(st):
                continue
            if "court" in kind:
                c = "court"
            elif k == "office-type":
                c = "office-type"
            elif k == "position-type":
                c = "position-type"
            elif k == "position":
                c = "position"
            elif "sub-unit" in kind:
                c = "organizational-unit"
            else:
                c = "government-agency"
            desc = f"{kind.capitalize()} in {S.NAME[st]}" + (f"; resolved by {b['resolve_by']}" if b.get("resolve_by") else "")
            it = self.add(key, b["name"], desc, cls(c))
            self.claim(it, "applies to jurisdiction", item(SC.key_for("jurisdiction", st)))
            qid = b.get("qid")
            parent = None                                 # the parent body, when the QID is the parent's
            if qid and b.get("qid_status") == "parent" and c in ("government-agency", "court", "organizational-unit"):
                # part of -> the parent, minted from the agencies fixture when it is not in the build already;
                # a parent that is a position (the Attorney General) is no P9 target: the edge is dropped
                parent = self._parent_agency(st, qid)
                if not parent:
                    self.gap("ladder parent edges dropped (parent not mintable from the fixture)")
                    self.log(f"{key}: parent {qid} is not a body the fixture can mint; part of dropped")
            if c == "office-type":
                self.claim(it, "subclass of", item(cls("court" if "court" in kind else "government-agency")))
            elif c in ("government-agency", "court", "organizational-unit"):
                self.claim(it, "part of", item(parent or self.root(st)))
            if qid and b.get("qid_status") == "exact" and c in ("government-agency", "court", "position"):
                # kind-checked against the agencies fixture's item_kind (the three known errors fail this)
                typed = next((a.get("item_kind") for a in self.agencies.get("bodies", []) if a.get("qid") == qid), None)
                ok = (typed in ("organisation", "court") and c != "position") or (typed == "position" and c == "position")
                if ok:
                    self.claim(it, "Wikidata item ID", ext(qid))
                    self.claim(it, "exact match", url(SC.WIKIDATA_ENTITY + qid))
                else:
                    self.gap("ladder QIDs left off (kind check failed)")
            elif qid and b.get("qid_status") == "parent" and parent:
                pass                                      # the parent edge above is what the QID gives
            elif qid:
                self.gap("ladder QIDs left off (not an exact match or not a body/position key)")

    def _office_types(self):
        """The office types of ``fixtures/entities/office_types.json`` (Virginia's constitutional officers and the
        general registrar): one item each, merged with the ladder's body of the same key when it has one."""
        for st in sorted(self.office_type_specs):
            if not self.want(st):
                continue
            for slug_, spec in sorted(self.office_type_specs[st].items()):
                if not isinstance(spec, dict) or not spec.get("name"):
                    continue
                key = SC.key_for("office-type", st, slug_)
                it = self.add(key, spec["name"], spec.get("description") or f"Office every {S.NAME[st]} locality has",
                              cls("office-type"))
                self.claim(it, "applies to jurisdiction", item(SC.key_for("jurisdiction", st)))
                self.claim(it, "subclass of", item(cls("government-agency")))
                pats = [re.compile(p, re.I) for p in spec.get("match") or [] if isinstance(p, str)]
                self.office_types.setdefault(st, []).append((key, pats, set(spec.get("actors") or [])))

    def office_type_for(self, st: str, name: str | None, actor_id: str | None = None) -> str | None:
        """The office-type key whose match words the name (or the state model's actor id) carries, else None."""
        text = " ".join((name or "").split())
        for key, pats, actors in self.office_types.get(st, []):
            if (actor_id and actor_id in actors) or any(p.search(text) for p in pats):
                return key
        return None

    def _parent_agency(self, st: str, qid: str) -> str | None:
        """The key of the agency or court item for ``qid``: the fixture's exact body when it is built, else a new
        item minted from the fixture's record of that QID (its ``qid_label`` and ``item_kind``); None when the
        fixture does not type it as an organisation or court."""
        if qid in self.body_by_qid:
            return self.body_by_qid[qid]
        rec = next((a for a in self.agencies.get("bodies", []) if a.get("qid") == qid and a.get("state") == st
                    and a.get("item_kind") in ("organisation", "court") and a.get("qid_label")), None)
        if not rec:
            return None
        name, kind = rec["qid_label"], rec["item_kind"]
        key = SC.key_for("agency", st, name)
        it = self.add(key, name, f"{'Court' if kind == 'court' else 'Government agency'} of {S.NAME[st]}",
                      cls("court" if kind == "court" else "government-agency"))
        self.claim(it, "part of", item(self.root(st)))
        self.claim(it, "applies to jurisdiction", item(SC.key_for("jurisdiction", st)))
        self.claim(it, "Wikidata item ID", ext(qid))
        self.claim(it, "exact match", url(SC.WIKIDATA_ENTITY + qid))
        self.body_by_qid[qid] = key
        self.log(f"{key}: minted as the parent of a ladder body from the fixture's record of {qid}")
        return key

    def _courts(self):
        """One item per CourtListener court of ``caselaw.COURTS``: labelled from ``fixtures/entities/courts.json``
        (CourtListener's own name, read by scripts/fetch_courts.py), else from the name ``case_law`` carries; the
        CourtListener id and the other name are aliases.  A court the ladder also holds is that one item."""
        names = {r["court_id"]: r["court"] for r in db.rows(self.con, "SELECT DISTINCT court_id, court FROM case_law "
                                                                    "WHERE court_id IS NOT NULL AND court IS NOT NULL")}
        for st in sorted(COURTS):
            if not self.want(st):
                continue
            for cid in COURTS[st]:
                key = self.court_key(st, cid)
                fixture = self.court_names.get(cid) or {}
                name = fixture.get("name") or names.get(cid)
                aliases = [a for a in (cid, names.get(cid), fixture.get("short_name")) if a and a != name]
                if key in self.items:                     # the ladder's court: one item, the other names aliases
                    self.add(key, self.items[key].label, self.items[key].description, self.items[key].cls,
                             aliases=[a for a in (name, *aliases) if a])
                    continue
                it = self.add(key, name or f"{S.NAME[st]} court {cid}",
                              f"Court in {S.NAME[st]} (CourtListener court {cid})", cls("court"), aliases=aliases)
                self.claim(it, "applies to jurisdiction", item(SC.key_for("jurisdiction", st)))
                self.claim(it, "part of", item(self.root(st)))
                if fixture.get("url") and privacy.is_office_url(fixture["url"]):
                    self.claim(it, "official website", url(fixture["url"]))
                if not name:
                    self.gap("courts without a name (courts.json or case_law)")

    def court_key(self, st: str, cid: str) -> str:
        """The key of the item for a CourtListener court: the ladder body's key when court_keys.json says they are
        the same court, else ``lexflow:agency:<st>:court_<id>``."""
        return self.court_keys.get(f"{st}:{cid}") or SC.key_for("agency", st, f"court_{cid}")

    # ---- governments and contacts
    def governments(self, gov_ids: set[str]):
        for gid in sorted(gov_ids):
            g = db.one(self.con, "SELECT * FROM governments WHERE gov_id=?", gid)
            if not g or not self.want(g["state"]):
                continue
            st = g["state"]
            it = self.add(SC.key_for("gov", gid), f"{g['name']}, {S.NAME[st]}",
                          f"{g['kind']} in {S.NAME[st]} (Census government {gid})", cls("government"))
            self.claim(it, "applies to jurisdiction", item(SC.key_for("jurisdiction", st)))
            self.claim(it, "government ID", ext(gid))
            if g.get("wikidata"):
                self.claim(it, "Wikidata item ID", ext(g["wikidata"]))
                self.claim(it, "exact match", url(SC.WIKIDATA_ENTITY + g["wikidata"]))
            if g.get("website") and privacy.is_office_url(g["website"]):
                self.claim(it, "official website", url(g["website"]))
            self.channels(it, gid, "general", g["name"], mailboxes=False)

    def channels(self, it: Item, gid: str, question: str, owner: str, *, mailboxes: bool, retrieved=None,
                 page: str | None = None, method: str = "official-page", also: Item | None = None):
        """Office channels of ``contacts`` for one owner and question, after ``privacy.is_office_channel``.  A
        mailbox is written only when ``mailboxes`` (a researched process whose contacts were read from the
        office's own page); the general question's mailboxes wait for the contact checks (entities-contacts
        section 5.2 rule 5), as the lab's places page does."""
        rows = db.rows(self.con, "SELECT kind, value, label, source FROM contacts WHERE gov_id=? AND question=? "
                                 "AND kind IN ('website','page','office','postal','email','phone') ORDER BY kind, value",
                       gid, question)
        for r in rows:
            kind, value = r["kind"], r["value"]
            if not privacy.is_office_channel(kind, value, r["label"], owner):
                self.gap("contact rows refused by the privacy checks")
                continue
            if kind == "email" and not mailboxes:
                self.gap("general mailboxes withheld until the contact checks land")
                continue
            if kind in ("office", "postal"):
                value = normalise_postal(privacy.office_value(normalise_postal(value), owner))
            elif kind == "phone":
                value = privacy.office_phone_value(value, owner)
            elif kind in ("website", "page"):
                value = _leading_url(value)                   # "https://… (what the page is)" -> the URL alone
            if not value:
                continue
            src = r["source"] if (r["source"] or "").startswith("http") else page
            ref = self.ground(None, None, None, source_url=src, method=method, retrieved=retrieved)
            prop, val = {"website": ("official website", url(value)), "page": ("contact page URL", url(value)),
                         "office": ("postal address", string(value)), "postal": ("postal address", string(value)),
                         "email": ("email address", url("mailto:" + value.strip())),
                         "phone": ("phone number", string(value))}[kind]
            for target in (it, also):
                if target is None:
                    continue
                if kind in ("office", "postal"):
                    # one claim per distinct address on an item: "605 E Main St" and "605 E Main Street, Room A-130
                    # (8:30 am to 4:30 pm)" are the same office once hours and spelling are normalised
                    seen = self._postal.setdefault(target.key, set())
                    k = postal_key(value)
                    if k in seen:
                        self.gap("postal addresses folded into one (trivial variants)")
                        continue
                    seen.add(k)
                self.claim(target, prop, val, references=[ref])

    # ---- process models
    def models(self):
        rows = db.rows(self.con, "SELECT * FROM process_models WHERE tier IN ('reviewed','agreed','single') "
                                 "ORDER BY model_id")
        for m in rows:
            if not self.want(m["state"]):
                continue
            if m["tier"] == "single" and not self.drafts:
                continue
            self._model(m)

    def _model(self, m: dict):
        st, q, mid = m["state"], m["question"], m["model_id"]
        facts = db.loads(m["facts"], {}) or {}
        metrics = db.loads(m["metrics"], {}) or {}
        stages = db.loads(m["stages"], {}) or {}
        draft = m["tier"] == "single"
        status = {"reviewed": "reviewed", "agreed": "agreed"}.get(m["tier"], "draft")
        short = QUESTIONS[q].short.lower() if q in QUESTIONS else q
        title = m["title"] or facts.get("process_name") or mid
        jur = item(SC.key_for("jurisdiction", st))
        pkey = SC.key_for("process", mid)
        how = {"reviewed": "reviewed, every quote checked", "agreed": "two independent extractions agree",
               "single": "unreviewed draft from one extraction"}[m["tier"]]
        proc = self.add(pkey, f"{title} ({S.NAME[st]})",
                        f"{QUESTIONS[q].title if q in QUESTIONS else q} Process model by lexflow, {how}.",
                        cls("legal-process"))
        self.claim(proc, "applies to jurisdiction", jur)
        if m.get("citation"):
            self.claim(proc, "citation", string(m["citation"]))
        if m.get("source_url") and privacy.is_office_url(m["source_url"]):
            self.claim(proc, "official text", url(m["source_url"]))
        if q in QUESTIONS:
            self.claim(proc, "question asked", mono(QUESTIONS[q].title))
            proc.aliases.append(_cut(QUESTIONS[q].title, SC.LABEL_MAX))
        if q in SC.QUESTION_TOPIC:
            self.claim(proc, "topic", vocab("topic", SC.QUESTION_TOPIC[q]))
            self.claim(proc, "audience", vocab("audience", SC.QUESTION_AUDIENCE[q]))
        self.claim(proc, "review status", vocab("review-status", status))
        self.claim(proc, "checked on", time(stages.get("validated") or stages.get("compiled") or m["updated_at"]))
        sections: dict[str, str] = {}                     # bare section number -> key
        for ref in metrics.get("sections") or []:
            key = self.section(st, ref)
            if key:
                sections[ref] = key
                self.claim(proc, "references", item(key))
        # roles
        actors = {a["id"]: a for a in facts.get("actors", []) if a.get("id")}
        for aid, a in sorted(actors.items()):
            rk = SC.key_for("role", st, q, aid)
            role = self.add(rk, f"{a.get('name') or aid} ({S.NAME[st]})", f"{a.get('kind') or 'party'} in the "
                            f"{short} process", cls("legal-role"))
            self.claim(role, "applies to jurisdiction", jur)
            self.claim(role, "review status", vocab("review-status", status))
            office_type = self.office_type_for(st, a.get("name"), aid) if not draft else None
            if a.get("kind") == "private-party":
                self.claim(role, "played by", item(SC.PRIVATE_PARTY))
            elif (st, q, aid) in self.actor_body and not draft:
                self.claim(role, "played by", item(self.actor_body[(st, q, aid)]))
            elif office_type:                            # a constitutional office every locality has
                self.claim(role, "played by", item(office_type))
                self.gap("roles played by an office type")
            else:
                self.gap("roles without a body to play them")
            src = a.get("source") or {}
            if src.get("section") and not draft:
                sk = self._src_section(st, src, sections)
                if sk:
                    self.claim(role, "authority conferred by", item(sk), references=[
                        self.ground(sk, src.get("subsection"), src.get("quote"), method="curated")])
        # decisions (so steps can hang on them)
        outputs: dict[str, str] = {}
        decisions = facts.get("decisions", []) if not draft else []
        for d in decisions:
            dk = SC.key_for("decision", mid, d["id"])
            dec = self.add(dk, f"{d.get('question') or d['id']} ({S.NAME[st]} {short})",
                           f"Decision point of “{title}”", cls("decision-point"))
            self.claim(dec, "part of", item(pkey))
            self.claim(dec, "applies to jurisdiction", jur)
            if d.get("question"):
                self.claim(dec, "heading text", mono(d["question"]))
            self.claim(proc, "has part", item(dk))
            for o in d.get("outputs") or []:
                if o.get("name"):
                    outputs[o["name"]] = dk
            for rule in d.get("rules") or []:
                src = rule.get("source") or {}
                sk = self._src_section(st, src, sections) if src.get("section") else None
                if sk:
                    self.claim(dec, "references", item(sk), references=[
                        self.ground(sk, src.get("subsection"), src.get("quote"))])
        outcomes = {o["id"] for o in facts.get("outcomes", []) if o.get("id")} if not draft else set()
        # steps
        steps = facts.get("steps", [])
        step_keys = {s["id"]: SC.key_for("step", mid, s["id"]) for s in steps if s.get("id")}
        rungs = self._rungs(m, sections, step_keys) if not draft else {}
        headline: Claim | None = None
        for i, s in enumerate(steps):
            if not s.get("id"):
                continue
            sk_ = step_keys[s["id"]]
            src = s.get("source") or {}
            sub = "".join(f"({p})" for p in (src.get("subsection") or "").split(".") if p)
            step = self.add(sk_, f"{s.get('action') or s['id']} ({S.NAME[st]} {short})",
                            f"Step of “{title}”; § {src.get('section', '')}{sub}", cls("legal-process-step"))
            self.claim(step, "part of", item(pkey))
            self.claim(step, "applies to jurisdiction", jur)
            self.claim(step, "sort key", string(f"{i + 1:04d}"))
            self.claim(step, "review status", vocab("review-status", status))
            self.claim(proc, "has part", item(sk_))
            if s.get("actor") in actors:
                self.claim(step, "bearer", item(SC.key_for("role", st, q, s["actor"])))
            if s.get("recipient") in actors:
                self.claim(step, "recipient", item(SC.key_for("role", st, q, s["recipient"])))
            if SC.key_for("vocab", "step-kind", s.get("kind") or "") in SC.VOCAB_BY_KEY:
                self.claim(step, "step kind", vocab("step-kind", s["kind"]))
            elif s.get("kind"):
                self.gap(f"steps of unknown kind ({s['kind']})")
            mod = {"obligation": "Obligation", "permission": "Permission", "prohibition": "Prohibition",
                   "right": "Right"}.get(s.get("modality") or "")
            if mod:
                self.claim(step, "deontic modality", item(mod))
            for prev in s.get("after") or []:
                if prev in step_keys:
                    self.claim(step, "follows", item(step_keys[prev]))
            if s.get("condition") and outputs.get(s["condition"]):
                self.claim(step, "condition", item(outputs[s["condition"]]))
            if s.get("decision") and not draft:
                self.claim(step, "has part", item(SC.key_for("decision", mid, s["decision"])))
            sec = self._src_section(st, src, sections) if src.get("section") else None
            if sec:
                self.claim(step, "references", item(sec), references=[
                    self.ground(sec, src.get("subsection"), src.get("quote"))])
            d = s.get("deadline") if not draft else None
            if d and d.get("amount") is not None:
                dsrc = d.get("source") or src
                dsec = self._src_section(st, dsrc, sections) if dsrc.get("section") else sec
                unit_ = SC.time_unit_for(d.get("unit"), dsrc.get("quote"))
                quals = []
                if unit_:
                    quals.append(("time unit", vocab("time-unit", unit_)))
                else:
                    self.gap(f"deadlines of unknown unit ({d.get('unit')})")
                if d.get("anchor"):
                    quals.append(("counted from", string(d["anchor"])))
                if d.get("on_miss") in outcomes:
                    quals.append(("on expiry", item(SC.key_for("outcome", mid, d["on_miss"]))))
                c = self.claim(step, "time limit", quantity(d["amount"]), quals,
                               [self.ground(dsec, dsrc.get("subsection"), dsrc.get("quote"))])
                if headline is None and c is not None:
                    headline = c
            for rk in rungs.get(s["id"], []):
                self.claim(step, "escalates to", item(rk))
        if headline is not None:
            self.claim(proc, "time limit", headline.value, headline.qualifiers, headline.references)
        # outcomes
        for o in facts.get("outcomes", []) if not draft else []:
            if not o.get("id"):
                continue
            ok = SC.key_for("outcome", mid, o["id"])
            out = self.add(ok, o.get("description") or o["id"], f"Outcome of “{title}”", cls("process-outcome"))
            src = o.get("source") or {}
            sec = self._src_section(st, src, sections) if src.get("section") else None
            refs = [self.ground(sec, src.get("subsection"), src.get("quote"))] if sec else []
            self.claim(out, "part of", item(pkey), references=refs)
            self.claim(out, "applies to jurisdiction", jur)
            for prev in o.get("after") or []:
                if prev in step_keys:
                    self.claim(out, "follows", item(step_keys[prev]))
            self.claim(proc, "outcome", item(ok))

    def _decided(self, entry: dict, field: str, pkey: str) -> str | None:
        """The ``topic`` or ``audience`` slug of a topics.json entry, when a person accepted the entry or the model's
        confidence for that field (``<field>_confidence``, else ``confidence``) reached ``TOPIC_CONFIDENCE`` and the
        slug is in the vocabulary; logged either way."""
        slug_ = entry.get(field)
        if not slug_:
            return None
        if SC.key_for("vocab", field, slug_) not in SC.VOCAB_BY_KEY:
            self.log(f"{pkey}: topics.json {field} {slug_!r} is not in the vocabulary; ignored")
            return None
        conf = entry.get(f"{field}_confidence", entry.get("confidence"))
        try:
            conf = float(conf) if conf is not None else None
        except (TypeError, ValueError):
            conf = None
        if entry.get("accepted") is True:
            self.log(f"{pkey}: {field} {slug_} from topics.json (accepted by a person)")
            self.gap(f"local {field}s from topics.json (accepted)")
            return slug_
        if conf is not None and conf >= TOPIC_CONFIDENCE:
            self.log(f"{pkey}: {field} {slug_} from topics.json (model confidence {conf:.2f} >= {TOPIC_CONFIDENCE})")
            self.gap(f"local {field}s from topics.json (confidence >= {TOPIC_CONFIDENCE})")
            return slug_
        self.log(f"{pkey}: topics.json {field} {slug_} not used (confidence "
                 f"{'none' if conf is None else f'{conf:.2f}'} < {TOPIC_CONFIDENCE}, not accepted)")
        self.gap(f"local {field}s in topics.json left unused (unsure, not accepted)")
        return None

    def _src_section(self, st: str, src: dict, sections: dict[str, str]) -> str | None:
        """The key of the section a model's ``source`` names: the model's section whose ref ends with it."""
        sec = str(src.get("section") or "").strip()
        if not sec:
            return None
        for ref, key in sections.items():
            if ref == sec or ref.endswith(sec) or ref.split("§")[-1].strip() == sec:
                return key
        return self.section(st, sec)

    def _rungs(self, m: dict, sections: dict[str, str], step_keys: dict[str, str]) -> dict[str, list[str]]:
        """Rung items for the model's ladder; step id -> rung keys that name it in ``model_ref``."""
        st, q, mid = m["state"], m["question"], m["model_id"]
        ladder = next((l for l in self.ladders.get("ladders", []) if l.get("id") == mid), None)
        if not ladder:
            return {}
        short = QUESTIONS[q].short.lower() if q in QUESTIONS else q
        by_step: dict[str, list[str]] = {}
        seen: set[str] = set()
        for r in ladder.get("rungs", []):
            code = SC.subtype_code(r.get("subtype"))
            if not code:
                self.gap("rungs without a subtype code")
                self.log(f"{r.get('id')}: subtype {r.get('subtype')!r} has no code in schema.SUBTYPE_CODES")
                continue
            cite, pin = SC.strip_pinpoint(r.get("section") or "")
            row = self.row(st, cite) if cite else None
            sec_key = self.section(st, cite) if cite else None
            slug_ = SC.section_slug(r.get("section") or "", row["act_id"] if row else None)
            key = SC.key_for("rung", st, q, slug_, code)
            if key in seen:
                self.gap("rung key collisions")
                self.log(f"{r.get('id')}: rung key {key} already used")
                continue
            seen.add(key)
            type_ = SC.ESCALATION_TYPES.get(r.get("type") or "")
            it = self.add(key, f"{r.get('subtype')} ({S.NAME[st]} {short})",
                          _cut(r.get("effect") or r.get("trigger") or r.get("type") or "", SC.DESCRIPTION_MAX),
                          cls("escalation-mechanism"))
            self.claim(it, "part of", item(SC.key_for("process", mid)))
            self.claim(it, "applies to jurisdiction", item(SC.key_for("jurisdiction", st)))
            self.claim(it, "review status", vocab("review-status", "reviewed" if m["tier"] == "reviewed" else "agreed"))
            if r.get("trigger"):
                self.claim(it, "heading text", mono(r["trigger"]))
            if type_:
                self.claim(it, "escalation type", vocab("escalation-type", type_))
            method = "software-match" if r.get("quote_verified") else "curated"
            ground = self.ground(sec_key, pin, r.get("quote"), method=method)
            if sec_key:
                self.claim(it, "references", item(sec_key), references=[ground])
            body = (r.get("body") or {}).get("key")
            if body and body in self.items:
                rel = "defers to" if (r.get("type") in ("referral", "delegation", "deferral to another process")) \
                    else "escalates to"
                self.claim(it, rel, item(body), references=[ground])
            elif body:
                self.gap("rung bodies not built")
            for d in r.get("deadline") or []:
                if d.get("amount") is None:
                    continue
                unit_ = SC.time_unit_for(d.get("unit"), d.get("quote"))
                quals = [("time unit", vocab("time-unit", unit_))] if unit_ else []
                if d.get("anchor"):
                    quals.append(("counted from", string(d["anchor"])))
                dcite, dpin = SC.strip_pinpoint(d.get("section") or "")
                dkey = self.section(st, dcite) if dcite else sec_key
                self.claim(it, "time limit", quantity(d["amount"]), quals, [self.ground(
                    dkey, dpin, d.get("quote"), method="software-match" if d.get("verified") else "curated")])
            for sid in _model_ref_steps(r.get("model_ref")):
                if sid in step_keys:
                    by_step.setdefault(sid, []).append(key)
        return by_step

    # ---- local processes
    def local(self) -> set[str]:
        rows = db.rows(self.con, "SELECT * FROM place_processes WHERE verified=1 ORDER BY gov_id, process")
        govs: set[str] = set()
        for p in rows:
            if not self.want(p["state"]) or (self.places and p["gov_id"] not in self.places):
                continue
            g = db.one(self.con, "SELECT * FROM governments WHERE gov_id=?", p["gov_id"])
            if not g:
                self.gap("place processes whose government is unknown")
                continue
            govs.add(p["gov_id"])
            self._local(p, g)
        return govs

    def _local(self, p: dict, g: dict):
        st, gid, pid = p["state"], p["gov_id"], p["process"]
        spec = db.loads(p["spec"], {}) or {}
        jur = item(SC.key_for("jurisdiction", st))
        gov = item(SC.key_for("gov", gid))
        owner = (g["name"], spec.get("office") or "")
        retrieved = max((s.get("retrieved") or "" for s in spec.get("sources") or []), default=None) or None
        page = next((s.get("url") for s in spec.get("sources") or [] if s.get("url")), None)
        pkey = SC.key_for("process", gid, pid)
        title = p["title"] or spec.get("title") or pid
        proc = self.add(pkey, f"{title} ({g['name']})", f"Researched local process in {g['name']}, {S.NAME[st]}; "
                        f"{spec.get('summary') or ''}", cls("legal-process"), aliases=[p["question"] or ""])
        self.claim(proc, "applies to jurisdiction", gov)
        if p.get("question"):
            self.claim(proc, "question asked", mono(p["question"]))
        category = p.get("category") or spec.get("category") or ""
        topic = SC.CATEGORY_TOPIC.get(category)
        decided = self.topics.get(f"{gid}/{pid}") or {}
        if not topic and decided:
            topic = self._decided(decided, "topic", pkey)
        if topic:
            self.claim(proc, "topic", vocab("topic", topic))
        else:
            self.gap(f"local processes of unmapped category ({category})")
        audiences = [SC.AUDIENCES[a] for a in spec.get("audience") or [] if SC.AUDIENCES.get(a)]
        if not audiences and decided:
            a = self._decided(decided, "audience", pkey)
            if a:
                audiences = [a]
        for a in audiences:
            self.claim(proc, "audience", vocab("audience", a))
        self.claim(proc, "review status", vocab("review-status", "agreed"))
        checks = spec.get("checks") or {}
        self.claim(proc, "checked on", time(checks.get("date") or p["updated_at"]))
        for lb in spec.get("legal_basis") or []:
            if lb.get("level") != "state" or not lb.get("citation"):
                continue
            cite, pin = SC.strip_pinpoint(lb["citation"])
            sk = self.section(st, cite)
            if sk:
                quals = []
                role = lb.get("role") or ""
                if SC.key_for("vocab", "reference-type", role) in SC.VOCAB_BY_KEY:
                    quals.append(("reference type", vocab("reference-type", role)))
                self.claim(proc, "references", item(sk), quals, [self.ground(
                    sk, pin, lb.get("quote"), source_url=lb.get("url"), method="software-match")])
            else:
                self.gap("local legal-basis citations not in the index")
        # the offices and their roles: the file's office text may name several offices ("Commissioner of the
        # Revenue (assessment); City Treasurer (billing and collection)"): one item each, the remark in the
        # description, one item per distinct name in the government; the first named office's role keeps the id
        # "office", the others are named after the office
        office_key = None
        offices: list[tuple[str, str]] = []                   # (office key, label) in the file's order
        for label, remark in split_offices(spec.get("office")):
            key = SC.key_for("agency", gid, label)
            desc = f"Office of {g['name']}, {S.NAME[st]}" + (f"; {remark}" if remark else "")
            office = self.add(key, _cut(label, SC.LABEL_MAX), _cut(desc, SC.DESCRIPTION_MAX), cls("government-agency"))
            if remark and office.description != desc and remark not in office.description:
                office.description = _cut(f"{office.description}; {remark}", SC.DESCRIPTION_MAX)
            self.claim(office, "part of", gov)
            self.claim(office, "applies to jurisdiction", gov)
            ot = self.office_type_for(st, label)
            if ot:
                self.claim(office, "instance of", item(ot))   # the local office is one of the state's office type
            if key not in dict(offices):
                offices.append((key, label))
        if len(offices) > 1:
            self.gap("local office texts split into several offices")
        office_key = offices[0][0] if offices else None
        roles = {}
        office_roles: list[tuple[str, str, str]] = []         # (role key, office key, label)
        named = [("applicant", "Person using the process", SC.PRIVATE_PARTY, None)]
        for i, (okey, label) in enumerate(offices or [(None, spec.get("office") or "The office")]):
            named.append(("office" if i == 0 else SC.slug(label), label, okey, label))
        for rid, name, played, label in named:
            rk = SC.key_for("role", gid, pid, rid)
            role = self.add(rk, f"{name} ({g['name']}: {title})", f"{'office' if label else rid} in the {g['name']} process",
                            cls("legal-role"))
            self.claim(role, "applies to jurisdiction", gov)
            if played:
                self.claim(role, "played by", item(played))
            roles[rid] = rk
            if label:
                office_roles.append((rk, played, label))
        # forms
        forms: dict[str, str] = {}
        for f in spec.get("forms") or []:
            if not f.get("id"):
                continue
            fk = SC.key_for("form", gid, pid, f["id"])
            form = self.add(fk, f.get("title") or f["id"], f"Form used in the {g['name']} process “{title}”",
                            cls("government-form"))
            if f.get("number"):
                self.claim(form, "form number", string(f["number"]))
            if f.get("url") and privacy.is_office_url(f["url"]):
                self.claim(form, "official text", url(f["url"]))
            if topic:
                self.claim(form, "topic", vocab("topic", topic))
            forms[f["id"]] = fk
            self.claim(proc, "form used", item(fk))
        # steps
        step_keys = {s["id"]: SC.key_for("step", gid, pid, s["id"]) for s in spec.get("steps") or [] if s.get("id")}
        prev = None
        for i, s in enumerate(spec.get("steps") or []):
            if not s.get("id"):
                continue
            sk = step_keys[s["id"]]
            step = self.add(sk, f"{s.get('step') or s['id']} ({g['name']})", f"Step of “{title}”, {g['name']}",
                            cls("legal-process-step"))
            self.claim(step, "part of", item(pkey))
            self.claim(step, "applies to jurisdiction", gov)
            self.claim(step, "sort key", string(f"{i + 1:04d}"))
            self.claim(step, "review status", vocab("review-status", "agreed"))
            self.claim(proc, "has part", item(sk))
            if _office_acts(s.get("who")):
                self.claim(step, "bearer", item(_pick_office_role(s.get("who"), s.get("step"), office_roles) or roles["office"]))
            else:
                self.claim(step, "bearer", item(roles["applicant"]))
            if prev:
                self.claim(step, "follows", item(prev))
            prev = sk
            self._local_step_kind(step, s)
            src = s.get("source") or s.get("url") or ""
            if src and not _URL.match(src) and _CITE.search(src):   # a citation, not a page: ground in the section
                cite, pin = SC.strip_pinpoint(src)
                ssk = self.section(st, cite)
                if not ssk:
                    self.gap("local step citations not in the index")
                ground = self.ground(ssk, pin, s.get("quote"), source_url=None if ssk else page,
                                     method="software-match", retrieved=retrieved)
            else:
                ground = self.ground(None, None, s.get("quote"), source_url=src or page, method="software-match",
                                     retrieved=retrieved)
            # the deadline and fee texts of a step may repeat the page's words: under a no-reprint source only
            # the numbers are written (no "counted from", no "fee basis")
            withhold = no_reprint(src) or no_reprint(page)
            lim = parse_limit(s.get("deadline"))
            if lim:
                n, unit_, anchor = lim
                quals = [("time unit", vocab("time-unit", unit_))]
                if anchor and not withhold:
                    quals.append(("counted from", string(anchor)))
                self.claim(step, "time limit", quantity(n), quals, [ground])
            elif s.get("deadline"):
                self.gap("local deadlines not reducible to a number")
            fee = parse_fee(s.get("fee"))
            if fee:
                quals = [("fee basis", string(fee[1]))] if fee[1] and not withhold else []
                if fee[1] and withhold:
                    self.gap("fee and deadline texts withheld (NO_REPRINT host)")
                self.claim(step, "fee", quantity(fee[0], SC.USD), quals, [ground])
            elif s.get("fee"):
                self.gap("local fees not reducible to a number")
            if s.get("form") in forms:
                self.claim(step, "form used", item(forms[s["form"]]))
            if s.get("url") and privacy.is_office_url(s["url"]):
                self.claim(step, "contact page URL", url(s["url"]), references=[ground])
        # fees of the process
        for f in spec.get("fees") or []:
            fee = parse_fee(f.get("amount"))
            if not fee:
                self.gap("local fees not reducible to a number")
                continue
            fb = (f.get("basis") or "").strip()
            fsk = None
            if fb and not _URL.match(fb) and not first_url(fb) and _CITE.search(fb):   # a statute sets the fee
                fcite, fpin = SC.strip_pinpoint(fb)
                fsk = self.section(st, fcite)
            if fsk:
                fground = self.ground(fsk, fpin, f.get("quote"), method="software-match", retrieved=retrieved)
                amount_text = fee[1]
            else:
                fee_url = first_url(fb) or page
                fground = self.ground(None, None, f.get("quote"), source_url=fee_url, method="software-match",
                                      retrieved=retrieved)
                amount_text = None if (no_reprint(fee_url) or no_reprint(page)) else fee[1]   # the page's words
            basis = " — ".join(x for x in (f.get("item"), amount_text) if x)
            quals = [("fee basis", string(basis))] if basis else []
            self.claim(proc, "fee", quantity(fee[0], SC.USD), quals, [fground])
        # escalation
        seen: set[str] = set()
        for e in spec.get("escalation") or []:
            type_ = SC.ESCALATION_TYPES.get((e.get("type") or "").strip())
            basis = (e.get("basis") or "").strip()
            basis_url = basis if _URL.match(basis) else None    # a page, not a citation: no section, no slug
            cite, pin = SC.strip_pinpoint(basis) if not basis_url else ("", None)
            sk = self.section(st, cite) if cite and re.search(r"§|ILCS|RCW", cite) else None
            code = type_ or "other"
            slug_ = SC.section_slug(basis, (self.row(st, cite) or {}).get("act_id") if sk else None) if sk \
                else basis_slug(basis)
            key = SC.key_for("rung", gid, pid, slug_ or "local", code)
            n = 2
            while key in seen:                            # several rungs of one type on one basis
                key = SC.key_for("rung", gid, pid, slug_ or "local", f"{code}-{n}")
                n += 1
            seen.add(key)
            rung = self.add(key, f"{e.get('type') or 'escalation'}: {_cut(e.get('next') or '', 120)} ({g['name']})",
                            _cut(e.get("trigger") or "", SC.DESCRIPTION_MAX), cls("escalation-mechanism"))
            self.claim(rung, "part of", item(pkey))
            self.claim(rung, "applies to jurisdiction", gov)
            self.claim(rung, "review status", vocab("review-status", "agreed"))
            if e.get("trigger"):
                self.claim(rung, "heading text", mono(e["trigger"]))
            if type_:
                self.claim(rung, "escalation type", vocab("escalation-type", type_))
            ground = self.ground(sk, pin, e.get("quote"), source_url=None if sk else (basis_url or page),
                                 method="software-match")
            if sk:
                self.claim(rung, "references", item(sk), references=[ground])
            lim = parse_limit(e.get("deadline"))
            if lim:
                quals = [("time unit", vocab("time-unit", lim[1]))]
                if lim[2]:
                    quals.append(("counted from", string(lim[2])))
                self.claim(rung, "time limit", quantity(lim[0]), quals, [ground])
            self.claim(proc, "escalates to", item(key))
        # contacts: for the process and for the office that owns the channel
        office = self.items.get(office_key) if office_key else None
        self.channels(proc, gid, pid, owner, mailboxes=True, retrieved=retrieved, page=page, also=office)

    def _local_step_kind(self, step: Item, s: dict) -> str | None:
        """The ``step kind`` claim of a researched local step: the file's ``kind`` when it gives one (curated),
        else the decision model's choice when ``LEXFLOW_DECIDE=1`` and its confidence is at least
        ``decide.KIND_CONFIDENCE`` (reference: determination method AI verifier); else no claim, as before.
        Returns ``file``, ``decision`` or None."""
        kind = (s.get("kind") or "").strip()
        if kind:
            if SC.key_for("vocab", "step-kind", kind) in SC.VOCAB_BY_KEY:
                self.claim(step, "step kind", vocab("step-kind", kind),
                           references=[[("determination method", vocab("determination-method", "curated"))]])
                return "file"
            self.gap(f"local steps of unknown kind ({kind})")
            return None
        if self.decider is None:
            return None
        kind, by, conf = DEC.step_kind(self.decider, s.get("step"), s.get("quote") or s.get("how"), None)
        if by == "decision" and kind:
            self.claim(step, "step kind", vocab("step-kind", kind),
                       references=[[("determination method", vocab("determination-method", "ai-verifier"))]])
            self.gap("local step kinds from the decision model")
            return "decision"
        self.gap("local steps the decision model was unsure about (no step kind)")
        return None

    # ---- case law
    def cases(self, per_section: int = 15):
        cited: dict[str, dict] = {}
        for r in db.rows(self.con, "SELECT DISTINCT state, section FROM case_law ORDER BY state, section"):
            st = r["state"]
            if not self.want(st):
                continue
            skey = self.section(st, r["section"], mint=False)
            if not skey or skey not in self.sections:
                continue
            for c in db.rows(self.con, "SELECT * FROM case_law WHERE state=? AND section=? ORDER BY cite_count DESC, "
                                       "date_filed DESC, cluster_id LIMIT ?", st, r["section"], per_section):
                e = cited.setdefault(SC.key_for("case", c["cluster_id"]), {"case": c, "sections": []})
                e["sections"].append(skey)
        for key in sorted(cited):
            c = cited[key]["case"]
            st = c["state"]
            it = self.add(key, c["case_name"] or f"Opinion {c['cluster_id']}",
                          f"{c.get('court') or 'court'}, {(c.get('date_filed') or '')[:10]}", cls("court-decision"))
            self.claim(it, "applies to jurisdiction", item(SC.key_for("jurisdiction", st)))
            if c.get("url") and privacy.is_office_url(c["url"]):
                self.claim(it, "official text", url(c["url"]))
            if c.get("citation"):
                self.claim(it, "citation", string(c["citation"]))
            self.claim(it, "CourtListener ID", ext(c["cluster_id"]))
            self.claim(it, "date decided", time(c.get("date_filed")))
            if c.get("court_id") and c["court_id"] in COURTS.get(st, []):
                self.claim(it, "court", item(self.court_key(st, c["court_id"])))
            elif c.get("court_id"):
                self.gap("decisions whose court is not in caselaw.COURTS")
            for sk in dict.fromkeys(cited[key]["sections"]):
                self.claim(it, "references", item(sk))

    # ---- the whole
    def run(self) -> list[Item]:
        self.vocabularies()
        self.jurisdictions()
        self.seed_sections()
        self.bodies()
        self.models()
        govs = self.local()
        govs |= {r["gov_id"] for r in db.rows(self.con, "SELECT DISTINCT gov_id FROM local_answers")}
        self.governments(govs)
        self.law()                                        # after models and places: they add sections
        self.cases()
        self._describe()
        self._check()
        for it in self.items.values():
            it.exists = it.key in self.existing
            it.claims.sort(key=_claim_order)
            it.aliases = sorted(dict.fromkeys(it.aliases))
        for what, n in sorted(self.gaps.items()):
            self.log(f"could not supply: {what}: {n}")
        return [self.items[k] for k in sorted(self.items)]

    def _describe(self):
        """Every new item gets a description, and no two new items share a label and a description: the wiki
        refuses to create an item whose English label and description another item already has.  Items in a
        clashing group get the tail of their key appended to the description (the step id, the actor id), and as
        much more of the key as it takes; every member of the group gets it, so the result does not depend on
        which was built first."""
        for it in self.items.values():
            if not it.description and not it.exists:
                kind = SC.kind_of(it.key)
                it.description = f"lexflow {kind} {it.key.split(':', 2)[-1]}"[:SC.DESCRIPTION_MAX]
        groups: dict[tuple[str, str], list[Item]] = {}
        for it in self.items.values():
            if not it.exists:
                groups.setdefault((it.label, it.description), []).append(it)
        for (label, desc), members in sorted(groups.items()):
            if len(members) < 2:
                continue
            self.gap("label and description clashes resolved with the key's tail", len(members))
            for depth in range(1, 6):
                tails = {it.key: ":".join(it.key.split(":")[-depth:]) for it in members}
                if len(set(tails.values())) == len(members):
                    break
            else:
                tails = {it.key: it.key for it in members}
            for it in members:
                tail = f" [{tails[it.key]}]"
                it.description = _cut(desc, SC.DESCRIPTION_MAX - len(tail)) + tail

    def _check(self):
        """Every item value points at an item in the build or an existing class label; sizes hold.  A dangling key
        fails the build (``DanglingKeyError`` lists every one), since a claim at a key no file creates would be
        skipped silently by the packet and never reach the wiki."""
        labels = {c.label for c in SC.CLASSES if c.qid}
        dangling: list[str] = []
        for it in self.items.values():
            assert len(it.label) <= SC.LABEL_MAX and len(it.description) <= SC.DESCRIPTION_MAX, it.key
            if it.cls and it.cls not in labels and it.cls not in self.items:
                dangling.append(f"{it.key}: instance of -> {it.cls}")
            for c in it.claims:
                vals = [c.value] + [v for _, v in c.qualifiers] + [v for ref in c.references for _, v in ref]
                for v in vals:
                    if v.kind == "item" and v.value not in self.items and v.value not in labels:
                        dangling.append(f"{it.key}: {c.prop} -> {v.value}")
                    if v.kind == "quantity" and v.unit and v.unit not in self.items:
                        dangling.append(f"{it.key}: {c.prop} unit -> {v.unit}")
                    if v.kind == "string" and len(v.value) > SC.STRING_MAX:
                        raise ValueError(f"{it.key}: {c.prop} string too long")
        if dangling:
            for d in dangling:
                self.log(f"dangling: {d} is not in the build")
            raise DanglingKeyError(dangling)


class DanglingKeyError(ValueError):
    """An item value names a key no item of the build carries; ``.keys`` lists ``<item>: <property> -> <key>``."""

    def __init__(self, keys: list[str]):
        self.keys = list(keys)
        shown = "; ".join(self.keys[:20]) + (f"; ... and {len(self.keys) - 20} more" if len(self.keys) > 20 else "")
        super().__init__(f"{len(self.keys)} item values point at keys the build does not emit: {shown}")


# --------------------------------------------------------------------------- helpers

_ORDER = {lab: i for i, lab in enumerate(SC.ALL_PROPERTY_LABELS)}


def _claim_order(c: Claim) -> tuple:
    return (_ORDER.get(c.prop, 999), c.value.kind, c.value.value, c.value.unit or "",
            tuple((q, v.sig()) for q, v in c.qualifiers))


def _json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _plural(word: str, n: int) -> str:
    return word if n == 1 else (word + "s")


def _unit_headings() -> dict[str, dict]:
    """``fixtures/law/unit_headings.json`` (unit key -> {name, source, retrieved}), through ``lexflow.law.headings``
    when that module offers a loader, else read directly; {} when neither is there yet."""
    data = None
    try:
        from ..law import headings as H
        for name in ("load", "headings", "read"):
            fn = getattr(H, name, None)
            if callable(fn):
                data = fn()
                break
    except Exception:  # noqa: BLE001 - written by another hand; absent or different is fine
        data = None
    if not isinstance(data, dict):
        data = _json(config.ROOT / "fixtures" / "law" / "unit_headings.json")
    out = {}
    for k, v in (data.items() if isinstance(data, dict) else []):
        if isinstance(v, dict) and v.get("name"):
            out[k] = v
        elif isinstance(v, str) and v.strip():
            out[k] = {"name": v.strip()}
    return out


def _leading_url(value: str | None) -> str | None:
    """The absolute URL a contact row's value starts with, without a remark after it (``https://x.gov/foia
    (redirects to https://y.gov/)`` -> ``https://x.gov/foia``); None when the value does not start with one."""
    first = (value or "").strip().split()[:1]
    return first[0].rstrip(",;") if first and _URL.match(first[0]) else None


def _token_name(tok: str) -> str:
    """A path element made from an act_id token when the index's path does not match the act_id: ``T48`` ->
    ``Title 48``, ``C3a`` -> ``Chapter 3a``, ``S48_3a_1103`` -> ``§ 48-3a-1103``."""
    level = SC.unit_level(None, tok)
    body = tok[1:] if len(tok) > 1 and tok[:1].isalpha() and not tok.isalpha() else tok
    if tok[:1] == "S" and "_" in tok:
        return "§ " + body.replace("_", "-")
    return f"{level.capitalize()} {body}" if level else tok


def _parent_key(st: str, r: dict) -> str:
    toks = SC.unit_tokens(r["act_id"])
    return SC.key_for("unit", st, SC.unit_prefix(r["act_id"], len(toks) - 1)) if len(toks) > 1 else \
        SC.key_for("code", st)


_ACTORS = re.compile(r"model (\w\w)/(\w+): actors?\s+([a-z_]+)(?:\s*\([^)]*\))?(?:,?\s+(?:and\s+)?([a-z_]+))?")


def _actors_of(source: str) -> list[tuple[str, str]]:
    """``"model ca/business: actor sos (Cal. Corp. Code § 17702.05)"`` -> ``[("business", "sos")]``."""
    out = []
    for m in _ACTORS.finditer(source or ""):
        q = m.group(2)
        out.append((q, m.group(3)))
        if m.group(4) and m.group(4) not in ("and",):
            out.append((q, m.group(4)))
    return out


def _model_ref_steps(ref: str | None) -> list[str]:
    """``"seek_agreement, petition_court"`` or ``"respond (decision response_type, rule B.3)"`` -> step ids."""
    out = []
    for part in re.split(r",\s*", ref or ""):
        sid = re.split(r"\s*\(", part.strip(), maxsplit=1)[0].strip()
        if re.fullmatch(r"[a-z][a-z0-9_]*", sid):
            out.append(sid)
    return out


_PERSON = re.compile(r"\b(you|your|person|applicant|requester|owner|voter|resident|taxpayer|business|petitioner|"
                     r"party|tenant|landlord|employer|contractor|buyer|seller|driver|citizen|anyone|someone)\b", re.I)


# words that mark a piece of an office text as an office's name rather than a remark
_OFFICE_WORD = re.compile(r"\b(?:office|department|dept|commissioner|treasurer|clerk|board|registrar|court|division|"
                          r"assessor|sheriff|attorney|services|bureau|director|administrator|council|authority|"
                          r"agency|unit|commission|inspections?|county|city|town)\b", re.I)
_PAREN = re.compile(r"\s*\(([^()]*)\)")
_GOV_TAIL = re.compile(r",\s*(?:the\s+)?(?:city|county|town)\s+of\s+[A-Z][\w.' -]*$", re.I)
_BY_THE = re.compile(r"\b(?:by|from|at|with|to)\s+the\s+([A-Z][\w'&. ]*?(?:Office|Department|Commissioner|Treasurer|Clerk|"
                     r"Board|Registrar|Court|Division|Assessor|Sheriff|Attorney|Administrator|Director)(?:\s+of\s+(?:the\s+)?"
                     r"[A-Z][\w'&.]*(?:\s+[A-Z][\w'&.]*)*)?)", re.I)


def _top_split(text: str) -> list[str]:
    """``text`` split at ``;`` and at a sentence end, outside parentheses."""
    parts, buf, depth = [], [], 0
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        if depth == 0 and ch == ";":
            parts.append("".join(buf))
            buf = []
        elif depth == 0 and ch == "." and i + 2 < len(text) and text[i + 1] == " " and text[i + 2].isupper()                 and buf and (buf[-1].islower() or buf[-1] == ")"):
            parts.append("".join(buf))
            buf = []
            i += 1
        else:
            buf.append(ch)
        i += 1
    parts.append("".join(buf))
    return [p.strip(" .;") for p in parts if p.strip(" .;")]


_NOT_A_NAME = re.compile(r"^(?:under|the|a|an|in|for|with|by|at|on|from|see|note|also|this|that|it|there|as|if|when|"
                         r"where|and|or|but|not|no|all|each|any|its|their)\b", re.I)
_OFFICE_HEAD = re.compile(r"\b(?:office|department|dept|commissioner|treasurer|clerk|board|registrar|court|division|"
                          r"assessor|sheriff|attorney|bureau|director|administrator|council|authority|agency|commission|"
                          r"services|inspections?)\b", re.I)


def _is_office_name(part: str) -> bool:
    return bool(part) and part[:1].isupper() and not _NOT_A_NAME.match(part) and bool(_OFFICE_WORD.search(part))


def split_offices(text: str | None) -> list[tuple[str, str | None]]:
    """A researched file's ``office`` text as ``[(office name, remark)]``: ``"Commissioner of the Revenue
    (assessment); City Treasurer (billing and collection)"`` -> ``[("Commissioner of the Revenue", "assessment"),
    ("City Treasurer", "billing and collection")]``.  Offices are split at ``;`` and at a sentence end outside
    parentheses, and at `` and `` when both halves open with an office word; a part's parenthesised remark, what
    follows a colon, and a trailing ``, City of X`` go to the remark; a part that is a remark itself ("billing
    and collection by the City Treasurer") yields the office it names, else joins the previous office's remark.
    A name never repeats in the result."""
    out: list[tuple[str, str | None]] = []
    seen: set[str] = set()

    def push(label: str, remarks: list[str]) -> None:
        label = " ".join(label.split()).strip(" ,;:.")
        if not label:
            return
        k = SC.slug(label)
        remark = "; ".join(" ".join(r.split()).strip(" ,;:.") for r in remarks if r and r.strip(" ,;:."))
        if k in seen:
            if remark:
                for i, (l, r) in enumerate(out):
                    if SC.slug(l) == k and remark not in (r or ""):
                        out[i] = (l, f"{r}; {remark}" if r else remark)
            return
        seen.add(k)
        out.append((label, remark or None))

    def note(*pieces: str) -> None:
        remark = "; ".join(" ".join(p.split()).strip(" ,;:.") for p in pieces if p and p.strip(" ,;:."))
        if out and remark:
            l, r = out[-1]
            out[-1] = (l, f"{r}; {remark}" if r else remark)

    t = " ".join((text or "").split())
    if not t:
        return out
    for part in _top_split(t):
        remarks: list[str] = []
        if ":" in _PAREN.sub("", part):
            head, after = part.split(":", 1)
            if "(" not in after or ")" in head:
                part = head
                remarks.append(after)
        for m in _PAREN.finditer(part):
            remarks.append(m.group(1))
        part = _PAREN.sub("", part).strip(" ,")
        m = _GOV_TAIL.search(part)
        if m:
            remarks.append(m.group(0).strip(" ,"))
            part = part[:m.start()].strip(" ,")
        if not part:
            note(*remarks)
            continue
        if not _is_office_name(part):
            # a remark, not a name: keep the office it names ("billing and collection by the City Treasurer")
            found = _BY_THE.search(part)
            if found and _is_office_name(found.group(1)):
                push(found.group(1), [part] + remarks)
            else:
                note(part, *remarks)
            continue
        halves = re.split(r"\s+and\s+", part)
        if len(halves) == 2 and all(_is_office_name(h) and _OFFICE_HEAD.search(" ".join(h.split()[:2])) for h in halves):
            for h in halves:
                push(h, remarks)
        else:
            push(part, remarks)
    return out


def _pick_office_role(who: str | None, step: str | None, office_roles: list[tuple[str, str, str]]) -> str | None:
    """The role of the office a local step's ``who`` names, among the process's offices; the first named office
    unless the step's ``who`` (else its action) says otherwise."""
    if not office_roles:
        return None
    for text in (who, step):
        t = " ".join((text or "").split()).lower()
        if not t:
            continue
        for rk, _, label in office_roles:
            if label.lower() in t:
                return rk
        for rk, _, label in office_roles:
            words = [w for w in re.findall(r"[a-z]{4,}", label.lower()) if w not in ("office", "city", "county", "town",
                                                                                       "department", "division", "services")]
            if words and all(w in t for w in words):
                return rk
    return office_roles[0][0]


_HOURS = re.compile(r"\s*\((?=[^()]*(?:\d\s*(?:a\.?m|p\.?m)\b|\bhours?\b|\bmonday\b|\bweekdays?\b|\bin person\b|"
                    r"\bphysical address\b|\bwalk-in\b))[^()]*\)\s*$", re.I)
_STREET_WORDS = {"street": "st", "st.": "st", "road": "rd", "rd.": "rd", "avenue": "ave", "ave.": "ave", "drive": "dr",
                 "dr.": "dr", "boulevard": "blvd", "blvd.": "blvd", "suite": "ste", "ste.": "ste", "room": "rm", "rm.": "rm",
                 "extended": "ext", "ext.": "ext", "east": "e", "west": "w", "north": "n", "south": "s", "virginia": "va",
                 "p.o.": "po", "p.o": "po", "floor": "fl", "building": "bldg", "northeast": "ne", "northwest": "nw",
                 "southeast": "se", "southwest": "sw"}


def normalise_postal(value: str | None) -> str | None:
    """An address with its whitespace collapsed, ``P. O.`` / ``P.O.`` written ``P.O.``, and a trailing remark of
    opening hours or how to visit dropped (``"605 E Main Street, Room A-130, Charlottesville, VA 22902 (in person
    Monday to Friday, 8:30 am to 4:30 pm)"`` -> the address alone)."""
    if not value:
        return value
    v = " ".join(value.split())
    v = re.sub(r"\bP\.?\s?O\.?\s+(Box|Drawer)\b", r"P.O. \1", v, flags=re.I)
    v = _HOURS.sub("", v).strip(" ,;")
    return v or None


def postal_key(value: str | None) -> str:
    """The form two addresses share when they differ only trivially: lower-case, remarks and punctuation out,
    street words abbreviated (``Street`` -> ``st``, ``Suite`` -> ``ste``)."""
    v = _PAREN.sub("", value or "").lower()
    v = re.sub(r"\bp\.?\s?o\.?\s+(box|drawer)\b", r"po \1", v)
    words = [_STREET_WORDS.get(w, w.rstrip(".")) for w in re.findall(r"[a-z0-9.'-]+", v)]
    return " ".join(w for w in words if w)


def _office_acts(who: str | None) -> bool:
    """Whether a local step's ``who`` names the office (else the person using the process)."""
    w = who or ""
    return not _PERSON.search(w) and bool(w.strip())


def build(con, *, states=None, places=None, drafts: bool = True, log: Log = print, decider=None) -> list[Item]:
    """Everything section 4 describes, as items in sorted key order; see the module docstring."""
    return Build(con, states=states, places=places, drafts=drafts, log=log, decider=decider).run()
