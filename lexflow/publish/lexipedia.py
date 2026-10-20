"""DokuWiki pages for lexipedia.xyz, in a ``lexflow:`` namespace beside the community's own pages.

    lexflow:start                          what is here (the jurisdictions and places), links to every state
    lexflow:method                         how pages are drafted and checked, what the checks do not prove, the
                                           licence of each source, corrections; and the notes for builders
    lexflow:<state>                        a state's main page: its process models, places and answered questions
    lexflow:<state>:<question>             a state process model: BPMN (bpmnio), steps with the words of the law,
                                           decision tables, what the text leaves open
    lexflow:<state>:<question id>          an answer to a question someone asked (marked for the wiki, and reviewed
                                           by a named person)
    lexflow:<state>:<place>                a place's main page: overview, contacts, one line per process
    lexflow:<state>:<place>:<question>     one process for that place (its own sub-page, not one long page)

A page named like a namespace (``lexflow:va:charlottesville``) is that namespace's start page in DokuWiki, so
each place's processes sit under its main page and the breadcrumbs follow.  When two governments in a state share
a name, the more populous keeps it and the other adds its kind or county (``lexflow:tx:oak_ridge_cooke``).  An
answer for a place with no main page is listed on the state's page.  Pages are plain DokuWiki syntax; the
BPMN is embedded with the bpmnio plugin the wiki already uses.  Write them with ``lexflow wiki-pages --out <dir>``
to review before posting.

Every page opens with the same three facts (``label``): "Drafted with an AI system from the statute text · Every
quote matched to Open US Law's copy of the official text on <date> · Not yet reviewed by a person".  A state
model's quotes are counted when the page is made, against this copy's statute text (``model_matched``), never
read from its stored metrics, and <date> is that day; without the text at hand the page says the quotes were not
matched.  After a quote fails the check the middle part says "21 of 23 quotes matched"; a page that also draws on
a place's official pages says which quotes it covers ("Every quote from the statute ..."); a researched local
process says how many of its quotes from the state code lexflow's software matched, and that the others were
checked only by an AI verifier, never "Every quote matched" from an AI's count.  lexflow:method opens with the same
label.  The last part names the person, from the operator's reviewer list, once someone on it signs the text the
page is built from on this copy: through this copy's review API (its review_log), or in this copy's own curated file;
a review that arrives through sync names no one (lexflow/signoff.py, lexflow/reviewers.py).  Time limits are printed
in the law's own words (lexflow/law/wording.py),
on the process map too, and a place's own text is marked as lexflow's words.  What is written for builders
(internal step names, process-map terms, the machine-check figures) is on lexflow:method, which every page's footer
links.
"""
from __future__ import annotations

import re
from urllib.parse import urlsplit

from .. import config, reviewers, signoff
from ..law import wording as W
from ..municipal import places as P
from ..municipal import states as S
from ..municipal import stats
from ..municipal.answer import answers_for
from ..municipal.questions import QUESTIONS
from ..pipeline import credits as C
from ..store import db
from . import notes as N

NS = "lexflow"
METHOD = f"{NS}:method"
CORRECTIONS_PLACEHOLDER = "<address to be set by the operator>"
STATUTES = "the statute text"
# the statute text every state page quotes, and the release it is matched to (statute_files records the version)
COPY = "Open US Law's copy of the official text"
SNAPSHOT = "v2026.09.1"
SNAPSHOT_DATES = {"v2026.09.1": "2026-09-30"}
LOCAL_SOURCES = "the official pages and the law they rest on"
NOT_REVIEWED = "Not yet reviewed by a person"
# lexflow:method's own label: what it was drafted from, and that the words it quotes (examples, builders' notes) are
# not matched by the software
METHOD_SOURCE = "lexflow's code and records"
METHOD_CHECK = "Quotes on this page are not matched by lexflow's software"
DISCLAIMER = ("//Information, not legal advice. Time limits are in the law's own words; a figure marked "
              "\"lexflow's count\" is lexflow's arithmetic, not the statute's.//")


def _dates(dates) -> list[str]:
    return sorted({d for d in (signoff.iso_date(x) for x in dates or []) if d})


def _when(dates) -> str:
    ds = _dates(dates)
    if not ds:
        return ""
    if len(ds) == 1:
        return f" on {signoff.long_date(ds[0])}"
    return f" between {signoff.long_date(ds[0])} and {signoff.long_date(ds[-1])}"


def _lower(text: str) -> str:
    return text[:1].lower() + text[1:]


def review_text(parts: list[tuple[str, object]]) -> str:
    """Who signed: "Reviewed by <name>, <role>, on <date>", or "Not yet reviewed by a person".  ``parts`` are
    (what, reviewer) pairs; a page built from several parts names each one's reviewer."""
    lines = [(what, signoff.line(rev)) for what, rev in parts]
    if not any(x for _, x in lines):
        return NOT_REVIEWED
    if len(lines) == 1:
        return lines[0][1]
    return "; ".join(f"{what}: {_lower(x or NOT_REVIEWED)}" for what, x in lines)


def review_summary(signers: list) -> str:
    """Who signed, for a page that lists several: none, all, or some of them.  ``signers`` are reviewers as
    ``signoff.bound`` gives them (None for a part nobody on the reviewer list has signed)."""
    signed = sum(1 for r in signers if signoff.line(r))
    if not signed:
        return NOT_REVIEWED
    if signed == len(signers):
        return "Reviewed by a person (named on each page)"
    return f"{signed} of {len(signers)} reviewed by a person (named on each page); the others not yet"


CORRECTIONS_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
CORRECTIONS_URL = re.compile(r"https?://[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+(?::\d+)?(?:[/?#][^\s<>\[\]|{}]*)?")


# the value .env.example shows (commented out): uncommenting it must not publish a corrections line to no one
ENV_EXAMPLE_CORRECTIONS = "corrections@example.org"
# names reserved for examples and tests (RFC 2606, RFC 6761)
RESERVED_DOMAINS = ("example.com", "example.org", "example.net")
RESERVED_SUFFIXES = (".example", ".invalid", ".test")
# special-use and private names that no reader outside the operator's own network can reach: this machine
# (.localhost, localhost.localdomain), the local network (.local: RFC 6762; .home.arpa: RFC 8375; .internal, and the
# private names .lan, .home, .corp, .intranet, .private and .localdomain, which no registry delegates), Tor's
# .onion (RFC 7686) and .alt (RFC 9476)
SPECIAL_SUFFIXES = (".localhost", ".localdomain", ".local", ".home.arpa", ".internal", ".lan", ".home", ".corp",
                    ".intranet", ".private", ".onion", ".alt")
# public names that point back to this machine or to the address written in them (lvh.me, 127.0.0.1.nip.io)
LOOPBACK_DOMAINS = ("lvh.me", "localtest.me", "nip.io", "sslip.io", "xip.io")
IPV4 = re.compile(r"\d{1,3}(?:\.\d{1,3}){3}")
# an IP address in any form a resolver reads as one (2130706433, 0x7f000001, 0177.0.0.1)
NUMERIC_HOST = re.compile(r"(?:0x[0-9a-f]+|\d+)(?:\.(?:0x[0-9a-f]+|\d+)){0,3}")
IP_IN_NAME = re.compile(r"(?:^|[.-])\d{1,3}(?:[.-]\d{1,3}){3}(?:[.-]|$)")
# an address that stands for no one: a placeholder local part on a placeholder domain (user@domain.com,
# name@email.com, foo@bar.com, test@test.com), or a "your domain" name
PLACEHOLDER_LOCAL = {"user", "username", "name", "yourname", "your.name", "firstname.lastname", "first.last", "you",
                     "me", "someone", "somebody", "foo", "bar", "test", "tester", "email", "mail", "address",
                     "changeme", "todo", "xxx", "x", "abc", "asdf", "example", "sample", "demo", "dummy", "info",
                     "admin", "contact"}
PLACEHOLDER_DOMAINS = {"domain.com", "domain.org", "domain.net", "email.com", "mail.com", "bar.com", "foo.com",
                       "test.com", "test.org", "company.com", "website.com", "site.com", "host.com", "server.com",
                       "acme.com", "todo.com", "x.com", "y.zz"}
# a "your domain" name as any label of the host, not only the first (www.yourdomain.com, mail.yourdomain.com,
# corrections.yourdomain.org), with at least one label after it
YOUR_DOMAIN = re.compile(r"(?:^|\.)(?:your|my)[-.]?(?:own[-.]?)?(?:domain|site|website|company|org|server|host|email|"
                         r"mail)(?:name)?\.[a-z0-9.-]+$")


def _host_of(value: str) -> tuple[str | None, str | None, str | None]:
    """(kind, host, local part) of a corrections value: ("url", host, None) for something written as an http(s)
    URL, ("email", host, local) for something with an @, else (None, None, None).  Read loosely, so a value that
    names a local host gets that reason, not "not an address"."""
    if re.match(r"(?i)https?://", value):
        try:
            return "url", (urlsplit(value).hostname or "").lower().rstrip("."), None
        except ValueError:
            return "url", "", None
    if "@" in value and not re.search(r"[\s<>]|^mailto:", value, re.I):
        local, host = value.rsplit("@", 1)
        return "email", host.lower().rstrip("."), local.lower()
    return None, None, None


def corrections_problem(value: str | None = None) -> str | None:
    """Why LEXFLOW_CORRECTIONS cannot be the address readers write to, or None when it can.  It must be an e-mail
    address or an http(s) URL, and its name must not be one the check knows stands for no reader: the example value
    from .env.example; a name reserved for examples and tests (example.com, .org and .net, any .example, .invalid or
    .test name); localhost, an IP address, or a name that points back to one (lvh.me, 127.0.0.1.nip.io); a
    special-use or private name (``SPECIAL_SUFFIXES``: .localhost, localhost.localdomain, .local, .home.arpa,
    .internal, .lan, .home, .corp, .intranet, .private, .onion, .alt); or a placeholder address (user@domain.com,
    name@email.com, foo@bar.com, test@test.com, a "yourdomain" name as any label of the host).  It cannot tell
    whether a reader's message will reach anyone: the operator answers for that."""
    value = (config.CORRECTIONS if value is None else value or "").strip()
    if not value:
        return "not set"
    if value.lower() == ENV_EXAMPLE_CORRECTIONS:
        return f"{value!r}, the example value from .env.example"
    kind, host, local = _host_of(value)
    if host == "localhost" or (host or "").endswith(".localhost") or host == "localhost.localdomain":
        return f"{value!r}, which is on {host}, a name for the operator's own machine that no reader can reach"
    if host and (IPV4.fullmatch(host) or ":" in host or host.startswith("[") or NUMERIC_HOST.fullmatch(host)):
        return f"{value!r}, which is on {host}, an IP address, not a domain name readers can reach"
    if host and (host in LOOPBACK_DOMAINS or any(host.endswith("." + d) for d in LOOPBACK_DOMAINS)
                 or IP_IN_NAME.search(host)):
        return (f"{value!r}, which is on {host}, a name that points back to the operator's machine or to the IP "
                f"address written in it")
    if host and any(host.endswith(sfx) or host == sfx[1:] for sfx in SPECIAL_SUFFIXES):
        return f"{value!r}, which is on {host}, a special-use or private name that is not in the public DNS"
    if host and (host in RESERVED_DOMAINS or any(host.endswith("." + d) for d in RESERVED_DOMAINS)
                 or any(host.endswith(sfx) for sfx in RESERVED_SUFFIXES)):
        return f"{value!r}, which is on {host}, a name reserved for examples and tests"
    if kind == "url" and not CORRECTIONS_URL.fullmatch(value) or kind == "email" and not \
            CORRECTIONS_EMAIL.fullmatch(value) or kind is None:
        return f"{value!r}, which is not an e-mail address or an http(s) URL"
    if host and (YOUR_DOMAIN.search(host) or kind == "email" and local in PLACEHOLDER_LOCAL
                 and host in PLACEHOLDER_DOMAINS):
        return f"{value!r}, a placeholder address that stands for no one"
    return None


def corrections_address() -> str | None:
    """The address readers write to (LEXFLOW_CORRECTIONS): an e-mail address or an http(s) URL on a real domain
    (``corrections_problem``), else None."""
    return None if corrections_problem() else config.CORRECTIONS.strip()


def corrections() -> str:
    """lexflow:method's line on where to report an error: the operator's address, or the placeholder."""
    return f"Corrections: {corrections_address() or CORRECTIONS_PLACEHOLDER}"


def corrections_set() -> bool:
    """Whether the operator has set where readers report an error.  Every page links lexflow:method for it, so
    until then the publish step writes nothing."""
    return corrections_address() is not None


NOT_AT_HAND = "the statute text was not at hand when this page was made"


def quote_check(dates, matched: tuple[int, int] | None = None, *, scope: str = "", count: bool = False,
                now: bool = False) -> str:
    """'Every quote matched to Open US Law's copy of the official text on <date>', or 'N of M quotes matched ...'
    when one did not, or always with ``count`` (a page with an asked answer).  ``now`` says the count was made by
    lexflow's software when the page was made (a state model's, ``model_matched``, as an asked answer's is): then,
    as with ``count``, no count means 'Quotes ... not matched by lexflow's software: the statute text was not at
    hand', never "Every quote matched".  ``scope`` says which quotes on a page that also draws on other sources ('
    from the statute')."""
    if (count or now) and not (matched and matched[1]):
        return f"Quotes{scope} not matched by lexflow's software: {NOT_AT_HAND}"
    head = (f"{matched[0]} of {matched[1]} quotes{scope} matched" if matched and (count or matched[0] < matched[1])
            else f"Every quote{scope} matched")
    return f"{head} to {COPY}{_when(dates)}"


def label(dates, review: str, *, source: str = STATUTES, matched: tuple[int, int] | None = None, scope: str = "",
          check: str | None = None, count: bool = False, now: bool = False) -> str:
    """The three public facts, in place of a model name or a score: who drafted it, what was checked and when,
    who signed.  ``matched`` is (quotes that matched, quotes checked), printed as a count with ``count``, and
    counted when the page is made with ``now`` (``quote_check``); ``check`` replaces the middle fact on a page
    whose quotes are not matched to the statute text."""
    return " · ".join([f"Drafted with an AI system from {source}",
                       check or quote_check(dates, matched, scope=scope, count=count, now=now), review])


def _head(text: str) -> list[str]:
    return [f"**{esc(text)}**", "", DISCLAIMER, ""]


def _footer(*links: str) -> list[str]:
    """The last line of every page: the way back, and the method page (sources, licences, corrections)."""
    back = f"← {' · '.join(links)} · " if links else ""
    return ["----", f"{back}[[{METHOD}|How these pages are made, sources and corrections]]", ""]


def _json(value) -> dict:
    return (db.loads(value, {}) if isinstance(value, str) else value) or {}


def model_checked_on(m: dict) -> str | None:
    """When a model's quotes were last matched to the statute text by its build: the build's own check, else the
    date in the drafting note ("Claude (...), 2026-10-10; every quote checked ..."), else when it was validated; a
    date in the future is not one (``signoff.past_date``).  Pages no longer print it: they count the quotes again
    when they are made (``model_matched``) and give that day."""
    metrics = _json(m.get("metrics"))
    note = metrics.get("reviewed_by") if isinstance(metrics.get("reviewed_by"), str) else ""
    found = re.search(r"\d{4}-\d{2}-\d{2}", note)
    return (signoff.past_date(metrics.get("checked_on")) or (found and signoff.past_date(found.group(0)))
            or signoff.past_date(_json(m.get("stages")).get("validated")) or signoff.past_date(m.get("updated_at")))


def roster(con) -> dict:
    """The reviewers a page may name: the operator's list (lexflow/reviewers.py), without those removed."""
    return reviewers.roster(con) if con is not None else {}


def model_reviewer(m: dict, con) -> dict | None:
    """The person on the reviewer list who signed this model's text (its facts, sections and notes), on a date
    neither in the future nor before the model was first built (``build.signoff_floor``: its stored first_built, or
    for a row without one the earliest build it records), and only while this copy's own curated file carries that
    sign-off (``build.file_carries``); else None.  A review in the stored row that this copy's file does not hold
    (pulled from another copy, or written into the database by hand) counts as not reviewed, with one log line per
    model."""
    from ..municipal import build as B
    metrics = _json(m.get("metrics"))
    rev = metrics.get("reviewed_by")
    if not isinstance(rev, dict) or con is None:
        return None
    who = signoff.bound(rev, signoff.model_text(m.get("facts"), metrics), roster(con), not_before=B.signoff_floor(m))
    if who and not B.file_carries(m, rev):
        signoff.unrecorded(f"the state model {m.get('model_id')}", "this copy's curated file does not carry that "
                           "sign-off (it was pulled from another copy, or written into the database by hand)")
        return None
    return who


# the quote counts made while all_pages runs, so each model is counted once a run (model_matched)
_COUNTS: dict | None = None


def model_matched(m: dict | None) -> tuple[int, int] | None:
    """(quotes that matched, quotes checked) for a state model, counted by lexflow's software when the page is
    made: its stored facts compiled again and every step, deadline and law quote matched to the statute text this
    copy holds (``build.recount``, the build's own check).  Never the count stored in its metrics, which a pull may
    bring from another copy.  None when that text is not at hand here."""
    from ..municipal import build as B
    if not m:
        return None
    key = (m.get("model_id"), signoff.text_hash(_json(m.get("facts"))),
           signoff.text_hash(_json(m.get("metrics")).get("sections") or []))
    if _COUNTS is not None and key in _COUNTS:
        return _COUNTS[key]
    c = B.recount(m)
    out = None if c is None else (int(c["quotes_checked"]) - int(c["quote_misses"]), int(c["quotes_checked"]))
    if _COUNTS is not None:
        _COUNTS[key] = out
    return out


def models_matched(rows) -> tuple[int, int] | None:
    """(quotes that matched, quotes checked) over every state model a page draws on, counted now
    (``model_matched``); None when there is none, or when the statute text of any of them is not at hand."""
    counts = [model_matched(r) for r in rows]
    if not counts or any(c is None for c in counts):
        return None
    return sum(a for a, _ in counts), sum(b for _, b in counts)


def process_checked_on(spec: dict, row: dict | None = None) -> str | None:
    """When a researched process's quotes were checked: its own record of the check, else the latest date its
    sources were retrieved, else when it was researched or loaded.  A check date in the future is not one
    (``signoff.past_date``; ``places.check_date_problem`` loads such a file as not verified)."""
    checks = spec.get("checks") if isinstance(spec.get("checks"), dict) else {}
    if spec.get("verified") and not P.is_verified(spec):
        checks = {}                       # an AI check dated before its sources were read is not this page's date
    retrieved = _dates(x.get("retrieved") for x in spec.get("sources") or [] if isinstance(x, dict))
    return (signoff.past_date(spec.get("checked")) or signoff.past_date(checks.get("date"))
            or signoff.past_date(checks.get("checked")) or (retrieved[-1] if retrieved else None)
            or signoff.iso_date(spec.get("researched")) or signoff.iso_date((row or {}).get("updated_at")))


def asked_checked_on(row: dict) -> str | None:
    """When an asked answer's quotes were taken from the statute text (not when it was ticked or signed)."""
    return signoff.iso_date(_json(row.get("metrics")).get("answered_at")) or signoff.iso_date(row.get("updated_at"))


def asked_matched(row: dict) -> tuple[int, int] | None:
    """(quotes that matched, quotes checked) for an asked answer, counted by lexflow's software when the page is
    made, with the matcher the answer was made with (ask.pipeline.recount): never the stored count, which older
    answers lack.  (0, 0) for an answer with no quotes; None when the statute text is not at hand here."""
    from ..ask import pipeline as AP
    c = AP.recount(row)
    if c is None:
        return None
    n = int(c.get("quotes_checked") or 0)
    return (n - int(c.get("quote_misses") or 0), n)


def asked_check(row: dict) -> str:
    """The middle fact of an asked answer's page: 'N of M quotes matched to Open US Law's copy of the official text
    on <the day the page was made>', counted then by lexflow's software; never "Every quote matched"."""
    m = asked_matched(row)
    if m and not m[1]:
        return "No quotes from the statute to match"
    return quote_check([db.now()], m, count=True)


def _same_review(a, b) -> bool:
    """Whether two review records are the same sign-off: reviewer, date, statement and text_hash."""
    return isinstance(a, dict) and isinstance(b, dict) and a.get("attested") is True and b.get("attested") is True \
        and a.get("reviewer") == b.get("reviewer") and a.get("text_hash") == b.get("text_hash") \
        and signoff.iso_date(a.get("date")) == signoff.iso_date(b.get("date"))


def _place_file_carries(con, loc: dict, rev) -> bool:
    """Whether this copy's own place file (curated/places/<state>/<place>.json) for this government carries the
    sign-off a stored local answer keeps: the review the loader would bind from the file (places.local_signoff) is
    that one, text_hash included."""
    import json
    lister = roster(con)
    for path in P.local_files():
        try:
            spec = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        ans = (spec.get("answers") or {}).get(loc.get("question")) if isinstance(spec, dict) else None
        if not isinstance(ans, dict) or str(spec.get("place") or "").partition(":")[0] != loc.get("state"):
            continue
        row = {**P.local_row(ans, spec), "researched": spec.get("researched")}
        if not _same_review(P.local_signoff(ans, spec, row, lister, log=lambda *_: None), rev):
            continue
        hits = P.resolve(con, spec["place"])
        if hits and hits[0]["gov_id"] == loc.get("gov_id"):
            return True
    return False


def _process_file_carries(spec: dict, rev) -> bool:
    """Whether this copy's own process file (curated/places/<state>/<place>/<process>.json) holds this text (the
    same file_hash) with this sign-off."""
    import json
    want = signoff.file_hash(spec)
    state = str(spec.get("place") or "").partition(":")[0]
    for path in P.process_files():
        if state and path.parent.parent.name != state:
            continue
        try:
            mine = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(mine, dict) and signoff.file_hash(mine) == want and _same_review(mine.get("reviewed_by"), rev):
            return True
    return False


def local_reviewer(loc: dict | None, con) -> dict | None:
    """The person on the reviewer list who signed a place's local answer as stored (its text, researched on or
    before the review), while this copy's own place file carries that sign-off (``_place_file_carries``); else
    None.  A review in the stored row that the file does not hold (pulled from another copy, or written into the
    database by hand) counts as not reviewed, with one log line per answer."""
    if not loc or con is None:
        return None
    rev = _json(loc.get("reviewed_by")) or None
    who = signoff.bound(rev, signoff.row_text(loc, signoff.LOCAL_TEXT), roster(con), not_before=loc.get("researched"))
    if who and not _place_file_carries(con, loc, rev):
        signoff.unrecorded(f"the local answer {loc.get('question')} of {loc.get('gov_id')}", "this copy's place file "
                           "does not carry that sign-off (it was pulled from another copy, or written into the "
                           "database by hand)")
        return None
    return who


def process_reviewer(spec: dict, con) -> dict | None:
    """The person on the reviewer list who signed a researched process file as it is (the file without its
    sign-off), while this copy's own process file holds that text with that sign-off (``_process_file_carries``);
    else None.  A sign-off in a stored or pulled copy that this copy's file does not hold counts as not reviewed,
    with one log line per process."""
    if con is None:
        return None
    rev = spec.get("reviewed_by")
    who = signoff.bound(rev, signoff.strip_signoffs(spec), roster(con), not_before=spec.get("researched"))
    if who and not _process_file_carries(spec, rev):
        signoff.unrecorded(f"the process {spec.get('place')}:{spec.get('process')}", "this copy's process file does "
                           "not carry that sign-off (it was pulled from another copy, or written into the database "
                           "by hand)")
        return None
    return who


AI_VERIFIED = "checked by an AI verifier against the cited page"
NOT_SOFTWARE = "not matched by lexflow's software"


def place_quote_check(row: dict, state: str) -> dict:
    """lexflow's software match of a researched process's quotes from the state code (places.check_quotes), as
    stored when the file was loaded; made again now when the stored one is for another version of the file (or
    there is none), so a page never gives a count for text it was not made from."""
    spec = row.get("spec") or {}
    qc = _json(row.get("quote_check"))
    if qc.get("hash") != signoff.text_hash(spec):
        qc = P.check_quotes(spec, state)
    return qc


def _n(n: int, what: str = "quote") -> str:
    return f"{n} {what}{'s' if n != 1 else ''}"


def local_check(spec: dict, dates, qc: dict | None = None) -> str:
    """The check fact for a researched local process: how many of its quotes lexflow's software matched word for
    word (``qc``: places.check_quotes), how many to Open US Law's copy of the state code and how many to the pages
    they cite (and of those, how many from Internet Archive copies), on the days the matches were made; then how
    many did not match, which the page lists.  "97 of 97 quotes matched by lexflow's software: 41 to Open US Law's
    copy of the Code of Virginia, 56 to the cited pages (12 from Internet Archive copies) on 12 October 2026".
    Never "Every quote", and never an AI's count: a ``qc`` for another version of the file is made again."""
    if not qc or qc.get("version") != P.QC_VERSION or qc.get("hash") != signoff.text_hash(spec):
        qc = P.check_quotes(spec, P.state_of(spec) or "va")
    n, m = int(qc.get("quotes") or 0), int(qc.get("matched") or 0)
    if not n:
        return f"Sources retrieved{_when(dates)}; no quotes to match"
    parts = []
    if qc.get("by_code"):
        parts.append(f"{qc['by_code']} to Open US Law's copy of the {qc.get('code') or 'state code'}")
    if qc.get("by_page"):
        arch = int(qc.get("by_archive") or 0)
        parts.append(f"{qc['by_page']} to the cited pages"
                     + (f" ({arch} from {'an Internet Archive copy' if arch == 1 else 'Internet Archive copies'})"
                        if arch else ""))
    text = f"{m} of {_n(n)} matched by lexflow's software" + (": " + ", ".join(parts) if parts else "")
    text += _when(qc.get("matched_on") or []) if m else ""
    if n > m:
        text += f"; {n - m} not matched (listed below)"
    return text


def _quote_item(qc: dict, where: str) -> dict:
    return (qc.get("items") or {}).get(where) or {}


def _shown_quote(qc: dict, where: str, entry: dict, quote: str | None, cites, italic: bool = False) -> str:
    """How a page prints one quote of a researched process: the words, marked when lexflow's software did not
    match them; or, from a site whose terms forbid reposting its content (quotes.NO_REPRINT; ``quotes.withheld``
    decides from the match and the quote's citations ``cites``), lexflow's own short paraphrase (the entry's
    ``paraphrase``, else the entry's own text above it) and a pointer to the page's "Words not reprinted" note,
    which says why (``_reprint_block``)."""
    from ..municipal import quotes as Q
    if not quote:
        return ""
    item = _quote_item(qc, where)
    pol = Q.withheld(item, [cites] if isinstance(cites, str) else list(cites or [])) or {}
    miss = "" if item.get("by") else f" (not matched by lexflow's software: {item.get('why') or 'not checked'})"
    if pol:
        para = entry.get("paraphrase")
        why = (f"//({esc(pol['publisher'])}'s words are not reprinted here; read them at the link. See \"Words not "
               f"reprinted\" below.)//{esc(miss)}")
        if italic:
            return (f"In lexflow's words: {esc(para)} " if para else "") + why
        return f" — {'in lexflow' + chr(39) + 's words: ' + esc(para) + ' ' if para else ''}{why}"
    if italic:
        return f"//{esc(quote)}//{esc(miss)}"
    return f" — “{esc(quote)}”{esc(miss)}"


def _reprint_block(pols: list[dict]) -> list[str]:
    """A researched process page's note on the sites whose words it does not reprint: each one's reason and terms
    (quotes.NO_REPRINT), once."""
    from ..municipal import quotes as Q
    if not pols:
        return []
    return (["===== Words not reprinted =====", ""]
            + [f"  * {esc(Q.reprint_note(p))}. "
               + ("lexflow's software matched the quotes it could read there" if p.get("fetch", True) else
                  "lexflow does not read that site, so its quotes are not matched")
               + "; lexflow's file keeps them as evidence, and this page gives lexflow's own words and the link instead"
               + (f" ([[{p['terms']}|the terms]])" if p.get("terms") else "") + "." for p in pols] + [""])


def esc(text: str) -> str:
    """Neutralise DokuWiki markup in law text and labels."""
    t = str(text or "").replace("\n", " ")
    # markup, plus DokuWiki's typography entities: (c) -> ©, (r) -> ®, (tm) -> ™ would garble "§ 4-202(c)(1)"
    return re.sub(r"(\[\[|\]\]|\{\{|\}\}|\*\*|//|__|''|\^|\||~~|<|>|%%|=====*|\((?:c|r|tm)\))",
                  lambda m: f"%%{m.group(1)}%%", t, flags=re.I)


def title_esc(text: str, heading: bool = False) -> str:
    """Text for a heading or a [[link|title]].  DokuWiki shows those raw (a %% would show), so only what would
    end the link or nest one in it is broken up; a heading also loses its outer '=' runs."""
    t = re.sub(r"([\[\]{}])(?=\1)", r"\1 ", str(text or "").replace("\n", " "))
    return t.strip().strip("=").strip() if heading else t


def state_page(state: str, question: str) -> str:
    return f"{NS}:{state}:{question}"


def _named(con, state: str, s: str) -> list[dict]:
    """Governments in a state whose place slug is ``s``."""
    like = "%" + "%".join(s.removesuffix("_county").split("_")) + "%"
    return [h for h in db.rows(con, "SELECT * FROM governments WHERE state=? AND name LIKE ?", state, like)
            if P.place_slug(h) == s]


def _tags(g: dict) -> tuple[str, str]:
    """The kind its name gives ('borough' for 'Borough of Litchfield', else the Census kind) and its county."""
    m = P.PREFIX.match(g["name"])
    return P.slug(m.group(1)) if m else g["kind"], P.slug(g.get("county_name") or "")


def place_segment(con, g: dict) -> str:
    """A place's name in page ids: its slug, unless another government in the state has the same one.  Then the
    most populous keeps the slug and each other one adds its kind or county (its gov_id as a last resort)."""
    s = P.place_slug(g)
    same = sorted(_named(con, g["state"], s), key=lambda h: (-(h["population"] or 0), h["gov_id"]))
    if len(same) < 2 or same[0]["gov_id"] == g["gov_id"]:
        return s
    mine, others = _tags(g), [_tags(h) for h in same if h["gov_id"] != g["gov_id"]]
    for pick in ((0,), (1,), (0, 1)):
        want = [mine[i] for i in pick]
        seg = "_".join([s] + want)
        if all(want) and all([t[i] for i in pick] != want for t in others) and not _named(con, g["state"], seg):
            return seg
    return f"{s}_{g['gov_id']}"


def place_page(g: dict, con=None) -> str:
    """A place's main page; pass ``con`` so that same-named governments in one state get distinct pages."""
    return f"{NS}:{g['state']}:{place_segment(con, g) if con is not None else P.place_slug(g)}"


def place_process_page(g: dict, question: str, con=None) -> str:
    return f"{place_page(g, con)}:{question}"


def has_place_page(con, gov_id: str | None) -> bool:
    """Whether a government gets a main page (it has checked local answers or a verified researched process)."""
    return bool(gov_id and (
        db.scalar(con, "SELECT 1 FROM local_answers l JOIN governments g ON g.gov_id=l.gov_id "
                       "WHERE l.gov_id=? LIMIT 1", gov_id)
        or db.scalar(con, "SELECT 1 FROM place_processes WHERE gov_id=? AND verified=1 LIMIT 1", gov_id)))


CATEGORY_TITLE = {
    "records": "Public records", "business": "Business", "permits_construction": "Building and construction permits",
    "zoning_land_use": "Zoning and land use", "taxes_assessments": "Taxes and assessments", "tax_relief": "Tax relief",
    "utilities_services": "Utilities and services", "public_safety": "Public safety", "courts_legal": "Courts and legal",
    "elections": "Elections", "health_social_services": "Health and social services",
    "transportation_parking": "Transportation and parking", "parks_events": "Parks and events", "animals": "Animals",
    "housing": "Housing", "other": "Other"}


def place_processes(con, gov_id: str, verified_only: bool = True) -> list[dict]:
    """A place's researched processes (curated/places/<state>/<place>/<process>.json), by category and title, with
    their titles in reader's words (``notes.title_without_drafting``).  ``verified_only`` keeps those that count as
    verified now (``places.is_verified``: a row loaded by older code is checked again)."""
    rows = db.rows(con, "SELECT * FROM place_processes WHERE gov_id=?" + (" AND verified=1" if verified_only else "")
                   + " ORDER BY category, title", gov_id)
    for r in rows:
        r["spec"] = db.loads(r.get("spec"), {}) or {}
        if r.get("title"):
            r["title"] = N.title_without_drafting(r["title"])
    return [r for r in rows if not verified_only or P.is_verified(r["spec"])]


def local_process_page(g: dict, process: str, con=None) -> str:
    """A researched process's page under its place; an id that a state model's sub-page uses gets a suffix."""
    pid = re.sub(r"[^a-z0-9_]+", "_", process.lower()).strip("_")
    return f"{place_page(g, con)}:{pid + '_p' if pid in QUESTIONS else pid}"


LOCAL_CAUTION = "//Procedures, fees and forms change; follow the links to the office before you act.//"


def reader_caveats(caveats) -> list[str]:
    """A place file's caveats as a page prints them: without the notes the researching and checking AI passes wrote
    about their own work (``notes.without_drafting``); the file is not changed."""
    return [c for c in (N.without_drafting(x) for x in caveats or [] if isinstance(x, str)) if c]


def source_title(src: dict) -> str:
    """A source's title as a page prints it, without drafting notes ("(lexflow index row 30394), added by the
    verifier"), or its address."""
    return N.title_without_drafting(src.get("title") or "") or src.get("url") or ""


def _quote(q: str | None) -> str:
    return f" — “{esc(q)}”" if q else ""


def _link(url: str | None, text: str) -> str:
    return f"[[{url}|{title_esc(text)}]]" if url and url.startswith("http") else esc(text)


def render_local_process(con, g: dict, row: dict) -> str:
    """One researched local process: what it is for, the law it rests on, the steps, forms, fees, contacts, what to
    do if it goes wrong, caveats and sources.  The label gives lexflow's software match of its quotes
    (``local_check``); a quote that did not match is marked where it stands and listed under "Quotes not matched";
    a quote from a site whose terms forbid reposting its content is replaced by lexflow's paraphrase, the link and
    why (``_shown_quote``).  Caveats and source titles are printed as the file words them, after a last check that
    logs any drafting words left (``places.drafting_left``)."""
    from ..municipal import quotes as Q
    s = row["spec"]
    title = s.get("title") or row["process"]
    L = [f"====== {title_esc(title + ' (' + g['name'] + ')', True)} ======", ""]
    dates = [process_checked_on(s, row)]
    qc = place_quote_check(row, g["state"])
    if qc.get("version") != P.QC_VERSION or qc.get("hash") != signoff.text_hash(s):
        qc = P.check_quotes(s, g["state"])
    L += _head(" · ".join([local_check(s, dates, qc), "Drafted with an AI system",
                           review_text([("", process_reviewer(s, con))])]))
    L += [LOCAL_CAUTION, ""]
    if s.get("question"):
        L += [f"**{esc(s['question'])}**", ""]
    if s.get("summary"):
        L += [esc(s["summary"]), ""]
    if s.get("office"):
        L += [f"//Office:// {esc(s['office'])}", ""]

    cites = {w: c for w, _, c in P.process_quotes(s)}             # each quote's citation fields

    def kept(where, quote):
        """The quote, unless its site's words may not be reprinted (a deadline is then put in lexflow's words)."""
        return None if Q.withheld(_quote_item(qc, where), cites.get(where)) else quote
    if s.get("legal_basis"):
        L += ["===== The law =====", ""] + [f"  * {_link(x.get('url'), x.get('citation') or 'source')}"
                                             f"{' (' + esc(x['role']) + ')' if x.get('role') else ''}"
                                             + _shown_quote(qc, f"legal_basis[{i}]", x, x.get("quote"),
                                                            cites.get(f"legal_basis[{i}]"))
                                             for i, x in enumerate(s["legal_basis"])] + [""]
    forms = {f.get("id"): f for f in s.get("forms") or []}
    if s.get("steps"):
        L += ["===== Steps =====", ""]
        for i, st in enumerate(s["steps"]):
            q = kept(f"steps[{i}]", st.get("quote"))
            extra = [f"time limit: {esc(W.describe_text(st['deadline'], q))}" if st.get("deadline") else "",
                     f"fee: {esc(st['fee'])}" if st.get("fee") else "",
                     f"form: {_link(forms[st['form']].get('url'), forms[st['form']].get('title') or st['form'])}"
                     if st.get("form") in forms else ""]
            extra = " · ".join(x for x in extra if x)
            L.append(f"  - **{esc(st.get('step', ''))}**" + (f" — {esc(st['who'])}" if st.get("who") else "")
                     + (f". {esc(st['how'])}" if st.get("how") else "") + (f" ({extra})" if extra else "")
                     + (f" {_link(st.get('url'), 'source')}" if st.get("url") else ""))
            if st.get("quote"):
                shown = _shown_quote(qc, f"steps[{i}]", st, st["quote"], cites.get(f"steps[{i}]"), italic=True)
                L.append(f"    * {shown.strip()}")
        L.append("")
    if forms:
        L += ["===== Forms =====", ""] + [f"  * {_link(f.get('url'), f.get('title') or f.get('id') or 'form')}"
                                          + (f" ({esc(f['number'])})" if f.get("number") else "") for f in forms.values()] + [""]
    if s.get("fees"):
        L += ["===== Fees =====", ""] + [f"  * {esc(f.get('item', ''))}: {esc(f.get('amount', ''))}"
                                         f"{' (' + _link(f.get('basis'), 'basis') + ')' if f.get('basis') else ''}"
                                         for f in s["fees"]] + [""]
    if s.get("contacts"):
        L += ["===== Who to contact =====", ""] + _contacts_block(s["contacts"]) + [""]
    if s.get("escalation"):
        L += ["===== If it goes wrong =====", ""]
        for i, e in enumerate(s["escalation"]):
            q = kept(f"escalation[{i}]", e.get("quote"))
            L.append(f"  * **{esc(e.get('trigger', ''))}**: {esc(e.get('next', ''))}"
                     + (f" ({esc(e['type'])})" if e.get("type") else "")
                     + (f"; time limit: {esc(W.describe_text(e['deadline'], q))}" if e.get("deadline") else "")
                     + (f" — {esc(e['basis'])}" if e.get("basis") else "")
                     + _shown_quote(qc, f"escalation[{i}]", e, e.get("quote"), cites.get(f"escalation[{i}]")))
        L.append("")
    misses = qc.get("unmatched") or []
    if misses:
        what = {"legal_basis": "The law", "steps": "Step", "fees": "Fee", "escalation": "If it goes wrong"}
        L += ["===== Quotes not matched =====", "",
              "//lexflow's software did not find these quotes word for word in the text they cite, so this process "
              "is not counted as checked. Read the cited page before relying on them.//", ""]
        for x in misses:
            kind, _, num = x["where"].partition("[")
            n = int(num.rstrip("]") or 0)
            entry = (s.get(kind) or [None] * (n + 1))[n] if n < len(s.get(kind) or []) else {}
            quote = (entry or {}).get("quote")
            pol = Q.withheld(_quote_item(qc, x["where"]) or x, cites.get(x["where"]))
            shown = (f"//({esc(pol['publisher'])}'s words are not reprinted here; see \"Words not reprinted\")//"
                     if pol else f"“{esc(quote)}”")
            L.append(f"  * {what.get(kind, kind)} {n + 1}: {shown} — {esc(x.get('why') or 'not matched')}")
        L.append("")
    held = {}
    for w, c in cites.items():
        pol = Q.withheld(_quote_item(qc, w) or next((x for x in misses if x["where"] == w), None), c)
        if pol:
            held.setdefault(pol["host"], pol)
    L += _reprint_block(list(held.values()))
    P.drafting_left(f"{g['state']}:{row.get('process')}", [s.get("title")] + list(s.get("caveats") or [])
                    + [x.get("title") for x in s.get("sources") or [] if isinstance(x, dict)])
    caveats = [c for c in s.get("caveats") or [] if isinstance(c, str) and c.strip()]
    if caveats:
        L += ["===== Caveats =====", ""] + [f"  * {esc(c)}" for c in caveats] + [""]
    srcs = [x for x in s.get("sources") or [] if x.get("url")]
    if srcs:
        L += ["===== Sources =====", ""] + [f"  * {_link(x['url'], x.get('title') or x['url'])}"
                                            + (f" (retrieved {esc(x['retrieved'])})" if x.get("retrieved") else "")
                                            for x in srcs] + [""]
    L += _footer(f"[[{place_page(g, con)}|{title_esc(g['name'])}]]",
                 f"[[{state_index_page(g['state'])}|{title_esc(S.NAME[g['state']])}]]")
    return "\n".join(L)


def state_index_page(state: str) -> str:
    return f"{NS}:{state}"


def asked_page(con, row: dict) -> str:
    """Where an asked question's answer lives: under the place, or under the state.  A question id that would
    collide with a state model or a place page gets a suffix."""
    qid = re.sub(r"[^a-z0-9_]+", "_", row["question_id"].lower())
    if row.get("gov_id"):
        g = db.one(con, "SELECT * FROM governments WHERE gov_id=?", row["gov_id"])
        if g:
            return f"{place_page(g, con)}:{qid if qid not in QUESTIONS else qid + '_q'}"
    # "start" too: lexflow:<state>:start would be DokuWiki's start page for the state's namespace
    taken = set(QUESTIONS) | {"start"} | {place_segment(con, g) for g in db.rows(
        con, "SELECT DISTINCT g.* FROM local_answers l JOIN governments g ON g.gov_id=l.gov_id WHERE g.state=?",
        row["state"])}
    return f"{NS}:{row['state']}:{qid if qid not in taken else qid + '_q'}"


CELL = {"true": "yes", "false": "no", "-": "any"}
HIT_POLICY = {"FIRST": "The first row that fits applies.", "UNIQUE": "Only one row can fit."}


def _table(d: dict) -> list[str]:
    head = "^ " + " ^ ".join(esc(c["label"]) for c in d["inputs"]) + " ^ " + \
        " ^ ".join(f"→ {esc(c['label'])}" for c in d["outputs"]) + " ^ Source ^"
    rows = [head]
    for r in d["rules"]:
        src = r.get("source") or {}
        sub = "".join(f"({p})" for p in (src.get("subsection") or "").split(".") if p)
        cells = [esc(CELL.get(str(x).strip().strip('"').lower(), str(x).strip().strip('"'))) for x in r["when"] + r["then"]]
        rows.append("| " + " | ".join(cells + [f"§ {esc(src.get('section', ''))}{sub}"]) + " |")
    return rows


TIMER = re.compile(r'<(?:bpmn:)?(?:boundaryEvent|intermediateCatchEvent)\b[^>]*>')
NAME_ATTR = re.compile(r'\bname="[^"]*"')
ID_ATTR = re.compile(r'\bid="([^"]+)"')


def relabel_timers(bpmn: str, facts: dict | None) -> str:
    """The process map with every time limit's timer named in the statute's words (lexflow/law/wording.py), as the
    compiler names them, so a map stored before that (or pulled from another machine) never shows lexflow's unit."""
    steps = {x.get("id"): x for x in (facts or {}).get("steps") or []}

    def name(m):
        tag = m.group(0)
        found = ID_ATTR.search(tag)
        tid = found.group(1) if found else ""
        sid, waiting = ((tid[:-len("_deadline")], False) if tid.endswith("_deadline") else
                        (tid[:-len("_timeout")], True) if tid.endswith("_timeout") else (None, False))
        step = steps.get(sid)
        text = W.timer_label(step, facts, waiting=waiting) if step and step.get("deadline") else None
        if not text:
            return tag
        attr = 'name="' + text.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;") + '"'
        if NAME_ATTR.search(tag):
            return NAME_ATTR.sub(lambda _: attr, tag, count=1)
        return tag.replace(found.group(0), f"{found.group(0)} {attr}", 1)
    return TIMER.sub(name, bpmn or "")


BPMN_DRAWN = {"http://www.omg.org/spec/BPMN/20100524/MODEL", "http://www.omg.org/spec/BPMN/20100524/DI",
              "http://www.omg.org/spec/DD/20100524/DC", "http://www.omg.org/spec/DD/20100524/DI",
              "http://www.w3.org/2001/XMLSchema-instance"}
BPMN_NS = "{http://www.omg.org/spec/BPMN/20100524/MODEL}"
GROUNDING_TAG = re.compile(r" ?\[(?:implied|assumed)\]")


def relabel_paths(root, facts: dict | None) -> None:
    """The names a map draws where a path is chosen or ends, as the compiler gives them now (extract/compile.py):
    the plain sentence of the step or outcome a path leads to, never a condition's id ("articles ok?", "Not
    doing business not exempt"), and labels in full or cut at a word boundary, never mid-word.  A map stored by
    older code, or pulled from another machine, is named the same way on the page; for a map built now this changes
    nothing."""
    from ..extract import compile as CF
    if not facts:
        return
    steps = {x.get("id"): x for x in facts.get("steps") or [] if isinstance(x, dict)}
    outcomes = {x.get("id"): x for x in facts.get("outcomes") or [] if isinstance(x, dict)}
    said = {k: v.get("action") or "" for k, v in steps.items()} | {k: v.get("description") or "" for k, v in
                                                                      outcomes.items()}
    cond_of = {k: v.get("condition") or v.get("when") for k, v in list(steps.items()) + list(outcomes.items())}
    by_cond: dict[str, str] = {}
    for k, c in cond_of.items():
        if c:
            by_cond.setdefault(c, k)
    olds = {c.replace("_", " ") for c in by_cond}
    for el in root.iter():
        if not isinstance(el.tag, str) or not el.tag.startswith(BPMN_NS):
            continue
        tag, eid, name = el.tag[len(BPMN_NS):], el.get("id") or "", el.get("name")
        if tag == "sequenceFlow":
            ce = el.find(f"{BPMN_NS}conditionExpression")
            cond = (ce.text or "").strip() if ce is not None else ""
            if cond in by_cond and name not in ("Yes", "No", "otherwise"):
                # the step the flow leads to (through its join, merge or wait), else the first with that condition
                base = re.sub(r"_(?:join|merge|wait)$", "", el.get("targetRef") or "")
                item = base if cond_of.get(base) == cond else by_cond[cond]
                el.set("name", CF.short(said[item], CF.FLOW_LABEL_MAX))
        elif tag == "startEvent" and eid == "start" and facts.get("trigger"):
            el.set("name", CF.short(facts["trigger"]))
        elif tag == "endEvent" and eid in outcomes:
            el.set("name", CF.short(said[eid]))
        elif tag == "endEvent" and name is not None and (name in {f"Not {c}"[:60] for c in olds} or
                                                         re.search(r"_not_[a-z0-9_]+$", eid) and name.startswith("Not ")):
            el.set("name", CF.OTHERWISE_END)
        elif tag == "endEvent" and eid.endswith("_deadline_end") and (name or "").startswith("Deadline missed: ") and \
                eid[:-len("_deadline_end")] in steps:
            el.set("name", CF.short(f"Deadline missed: {said[eid[:-len('_deadline_end')]]}"))
        elif tag == "exclusiveGateway" and name and name.endswith("?") and name[:-1] in olds:
            # the step its "Yes" flow leads to
            yes = next((re.sub(r"_(?:join|merge|wait)$", "", f.get("targetRef") or "") for f in
                        root.iter(f"{BPMN_NS}sequenceFlow") if f.get("sourceRef") == eid and f.get("name") == "Yes"), "")
            target = yes if yes in said else next(by_cond[c] for c in by_cond if c.replace("_", " ") == name[:-1])
            el.set("name", CF.ask(said[target]))
        elif tag == "eventBasedGateway" and eid.endswith("_wait") and eid[:-len("_wait")] in steps:
            el.set("name", CF.ask(f"{said[eid[:-len('_wait')]]} in time"))
        elif tag == "intermediateCatchEvent" and eid in steps and name is not None:
            el.set("name", CF.short(said[eid]))


SNAKE_ID = re.compile(r"\b[a-z0-9]+(?:_[a-z0-9]+)+\b")
ID_START = re.compile(r"A [a-z0-9_]+ process(?: b(?:e(?:g(?:i(?:ns?)?)?)?)?)?…?")
ID_TRIGGER = re.compile(r"\bA [a-z0-9]+(?:_[a-z0-9]+)+ process begins\b")


def plain_question_labels(root, question: str | None, question_id: str | None = None) -> None:
    """Start and end labels that carry a question id, in the question's plain words: an asked answer's map starts
    with "A criminal_record_expunged_sealed process begins" (its trigger is made from the id), which the page draws
    as "How do I get my criminal record expunged or sealed?".  Any other id in a start or end label is replaced by
    the question in quotation marks.  The same trigger in a ``documentation`` text (the collaboration's, which
    DokuWiki indexes with the page) becomes the question too."""
    from ..extract import compile as CF
    words = " ".join(str(question or "").split()).rstrip("?").strip()
    if not words:
        return
    asked = f"{words}?"

    def plain(text: str) -> str:
        return SNAKE_ID.sub(lambda m: f"“{asked}”" if not question_id or question_id.startswith(m.group(0))
                            or m.group(0).startswith(question_id) else m.group(0).replace("_", " "), text)
    for el in root.iter():
        if not isinstance(el.tag, str):
            continue
        tag = el.tag[len(BPMN_NS):] if el.tag.startswith(BPMN_NS) else ""
        if tag == "documentation" and el.text and ID_TRIGGER.search(el.text):
            el.text = ID_TRIGGER.sub(asked, el.text)
            continue
        if tag not in ("startEvent", "endEvent"):
            continue
        name = el.get("name") or ""
        if not SNAKE_ID.search(name):
            continue
        el.set("name", CF.short(asked if ID_START.fullmatch(name) else plain(name)))


def reader_bpmn(bpmn: str, facts: dict | None, *, question: str | None = None, question_id: str | None = None) -> str:
    """The process map as a page embeds it: the diagram and its timers, named in the statute's words
    (``relabel_timers``), and the names where a path is chosen or ends in plain sentences (``relabel_paths``),
    without what only builders use.  On an asked answer's map, a start or end label made from the question id is
    the question in its plain words (``plain_question_labels``).  DokuWiki indexes the page source for search, so the builders' layer stays out
    of it: every ``extensionElements`` block (lexflow's notes on what the text leaves open, ``lex:gap``; its actors,
    norms, grounding and deadline records; the workflow engine's decision links), attributes in other namespaces
    (``camunda:decisionRef``), each flow's condition expression (a variable id such as ``articles_ok``; the flow
    keeps its name), the grounding tags in the source lines ("[implied]"), and each timer's machine duration
    (``P5D`` for "five working days": lexflow's own arithmetic, which the page does not show).  bpmn-js draws none
    of these; the stored model, with all of them, is unchanged."""
    from lxml import etree
    text = relabel_timers(bpmn, facts).strip()
    if not text:
        return text
    try:
        root = etree.fromstring(text.encode("utf-8"), etree.XMLParser(remove_blank_text=False, resolve_entities=False,
                                                                       no_network=True))
    except etree.XMLSyntaxError:
        return text
    relabel_paths(root, facts)
    # an asked answer's map (its trigger made from the question id) names the question; a state model's is unchanged
    made_from_id = bool(ID_TRIGGER.fullmatch(str((facts or {}).get("trigger") or "")))
    plain_question_labels(root, question or ((facts or {}).get("process_name") if made_from_id else None), question_id)
    for el in list(root.iter(f"{BPMN_NS}extensionElements")):
        el.getparent().remove(el)
    # a flow's condition is a variable id (articles_ok, denied_in_whole_or_part): the flow keeps its plain name
    for el in list(root.iter(f"{BPMN_NS}conditionExpression")):
        el.getparent().remove(el)
    # the grounding tags lexflow writes into each source line ("Code of Virginia § 2.2-3704(E) [implied]: ...")
    for el in root.iter(f"{BPMN_NS}documentation"):
        if el.text:
            el.text = GROUNDING_TAG.sub("", el.text)
    for el in root.iter(f"{BPMN_NS}timerEventDefinition"):
        for expr in [c for c in el if isinstance(c.tag, str) and etree.QName(c).localname in
                     ("timeDuration", "timeDate", "timeCycle")]:
            el.remove(expr)
    for el in root.iter():
        if not isinstance(el.tag, str):
            continue
        for a in [a for a in el.attrib if a.startswith("{") and a[1:a.index("}")] not in BPMN_DRAWN]:
            del el.attrib[a]
    etree.cleanup_namespaces(root)
    out = etree.tostring(root, encoding="unicode")
    # the same layout as before: the indentation left by a removed block is collapsed
    out = re.sub(r"\n[ \t]*(?=\n)", "", out)
    return "<?xml version='1.0' encoding='UTF-8'?>\n" + out


def _time_limit(step: dict) -> str:
    """' · time limit: “within five working days”' (or lexflow's count), from a steps_of() step."""
    ld = step.get("law_deadline")
    return f" · time limit: {esc(ld['text'])}" if ld else ""


def render_state_model(con, state: str, question: str) -> str | None:
    m = stats.model_detail(con, f"{state}.{question}")
    if not m or not m.get("bpmn"):
        return None
    q = QUESTIONS[question]
    law = m.get("law") or {}
    metrics = m.get("metrics") or {}
    facts = m.get("facts") or {}
    L = [f"====== {title_esc(m['title'] or q.title, True)} ======", "", f"**{esc(S.NAME[state])} · {esc(q.title)}**", ""]
    # the quotes are counted again now, against this copy's statute text (model_matched), and dated today
    L += _head(label([db.now()], review_text([("", model_reviewer(m, con))]), matched=model_matched(m), now=True))
    if law.get("citation"):
        L += [f"**Governing law:** [[{law['url']}|{title_esc(law['citation'])}]]"
              + (f" — {esc(law['heading'])}" if law.get("heading") else ""), ""]
    L += ["===== Process map =====", "", "<bpmnio type=\"bpmn\">", reader_bpmn(m["bpmn"], facts), "</bpmnio>", "",
          "===== Steps and the words they come from =====", ""]
    for s in stats.steps_of(m):
        duty = f" · //{s['modality']}//" if s.get("modality") and s["modality"] != "none" else ""
        quote = f" \\\\ “//{esc(s['quote'])}//”" if s.get("quote") else ""     # DokuWiki line break, same item
        L.append(f"  - **{esc(s['step'])}** — {esc(s['who'])}{_time_limit(s)}{duty} ({esc(s['cite'])}){quote}")
    L.append("")
    for d in facts.get("decisions", []):
        L += [f"===== {title_esc(d['question'], True)} =====", ""]
        L += ([HIT_POLICY[d["hit_policy"]], ""] if d.get("hit_policy") in HIT_POLICY else [])
        L += _table(d) + [""]
    reader, builder = N.split(metrics, facts)
    if reader or builder:
        L += ["===== What the text leaves open =====", ""] + [f"  * {esc(g)}" for g in reader]
        if builder:
            L += ["" if reader else None,
                  f"//{'More notes' if reader else 'Notes'} on what the text leaves open, written for the people who "
                  f"build the models, are on [[{METHOD}#notes_for_builders|the method page]].//"]
        L.append("")
    if m.get("cases"):
        L += ["===== Court decisions citing this law =====", "",
              "//Found with [[https://www.courtlistener.com|CourtListener]] (Free Law Project): opinions in the state's "
              "appellate courts whose text cites these sections. Listed for research; not every citing case "
              "construes the section.//", ""]
        for c in m["cases"][:20]:
            cite = f", {esc(c['citation'])}" if c.get("citation") else ""
            L.append(f"  * [[{c['url']}|{title_esc(c['case_name'])}]] ({esc(c.get('court') or '')}, "
                     f"{esc((c.get('date_filed') or '')[:4])}{cite}) — cites § {esc(c['section'])}")
        L.append("")
    places = [r for r in db.rows(con, "SELECT g.* FROM local_answers l JOIN governments g ON g.gov_id=l.gov_id "
                                      "WHERE l.state=? AND l.question=?", state, question)]
    if places:
        L += ["===== Local answers =====", ""] + [f"  * [[{place_process_page(g, question, con)}|{title_esc(g['name'])}]]"
                                                  for g in places] + [""]
    L += _footer(f"[[{state_index_page(state)}|{title_esc(S.NAME[state])}]]", f"[[{NS}:start|lexflow models]]")
    return "\n".join(x for x in L if x is not None)


def _contacts_block(contacts: list[dict]) -> list[str]:
    out = []
    for c in contacts:
        v = c.get("value") or c.get("url") or ""
        if v.startswith("http"):
            out.append(f"  * [[{v}|{title_esc(c.get('label') or v)}]]")
        elif "@" in v and " " not in v:
            out.append(f"  * {esc(c.get('label', ''))}: [[{v}]]")
        else:
            out.append(f"  * {esc(c.get('label') or c.get('kind', ''))}: {esc(v)}")
    return out


def asked_reviewer(row: dict, con) -> dict | None:
    """The person on the reviewer list who reviewed this text of an asked answer (its ``reviewed_by`` column, whose
    text_hash must be the stored answer's, dated on or after the day the answer was made), recorded through this
    copy's review API with that reviewer's own token (``reviewers.asked_reviewer``: this copy's review_log holds
    it); or None.  A review pulled from another copy, or written into the database by hand, names no one."""
    if con is None:
        return None
    return reviewers.asked_reviewer(con, row, roster(con))


def wiki_ready(row: dict, con) -> bool:
    """An asked answer goes on the wiki only when it is marked for it and a person on the reviewer list has
    reviewed it."""
    return bool(row.get("published")) and asked_reviewer(row, con) is not None


def published_asked(con, *, state: str | None = None, gov_id: str | None = None) -> list[dict]:
    """Asked-question answers for the wiki (state answers when gov_id is None and state is given): marked for it
    and reviewed by a named person."""
    sql = "SELECT * FROM asked_answers WHERE published=1"
    args: list = []
    if gov_id:
        sql += " AND gov_id=?"
        args.append(gov_id)
    elif state:
        sql += " AND state=? AND gov_id IS NULL"
        args.append(state)
    from ..ask import prefer
    return [r for r in prefer.preferred(db.rows(con, sql + " ORDER BY question_id", *args)) if wiki_ready(r, con)]


def render_place(con, gov_id: str) -> str:
    """A place's main page: what it is, whom to contact, and one line per process (each on its own sub-page)."""
    d = answers_for(con, gov_id)
    g = d["government"]
    locs = [a["local"] for a in d["answers"].values() if a.get("local")]
    procs = place_processes(con, gov_id)
    mrows = [r for r in (_model_row(con, a.get("model_id")) for a in d["answers"].values()) if r]
    signers = [local_reviewer(x, con) for x in locs] + [process_reviewer(p["spec"], con) for p in procs]
    researched = ([x.get("researched") or x.get("updated_at") for x in locs]
                  + [process_checked_on(p["spec"], p) for p in procs])
    # the page links the state law's pages (whose quotes are matched, counted again now) and the local ones (whose
    # words are not)
    check = (quote_check([db.now()], models_matched(mrows), scope=" from the statute", now=True)
             if mrows else f"Researched from the official pages{_when(researched)}")
    L = [f"====== {title_esc(g['name'], True)} ======", "",
         f"{g['kind'].title()}, {S.NAME[g['state']]}" + (f" · population {g['population']:,}" if g.get("population") else "")
         + (f" · [[{g['website']}|official website]]" if g.get("website") else ""), ""]
    L += _head(label([], review_summary(signers) if signers else NOT_REVIEWED, source=LOCAL_SOURCES, check=check))
    L += ["===== Processes =====", "",
          "Each process has its own page: what state law requires, what this place adds, whom to contact and the "
          "sources.", ""]
    for qid, q in QUESTIONS.items():
        a = d["answers"].get(qid)
        if not a:
            L.append(f"  * {esc(q.title)} — not answered yet")
            continue
        L.append(f"  * [[{place_process_page(g, qid, con)}|{title_esc(q.title)}]]"
                 + (" — with the local procedure" if (a.get("local") or {}).get("summary") else ""))
    if procs:
        L += ["", "===== Local processes =====", "",
              "//Researched from the official pages and the law they rest on.//", ""]
        for cat in dict.fromkeys(p.get("category") or "other" for p in procs):
            L += [f"==== {title_esc(CATEGORY_TITLE.get(cat, cat.replace('_', ' ').title()), True)} ====", ""]
            L += [f"  * [[{local_process_page(g, p['process'], con)}|{title_esc(p.get('title') or p['process'])}]]"
                  + (f" — {esc(p['office'])}" if p.get("office") else "")
                  for p in procs if (p.get("category") or "other") == cat]
            L.append("")
    asked = published_asked(con, gov_id=gov_id)
    if asked:
        L += ["", "===== Other questions =====", "",
              "//Answers to questions people asked, drafted with an AI system from the statute text; each page names "
              "the person who reviewed it.//", ""]
        L += [f"  * [[{asked_page(con, r)}|{title_esc(r['question_text'])}]]" for r in asked]
    contacts = []
    for a in d["answers"].values():
        for c in ((a.get("local") or {}).get("contacts") or []):
            if c not in contacts:
                contacts.append(c)
    if contacts:
        L += ["", "===== Contacts =====", ""] + _contacts_block(contacts)
    L += [""] + _footer(f"[[{state_index_page(g['state'])}|{title_esc(S.NAME[g['state']])}]]",
                        f"[[{NS}:start|lexflow models]]")
    return "\n".join(L)


def _model_row(con, mid: str | None) -> dict | None:
    return db.one(con, "SELECT model_id, metrics, stages, updated_at, facts FROM process_models WHERE model_id=?",
                  mid) if mid else None


def local_words(researched) -> str:
    """The line that marks a place's own text as lexflow's summary, not the law's words."""
    return (f"//What this page says about the local procedure is in lexflow's words, not the law's: an AI system "
            f"summarised the place's official pages{_when([researched])}, and a second AI pass fetched each source "
            f"again and corrected or removed what it could not find there. Follow the source links before you act.//")


def render_place_process(con, gov_id: str, qid: str) -> str | None:
    """One process for one place: state law, the local procedure, contacts, local law, fees, caveats, sources."""
    d = answers_for(con, gov_id)
    g = d["government"]
    a = d["answers"].get(qid)
    if not a:
        return None
    q = QUESTIONS[qid]
    loc = a.get("local") or {}
    mrow = _model_row(con, a.get("model_id"))
    parts = [("state law", model_reviewer(mrow, con) if mrow else None)] + (
        [("local procedure", local_reviewer(loc, con))] if loc else [])
    L = [f"====== {title_esc(q.title.rstrip('?') + ' in ' + g['name'] + '?', True)} ======", ""]
    # with no state model for this question, no statute quote was counted, so none is said to match
    no_model = (None if mrow else
                f"Researched from the official pages{_when([loc.get('researched') or loc.get('updated_at')])}" if loc
                else "Quotes not matched by lexflow's software: there is no state process map for this question yet")
    L += _head(label([db.now()] if mrow else [], review_text(parts),
                     source="the statute text and the official pages" if loc else STATUTES,
                     matched=model_matched(mrow) if mrow else None, now=bool(mrow),
                     scope=" from the statute" if loc else "", check=no_model))
    if loc:
        L += [local_words(loc.get("researched") or loc.get("updated_at")), ""]
    if loc.get("summary"):
        L += [esc(loc["summary"]), ""]
    L += [f"The state model, with the words of the law for each step: [[{state_page(g['state'], qid)}|"
          f"{title_esc(S.NAME[g['state']] + ': ' + q.title)}]]", ""]
    if a.get("steps"):
        L += ["===== What state law requires =====", ""]
        for s in a["steps"]:
            L.append(f"  - **{esc(s['step'])}** — {esc(s['who'])}{_time_limit(s)} ({esc(s['cite'])})")
        L.append("")
    for t in a.get("decisions") or []:
        if t["id"] == "business_structure":
            L += [f"===== {title_esc(t['question'], True)} =====", ""] + _table(t) + [""]
    if loc.get("steps"):
        L += [f"===== {title_esc('What ' + g['name'] + ' adds', True)} =====", "",
              "//In lexflow's words, from the office's own pages; each step links its source.//", ""]
        for s in loc["steps"]:
            src = f" ([[{s['url']}|source]])" if s.get("url") else ""
            L.append(f"  - **{esc(s['step'])}**" + (f" — {esc(s['who'])}" if s.get("who") else "") +
                     f". {esc(s.get('how', ''))}{src}")
        L.append("")
    if loc.get("contacts"):
        L += ["===== Who to contact =====", ""] + _contacts_block(loc["contacts"]) + [""]
    if loc.get("local_law"):
        L += ["===== Local law =====", ""] + [f"  * [[{x['url']}|{title_esc(x['citation'])}]]: {esc(x['summary'])}"
                                             if x.get("url") else f"  * {esc(x['citation'])}: {esc(x['summary'])}"
                                             for x in loc["local_law"]] + [""]
    if loc.get("fees"):
        L += [f"**Fees.** {esc(loc['fees'])}", ""]
    caveats = reader_caveats(loc.get("caveats"))
    if caveats:
        L += ["===== Caveats =====", ""] + [f"  * {esc(c)}" for c in caveats] + [""]
    srcs = [s for s in (loc.get("sources") or []) if s.get("url")]
    if srcs:
        L += ["===== Sources =====", ""] + [f"  * [[{s['url']}|{title_esc(source_title(s))}]]" for s in srcs] + [""]
    L += _footer(f"[[{place_page(g, con)}|{title_esc(g['name'])}]]",
                 f"[[{state_index_page(g['state'])}|{title_esc(S.NAME[g['state']])}]]")
    return "\n".join(L)


ASKED_STATUS = {"answered": "answered", "partial": "partly answered",
                "not_found": "no statute section found that clearly governs this",
                "no-statutes": "no statute text for this state"}


def render_asked(con, row: dict) -> str:
    """An asked question's answer: the governing sections, the checked summary claims, the steps and the quotes."""
    a = db.loads(row.get("answer"), {}) or {}
    sec = db.loads(row.get("sections"), {}) or {}
    local = db.loads(row.get("local"), {}) or {}
    where = local.get("name") or S.NAME.get(row["state"], row["state"])
    L = [f"====== {title_esc(row['question_text'], True)} ======", "",
         f"**{esc(where)}** · {esc(ASKED_STATUS.get(row['status'], row['status'] or ''))}", ""]
    L += _head(label([], review_text([("", asked_reviewer(row, con))]), check=asked_check(row)))
    L += ["//lexflow searched the state's statutes, chose the sections below and quoted their clauses word for "
          "word. Read the sections before relying on it.//", ""]
    if row["status"] == "not_found":
        L += ["lexflow did not find a statute section that clearly governs this. The answer may be in regulations, "
              "court rules, agency policy, contracts or local ordinances.", ""]
    claims = (a.get("summary") or {}).get("claims") or []
    if claims:
        L += ["===== In short =====", "", "//Summarised by an AI system from the quotes below; each claim cites them.//", ""]
        L += [f"  * {esc(c['text'])} " + " ".join(f"[{esc(i)}]" for i in c["quotes"]) for c in claims] + [""]
    if sec.get("chosen"):
        L += ["===== Governing law =====", ""]
        L += [f"  * [[{s['url']}|{title_esc(s['citation'])}]] — {esc(s['title'])}" if s.get("url")
              else f"  * {esc(s['citation'])} — {esc(s['title'])}" for s in sec["chosen"]] + [""]
    if a.get("steps"):
        L += ["===== Steps =====", ""]
        for s in a["steps"]:
            lim = W.describe_text(s.get("deadline"), s.get("quote"))
            dl = f" · time limit: {esc(lim)}" if lim else ""
            L.append(f"  - **{esc(s['action'])}** — {esc(s['actor'])}{dl} (§ {esc(s['section'])}) \\\\ "
                     f"“//{esc(s['quote'])}//”")
        L.append("")
    if row.get("bpmn"):
        L += ["===== Process map (draft) =====", "", "<bpmnio type=\"bpmn\">",
              reader_bpmn(row["bpmn"], _json(row.get("facts")), question=row.get("question_text"),
                          question_id=row.get("question_id")), "</bpmnio>", ""]
    if a.get("quotes"):
        L += ["===== Key provisions =====", ""]
        L += [f"  * **{esc(q['id'])}** § {esc(q.get('section') or '')}: “//{esc(q['text'])}//”" for q in a["quotes"]]
        L.append("")
    if local.get("locus"):
        L += [f"===== {title_esc('Local ordinances in ' + where, True)} =====", "",
              "//Headings from LOCUS-v1, LocalLaws' dataset of local ordinances (the Local Ordinance Corpus for the "
              "United States), that mention the question; read the ordinance itself.//",
              ""] + [f"  * {esc(x['header'])}" for x in local["locus"]] + [""]
    if local.get("web"):
        L += ["===== Official pages =====", ""] + [f"  * [[{w['url']}|{title_esc(w.get('title') or w['url'])}]]"
                                                  for w in local["web"]] + [""]
    if a.get("cases"):
        L += ["===== Court decisions citing these sections =====", ""]
        L += [f"  * [[{c['url']}|{title_esc(c['case_name'])}]] ({esc(c.get('court') or '')}, "
              f"{esc((c.get('date_filed') or '')[:4])}) — cites § {esc(c['section'])}" for c in a["cases"]] + [""]
    if local.get("contacts"):
        L += ["===== Contacts =====", ""] + _contacts_block(local["contacts"]) + [""]
    # back to the place only when it has a main page; otherwise the state's page lists this answer
    g = (db.one(con, "SELECT * FROM governments WHERE gov_id=?", row["gov_id"])
         if has_place_page(con, row.get("gov_id")) else None)
    back = [f"[[{place_page(g, con)}|{title_esc(where)}]]"] if g else []
    L += _footer(*back, f"[[{state_index_page(row['state'])}|{title_esc(S.NAME.get(row['state'], row['state']))}]]")
    return "\n".join(L)


def _local_rows(con, gov_ids: list[str]) -> list[dict]:
    if not gov_ids:
        return []
    return db.rows(con, f"SELECT * FROM local_answers WHERE gov_id IN ({','.join('?' for _ in gov_ids)})", *gov_ids)


def render_state_index(con, state: str, models: list[str], places: list[dict]) -> str:
    """A state's main page: its process models, the places with checked local answers, and answered questions
    (with the answers for places that have no main page of their own)."""
    name = S.NAME[state]
    mrows = [r for r in (_model_row(con, f"{state}.{q}") for q in models) if r]
    locs = _local_rows(con, [g["gov_id"] for g in places])
    asked = published_asked(con, state=state)
    from ..ask import prefer
    loose = [r for r in prefer.preferred(db.rows(
        con, "SELECT a.*, g.name AS gov_name FROM asked_answers a LEFT JOIN governments g ON g.gov_id=a.gov_id WHERE "
             "a.published=1 AND a.state=? AND a.gov_id IS NOT NULL AND a.gov_id NOT IN (SELECT l.gov_id FROM "
             "local_answers l JOIN governments h ON h.gov_id=l.gov_id) ORDER BY a.question_id, g.name", state))
        if wiki_ready(r, con)]
    # the quotes it vouches for are those of the state law pages it lists (models and asked answers); the places'
    # own pages say how their text was checked.  The software counts the models' and the asked answers' quotes now.
    counted = [m for m in (asked_matched(r) for r in asked + loose) if m and m[1]]
    models_part = models_matched(mrows) if mrows else None
    parts = [x for x in [models_part] if x and x[1]] + counted
    # a model whose statute text is not at hand here: no count for the page, which says so
    matched = None if mrows and models_part is None else \
        (sum(a for a, _ in parts), sum(b for _, b in parts)) if parts else None
    dates = [db.now()] if (mrows or counted) else []
    signers = ([model_reviewer(r, con) for r in mrows] + [local_reviewer(x, con) for x in locs]
               + [asked_reviewer(r, con) for r in asked + loose])
    L = [f"====== {title_esc(name, True)} ======", ""]
    L += _head(label(dates, review_summary(signers) if signers else NOT_REVIEWED,
                     source="the statute text and, for places, their official pages" if places else STATUTES,
                     matched=matched, scope=" from the statute" if places else "", count=bool(asked or loose),
                     now=bool(mrows)))
    if models:
        L += ["===== Process models =====", ""] + [f"  * [[{state_page(state, q)}|{title_esc(QUESTIONS[q].title)}]]"
                                                for q in models] + [""]
    if places:
        L += ["===== Places =====", ""] + [f"  * [[{place_page(g, con)}|{title_esc(g['name'])}]]" for g in places] + [""]
    if asked or loose:
        L += ["===== Other questions =====", "",
              "//Answers to questions people asked; each page names the person who reviewed it.//", ""]
        L += [f"  * [[{asked_page(con, r)}|{title_esc(r['question_text'])}]]" for r in asked]
        L += [f"  * [[{asked_page(con, r)}|{title_esc(r['question_text'])}]] — {esc(r['gov_name'] or r['target'])}"
              for r in loose] + [""]
    L += _footer(f"[[{NS}:start|lexflow models]]")
    return "\n".join(L)


def _names(items: list[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1] if items else ""


def _state_name(st: str) -> str:
    n = S.NAME[st]
    return f"the {n}" if n.startswith("District of") else n


def _model_rows(con, models: dict[str, list[str]]) -> list[dict]:
    return [r for r in (_model_row(con, f"{st}.{q}") for st in sorted(models) for q in models[st]) if r]


def render_index(con, states: list[str], place_pages: list[tuple[str, str]],
                 models: dict[str, list[str]] | None = None) -> str:
    """lexflow:start: what is here, and nothing that is not: the jurisdictions with process models, the questions
    they answer, the places with local pages, and that no person has reviewed them yet (until one has)."""
    models = models if models is not None else {
        r["state"]: [] for r in db.rows(con, "SELECT DISTINCT state FROM process_models WHERE tier IN ('reviewed','agreed')")}
    mrows = _model_rows(con, models)
    with_models = sorted((st for st in models if models[st]), key=lambda st: S.NAME[st])
    signed = sum(1 for r in mrows if model_reviewer(r, con))
    review = ("none has yet been reviewed by a person" if not signed else
              "each names the person who reviewed it" if signed == len(mrows) else
              f"{signed} of them name the person who reviewed them; the others have not yet been reviewed by a person")
    per_q = {q: n for q in QUESTIONS if (n := sum(1 for st in with_models if q in models[st]))}
    L = ["====== lexflow: process maps of state law ======", ""]
    matched = models_matched(mrows) if mrows else None          # counted again now (model_matched)
    L += _head(label([db.now()] if mrows else [], review_summary([model_reviewer(r, con) for r in mrows])
                     if mrows else NOT_REVIEWED, matched=matched, now=bool(mrows)))
    quotes = ("lexflow's software could not match their quotes when this page was made, since the statute text was "
              "not at hand" if mrows and matched is None else
              "every quote in it was matched to Open US Law's copy of the official text" if not matched or
              matched[0] == matched[1] else f"{matched[0]} of their {matched[1]} quotes were matched to Open US "
                                            f"Law's copy of the official text")
    L += [f"These pages hold process maps of state law: the steps a statute sets out, who takes each one and the time "
          f"limits, with the law's own words beside every step. They cover {len(with_models)} "
          f"jurisdiction{'s' if len(with_models) != 1 else ''}: {_names([_state_name(st) for st in with_models])}. "
          f"Each map was drafted with an AI system from the statute text, and {quotes}; {review}."
          + (f" Local pages for {len(place_pages)} place{'s' if len(place_pages) != 1 else ''} add what each place's "
             f"own offices publish, researched from their official pages." if place_pages else "")
          + " Other states, places and questions are not covered here.", ""]
    if per_q:
        L += ["===== Questions =====", ""] + [
            f"  * {esc(QUESTIONS[q].title)} — {n} jurisdiction{'s' if n != 1 else ''}" for q, n in per_q.items()] + [""]
    L += ["===== States =====", ""]
    L += [f"  * [[{state_index_page(st)}|{title_esc(S.NAME[st])}]]" for st in states] + [""]
    if place_pages:
        L += ["===== Places =====", ""] + [f"  * [[{pid}|{title_esc(title)}]]" for pid, title in place_pages] + [""]
    L += ["===== How these pages are made =====", "",
          f"How each page is drafted and checked, what the checks do not prove, the licence of each source, and how to "
          f"report an error: [[{METHOD}|How these pages are made]].", ""]
    L += _footer()          # no link out of the lexflow: namespace: the wiki's own start page is not lexflow's
    return "\n".join(L)


def _source_row(c: dict, use: str, terms: str) -> str:
    return f"| [[{c['url']}|{title_esc(c['name'])}]] | {esc(c['by'])} | {esc(use)} | {esc(terms)} |"


def snapshot(con) -> str:
    """The Open US Law release the statute text comes from, with its date: 'release v2026.09.1 of 30 September
    2026' (from statute_files, else the release the curated models were checked against)."""
    versions = sorted({r["version"] for r in db.rows(con, "SELECT DISTINCT version FROM statute_files WHERE "
                                                          "status='downloaded' AND version IS NOT NULL")} or {SNAPSHOT})
    parts = [f"{v} of {signoff.long_date(SNAPSHOT_DATES[v])}" if v in SNAPSHOT_DATES else v for v in versions]
    return f"release{'s' if len(parts) > 1 else ''} {_names(parts)}"


def _drafted(note) -> tuple[str | None, str | None]:
    """(the drafting system, the date) from a curated model's drafting note: 'Claude (claude-opus-5-5), 2026-10-10;
    every quote checked ...'."""
    m = re.match(r"\s*(.+?),\s*(\d{4}-\d{2}-\d{2})\b", note or "") if isinstance(note, str) else None
    return (m.group(1).strip(), m.group(2)) if m else (None, None)


_STORED = object()


def _passes(mm: dict, matched=_STORED) -> bool:
    """Every check passed: no quote missed, no schema error, no diagram-check error and no warning, every route can
    finish.  ``matched`` is the quote count made when the page is made (``model_matched``; None when the statute
    text is not at hand, which is not a pass); without it, the count the build stored."""
    misses = (mm.get("quote_misses") or 0) if matched is _STORED else (matched[1] - matched[0] if matched else None)
    return misses == 0 and not mm.get("bpmn_xsd_errors") and not mm.get("dmn_xsd_errors") \
        and not mm.get("lint_errors") and not mm.get("lint_warnings") and mm.get("nets_sound") == mm.get("nets")


def render_method(con, models: dict[str, list[str]]) -> str:
    """lexflow:method: how the pages are drafted and machine-checked, what the checks do not prove, the licence of
    each source, that lexflow is not affiliated with the Wikimedia Foundation, how to report an error, and the
    builders' layer (machine-check figures and notes with internal names) that the reader pages leave out."""
    mrows = []
    for st in sorted(models):
        for q in models[st]:
            r = db.one(con, "SELECT model_id, state, question, title, tier, built_by, metrics, facts, stages, "
                            "updated_at FROM process_models WHERE model_id=?", f"{st}.{q}")
            if r:
                r["metrics"], r["facts"] = _json(r["metrics"]), _json(r["facts"])
                mrows.append(r)
    signed = sum(1 for r in mrows if model_reviewer(r, con))
    release = snapshot(con)
    counts = [model_matched(r) for r in mrows]                  # counted again now, as on each model's page
    passing = sum(1 for r, c in zip(mrows, counts) if _passes(r["metrics"], c))
    today = ("" if not mrows else " Today every model passes all of them, with no errors and no warnings."
             if passing == len(mrows) else f" Today {passing} of the {len(mrows)} models pass all of them with no "
                                           f"errors and no warnings.")
    L = ["====== How lexflow pages are made ======", ""]
    L += _head(label([], NOT_REVIEWED, source=METHOD_SOURCE, check=METHOD_CHECK))
    L += ["//This page says how the lexflow pages are drafted and checked, what those checks do not prove, where the "
         "material comes from and on what terms, and how to report an error. It was written with an AI system and "
         "has not yet been reviewed by a person.//", "",
         "===== What each page tells you =====", "",
         "Every lexflow page, this one included, opens with three facts:", "",
         "  * **Drafted with an AI system from the statute text.** An AI system wrote the first draft. Local pages "
         "say they were drafted from the place's official pages and the law they rest on.",
         "  * **Every quote matched to Open US Law's copy of the official text on <date>.** On that date lexflow's "
         "software found these quotes, word for word, in the statute text it holds (Open US Law's "
         f"{release}, a compilation of the text each state's official publisher puts out): the **step quotes** "
         "(the words of the law under each step), the **deadline quotes** (the words each time limit is read from) "
         "and the **law quotes** behind each decision table and each of its rows. lexflow's software matches them "
         "again each time the page is made, against the statute text this copy of lexflow holds, so the date is the "
         "day the page was made, and a map that came from another copy through sync is counted here the same way; if "
         "that text is not at hand, the page says its quotes were not matched. If any of them was not found, the "
         "page says how many were. Words in quotation marks inside the notes on what the text leaves open are not "
         "checked by the software. A page that also draws on a place's official pages says the quotes from the "
         "statute were matched. An answer to a question someone asked always gives the count: lexflow's software "
         "matches its quotes to the sections it cites again when the page is made, and the page says \"N of M quotes "
         "matched to Open US Law's copy of the official text on <that day>\" (or that they were not matched, when the "
         "statute text is not at hand). A researched local process gives two counts instead: how many of its quotes "
         "that cite a section of the Code of Virginia or the D.C. Code (the only citations lexflow's local-quote "
         "matcher reads; other states' are counted with the other quotes) found in Open US Law's copy lexflow's "
         "software matched to that section, with the same check as the state maps, and on what date; and, for its "
         "other quotes (from the place's own "
         "pages, other offices' pages, city codes and regulations), that they were \"" + AI_VERIFIED + " on <date>; "
         + NOT_SOFTWARE + "\", with the number of quotes the AI verifier did not confirm. lexflow does not turn an AI "
         "system's count into \"Every quote matched\".",
         "  * **Not yet reviewed by a person**, or, once someone has signed, **Reviewed by <name>, <role>, on "
         "<date>**. For an attorney: **Reviewed by <name>, attorney licensed in <state>, on <date>**. A page names "
         "a reviewer only from the list of reviewers that the operator of this lexflow copy keeps. The list is this "
         "copy's own: it is not shared with other copies, and a review that arrives from another copy never counts "
         "here, since a page names a reviewer only for a review recorded on this copy. The operator "
         "adds each person to that list, with a role from a fixed list (" + ", ".join(signoff.ROLES) + ") and, for "
         "an attorney, the state where they are licensed, and so vouches that each reviewer on it is a person with "
         "that role. **lexflow cannot check that a reviewer is a person**, or their role or licence. It only cleans "
         "the name when it is added (letters, spaces, hyphens, apostrophes and full stops; no invisible characters; "
         "each word in one script; none of the role and credential words or placeholders on lexflow's lists, such "
         "as \"attorney\" or \"Anonymous\"), and warns the operator when the name contains that of an AI system, "
         "which proves nothing either way. Those lists catch only what they hold, and the operator answers for every "
         "name on the list. The name, role and licence a page prints come from the list, never from the review. A "
         "review names someone on the list and states that they, a person, read this exact text against the law. "
         "lexflow's review tool records that statement only with the reviewer's own token, which the operator gives "
         "them; a token shows that whoever used it had it, not who they are. A state process map, a place's page and "
         "a researched local process can carry only a sign-off written into lexflow's own file for it (a curated "
         "file), and that sign-off is not bound to any token: whoever edits the file records it, and the operator "
         "answers for it. A map's sign-off may not be dated before the map was first built (the date this copy "
         "stored at its first build, which nothing later moves back) or in the future. A review covers only that "
         "text; if the text changes, or the operator takes the reviewer off the list, the page says it has not yet "
         "been reviewed by a person until someone on the list signs, on this copy, the text it shows.", "",
         f"Today {signed} of the {len(mrows)} state process maps name a reviewer." if mrows else "", "",
         "===== How a page is drafted =====", "",
         "  * **State process maps.** Claude, an AI system made by Anthropic, read the sections of each state's "
         "statutes that govern the question and wrote down each step, who takes it, any time limit, and the words of "
         "the law each one comes from. Two further passes by an AI system checked the draft against the statute for "
         "accuracy and for missing steps. lexflow's software then draws the process map and the decision tables "
         "from those notes.",
         "  * **Local pages.** An AI system researched each place's official web pages and the law they rest on. A "
         "second AI pass fetched every source again and corrected or removed what it could not find there. The page "
         "marks that text as lexflow's words.",
         "  * **Answers to questions people asked.** lexflow's software searches the statute text, chooses the "
         "sections and clauses that answer the question and quotes them word for word. A short summary, when there "
         "is one, is written by a small AI model that lexflow runs itself, and every claim in it must cite a quote. "
         "These answers appear on the wiki only after a person on the operator's reviewer list has recorded on this "
         "copy, with their own token, that they reviewed them.",
         "",
         "===== What the machine checks do =====", "",
         "  * **Quotes.** Every step quote, deadline quote and law quote in a state process map must appear, word "
         f"for word (spacing and curly apostrophes aside), in the statute text lexflow holds: Open US Law's {release}. "
         "Quoted words in the notes are not checked by the software; there, quotation marks give words of the "
         "sections the page cites, and a reader can look them up there. Each page links its "
         "governing section to the state's official publisher; the other sections it cites are named, not linked. "
         "On a researched local process, lexflow's software matches the quotes that cite a section of the Code of "
         "Virginia or the D.C. Code found in that copy, with the same check, and the page says how many matched and "
         "when; it reads no other state's citations yet. The quotes of a state process map and those of an answer to "
         "an asked question are matched the same way each time the page is made, against the statute text this copy "
         "holds, never taken from a count stored with the map or the answer. lexflow's "
         "software does not match the words quoted from local pages, other offices' pages, city codes or "
         "regulations: for those, an AI verifier's check against the cited page is the only check, and the page "
         "says so, with the number it did not confirm.",
         "  * **Time limits.** Each time limit is printed in the words of the law it comes from (\"within five "
         "working days\"), in the list of steps and on the process map. lexflow also keeps the number and a unit for "
         "its own date arithmetic; the page does not show that unit. Where lexflow adds two periods together, the "
         "page says \"lexflow's count\" and shows the words it added up (\"lexflow's count: 15 + up to 10\").",
         "  * **The process map.** lexflow checks each process map and decision table against the published "
         "standards (the BPMN 2.0 and DMN 1.3 schemas, from the Object Management Group) and with a diagram checker "
         "(bpmnlint), using its recommended rules and five lexflow rules. Three of the five are errors: every step "
         "cites the law, every time limit is in a standard format, and every decision step names its table. Two are "
         "warnings: every time limit says what starts the clock, and anything assumed rather than stated says why. "
         "It also checks that every route through the map can reach an end without getting stuck (a Petri-net "
         "soundness check). A page is published from a reviewed or agreed model even if one of these checks fails "
         f"or warns; the table below gives each model's results.{today} The map on a page is the diagram only: its "
         "time limits are named in the law's words, and lexflow's notes for builders and its own day counts are "
         "left out of it.", "",
         "===== What the checks do not prove =====", "",
         "  * That the right sections were chosen, or that no other law changes the answer: regulations, court "
         "rules, local ordinances and court decisions are not checked.",
         "  * That every step is there, or that the steps are in the right order.",
         "  * That a time limit is counted the way the office, a court or a state agency counts it. Where the text "
         "leaves a question open, the page says so.",
         f"  * That the law is current. The text is Open US Law's {release}, not the current code; the date on each "
         "page is when its quotes were matched to that copy.",
         "  * That the compilation matches the official code everywhere. Follow the link to the official publisher "
         "before relying on a quote.",
         "  * That the page is right. Passing every check is not a legal review, and no person has reviewed a page "
         "unless it names its reviewer.", "",
         "===== Sources and licences =====", "",
         "Licences vary by source. The material taken from each source stays under that source's terms. Listing a "
         "source does not mean its maker has reviewed or endorsed lexflow.", "",
         "^ Source ^ From ^ Used for ^ Terms ^",
         _source_row(C.OPEN_US_LAW, "The statute text quoted on every state page, compiled from each state's official "
                                    f"publisher ({release})",
                     "CC BY-NC 4.0 (non-commercial use, with attribution). The statute text is public law; the "
                     "compilation is Vaquill AI's"),
         _source_row(C.LOCUS, "Finding local ordinances; ordinance headings on answers to asked questions",
                     "CC BY-NC 4.0 (non-commercial use, with attribution)"),
         _source_row(C.WIKIDATA, "Governments' official websites, emails and phone numbers", "CC0 1.0 (public domain)"),
         _source_row(C.COURTLISTENER, "The lists of court decisions that cite a section",
                     "Free Law Project's allowed API usage policy; no data licence is stated"),
         _source_row(C.CENSUS_GUS, "The list of governments that places are matched to",
                     "Public domain (US government work)"),
         "| Each place's official pages | That government | Local steps, fees, forms and contacts on place pages | "
         "The government's own terms; summarised, with a link |", "",
         "===== Not affiliated with the Wikimedia Foundation =====", "",
         "Lexipedia and lexflow are not affiliated with, or endorsed by, the Wikimedia Foundation, Wikipedia or "
         "Wikidata. lexflow uses Wikidata's data under its CC0 licence.", "",
         "===== Report an error =====", "",
         "If something on a lexflow page is wrong or out of date, please say which page, what is wrong and, if you "
         "can, the source that shows it.", "",
         f"  * {corrections()}", ""]
    L = [x for x in L if x is not None]
    if mrows:
        drafted = [_drafted(r["metrics"].get("reviewed_by")) for r in mrows]
        systems = sorted({s for s, _ in drafted if s})
        L += ["===== The machine checks, model by model =====", ""]
        if systems:
            L += [f"The models with a drafting date were drafted by {esc(_names(systems))}, an AI system, on that date; "
                  f"lexflow's software matched their quotes to Open US Law's copy of the official text when this page "
                  f"was made, on the date in the last column.", ""]
        L += ["^ Model ^ Quotes checked ^ Not exact ^ Schema errors (map / tables) ^ Diagram-check errors / warnings ^ "
              "Routes that can finish ^ Sections ^ Drafted ^ Quotes matched ^"]
        made = signoff.long_date(db.now())
        for r, (_, day), c in zip(mrows, drafted, counts):
            mm = r["metrics"]
            how = (signoff.long_date(day) if day else "by an AI system" if r["tier"] == "reviewed" else
                   "two independent extractions agree")
            # the quote columns are the count made now (model_matched), never the one stored with the model
            checked, missed = (c[1], c[1] - c[0]) if c else ("statute text not at hand", "")
            L.append(f"| [[{state_page(r['state'], r['question'])}|{esc(r['model_id'])}]] | {checked} "
                     f"| {missed} | {mm.get('bpmn_xsd_errors', '')} / {mm.get('dmn_xsd_errors', 0)} "
                     f"| {mm.get('lint_errors', '')} / {mm.get('lint_warnings', 0)} "
                     f"| {mm.get('nets_sound', '')} of {mm.get('nets', '')} "
                     f"| {esc(', '.join(mm.get('sections') or []))} | {esc(how)} "
                     f"| {esc(made if c else 'not matched')} |")
        L += ["", "===== Notes for builders =====", "",
              "//Notes on what each statute leaves open, as written for the people who build the models: they use the "
              "model's internal names for steps and outcomes and the terms of the process-map standard. Each model's "
              "page gives these notes in plain words.//", ""]
        for r in mrows:
            _, builder = N.split(r["metrics"], r["facts"])
            if not builder:
                continue
            L += [f"==== {title_esc(r['model_id'] + ': ' + (r['title'] or QUESTIONS[r['question']].title), True)} ====",
                  "", f"[[{state_page(r['state'], r['question'])}|The model's page]]", ""]
            L += [f"  * {esc(g)}" for g in builder] + [""]
    L += _footer(f"[[{NS}:start|lexflow models]]")
    return "\n".join(L)


def all_pages(con) -> dict[str, str]:
    """Every lexflow page.  Each state model's quotes are counted once a run (``model_matched``), when its pages
    are made."""
    global _COUNTS
    _COUNTS = {}
    try:
        return _all_pages(con)
    finally:
        _COUNTS = None


def _all_pages(con) -> dict[str, str]:
    pages: dict[str, str] = {}
    models: dict[str, list[str]] = {}
    for r in db.rows(con, "SELECT state, question, title FROM process_models WHERE tier IN ('reviewed','agreed') "
                          "ORDER BY state, question"):
        text = render_state_model(con, r["state"], r["question"])
        if text:
            pages[state_page(r["state"], r["question"])] = text
            models.setdefault(r["state"], []).append(r["question"])
    places: dict[str, list[dict]] = {}
    place_pages = []
    for g in db.rows(con, "SELECT DISTINCT g.* FROM governments g WHERE g.gov_id IN "
                          "(SELECT gov_id FROM local_answers UNION SELECT gov_id FROM place_processes WHERE verified=1) "
                          "ORDER BY g.state, g.name"):
        pid = place_page(g, con)
        pages[pid] = render_place(con, g["gov_id"])
        for qid in QUESTIONS:
            text = render_place_process(con, g["gov_id"], qid)
            if text:
                pages[f"{pid}:{qid}"] = text
        for p in place_processes(con, g["gov_id"]):
            pages[local_process_page(g, p["process"], con)] = render_local_process(con, g, p)
        places.setdefault(g["state"], []).append(g)
        place_pages.append((pid, f"{g['name']}, {S.NAME[g['state']]}"))
    asked_states = set()
    # an asked answer is published only when it is marked for the wiki and a named person has reviewed it; one
    # per question and target when several models answered (lexflow.ask.prefer)
    from ..ask import prefer
    for r in prefer.preferred(db.rows(con, "SELECT * FROM asked_answers WHERE published=1")):
        if wiki_ready(r, con):
            pages[asked_page(con, r)] = render_asked(con, r)
            asked_states.add(r["state"])
    states = sorted(set(models) | set(places) | asked_states)
    for st in states:
        pages[state_index_page(st)] = render_state_index(con, st, models.get(st, []), places.get(st, []))
    pages[f"{NS}:start"] = render_index(con, states, place_pages, models)
    pages[METHOD] = render_method(con, models)
    return pages
