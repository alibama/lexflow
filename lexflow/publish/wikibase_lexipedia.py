"""The action-API client for lexipedia.wikibase.cloud: login with a bot password, csrf token, ``wbeditentity``
with retries and back-off on ``ratelimited`` / ``maxlag``, and a label lookup.  ``lexflow.publish.push`` (the
schema-v2 writer behind ``lexflow wikibase push`` and the dashboard's wikibase step) builds its ``Api`` on it.

This module used to hold the v1 loader (``Loader``, ``run``, ``retire_drafts``), which wrote the v1 statement set
with ``clear`` and relabelled "superseded" drafts.  It is gone: job 77 (2026-10-18) ran it over 1,795 items the
v2 pusher had written and wiped their schema-v2 claims.  Nothing writes the v1 shape any more; the v2 pusher's
``--resume`` re-sends the items whose ``content_hash`` the coordinator cleared.

Credentials: a bot password (Special:BotPasswords) in ``WIKIBASE_BOT_USER`` / ``WIKIBASE_BOT_PASSWORD``
(or ``LEXI_USER`` / ``LEXI_PASS``).
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field

import requests

from .. import config


class WikibaseError(RuntimeError):
    pass


@dataclass
class Wikibase:
    base: str
    user: str | None = None
    password: str | None = None
    dry_run: bool = False
    session: requests.Session = field(default_factory=requests.Session)
    csrf: str | None = None
    writes: int = 0

    def __post_init__(self):
        self.api = self.base.rstrip("/") + "/w/api.php"
        self.session.headers["User-Agent"] = config.USER_AGENT

    def get(self, **params):
        r = self.session.get(self.api, params={**params, "format": "json"}, timeout=60)
        r.raise_for_status()
        return r.json()

    def post(self, **params):
        for attempt in range(4):
            r = self.session.post(self.api, data={**params, "format": "json", "token": self.csrf}, timeout=120)
            r.raise_for_status()
            data = r.json()
            err = data.get("error")
            if err and err.get("code") in ("ratelimited", "maxlag"):
                time.sleep(10 * (attempt + 1))
                continue
            if err:
                raise WikibaseError(f"{params.get('action')}: {err.get('code')}: {err.get('info')}")
            return data
        raise WikibaseError("rate limited")

    def login(self):
        token = self.get(action="query", meta="tokens", type="login")["query"]["tokens"]["logintoken"]
        r = self.session.post(self.api, data={"action": "login", "lgname": self.user, "lgpassword": self.password,
                                              "lgtoken": token, "format": "json"}, timeout=60).json()
        if r.get("login", {}).get("result") != "Success":
            raise WikibaseError(f"login failed: {r.get('login', {}).get('reason') or r}")
        self.csrf = self.get(action="query", meta="tokens")["query"]["tokens"]["csrftoken"]
        return r["login"].get("lgusername")

    # --- lookups
    def labels(self, namespace: int) -> dict[str, str]:
        out, cont = {}, {}
        while True:
            res = self.get(action="query", list="allpages", apnamespace=namespace, aplimit=500, **cont)
            ids = [p["title"].split(":")[-1] for p in res["query"]["allpages"]]
            for i in range(0, len(ids), 50):
                ent = self.get(action="wbgetentities", ids="|".join(ids[i:i + 50]), props="labels", languages="en")
                for eid, e in ent.get("entities", {}).items():
                    lab = (e.get("labels", {}).get("en") or {}).get("value")
                    if lab:
                        out.setdefault(lab, eid)
            if "continue" not in res:
                return out
            cont = res["continue"]

    # --- writes
    def save(self, data: dict, qid: str | None = None, summary: str = "lexflow") -> str:
        """One ``wbeditentity``.  ``clear`` inside ``data`` is the API parameter (replace the item's statements),
        not part of the entity; ``push.Api.edit`` is the writer the v2 pusher uses on top of this."""
        if self.dry_run:
            self.writes += 1
            return qid or f"Q{9_000_000 + self.writes}"          # placeholder ids so later claims can point at them
        data = dict(data)
        clear = data.pop("clear", False)        # an API parameter, not part of the entity: inside data it is ignored
        params = {"action": "wbeditentity", "data": json.dumps(data), "summary": summary, "bot": 1}
        if qid:
            params["id"] = qid
            if clear:
                params["clear"] = 1             # replace the item's statements instead of appending to them
        else:
            params["new"] = "item"
        res = self.post(**params)
        self.writes += 1
        return res["entity"]["id"]
