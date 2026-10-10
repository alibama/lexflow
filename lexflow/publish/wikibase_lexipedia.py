"""Load lexflow's laws, process models and case law into lexipedia.wikibase.cloud, using its own ontology.

The wiki already defines the classes (legal process, legal process step, decision point, statute or legal
provision, Obligation / Permission / Prohibition / Right) and properties (instance of, part of, has part,
follows, references, applies to jurisdiction, deontic modality, bearer, citation, official text, legal
identifier, exact match).  They are looked up by English label, so nothing is hard-coded to an id; classes
lexflow needs that the wiki lacks (jurisdiction, court decision, legal role) are created once.

Every entity carries a ``legal identifier`` (P25 on this wiki) such as ``lexflow:statute:va:2.2-3704``;
the ``wikibase_items`` table remembers the item each key became, so a re-run updates instead of
duplicating (without it, an item whose label clashes is reused when it carries the same key).
Credentials: a bot password (Special:BotPasswords) in ``WIKIBASE_BOT_USER`` / ``WIKIBASE_BOT_PASSWORD``
(or ``LEXI_USER`` / ``LEXI_PASS``).
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field

import requests

from .. import config
from ..municipal import states as S
from ..municipal.questions import QUESTIONS
from ..store import db

PROPS = {"instance of": "instance", "subclass of": "subclass", "part of": "part_of", "has part": "has_part",
         "follows": "follows", "references": "references", "applies to jurisdiction": "jurisdiction",
         "deontic modality": "deontic", "bearer": "bearer", "citation": "citation", "official text": "url",
         "legal identifier": "key", "exact match": "exact"}
CLASSES = {"legal process": None, "legal process step": None, "decision point": None,
           "statute or legal provision": None, "Obligation": None, "Permission": None, "Prohibition": None,
           "Right": None, "jurisdiction": "A government whose law a provision or process belongs to.",
           "court decision": "A judicial opinion; here, one that cites a provision modelled by lexflow.",
           "legal role": "A party or office that acts in a legal process (a bearer of duties and permissions)."}
MODALITY = {"obligation": "Obligation", "permission": "Permission", "prohibition": "Prohibition", "right": "Right"}


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


def _snak(pid: str, kind: str, value) -> dict:
    if kind == "item":
        dv = {"type": "wikibase-entityid", "value": {"entity-type": "item", "numeric-id": int(value[1:]), "id": value}}
    else:
        dv = {"type": "string", "value": str(value)[:400]}
    return {"mainsnak": {"snaktype": "value", "property": pid, "datavalue": dv}, "type": "statement", "rank": "normal"}


class Loader:
    def __init__(self, con, wb: Wikibase, log=print):
        self.con, self.wb, self.log = con, wb, log
        self.drafting = False                     # True while relabelling an unreviewed model's existing items
        self.touched: set[str] = set()            # keys written in this run
        self.p: dict[str, str] = {}
        self.c: dict[str, str] = {}
        self.items = {r["key"]: r["qid"] for r in db.rows(con, "SELECT key, qid FROM wikibase_items")}
        self.counts: dict[str, int] = {}
        self.done: set[str] = set()
        self.skipped: set[str] = set()            # models left out: their state has no jurisdiction item

    def prepare(self):
        props = self.wb.labels(122)
        missing = [lab for lab in PROPS if lab not in props]
        if missing:
            raise WikibaseError(f"the wiki lacks properties: {missing}")
        self.p = {PROPS[lab]: props[lab] for lab in PROPS}
        classes = self.wb.labels(120)
        for lab, desc in CLASSES.items():
            if lab in classes:
                self.c[lab] = classes[lab]
            elif desc is None:
                raise WikibaseError(f"the wiki lacks the class item {lab!r}")
            else:
                self.c[lab] = self.entity(f"lexflow:class:{lab}", lab, desc, [], kind="class")

    def entity(self, key: str, label: str, description: str, claims: list[dict], kind: str = "item") -> str:
        if self.drafting:
            # an unreviewed model: only items an earlier version already wrote are touched, and they say so
            if not self.items.get(key):
                return None
            description, kind = f"Unreviewed draft. {description}", "draft-relabelled"
        data = {"labels": {"en": {"language": "en", "value": label[:250]}},
                "descriptions": {"en": {"language": "en", "value": description[:250]}},
                "claims": [_snak(self.p["key"], "string", key)] + claims if self.p else claims}
        qid = self.items.get(key)
        if qid and not self.wb.dry_run:
            # replace our own statements wholesale on update: lexflow owns these items
            data["clear"] = True
        suffixed = False
        while True:
            try:
                new = self.wb.save(data, qid=qid, summary=f"lexflow: {key}")
                break
            except WikibaseError as e:
                # the wiki allows one item per label and description: the item an earlier run wrote for this key
                # (when wikibase_items was lost), or another entity, e.g. two opinions with one name, court and date
                if "already has label" not in str(e):
                    raise
                mine = None if qid else self.owner(str(e), key)
                if mine:
                    qid, data["clear"] = mine, True
                elif not suffixed:
                    data["descriptions"]["en"]["value"] = f"{description[:220]} [{key.rsplit(':', 1)[-1]}]"
                    suffixed = True
                else:
                    raise
        if not self.wb.dry_run:
            self.con.execute("INSERT INTO wikibase_items(key, qid, label, updated_at) VALUES (?,?,?,?) ON CONFLICT(key) "
                             "DO UPDATE SET qid=excluded.qid, label=excluded.label, updated_at=excluded.updated_at",
                             (key, new, label, db.now()))
            self.con.commit()
        self.items[key] = new
        self.touched.add(key)
        self.counts[kind] = self.counts.get(kind, 0) + 1
        return new

    def owner(self, error: str, key: str) -> str | None:
        """The item a label conflict names, when its legal identifier is ``key`` (lexflow wrote it before)."""
        m = re.search(r"\bQ\d+\b", error.split("already has label")[0])
        if not m or not self.p.get("key"):
            return None
        q = m.group(0)
        ent = self.wb.get(action="wbgetentities", ids=q, props="claims").get("entities", {}).get(q, {})
        keys = [((s.get("mainsnak") or {}).get("datavalue") or {}).get("value")
                for s in (ent.get("claims") or {}).get(self.p["key"], [])]
        return q if key in keys else None

    def retire_drafts(self):
        """Items an earlier version wrote for an unreviewed model that this run did not rewrite (the model was
        rebuilt since): keep the item and its label, drop its statements and mark it superseded.  Nothing is
        deleted; that is for a wiki admin to decide."""
        reviewed = {r["model_id"] for r in db.rows(self.con, "SELECT model_id FROM process_models "
                                                             "WHERE tier IN ('reviewed','agreed')")}
        for key, qid in list(self.items.items()):
            parts = key.split(":")
            # lexflow:process:<model> · lexflow:step:<model>:<step> · lexflow:role:<state>:<question>:<actor>
            if key in self.touched or not qid or parts[1] not in ("process", "role", "step") or \
                    (parts[1] == "role" and len(parts) < 5):
                continue
            mid = parts[2] if parts[1] != "role" else f"{parts[2]}.{parts[3]}"
            if mid in reviewed or mid in self.skipped:
                continue
            ent = self.wb.get(action="wbgetentities", ids=qid, props="labels").get("entities", {}).get(qid, {})
            label = (ent.get("labels", {}).get("en") or {}).get("value") or key
            self.wb.save({"labels": {"en": {"language": "en", "value": label}},
                          "descriptions": {"en": {"language": "en", "value":
                                                  "Unreviewed draft, superseded; no longer maintained by lexflow."}},
                          "claims": [_snak(self.p["key"], "string", key)], "clear": True},
                         qid=qid, summary=f"lexflow: retire superseded draft {key}")
            self.touched.add(key)
            self.counts["draft-retired"] = self.counts.get("draft-retired", 0) + 1

    def item(self, key):
        return self.items.get(key)

    def _log_skipped(self, what: str, by_state: dict[str, int]):
        for st, n in sorted(by_state.items()):
            self.log(f"skipped {n} {what} in {st}: no jurisdiction item for it yet (add {st} to the run's states)")

    # --- what lexflow knows
    def jurisdictions(self, states: list[str]):
        for st in states:
            self.entity(f"lexflow:jurisdiction:{st}", S.NAME[st], "US state or district (lexflow jurisdiction)",
                        [_snak(self.p["instance"], "item", self.c["jurisdiction"])], kind="jurisdiction")
        skipped: dict[str, int] = {}
        for g in db.rows(self.con, "SELECT DISTINCT g.* FROM local_answers l JOIN governments g ON g.gov_id=l.gov_id"):
            parent = self.item(f"lexflow:jurisdiction:{g['state']}")
            if not parent:                        # a run for other states, before this one's item was written
                skipped[g["state"]] = skipped.get(g["state"], 0) + 1
                continue
            claims = [_snak(self.p["instance"], "item", self.c["jurisdiction"]),
                      _snak(self.p["part_of"], "item", parent)]
            if g.get("wikidata"):
                claims.append(_snak(self.p["exact"], "string", f"http://www.wikidata.org/entity/{g['wikidata']}"))
            self.entity(f"lexflow:gov:{g['gov_id']}", f"{g['name']}, {S.NAME[g['state']]}",
                        f"{g['kind']} in {S.NAME[g['state']]} (Census government {g['gov_id']})", claims,
                        kind="jurisdiction")
        self._log_skipped("places", skipped)

    def statute(self, state: str, ref: str, citation: str, heading: str | None, url: str | None) -> str:
        key = f"lexflow:statute:{state}:{ref}"
        if key in self.done:
            return self.items[key]
        # one section can be named two ways ("Corporations and Associations § 4A-202" in a curated file,
        # "Md. Code, Corporations and Associations § 4A-202" from the locator); the wiki allows one item per label
        by_label = self.__dict__.setdefault("_by_citation", {})
        first = by_label.get((state, citation))
        if first and first != key:
            self.items[key] = self.items.get(first)
            self.done.add(key)
            return self.items[key]
        by_label[(state, citation)] = key
        claims = [_snak(self.p["instance"], "item", self.c["statute or legal provision"]),
                  _snak(self.p["citation"], "string", citation),
                  _snak(self.p["jurisdiction"], "item", self.item(f"lexflow:jurisdiction:{state}"))]
        if url:
            claims.append(_snak(self.p["url"], "string", url))
        self.done.add(key)
        return self.entity(key, citation, (heading or f"{S.NAME[state]} statute")[:250], claims, kind="statute")

    def statutes(self, states: list[str]):
        from ..municipal import statutes as ST
        for st in states:
            refs = {}
            for r in db.rows(self.con, "SELECT metrics FROM process_models WHERE state=?", st):
                for ref in (db.loads(r["metrics"], {}) or {}).get("sections") or []:
                    refs[ref] = None
            for r in db.rows(self.con, "SELECT section, citation, heading, url FROM located_law WHERE state=? AND "
                                       "status='found' AND method IN ('seed','verified')", st):
                refs[r["section"]] = r
            for ref, r in refs.items():
                if r is None:
                    try:
                        t = ST.section_texts(st, [ref])[0]
                        r = {"citation": f"{t.code} § {t.section}", "heading": t.title, "url": t.url}
                    except Exception:  # noqa: BLE001 - statutes not downloaded here
                        continue
                self.statute(st, ref, r["citation"], r.get("heading"), r.get("url"))

    def processes(self):
        """Processes checked by Claude or agreed by two independent extractions, with their roles and steps.
        Models from one extraction alone are drafts: they are not loaded, and the items an earlier version wrote
        for one are rewritten as unreviewed drafts."""
        skipped: dict[str, int] = {}
        for m in db.rows(self.con, "SELECT * FROM process_models WHERE tier IN ('reviewed','agreed','single')"):
            st, qid_q = m["state"], m["question"]
            facts = db.loads(m["facts"], {}) or {}
            metrics = db.loads(m["metrics"], {}) or {}
            pkey = f"lexflow:process:{m['model_id']}"
            title = f"{m['title']} ({S.NAME[st]})"
            self.drafting = m["tier"] == "single"
            if self.drafting and not self.item(pkey):
                continue
            jur = self.item(f"lexflow:jurisdiction:{st}")
            if not jur:                           # a run for other states, before this one's item was written
                skipped[st] = skipped.get(st, 0) + 1
                self.skipped.add(m["model_id"])
                continue
            refs = [self.item(f"lexflow:statute:{st}:{ref}") for ref in metrics.get("sections") or []]
            claims = [_snak(self.p["instance"], "item", self.c["legal process"]),
                      _snak(self.p["jurisdiction"], "item", jur)]
            claims += [_snak(self.p["references"], "item", q) for q in refs if q]
            used_labels: set[tuple[str, str]] = set()
            how = {"reviewed": "checked by Claude", "agreed": "two independent extractions agree",
                   "single": "machine-extracted by the learned selector"}[m["tier"]]
            pqid = self.entity(pkey, title, f"{QUESTIONS[qid_q].title} Process model by lexflow, {how}.", claims,
                               kind="process")
            actors = {a["id"]: a for a in facts.get("actors", [])}
            for a in actors.values():
                self.entity(f"lexflow:role:{st}:{qid_q}:{a['id']}", f"{a['name']} ({S.NAME[st]})",
                            f"{a['kind']} in the {QUESTIONS[qid_q].short.lower()} process",
                            [_snak(self.p["instance"], "item", self.c["legal role"]),
                             _snak(self.p["jurisdiction"], "item", jur)],
                            kind="role")
            step_q = {}
            for s in facts.get("steps", []):
                cls = self.c["decision point"] if s.get("decision") else self.c["legal process step"]
                claims = [_snak(self.p["instance"], "item", cls), _snak(self.p["part_of"], "item", pqid)]
                for prev in s.get("after", []):
                    if step_q.get(prev):
                        claims.append(_snak(self.p["follows"], "item", step_q[prev]))
                if MODALITY.get(s.get("modality")):
                    claims.append(_snak(self.p["deontic"], "item", self.c[MODALITY[s["modality"]]]))
                bearer = self.item(f"lexflow:role:{st}:{qid_q}:{s['actor']}")
                if bearer:
                    claims.append(_snak(self.p["bearer"], "item", bearer))
                src = s.get("source") or {}
                sec = next((ref for ref in metrics.get("sections") or [] if ref.endswith(src.get("section", "\0"))), None)
                if sec and self.item(f"lexflow:statute:{st}:{sec}"):
                    claims.append(_snak(self.p["references"], "item", self.item(f"lexflow:statute:{st}:{sec}")))
                sub = "".join(f"({p})" for p in (src.get("subsection") or "").split(".") if p)
                label = f"{s['action']} ({S.NAME[st]} {QUESTIONS[qid_q].short.lower()})"
                desc = f"Step of “{m['title']}”; § {src.get('section', '')}{sub}"
                if (label, desc) in used_labels:            # the wiki allows one item per label and description
                    desc = f"{desc} [{s['id']}]"
                used_labels.add((label, desc))
                step_q[s["id"]] = self.entity(f"lexflow:step:{m['model_id']}:{s['id']}", label, desc, claims,
                                              kind="step")
            # has part, now that the steps exist
            claims = [_snak(self.p["instance"], "item", self.c["legal process"]),
                      _snak(self.p["jurisdiction"], "item", jur)]
            claims += [_snak(self.p["references"], "item", q) for q in refs if q]
            claims += [_snak(self.p["has_part"], "item", q) for q in step_q.values() if q]
            self.entity(pkey, title, f"{QUESTIONS[qid_q].title} Process model by lexflow, {how}.", claims,
                        kind="process-update")
        self.drafting = False
        self._log_skipped("models", skipped)

    def cases(self, per_section: int = 15):
        cited: dict[str, dict] = {}
        for r in db.rows(self.con, "SELECT DISTINCT state, section FROM case_law"):
            skey = f"lexflow:statute:{r['state']}:{r['section']}"
            if not self.item(skey) or not self.item(f"lexflow:jurisdiction:{r['state']}"):
                continue
            for c in db.rows(self.con, "SELECT * FROM case_law WHERE state=? AND section=? ORDER BY cite_count DESC, "
                                       "date_filed DESC LIMIT ?", r["state"], r["section"], per_section):
                entry = cited.setdefault(f"courtlistener:cluster:{c['cluster_id']}", {"case": c, "statutes": []})
                entry["statutes"].append(skey)
        for key, e in cited.items():
            c = e["case"]
            claims = [_snak(self.p["instance"], "item", self.c["court decision"]),
                      _snak(self.p["jurisdiction"], "item", self.item(f"lexflow:jurisdiction:{c['state']}")),
                      _snak(self.p["url"], "string", c["url"])]
            claims += [_snak(self.p["references"], "item", self.item(k)) for k in dict.fromkeys(e["statutes"])]
            if c.get("citation"):
                claims.append(_snak(self.p["citation"], "string", c["citation"]))
            self.entity(key, c["case_name"] or f"Opinion {c['cluster_id']}",
                        f"{c.get('court') or 'court'}, {(c.get('date_filed') or '')[:10]}", claims, kind="case")


def run(con, *, dry_run: bool = False, states: list[str] | None = None, log=print) -> dict:
    user = config.WIKIBASE_BOT_USER
    password = config.WIKIBASE_BOT_PASSWORD
    wb = Wikibase(config.WIKIBASE_URL, user, password, dry_run=dry_run)
    if not dry_run:
        if not (user and password):
            raise WikibaseError("set WIKIBASE_BOT_USER and WIKIBASE_BOT_PASSWORD (or LEXI_USER / LEXI_PASS) in .env")
        log(f"signed in to {config.WIKIBASE_URL} as {wb.login()}")
    loader = Loader(con, wb, log=log)
    loader.prepare()
    # every state with a model or a verified located law ("keyword" guesses are left out)
    sts = states or sorted({r["state"] for r in db.rows(con, "SELECT DISTINCT state FROM process_models")} |
                           {r["state"] for r in db.rows(con, "SELECT DISTINCT state FROM located_law WHERE "
                                                             "status='found' AND method IN ('seed','verified')")})
    loader.jurisdictions(sorted(set(sts)))
    loader.statutes(sts)
    loader.processes()
    loader.cases()
    if not dry_run:
        loader.retire_drafts()
    log("wrote " + ", ".join(f"{n} {k}" for k, n in loader.counts.items()) + (" (dry run)" if dry_run else ""))
    return {"counts": loader.counts, "writes": wb.writes, "dry_run": dry_run}
