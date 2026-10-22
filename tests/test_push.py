"""The direct API writer (lexflow/publish/push.py): request bodies for every value kind against a fake session,
find-before-create, resume by content hash, the dry run and the HELD gate."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from lexflow.publish import graph, push, schema as SC
from lexflow.publish.graph import Claim, Item, Value

SITE = "https://lexipedia.wikibase.cloud"


# --------------------------------------------------------------------------- a fake wiki
class _Resp:
    def __init__(self, data, status=200):
        self.data, self.status_code = data, status

    def raise_for_status(self):
        pass

    def json(self):
        return self.data


class FakeSession:
    """GET answers the SPARQL key map, allpages and wbgetentities from an in-memory wiki; POST is wbeditentity (and
    the login dance), allowing one item per label and description like Wikibase does."""

    def __init__(self, entities=None, keys=None, fail=None):
        self.headers = {}
        self.entities: dict[str, dict] = dict(entities or {})
        self.keys: dict[str, str] = dict(keys or {})       # P25 -> Q on the query service
        self.gets: list[dict] = []
        self.posts: list[dict] = []
        self.fail = fail
        self.next_q, self.next_p = 100, 100

    def get(self, url, params=None, headers=None, timeout=None):
        params = dict(params or {})
        self.gets.append(params)
        if url.endswith("/query/sparql"):
            rows = [{"item": {"value": f"{SITE}/entity/{q}"}, "key": {"value": k}} for k, q in self.keys.items()]
            return _Resp({"results": {"bindings": rows}})
        action = params.get("action")
        if action == "query" and params.get("list") == "allpages":
            return _Resp({"query": {"allpages": [{"title": f"Property:{p}"} for p in self.entities if p.startswith("P")]}})
        if action == "query" and params.get("meta") == "tokens":
            return _Resp({"query": {"tokens": {"logintoken": "L", "csrftoken": "C"}}})
        if action == "wbgetentities":
            out = {}
            for i in params["ids"].split("|"):
                out[i] = self.entities[i] if i in self.entities else {"id": i, "missing": ""}
            return _Resp({"entities": out})
        raise AssertionError(f"unexpected GET {params}")

    def post(self, url, data=None, timeout=None):
        data = dict(data or {})
        self.posts.append(data)
        if data.get("action") == "login":
            return _Resp({"login": {"result": "Success", "lgusername": "Bot"}})
        assert data["action"] == "wbeditentity"
        if self.fail:
            return _Resp({"error": {"code": self.fail, "info": "fake failure"}})
        ent = json.loads(data["data"])
        eid = data.get("id")
        label = ((ent.get("labels") or {}).get("en") or {}).get("value")
        desc = ((ent.get("descriptions") or {}).get("en") or {}).get("value", "")
        if label is not None:
            for q, e in self.entities.items():
                if q != eid and ((e.get("labels") or {}).get("en") or {}).get("value") == label and \
                        ((e.get("descriptions") or {}).get("en") or {}).get("value", "") == desc:
                    return _Resp({"error": {"code": "modification-failed", "info":
                                            f'Item [[Item:{q}|{q}]] already has label "{label}" associated with '
                                            f'language code en, using the same description text.'}})
        if not eid:
            if data.get("new") == "property":
                eid, self.next_p = f"P{self.next_p}", self.next_p + 1
            else:
                eid, self.next_q = f"Q{self.next_q}", self.next_q + 1
            self.entities[eid] = {"id": eid, "type": data.get("new", "item"), "labels": {}, "descriptions": {},
                                  "aliases": {}, "claims": {}}
        e = self.entities[eid]
        if data.get("clear"):
            e.update({"labels": {}, "descriptions": {}, "aliases": {}, "claims": {}})
        if ent.get("datatype"):
            e["datatype"] = ent["datatype"]
        e["labels"].update(ent.get("labels") or {})
        e["descriptions"].update(ent.get("descriptions") or {})
        for lang, als in (ent.get("aliases") or {}).items():
            e["aliases"].setdefault(lang, [])
            e["aliases"][lang] += [{"language": lang, "value": a["value"]} for a in als]
        for s in ent.get("claims") or []:
            e["claims"].setdefault(s["mainsnak"]["property"], []).append(s)
        return _Resp({"entity": {"id": eid}, "success": 1})


def entity(qid, label, desc="", claims=None, aliases=()):
    return {"id": qid, "labels": {"en": {"language": "en", "value": label}},
            "descriptions": {"en": {"language": "en", "value": desc}} if desc else {},
            "aliases": {"en": [{"language": "en", "value": a} for a in aliases]} if aliases else {},
            "claims": claims or {}}


def key_claim(key):
    return {"mainsnak": {"snaktype": "value", "property": "P25", "datavalue": {"type": "string", "value": key}},
            "type": "statement", "rank": "normal"}


def api_for(session, dry_run=True):
    api = push.Api(SITE, "bot", "pw", dry_run=dry_run)
    api.session = session
    api.pause = 0
    return api


def base_items():
    usd = Item(SC.USD, "US dollar", "the unit", [], SC.class_key("currency"), [], False)
    cur = Item(SC.class_key("currency"), "currency", "Vocabulary: the unit of a fee.", [], None, [], False)
    tu = Item(SC.class_key("time-unit"), "time unit", "Vocabulary.", [], None, [], False)
    days = Item(SC.vocab_key("time-unit", "calendar-days"), "calendar days", "Days.", [], SC.class_key("time-unit"),
                [], False)
    return [cur, tu, usd, days]


def step_item(key="lexflow:step:va.records:respond"):
    st = Item(key, "Respond to the request (Virginia records)", "Step of the records process", ["Answer"],
              "legal process step", [], False)
    st.claims = [
        Claim("part of", Value("item", "lexflow:process:va.records")),
        Claim("sort key", Value("string", "0001")),
        Claim("heading text", Value("monolingual", "Respond", lang="en")),
        Claim("official text", Value("url", "https://law.lis.virginia.gov/vacode/2.2-3704/")),
        Claim("act identifier", Value("external-id", "STATE_VA_T2.2_S2.2-3704")),
        Claim("effective date", Value("time", "2024-07-00", precision=10)),
        Claim("time limit", Value("quantity", "5"), [("time unit", Value("item", SC.vocab_key("time-unit", "calendar-days"))),
                                                     ("counted from", Value("string", "receipt"))],
              [[("source section", Value("item", "lexflow:statute:va:2.2-3704")), ("pinpoint", Value("string", "B")),
                ("quoted text", Value("string", "within five working days")),
                ("retrieved", Value("time", "2026-10-10", precision=11))]]),
        Claim("fee", Value("quantity", "20.5", unit=SC.USD), [("fee basis", Value("string", "first hour"))]),
    ]
    return st


def graph_items():
    proc = Item("lexflow:process:va.records", "Records (Virginia)", "Process model by lexflow", [], "legal process",
                [Claim("applies to jurisdiction", Value("item", "lexflow:jurisdiction:va"))], False)
    sec = Item("lexflow:statute:va:2.2-3704", "Va. Code Ann. § 2.2-3704", "Public records to be open", [],
               "statute or legal provision", [Claim("citation", Value("string", "Va. Code Ann. § 2.2-3704"))], False)
    jur = Item("lexflow:jurisdiction:va", "Virginia", "US state or district (lexflow jurisdiction)", [], "jurisdiction",
               [Claim("Wikidata item ID", Value("external-id", "Q1370")),
                Claim("official website", Value("url", "https://www.virginia.gov/"))], True)
    return base_items() + [jur, sec, proc, step_item()]


@pytest.fixture()
def out(tmp_path):
    return tmp_path / "out"


@pytest.fixture()
def wiki():
    return FakeSession(entities={
        **{pid: {"id": pid, "datatype": SC.EXISTING_DATATYPES[label], "labels": {"en": {"language": "en", "value": label}},
                 "descriptions": {}, "aliases": {}, "claims": {}} for label, pid in SC.EXISTING.items()},
        "Q7": entity("Q7", "legal process", "A modeled legal process."),
        "Q8": entity("Q8", "legal process step", "A step or action within a legal process."),
        "Q10": entity("Q10", "statute or legal provision", "A statute or provision."),
        "Q21": entity("Q21", "jurisdiction", "A government.", {"P25": [key_claim("lexflow:class:jurisdiction")]}),
        "Q24": entity("Q24", "Virginia", "US state or district (lexflow jurisdiction)",
                      {"P25": [key_claim("lexflow:jurisdiction:va")],
                       "P5": [{"mainsnak": {"snaktype": "value", "property": "P5", "datavalue": {
                           "type": "wikibase-entityid", "value": {"entity-type": "item", "numeric-id": 21, "id": "Q21"}}},
                           "type": "statement", "rank": "normal"}]}),
    }, keys={"lexflow:jurisdiction:va": "Q24", "lexflow:class:jurisdiction": "Q21"})


def _pids(labels=()):
    r = push.Resolver()
    for i, lab in enumerate(labels, 900):
        r.pids[lab] = f"P{i}"
    return r


# --------------------------------------------------------------------------- bodies
def test_snaks_for_every_value_kind():
    r = _pids(["unit level"])
    r.qids.update({"lexflow:vocab:unit-level:section": "Q55", SC.USD: "Q66"})
    assert push.snak("P9", Value("item", "lexflow:vocab:unit-level:section"), r.qid) == {
        "snaktype": "value", "property": "P9",
        "datavalue": {"type": "wikibase-entityid", "value": {"entity-type": "item", "numeric-id": 55, "id": "Q55"}}}
    assert push.snak("P22", Value("string", "x"), r.qid)["datavalue"] == {"type": "string", "value": "x"}
    assert push.snak("P23", Value("url", "https://a.gov/"), r.qid)["datavalue"] == {"type": "string",
                                                                                     "value": "https://a.gov/"}
    assert push.snak("P1", Value("external-id", "Q1"), r.qid)["datavalue"] == {"type": "string", "value": "Q1"}
    assert push.snak("P24", Value("time", "2026-10-15", precision=11), r.qid)["datavalue"] == {
        "type": "time", "value": {"time": "+2026-10-15T00:00:00Z", "timezone": 0, "before": 0, "after": 0,
                                  "precision": 11, "calendarmodel": push.GREGORIAN}}
    assert push.snak("P24", Value("time", "2026-10-00", precision=10), r.qid)["datavalue"]["value"]["time"] == \
        "+2026-10-00T00:00:00Z"
    assert push.snak("P24", Value("time", "2026-00-00", precision=9), r.qid)["datavalue"]["value"]["precision"] == 9
    assert push.snak("P36", Value("quantity", "5"), r.qid)["datavalue"] == {"type": "quantity",
                                                                             "value": {"amount": "+5", "unit": "1"}}
    assert push.snak("P46", Value("quantity", "20.50", unit=SC.USD), r.qid)["datavalue"]["value"] == {
        "amount": "+20.50", "unit": f"{SITE}/entity/Q66"}
    assert push.snak("P11", Value("monolingual", "Heading", lang="en"), r.qid)["datavalue"] == {
        "type": "monolingualtext", "value": {"text": "Heading", "language": "en"}}
    with pytest.raises(push.Unresolved):
        push.snak("P9", Value("item", "lexflow:nowhere"), r.qid)
    with pytest.raises(ValueError):
        push.snak("P24", Value("time", "yesterday"), r.qid)


def test_claim_with_qualifier_and_reference_is_exact_json():
    r = _pids(["time unit", "counted from", "source section", "pinpoint", "quoted text", "retrieved", "time limit"])
    r.qids.update({SC.vocab_key("time-unit", "calendar-days"): "Q70", "lexflow:statute:va:2.2-3704": "Q500"})
    c = step_item().claims[6]
    st = push.statement(c, r.pid, r.qid)
    p = {lab: r.pids[lab] for lab in r.pids}
    assert st == {
        "mainsnak": {"snaktype": "value", "property": p["time limit"],
                     "datavalue": {"type": "quantity", "value": {"amount": "+5", "unit": "1"}}},
        "type": "statement", "rank": "normal",
        "qualifiers": {p["time unit"]: [{"snaktype": "value", "property": p["time unit"], "datavalue": {
                           "type": "wikibase-entityid", "value": {"entity-type": "item", "numeric-id": 70, "id": "Q70"}}}],
                       p["counted from"]: [{"snaktype": "value", "property": p["counted from"],
                                            "datavalue": {"type": "string", "value": "receipt"}}]},
        "qualifiers-order": [p["time unit"], p["counted from"]],
        "references": [{"snaks": {
            p["source section"]: [{"snaktype": "value", "property": p["source section"], "datavalue": {
                "type": "wikibase-entityid", "value": {"entity-type": "item", "numeric-id": 500, "id": "Q500"}}}],
            p["pinpoint"]: [{"snaktype": "value", "property": p["pinpoint"],
                             "datavalue": {"type": "string", "value": "B"}}],
            p["quoted text"]: [{"snaktype": "value", "property": p["quoted text"],
                                "datavalue": {"type": "string", "value": "within five working days"}}],
            p["retrieved"]: [{"snaktype": "value", "property": p["retrieved"], "datavalue": {
                "type": "time", "value": {"time": "+2026-10-10T00:00:00Z", "timezone": 0, "before": 0, "after": 0,
                                          "precision": 11, "calendarmodel": push.GREGORIAN}}}]},
            "snaks-order": [p["source section"], p["pinpoint"], p["quoted text"], p["retrieved"]]}]}
    # a reference snak whose item has no id is dropped, listed, and the statement still stands
    r.qids.pop("lexflow:statute:va:2.2-3704")
    dropped = []
    st = push.statement(c, r.pid, r.qid, dropped)
    assert dropped == ["time limit reference source section: 'item \\'lexflow:statute:va:2.2-3704\\' has no id'"] \
        or dropped[0].startswith("time limit reference source section")
    assert p["source section"] not in st["references"][0]["snaks"]


def test_owned_and_content_hash():
    assert push.owned("lexflow:step:va.records:s1") and push.owned("lexflow:class:government")
    assert push.owned("lexflow:vocab:topic:taxes") and push.owned("lexflow:gov:1")
    assert not push.owned("lexflow:jurisdiction:va") and not push.owned("lexflow:class:legal-process")
    assert not push.owned("courtlistener:cluster:7")
    a, b = step_item(), step_item()
    assert push.content_hash(a) == push.content_hash(b)
    b.claims[0].value.value = "lexflow:process:va.other"
    assert push.content_hash(a) != push.content_hash(b)


# --------------------------------------------------------------------------- the real path against the fake wiki
def _run(con, wiki, out, items, **kw):
    kw.setdefault("dry_run", False)
    kw.setdefault("allow_held", True)
    return push.run(con, items=items, api=api_for(wiki, dry_run=kw["dry_run"]), out_dir=out, log=lambda *a: None, **kw)


def test_property_create_body_and_item_create_body(con, wiki, out):
    result = _run(con, wiki, out, graph_items(), pass_no="1")
    creates = [p for p in wiki.posts if p.get("new") == "property"]
    assert len(creates) == len(SC.PROPERTIES) and all("bot" not in p and p["maxlag"] == 5 for p in creates)
    first = json.loads(creates[0]["data"])
    assert first == {"datatype": "external-id",
                     "labels": {"en": {"language": "en", "value": "Wikidata item ID"}},
                     "descriptions": {"en": {"language": "en", "value": SC.PROPERTIES[0].description}}}
    fmt = json.loads(creates[1]["data"])
    assert fmt["datatype"] == "string" and fmt["claims"] == [{
        "mainsnak": {"snaktype": "value", "property": "P7",
                     "datavalue": {"type": "string", "value": "http://www.wikidata.org/entity/P1630"}},
        "type": "statement", "rank": "normal"}]
    props = {r["label"]: r["pid"] for r in con.execute("SELECT label, pid FROM wikibase_props")}
    assert len(props) == len(SC.PROPERTIES) and props["Wikidata item ID"] == "P100"
    # the step item: labels, description, aliases, P25 and P5 (its class item Q8 is known)
    step = next(p for p in wiki.posts if p.get("new") == "item" and "Respond to the request" in p["data"])
    assert json.loads(step["data"]) == {
        "labels": {"en": {"language": "en", "value": "Respond to the request (Virginia records)"}},
        "descriptions": {"en": {"language": "en", "value": "Step of the records process"}},
        "aliases": {"en": [{"language": "en", "value": "Answer"}]},
        "claims": [{"mainsnak": {"snaktype": "value", "property": "P25",
                                 "datavalue": {"type": "string", "value": "lexflow:step:va.records:respond"}},
                    "type": "statement", "rank": "normal"},
                   {"mainsnak": {"snaktype": "value", "property": "P5", "datavalue": {
                       "type": "wikibase-entityid", "value": {"entity-type": "item", "numeric-id": 8, "id": "Q8"}}},
                    "type": "statement", "rank": "normal"}]}
    # the vocab item points at a class item created moments before, in the same pass
    usd = next(json.loads(p["data"]) for p in wiki.posts if p.get("new") == "item" and SC.USD in p["data"])
    cur_q = {r["key"]: r["qid"] for r in con.execute("SELECT key, qid FROM wikibase_items")}[SC.class_key("currency")]
    assert usd["claims"][1]["mainsnak"]["datavalue"]["value"]["id"] == cur_q
    # the existing jurisdiction was found on the live key map and left to pass 2
    rows = {r["key"]: r["qid"] for r in con.execute("SELECT key, qid FROM wikibase_items")}
    assert rows["lexflow:step:va.records:respond"].startswith("Q") and "lexflow:jurisdiction:va" not in rows
    c = result["summary"]["counts"]["1"]
    assert c["jurisdiction"] == {"skip-exists": 1} and c["step"] == {"create": 1} and c["property"]["create"] == len(SC.PROPERTIES)
    assert result["summary"]["creates"] == len(SC.PROPERTIES) + 7 and not result["summary"]["failures_by_code"]


def test_pass2_clears_owned_items_and_appends_to_the_rest(con, wiki, out):
    _run(con, wiki, out, graph_items(), pass_no="1")
    wiki.posts.clear()
    result = _run(con, wiki, out, graph_items(), pass_no="2")
    step_qid = {r["key"]: r["qid"] for r in con.execute("SELECT key, qid FROM wikibase_items")}["lexflow:step:va.records:respond"]
    edit = next(p for p in wiki.posts if p.get("id") == step_qid)
    assert edit["clear"] == 1 and edit["maxlag"] == 5 and "bot" not in edit
    body = json.loads(edit["data"])
    assert body["labels"]["en"]["value"].startswith("Respond") and body["aliases"]["en"] == [{"language": "en", "value": "Answer"}]
    props = {r["label"]: r["pid"] for r in con.execute("SELECT label, pid FROM wikibase_props")}
    by_prop = [s["mainsnak"]["property"] for s in body["claims"]]
    assert by_prop[:2] == ["P25", "P5"] and props["time limit"] in by_prop and props["fee"] in by_prop
    fee = next(s for s in body["claims"] if s["mainsnak"]["property"] == props["fee"])
    usd_q = {r["key"]: r["qid"] for r in con.execute("SELECT key, qid FROM wikibase_items")}[SC.USD]
    assert fee["mainsnak"]["datavalue"]["value"] == {"amount": "+20.5", "unit": f"{SITE}/entity/{usd_q}"}
    assert fee["qualifiers"][props["fee basis"]][0]["datavalue"]["value"] == "first hour"
    limit = next(s for s in body["claims"] if s["mainsnak"]["property"] == props["time limit"])
    assert limit["references"][0]["snaks"][props["quoted text"]][0]["datavalue"]["value"] == "within five working days"
    # the jurisdiction (not lexflow's to clear) gets only what it lacks: no clear, no labels, P25 and P5 not repeated
    jur = next(p for p in wiki.posts if p.get("id") == "Q24")
    assert "clear" not in jur
    jbody = json.loads(jur["data"])
    assert "labels" not in jbody and {s["mainsnak"]["property"] for s in jbody["claims"]} == {props["Wikidata item ID"],
                                                                                              props["official website"]}
    # the formatter claims reach the property items in pass 2
    pf = next(p for p in wiki.posts if p.get("id") == props["Wikidata item ID"])
    assert {s["mainsnak"]["datavalue"]["value"] for s in json.loads(pf["data"])["claims"]} == {
        "https://www.wikidata.org/wiki/$1", "http://www.wikidata.org/entity/$1"}
    hashes = {r["key"]: r["content_hash"] for r in con.execute("SELECT key, content_hash FROM wikibase_items")}
    assert hashes["lexflow:step:va.records:respond"] == push.content_hash(step_item())
    c = result["summary"]["counts"]["2"]
    assert c["step"] == {"clear": 1} and c["jurisdiction"] == {"update": 1} and c["process"] == {"clear": 1}
    # a second pass 2 run appends nothing more to the jurisdiction and, with --resume, skips the step
    wiki.posts.clear()
    result = _run(con, wiki, out, graph_items(), pass_no="2", resume=True)
    c = result["summary"]["counts"]["2"]
    assert c["step"] == {"skip-resume": 1} and c["jurisdiction"] == {"skip-resume": 1}
    assert not [p for p in wiki.posts if p["action"] == "wbeditentity"]
    result = _run(con, wiki, out, graph_items(), pass_no="2")
    c = result["summary"]["counts"]["2"]
    assert c["step"] == {"clear": 1} and c["jurisdiction"] == {"skip-current": 1}
    assert not any(p.get("id") == "Q24" for p in wiki.posts)


def test_find_before_create_reuses_the_label_clash_owner_or_suffixes(con, wiki, out):
    # an item an earlier run created for the key, forgotten by wikibase_items and not yet on the query service
    wiki.entities["Q90"] = entity("Q90", "Va. Code Ann. § 2.2-3704", "Public records to be open",
                                  {"P25": [key_claim("lexflow:statute:va:2.2-3704")]})
    # another item with the step's label and description that carries a different key
    wiki.entities["Q91"] = entity("Q91", "Respond to the request (Virginia records)", "Step of the records process",
                                  {"P25": [key_claim("lexflow:step:other")]})
    result = _run(con, wiki, out, graph_items(), pass_no="1")
    rows = {r["key"]: r["qid"] for r in con.execute("SELECT key, qid FROM wikibase_items")}
    assert rows["lexflow:statute:va:2.2-3704"] == "Q90"
    step_q = rows["lexflow:step:va.records:respond"]
    assert step_q not in ("Q90", "Q91")
    assert wiki.entities[step_q]["descriptions"]["en"]["value"] == "Step of the records process [respond]"
    w = next(w for w in result["summary"]["counts"]["1"].items() if w[0] == "statute")
    assert w[1] == {"skip-exists": 1}
    assert len([p for p in wiki.posts if p.get("new") == "item"]) == 7 + 1    # one retry after the clash


def test_failures_are_counted_by_code_and_the_run_goes_on(con, wiki, out):
    wiki.fail = "failed-save"
    result = _run(con, wiki, out, graph_items(), pass_no="1")
    assert result["summary"]["failures_by_code"] == {"failed-save": len(SC.PROPERTIES) + 7}
    assert push.error_code(push.WikibaseError("wbeditentity: maxlag: Waiting for a database")) == "maxlag"
    assert push.owner_of('Item [[Item:Q5|Q5]] already has label "x" associated') == "Q5"


# --------------------------------------------------------------------------- the dry run
def test_dry_run_writes_the_plan_and_performs_no_post(con, wiki, out):
    result = _run(con, wiki, out, graph_items(), dry_run=True, pass_no="all")
    assert wiki.posts == [] and all(isinstance(g, dict) for g in wiki.gets)
    assert any(g.get("action") == "wbgetentities" for g in wiki.gets)     # the live reads the plan needs
    plan = json.loads((out / push.PLAN_NAME).read_text(encoding="utf-8"))
    assert plan["dry_run"] and plan["creates"] == len(SC.PROPERTIES) + 7 and plan["updates"] >= 8
    assert plan["counts"]["1"]["property"]["create"] == len(SC.PROPERTIES) and plan["counts"]["2"]["step"]["clear"] == 1
    assert plan["properties_to_create"][0] == "Wikidata item ID"
    assert all(w["placeholder"] for w in plan["writes"] if w["action"] == "create")
    assert plan["examples"]["1:step:create"][0]["key"] == "lexflow:step:va.records:respond"
    bodies = [json.loads(l) for l in (out / push.BODIES_NAME).read_text(encoding="utf-8").splitlines()]
    assert any(b["clear"] and b["key"] == "lexflow:step:va.records:respond" for b in bodies)
    assert con.execute("SELECT count(*) FROM wikibase_items").fetchone()[0] == 0
    assert result["api_writes"] == 0


# --------------------------------------------------------------------------- the HELD gate
def _lint(out, held):
    out.mkdir(parents=True, exist_ok=True)
    (out / push.LINT_NAME).write_text(json.dumps({"held": [{"key": k, "reasons": ["x"]} for k in held]}),
                                      encoding="utf-8")


def test_really_refuses_without_a_lint_report_or_with_held_items(con, wiki, out):
    with pytest.raises(push.HeldError, match="missing"):
        push.run(con, items=graph_items(), api=api_for(wiki, False), out_dir=out, dry_run=True and False,
                 log=lambda *a: None)
    _lint(out, ["lexflow:step:va.records:respond"])
    with pytest.raises(push.HeldError, match="holds 1 items"):
        push.run(con, items=graph_items(), api=api_for(wiki, False), out_dir=out, dry_run=False, log=lambda *a: None)
    assert wiki.posts == []
    # --allow-held runs, but the held item is still never written, nor pointed at
    result = push.run(con, items=graph_items(), api=api_for(wiki, False), out_dir=out, dry_run=False,
                      allow_held=True, log=lambda *a: None)
    assert "Respond to the request" not in json.dumps(wiki.posts)
    assert result["summary"]["counts"]["1"]["step"] == {"skip-held": 1}
    assert result["summary"]["held_skipped"] == ["lexflow:step:va.records:respond"]
    _lint(out, [])
    result = push.run(con, items=graph_items(), api=api_for(wiki, False), out_dir=out, dry_run=False,
                      log=lambda *a: None, pass_no="1")
    assert result["summary"]["counts"]["1"]["step"] == {"create": 1}


# --------------------------------------------------------------------------- the ontology equivalents
def test_property_items_carry_the_ontology_equivalents(con, wiki, out):
    _run(con, wiki, out, graph_items(), pass_no="1")
    topic = SC.PROP_BY_LABEL["topic"]
    assert topic.equivalents == ("http://data.europa.eu/eli/ontology#is_about", "https://schema.org/about")
    create = next(json.loads(p["data"]) for p in wiki.posts if p.get("new") == "property" and '"topic"' in p["data"])
    p7 = [s["mainsnak"]["datavalue"]["value"] for s in create["claims"] if s["mainsnak"]["property"] == "P7"]
    assert p7 == ([SC.WIKIDATA_ENTITY + topic.wikidata] if topic.wikidata else []) + list(topic.equivalents)
    assert all(s["mainsnak"]["datavalue"]["type"] == "string" for s in create["claims"])        # url snaks
    # pass 2: the existing properties (P5-P25) are appended their P7 claims, once: the Wikidata property of
    # schema.EXISTING_WIKIDATA first, then the ontology IRIs
    wiki.posts.clear()
    result = _run(con, wiki, out, graph_items(), pass_no="2")
    part_of = [json.loads(p["data"]) for p in wiki.posts if p.get("id") == "P9"]
    assert len(part_of) == 1 and "clear" not in next(p for p in wiki.posts if p.get("id") == "P9")
    assert [s["mainsnak"]["datavalue"]["value"] for s in part_of[0]["claims"]] == [
        "http://www.wikidata.org/entity/P361", "http://data.europa.eu/eli/ontology#is_part_of",
        "https://schema.org/isPartOf"]
    assert all(s["mainsnak"]["property"] == "P7" for s in part_of[0]["claims"])
    posted = {p.get("id") for p in wiki.posts if p.get("id", "").startswith("P")}
    assert {pid for label, pid in SC.EXISTING.items() if SC.EXISTING_EQUIVALENTS[label]} <= posted
    assert {SC.EXISTING[label] for label in SC.EXISTING_WIKIDATA} <= posted
    assert "P16" not in posted, "deontic modality has no equivalent: nothing to append"
    c = result["summary"]["counts"]["2"]["property"]
    assert c.get("update", 0) >= 13 + 1
    # a second pass 2 finds them present and appends nothing
    wiki.posts.clear()
    result = _run(con, wiki, out, graph_items(), pass_no="2", resume=True)
    assert not [p for p in wiki.posts if p.get("id", "").startswith("P")]
    assert result["summary"]["counts"]["2"]["property"].get("update", 0) == 0
    assert push.equivalent_claims("part of", None) == [
        graph.Claim("equivalent property", graph.url("http://data.europa.eu/eli/ontology#is_part_of")),
        graph.Claim("equivalent property", graph.url("https://schema.org/isPartOf"))]
    assert push.equivalent_claims("sort key", None) == []
