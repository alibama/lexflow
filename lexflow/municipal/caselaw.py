"""Court decisions that cite the statutes behind each process model (CourtListener, Free Law Project).

For every section a state model rests on (its curated or located sections), the search API is asked
for opinions in that state's courts that quote the section number, at most two pages per section.
Requests are paced to CourtListener's documented limits for an authenticated account (API v4 overview,
checked 10 October 2026): 5 requests a minute, 50 an hour and 125 a day, plus at least a second
between requests.  Without a token, whose limits are not documented, requests are paced the same way.  Each of
CourtListener's windows gets ``MARGIN`` seconds more, because the pacer counts when requests are sent, not when they
arrive.  The request times are kept in ``DATA_DIR/courtlistener-requests.json``, so every lexflow process on one
data folder (the cases job, Ask) shares the same allowance.

The pacer does not see every request CourtListener counts, nor count them exactly as it does, so CourtListener can
still answer 429 when the pacer's count is within the limits.  Other clients using the same account count against
it.  On 11 October 2026 (UTC) a run with no token, and no other lexflow request at the time, got a 429 for a
request that fitted the minute limit, margin included, by the pacer's count.  An earlier request had taken about a
minute to answer, so CourtListener may count some requests later than they are sent; that was not confirmed.  A 429
is waited out (for its ``Retry-After``, else 30 s, then 60 s and so on) and the request is tried again, up to
``ATTEMPTS`` tries in all, with no wait after the last.

The waits of one ``search()`` call, the pacer's and the back-off after a 429 answer together, add up to its
``max_wait`` at most; a longer wait raises ``RateLimited`` instead of waiting.  Ask passes the default, so one of its
searches waits a minute at most, besides the time the requests themselves take (a request fails when connecting,
or any one read of its answer, takes more than 90 seconds; there is no limit on the whole answer).
The cases step allows an hour a search, which waits out the minute and hour limits, and it stops when the day's
allowance is used.

A search that fails in any other way (an error answer such as 400, 401, 403 or 5xx, a timeout, a lost connection,
an answer that is not the JSON expected) is never read as "no opinions": ``run()`` raises ``SearchFailed``, and the
cases step (lexflow/pipeline/steps.py) records the state as failed, with the reason, so later runs search it again.
A state with nothing to search (no CourtListener court ids, or no sections) is not a finished search either:
``run()`` raises ``Skipped``, a SearchFailed whose reason starts "skipped:" and which never stops the run, so the
state is recorded with that reason rather than as done, and the next run looks at it again.  (A state already
recorded as done keeps that record when a Redo of it is skipped, as after any failure; see steps.run_cases.)
``search()`` makes no request for a state with no court ids, since an empty court filter would not keep the
search to the state's courts.

Results go to ``case_law`` (shared through Turso) and show on model pages, the wiki and the Wikibase.
Court opinions are public domain in the US.  No Free Law Project page read for the credits states a
licence for the API's data.  Its allowed API usage policy (https://free.law/membership/allowed-api-usage/)
governs access through a membership, and rules out powering a revenue-earning commercial product or
building tools for for-profit or non-profit organisations (see the cases credit in
lexflow/pipeline/credits.py).
"""
from __future__ import annotations

import json
import re
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlparse

import requests

try:
    import fcntl
except ImportError:  # pragma: no cover - not POSIX: the in-process lock still applies
    fcntl = None

from .. import config
from ..store import db
from . import states as S
from .fetch import Log

API = "https://www.courtlistener.com/api/rest/v4/search/"
# CourtListener court ids for each state's appellate courts (high court first; Delaware adds the Court of
# Chancery, where most LLC law is made).  The ids for VA, DC, MD and CA returned opinions here; the rest follow
# CourtListener's naming and are not all confirmed.  An error answer to a search records the state as failed, with
# the reason, never as "0 opinions"; but an id that CourtListener accepts without matching a court would find
# nothing, so a state with no opinions at all is worth checking.  A jurisdiction missing here (Puerto Rico) is
# skipped (Skipped), never searched and never recorded as done.
COURTS = {
    "al": ["ala", "alacivapp", "alacrimapp"], "ak": ["alaska", "alaskactapp"], "az": ["ariz", "arizctapp"],
    "ar": ["ark", "arkctapp"], "ca": ["cal", "calctapp"], "co": ["colo", "coloctapp"], "ct": ["conn", "connappct"],
    "de": ["del", "delch", "delsuperct"], "dc": ["dc"], "fl": ["fla", "fladistctapp"], "ga": ["ga", "gactapp"],
    "hi": ["haw", "hawapp"], "id": ["idaho", "idahoctapp"], "il": ["ill", "illappct"], "in": ["ind", "indctapp"],
    "ia": ["iowa", "iowactapp"], "ks": ["kan", "kanctapp"], "ky": ["ky", "kyctapp"], "la": ["la", "lactapp"],
    "me": ["me"], "md": ["md", "mdctspecapp"], "ma": ["mass", "massappct"], "mi": ["mich", "michctapp"],
    "mn": ["minn", "minnctapp"], "ms": ["miss", "missctapp"], "mo": ["mo", "moctapp"], "mt": ["mont"],
    "ne": ["neb", "nebctapp"], "nv": ["nev", "nevapp"], "nh": ["nh"], "nj": ["nj", "njsuperctappdiv"],
    "nm": ["nm", "nmctapp"], "ny": ["ny", "nyappdiv"], "nc": ["nc", "ncctapp"], "nd": ["nd", "ndctapp"],
    "oh": ["ohio", "ohioctapp"], "ok": ["okla", "oklacivapp", "oklacrimapp"], "or": ["or", "orctapp"],
    "pa": ["pa", "pasuperct", "pacommwct"], "ri": ["ri"], "sc": ["sc", "scctapp"], "sd": ["sd"],
    "tn": ["tenn", "tennctapp"], "tx": ["tex", "texapp", "texcrimapp"], "ut": ["utah", "utahctapp"], "vt": ["vt"],
    "va": ["va", "vactapp"], "wa": ["wash", "washctapp"], "wv": ["wva"], "wi": ["wis", "wisctapp"], "wy": ["wyo"],
}


class RateLimited(RuntimeError):
    """CourtListener answered 429 and waiting it out would take the search past its ``max_wait``, it kept answering
    429 for ``ATTEMPTS`` tries, or the next request would have to wait longer than allowed to stay within the
    limits: the section was not searched (which is not the same as no opinions).  ``run()`` sets
    ``sections_done`` and ``opinions`` to what the state got before it stopped."""
    sections_done = 0
    opinions = 0


class SearchFailed(RuntimeError):
    """A search failed for a reason other than a rate limit: an error answer, a timeout, a lost connection or an
    answer that is not the JSON expected.  The section was not searched, so this is never "no opinions".
    ``reason`` says why in a few words (never a header or the token).  ``stops_run`` is True when every other state
    would most likely fail the same way (401, 403, 5xx, a timeout, a lost connection, an answer that is not the JSON
    expected), and False for another 4xx answer, which may be the state's own (such as a query or court id that is
    rejected), and for Skipped.
    ``run()`` sets ``sections_done`` and ``opinions`` as for RateLimited."""
    sections_done = 0
    opinions = 0

    def __init__(self, reason: str, stops_run: bool = True):
        super().__init__(reason)
        self.reason, self.stops_run = reason, stops_run


class Skipped(SearchFailed):
    """Nothing was searched for the state: ``COURTS`` has no CourtListener court ids for it, or no model and no
    seed or verified located section gives it a section to search.  That is neither "no opinions" nor a finished
    search, so ``run()`` raises it instead of returning.  It is a SearchFailed that never stops the run, with a
    ``reason`` that starts "skipped:", so the cases step records the state with that reason (not as done), the
    Setup status shows it, and the next run looks at the state again: once it has court ids and sections, it is
    searched."""

    def __init__(self, reason: str):
        super().__init__(f"skipped: {reason}", stops_run=False)


# CourtListener's documented limits for an authenticated account (REST API v4 overview, checked 10 October 2026),
# over rolling windows, plus lexflow's own second between requests.  Anonymous use has no documented limit, so it
# is paced the same way.  (window in seconds, requests allowed in it, whose limit it is)
LIMITS = ((1.0, 1, "lexflow's one request a second"), (60.0, 5, "CourtListener's 5 requests a minute"),
          (3600.0, 50, "CourtListener's 50 requests an hour"), (86400.0, 125, "CourtListener's 125 requests a day"))
# seconds added to each of CourtListener's windows (a minute or longer): the pacer counts the times requests are
# sent, and network delays can bring two of them closer together by the time they arrive.  It does not cover every
# difference between the pacer's count and CourtListener's (see the module docstring on 429 answers).
MARGIN = 2.0
SEARCH_MAX_WAIT = 60.0     # what one search (as Ask makes) may wait in all, pacer and 429 back-off together
STEP_MAX_WAIT = 3600.0     # the cases step's searches also wait out the hour limit; the day's limit stops it
TIMEOUT = 90               # seconds a request may take to connect, and then for each read of its answer
ATTEMPTS = 5               # tries of one request while CourtListener answers 429
PACE_FILE = "courtlistener-requests.json"
# why a state is skipped (Skipped prefixes "skipped: "); short, since the Setup status shows the first 80 characters
NO_COURTS = "no CourtListener court ids for this jurisdiction"
NO_SECTIONS = "no sections to search"


def _dur(seconds: float) -> str:
    s = int(round(seconds))
    if s < 60:
        return f"{s} s"
    if s < 3600:
        return f"{round(s / 60)} min"
    h, m = divmod(round(s / 60), 60)
    return f"{h} h {m} min" if m else f"{h} h"


def wait_for(sent: list[float], now: float, limits=LIMITS, margin: float = MARGIN) -> tuple[float, str]:
    """Seconds from ``now`` until one more request fits every window, given the (sorted) times already sent or
    reserved, and the limit that sets the wait.  Windows of a minute or longer (CourtListener's) get ``margin``
    seconds more."""
    need, why = 0.0, ""
    if sent and sent[-1] > now:                       # requests are reserved in order
        need, why = sent[-1] - now, "the requests already queued"
    for window, cap, label in limits:
        if len(sent) >= cap:
            pad = margin if window >= 60 else 0.0
            w = sent[-cap] + window + pad - now       # the cap-th latest must leave the window first
            if w > need:
                need, why = w, label
    return max(0.0, need), why


class Pacer:
    """Reserves a time for each CourtListener request so that ``LIMITS`` hold.  The times are shared through a
    JSON file in the data folder (locked while read and written) when it can be used, else kept in memory."""

    def __init__(self, limits=LIMITS, path: Path | None = None, clock=time.time, sleep=None):
        self.limits, self.path, self.clock, self._sleep = limits, path, clock, sleep
        self.memory: list[float] = []
        self.lock = threading.Lock()

    def _path(self) -> Path:
        return self.path if self.path is not None else Path(config.DATA_DIR) / PACE_FILE

    @contextmanager
    def _times(self):
        """The request times, written back when the block finishes without an error."""
        try:
            path = self._path()
            path.parent.mkdir(parents=True, exist_ok=True)
            f = open(path, "a+", encoding="utf-8")
        except OSError:
            f = None
        if f is None:
            box = {"sent": list(self.memory)}
            yield box
            self.memory = box["sent"]
            return
        with f:
            if fcntl:
                fcntl.flock(f, fcntl.LOCK_EX)
            try:
                f.seek(0)
                try:
                    sent = sorted(float(t) for t in json.loads(f.read() or "[]"))
                except (ValueError, TypeError):
                    sent = []
                box = {"sent": sent}
                yield box
                f.seek(0)
                f.truncate()
                f.write(json.dumps([round(t, 3) for t in box["sent"]]))
            finally:
                if fcntl:
                    fcntl.flock(f, fcntl.LOCK_UN)

    def acquire(self, max_wait: float = SEARCH_MAX_WAIT, log: Log = print, what: str = "") -> float:
        """Wait until a request may be sent, and count it.  Raises RateLimited, counting nothing, when the wait
        would be longer than ``max_wait`` seconds.  Returns the seconds waited."""
        longest = max(w for w, _, _ in self.limits)
        with self.lock, self._times() as box:
            now = self.clock()
            sent = [t for t in box["sent"] if t > now - longest]
            need, why = wait_for(sent, now, self.limits)
            if need > max_wait:
                raise RateLimited(f"{what}staying within {why} would mean waiting {_dur(need)}, longer than "
                                  f"{_dur(max_wait)}")
            box["sent"] = sent + [now + need]
        if need >= 5:
            log(f"{what}waiting {_dur(need)} to stay within {why}")
        if need > 0:
            self.sleep(need)
        return need

    def sleep(self, seconds: float) -> None:
        (self._sleep or time.sleep)(seconds)


PACER = Pacer()


def courts_for(state: str) -> list[str]:
    return COURTS.get(state, [])


# the dataset's abbreviations of New York's consolidated laws, as opinions write them
NY_LAWS = {"PBO Law": "Public Officers Law", "LLC Law": "Limited Liability Company Law",
           "BSC Law": "Business Corporation Law", "PTR Law": "Partnership Law", "GBS Law": "General Business Law"}


def query_for(state: str, ref: str) -> str:
    """'2.2-3704' -> "2.2-3704".  A distinctive number ('40.25.110', '39-121.01') is searched alone, since
    opinions cite it in many styles ('AS 40.25.110'); a short one, and Maryland's numbers, which repeat across
    articles ('General Provisions § 4-203'), also need the code's name."""
    if "§" not in ref:
        return f'"{ref}"'
    article, number = (x.strip() for x in ref.rsplit("§", 1))
    distinctive = bool(re.search(r"[.\-]", number)) and len(number) >= 5
    if distinctive and state != "md":
        return f'"{number}"'
    article = re.sub(r"^(Md\. Code,|Tex\.|Cal\.|N\.Y\.)\s*", "", article).strip(" ,")
    article = NY_LAWS.get(article, article)
    return f'"{number}" AND "{article}"' if article else f'"{number}"'


def _failure(e: Exception) -> tuple[str, bool]:
    """Why a request failed, in a few words (no URL, header or token), and whether every other search would most
    likely fail the same way (see SearchFailed)."""
    resp = getattr(e, "response", None)
    if isinstance(e, requests.HTTPError) and resp is not None:
        code = resp.status_code
        why = f"HTTP {code}" + (f" {resp.reason}" if resp.reason else "")
        if code in (401, 403):
            why += " (check COURTLISTENER_TOKEN)"
        return why[:120], code in (401, 403) or code >= 500
    if isinstance(e, requests.Timeout):
        return f"no answer within {TIMEOUT} s", True
    if isinstance(e, requests.ConnectionError):
        return "could not connect", True
    if isinstance(e, ValueError):                     # requests' JSONDecodeError is a ValueError too
        return "the answer was not the JSON expected", True
    return type(e).__name__, True


def _get(url: str, params: dict | None, headers: dict, max_wait: float, waited: float, log: Log, what: str):
    """One request through ``PACER``, tried again after a 429 answer.  Returns the response and the seconds waited
    so far in this search; raises RateLimited when a wait would take the search past ``max_wait``, or when every
    one of the ``ATTEMPTS`` tries was answered 429 (there is no back-off after the last)."""
    hint = "" if config.COURTLISTENER_TOKEN else " (add COURTLISTENER_TOKEN to .env)"
    for attempt in range(ATTEMPTS):
        waited += PACER.acquire(max(0.0, max_wait - waited), log=log, what=what)
        r = requests.get(url, params=params, headers=headers, timeout=TIMEOUT)
        if r.status_code != 429:
            return r, waited
        if attempt == ATTEMPTS - 1:
            break                                     # no back-off after the last try
        after = str(r.headers.get("Retry-After", "")).strip()
        pause = float(after) if after.isdigit() else 30.0 * (attempt + 1)
        if waited + pause > max_wait:
            raise RateLimited(f"{what}CourtListener answered 429 (rate limited) and the back-off of {_dur(pause)} "
                              f"would take this search past {_dur(max_wait)} of waiting{hint}")
        log(f"{what}CourtListener answered 429 (rate limited); waiting {_dur(pause)}")
        PACER.sleep(pause)
        waited += pause
    raise RateLimited(f"{what}CourtListener kept answering 429 (rate limited){hint}")


def search(state: str, ref: str, pages: int = 2, log: Log = print, max_wait: float = SEARCH_MAX_WAIT,
           strict: bool = False) -> list[dict]:
    """Opinions that cite ``ref``.  Every request, retries included, goes through ``PACER``, and the call's waits
    (the pacer's and the back-off after 429 answers) add up to ``max_wait`` seconds at most: a longer wait raises
    RateLimited.  Any other failure raises SearchFailed with ``strict`` (as ``run()`` asks); without it (Ask) the
    failure is logged and the opinions found so far are returned.  The answer must be a JSON object whose
    ``results`` is a list of objects and whose ``next`` is a link or empty; anything else is a failure.  A state with
    no court ids is not searched at all (an empty court filter would not keep the search to the state's courts):
    with ``strict`` that raises Skipped, without it nothing is returned."""
    courts = courts_for(state)
    if not courts:
        if strict:
            raise Skipped(NO_COURTS)
        log(f"{state} {ref}: not searched, {NO_COURTS}")
        return []
    params = {"q": query_for(state, ref), "type": "o", "court": " ".join(courts), "order_by": "score desc"}
    headers = {"User-Agent": config.USER_AGENT}
    if config.COURTLISTENER_TOKEN:
        headers["Authorization"] = f"Token {config.COURTLISTENER_TOKEN}"
    what = f"{state} {ref}: "
    out, url, waited = [], API, 0.0
    for _ in range(pages):
        try:
            r, waited = _get(url, params if url == API else None, headers, max_wait, waited, log, what)
            r.raise_for_status()
            data = r.json()
            if not isinstance(data, dict):
                raise ValueError("not a JSON object")
            results, nxt = data.get("results"), data.get("next")
            if not (isinstance(results, list) and all(isinstance(x, dict) for x in results)
                    and (nxt is None or isinstance(nxt, str))):
                raise ValueError("not the results expected")
        except (requests.RequestException, ValueError) as e:
            why, stops_run = _failure(e)
            if strict:
                raise SearchFailed(f"§ {ref}: {why}", stops_run) from None
            log(f"{what}CourtListener search failed: {why}")
            break
        out += results
        url = nxt
        if not url:
            break
        if urlparse(url).scheme != "https" or urlparse(url).hostname != urlparse(API).hostname:
            # the token goes only to CourtListener: a 'next' link to any other host is not followed
            log(f"{what}not following a next page on another host")
            break
    return out


def sections_for(con, state: str) -> list[tuple[str, str]]:
    """(question, section ref) for every section a state's models rest on."""
    refs: list[tuple[str, str]] = []
    for r in db.rows(con, "SELECT question, metrics FROM process_models WHERE state=?", state):
        for ref in (db.loads(r["metrics"], {}) or {}).get("sections") or []:
            if (r["question"], ref) not in refs:
                refs.append((r["question"], ref))
    for r in db.rows(con, "SELECT question, section FROM located_law WHERE state=? AND status='found' "
                          "AND method IN ('seed','verified')", state):
        if r["section"] and (r["question"], r["section"]) not in refs:
            refs.append((r["question"], r["section"]))
    return refs


def run(con, state: str, log: Log = print, progress=None) -> dict:
    """Search every section of one state, paced to CourtListener's limits (waiting out the minute and hour
    limits).  A section counts only when its search answered.  A rate limit, or the day's allowance used up, raises
    RateLimited, and any other failure raises SearchFailed; either carries ``sections_done`` and ``opinions`` (what
    the state got before it), and the sections after it are not recorded as having no opinions.  A state with no
    CourtListener court ids, or with no section to search, raises Skipped before any request: it returns only
    when at least one section was searched and every search answered."""
    name = S.NAME.get(state, state)
    if not courts_for(state):
        log(f"{name}: nothing searched, {NO_COURTS}")
        raise Skipped(NO_COURTS)
    refs = sections_for(con, state)
    if not refs:
        log(f"{name}: nothing searched, {NO_SECTIONS}")
        raise Skipped(NO_SECTIONS)
    total = 0
    for i, (qid, ref) in enumerate(refs):
        rows, ts = [], db.now()
        try:
            found = search(state, ref, log=log, max_wait=STEP_MAX_WAIT, strict=True)
        except (RateLimited, SearchFailed) as e:
            e.sections_done, e.opinions = i, total
            if total:
                db.bump(con)
                con.commit()
            raise
        for x in found:
            cites = [c for c in (x.get("citation") or []) if c]
            rows.append({"state": state, "section": ref, "question": qid, "cluster_id": str(x.get("cluster_id")),
                         "case_name": (x.get("caseName") or "")[:300], "court": x.get("court"),
                         "court_id": x.get("court_id"), "date_filed": x.get("dateFiled"),
                         "citation": "; ".join(cites)[:200] or None, "cite_count": x.get("citeCount") or 0,
                         "url": "https://www.courtlistener.com" + (x.get("absolute_url") or ""),
                         "source": "courtlistener", "updated_at": ts})
        db.upsert(con, "case_law", rows)
        con.commit()
        total += len(rows)
        log(f"{name} § {ref}: {len(rows)} opinions")
        if progress:
            progress((i + 1) / max(1, len(refs)))
    db.bump(con)
    con.commit()
    return {"sections": len(refs), "opinions": total}


def for_model(con, state: str, sections: list[str], limit: int = 25) -> list[dict]:
    if not sections:
        return []
    q = ",".join("?" for _ in sections)
    return db.rows(con, f"""SELECT section, case_name, court, court_id, date_filed, citation, cite_count, url, cluster_id
                            FROM case_law WHERE state=? AND section IN ({q})
                            ORDER BY cite_count DESC, date_filed DESC LIMIT ?""", state, *sections, limit)
