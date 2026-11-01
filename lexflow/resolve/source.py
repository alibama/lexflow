"""The queue: the Glass Database's Wikidata lookup rows, over its public API.

* ``GET {GLASSDB_URL}/wikibase/wikidata?status=unsure``   the lookup's rows (our label, kind, the candidates it saw)
* ``GET {GLASSDB_URL}/wikibase/items/{key}``             the staged item as it would be pushed: its statements
* ``POST {GLASSDB_URL}/wikibase/wikidata/{key}``         admin: ``{"qid": "Q1"}`` links, ``{"qid": ""}`` rules out,
                                                        ``{"suggest": {...}}`` leaves a suggestion for the reviewer

Reads need nothing; writes need ``GLASSDB_ADMIN_TOKEN`` (the site's API key, sent as ``X-API-Key``), and the
live run writes only when it is told to (``suggest`` always when a token is set, ``decide`` only with ``apply``).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

import requests

from .. import config

# statements worth showing a judge; the rest (hashes, image URLs, the round-trip key) say nothing about identity
FACT_PROPS = ("instance of", "occupation", "work location", "located in", "country", "technique", "official website",
              "Instagram username", "collection", "educated at", "worked at", "student of", "student", "award received",
              "part of", "inception", "start time", "end time", "made at", "maker", "participant", "participant in",
              "subclass of", "AAT ID", "exact match", "coordinates")
PAGE = 200


@dataclass
class Case:
    key: str
    kind: str
    label: str
    description: str = ""
    aliases: list[str] = field(default_factory=list)
    facts: dict = field(default_factory=dict)        # statement label -> readable values
    candidates: list[dict] = field(default_factory=list)
    status: str = ""                                 # the lookup's status: unsure | matched | none | confirmed | rejected | known
    qid: str = ""                                    # the id the lookup or a person settled on
    why: str = ""
    url: str = ""                                    # the record's page on the site

    def gold(self) -> str | None:
        """What is already decided: a Q id, ``"none"``, or None while the question is open."""
        if self.status in ("confirmed", "matched", "known") and self.qid:
            return self.qid
        if self.status in ("rejected", "none"):
            return "none"
        return None

    def human(self) -> bool:
        return self.status in ("confirmed", "rejected")

    def candidate_ids(self) -> list[str]:
        return [c["qid"] for c in self.candidates if c.get("qid")]

    def to_row(self) -> dict:
        return {"key": self.key, "kind": self.kind, "label": self.label, "description": self.description,
                "aliases": self.aliases, "facts": self.facts, "candidates": self.candidates, "status": self.status,
                "gold_qid": self.qid, "why": self.why, "url": self.url}

    @staticmethod
    def from_row(r: dict) -> "Case":
        from ..store import db
        return Case(r["key"], r["kind"], r["label"], r.get("description") or "", db.loads(r.get("aliases"), []),
                    db.loads(r.get("facts"), {}), db.loads(r.get("candidates"), []), r.get("status") or "",
                    r.get("gold_qid") or "", r.get("why") or "", r.get("url") or "")


class GlassDatabase:
    """The Glass Database's API. Reads are paced (one request every ``interval`` seconds) and retried."""

    def __init__(self, base: str | None = None, token: str | None = None, interval: float = 0.2, log=None):
        self.base = (base or config.GLASSDB_URL).rstrip("/")
        self.token = token if token is not None else config.GLASSDB_ADMIN_TOKEN
        self.interval = interval
        self.session = requests.Session()
        self.session.headers["User-Agent"] = config.USER_AGENT
        self.last = 0.0
        self.log = log or (lambda *a: None)

    def _pace(self) -> None:
        wait = self.last + self.interval - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        self.last = time.monotonic()

    def _get(self, path: str, **params) -> dict:
        last: Exception | None = None
        for attempt in range(3):
            self._pace()
            try:
                r = self.session.get(self.base + path, params=params, timeout=60)
                if r.status_code >= 500:
                    raise requests.HTTPError(f"{r.status_code} from {path}", response=r)
                r.raise_for_status()
                return r.json()
            except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as e:
                last = e
                if isinstance(e, requests.HTTPError) and e.response is not None and e.response.status_code < 500:
                    raise
                time.sleep(1.5 * (attempt + 1))
        raise RuntimeError(f"the Glass Database did not answer {path} ({last})")

    def _post(self, path: str, body: dict) -> dict:
        if not self.token:
            raise PermissionError("GLASSDB_ADMIN_TOKEN is not set: the Glass Database takes no decisions or suggestions "
                                  "from this machine without it")
        self._pace()
        r = self.session.post(self.base + path, json=body, headers={"X-API-Key": self.token}, timeout=60)
        if r.status_code in (401, 403):
            raise PermissionError(f"the Glass Database refused the API key ({r.status_code})")
        r.raise_for_status()
        return r.json()

    # ------------------------------------------------------------------ reads
    def rows(self, status: tuple[str, ...] | list[str] = ("unsure",), kind: str | None = None,
             limit: int | None = None) -> list[dict]:
        """The lookup's rows for these statuses, every page."""
        out: list[dict] = []
        page = 1
        while True:
            j = self._get("/wikibase/wikidata", status=",".join(status), kind=kind or "", page=page, per=PAGE)
            items = j.get("items") or []
            out.extend(items)
            if limit and len(out) >= limit:
                return out[:limit]
            if len(items) < PAGE or page * PAGE >= int(j.get("total") or 0):
                return out
            page += 1

    def item(self, key: str) -> dict:
        """The staged item: ``{"aliases", "facts", "url", "description"}`` from its statements and the labels of what
        they point at."""
        j = self._get("/wikibase/items/" + key)
        it = j.get("item") or {}
        refs = j.get("refs") or {}
        facts: dict[str, list[str]] = {}
        for c in it.get("claims") or []:
            p = c.get("p")
            if p not in FACT_PROPS:
                continue
            v = c.get("v") or {}
            if v.get("k") == "item":
                ref = refs.get(v.get("v")) or {}
                text = ref.get("label") or str(v.get("v", "")).rsplit(":", 1)[-1].replace("-", " ")
            else:
                text = str(v.get("v", ""))
            if text and text not in facts.setdefault(p, []):
                facts[p].append(text)
        return {"aliases": list(it.get("aliases") or []), "facts": facts, "url": it.get("url") or j.get("url") or "",
                "description": it.get("description") or j.get("description") or ""}

    def cases(self, status: tuple[str, ...] | list[str] = ("unsure",), kinds: list[str] | None = None,
              limit: int | None = None, with_facts: bool = True, known: dict[str, Case] | None = None) -> list[Case]:
        """Cases for these statuses: the lookup's row plus (``with_facts``) the item's statements.  ``known`` holds
        cases fetched earlier (the store's cache): their facts are reused when label and candidates are unchanged."""
        rows = self.rows(status, limit=limit)
        if kinds:
            rows = [r for r in rows if r.get("kind") in kinds]
        out = []
        for r in rows:
            c = Case(r["key"], r.get("kind") or "", r.get("label") or "", r.get("item_description") or "",
                     [], {}, [dict(x) for x in (r.get("candidates") or []) if isinstance(x, dict)],
                     r.get("status") or "", r.get("qid") or "", r.get("why") or "")
            old = (known or {}).get(c.key)
            if old and old.label == c.label and old.candidate_ids() == c.candidate_ids() and (old.facts or not with_facts):
                c.aliases, c.facts, c.url = old.aliases, old.facts, old.url
                c.description = c.description or old.description
            elif with_facts:
                try:
                    d = self.item(c.key)
                except Exception as e:  # noqa: BLE001 - a row without its statements is still a case
                    self.log(f"  {c.key}: could not read the item ({e})")
                    d = {}
                c.aliases = d.get("aliases") or []
                c.facts = d.get("facts") or {}
                c.url = d.get("url") or ""
                c.description = c.description or d.get("description") or ""
            out.append(c)
        return out

    # ------------------------------------------------------------------ writes
    def decide(self, key: str, qid: str) -> dict:
        """Link the item to ``qid``, or rule Wikidata out with ``""``.  Admin."""
        return self._post("/wikibase/wikidata/" + key, {"qid": qid or ""})

    def suggest(self, key: str, suggestion: dict) -> dict:
        """Leave the panel's answer on the row for the reviewer; the row stays unsure.  Admin."""
        return self._post("/wikibase/wikidata/" + key, {"suggest": suggestion})

    def enrich(self, key: str, proposal: dict) -> dict:
        """Leave what a web search found (website, Instagram, city) on the staged item for the reviewer.  Admin."""
        return self._post("/wikibase/items/" + key, {"enrich": proposal})

    def can_write(self) -> bool:
        return bool(self.token)
