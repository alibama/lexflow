"""The local SPARQL copy of Lexipedia (docs/design/wikibase-schema.md sections 6 and 7): Turtle round trip, token
expansion, the canned queries, the API, and a privacy scan of the Turtle built from the live database."""
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlsplit

import pytest

pytest.importorskip("pyoxigraph")

from lexflow import config, privacy  # noqa: E402
from lexflow.municipal import quotes  # noqa: E402
from lexflow.publish import ids as I  # noqa: E402
from lexflow.publish import rdf  # noqa: E402
from lexflow.publish import sparql as SQ  # noqa: E402
from lexflow.publish.rdf import Claim, Item, Value  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def hand_made() -> list[Item]:
    """A section in its chapter, a process with two steps, a role played by a body with a contact, and a rung."""
    quote = "within five working days of receiving a request"
    return [
        Item("lexflow:code:va", "Virginia Code", "the code", [], "lexflow:class:legal-code",
             [Claim("unit level", Value("item", "lexflow:vocab:unit-level:code"))]),
        Item("lexflow:unit:va:t2.2-sii-pb-c37", "Va. Code Title 2.2, Chapter 37", "", [], "lexflow:class:statutory-unit", [
            Claim("part of", Value("item", "lexflow:code:va")),
            Claim("unit level", Value("item", "lexflow:vocab:unit-level:chapter")),
            Claim("sort key", Value("string", "0002.2-0037")),
            Claim("heading text", Value("monolingual", "Virginia Freedom of Information Act", lang="en"))]),
        Item("lexflow:statute:va:2.2-3704", "Va. Code Ann. § 2.2-3704", "a section", ["§ 2.2-3704"],
             "statute or legal provision", [
                 Claim("part of", Value("item", "lexflow:unit:va:t2.2-sii-pb-c37")),
                 Claim("unit level", Value("item", "lexflow:vocab:unit-level:section")),
                 Claim("sort key", Value("string", "0002.2-0037-0003704")),
                 Claim("section number", Value("string", "2.2-3704")),
                 Claim("heading text", Value("monolingual", 'Public records to be open to inspection; "quoted" words', lang="en")),
                 Claim("effective date", Value("time", "2024-07-01")),
                 Claim("effective until", Value("time", "+2030-01-01T00:00:00Z/11")),
                 Claim("official text", Value("url", "https://law.lis.virginia.gov/vacode/2.2-3704/")),
                 Claim("references", Value("item", "lexflow:statute:va:2.2-3701"),
                       qualifiers=[("reference type", Value("item", "lexflow:vocab:reference-type:definition"))],
                       references=[[("quoted text", Value("string", 'As used in this chapter, "public body"')),
                                    ("pinpoint", Value("string", "A"))]])], exists=True),
        Item("lexflow:statute:va:2.2-3701", "Va. Code Ann. § 2.2-3701", "", [], "statute or legal provision", [], exists=True),
        Item("lexflow:vocab:unit-level:section", "section", "", [], "lexflow:class:unit-level", []),
        Item("lexflow:vocab:unit-level:chapter", "chapter", "", [], "lexflow:class:unit-level", []),
        Item("lexflow:vocab:unit-level:code", "code", "", [], "lexflow:class:unit-level", []),
        Item("lexflow:vocab:time-unit:working-days", "working days", "", [], "lexflow:class:time-unit", []),
        Item("lexflow:vocab:reference-type:definition", "definition", "", [], "lexflow:class:reference-type", []),
        Item("lexflow:vocab:topic:public-records", "public records", "", [], "lexflow:class:topic", []),
        Item("lexflow:vocab:review-status:reviewed", "reviewed", "", [], "lexflow:class:review-status", []),
        Item("lexflow:vocab:currency:usd", "US dollar", "", [], "lexflow:class:currency", []),
        Item("lexflow:jurisdiction:va", "Virginia", "", [], "jurisdiction",
             [Claim("Wikidata item ID", Value("external-id", "Q1370"))], exists=True),
        Item("lexflow:process:va.records", "Request public records (Virginia)", "", ["How do I get records in Virginia?"],
             "legal process", [
                 Claim("applies to jurisdiction", Value("item", "lexflow:jurisdiction:va")),
                 Claim("topic", Value("item", "lexflow:vocab:topic:public-records")),
                 Claim("question asked", Value("monolingual", "How do I request public records in Virginia?", lang="en")),
                 Claim("review status", Value("item", "lexflow:vocab:review-status:reviewed"))], exists=True),
        Item("lexflow:role:va:records:requester", "requester", "", [], "legal role",
             [Claim("played by", Value("item", "lexflow:private-party"))], exists=True),
        Item("lexflow:role:va:records:custodian", "custodian", "", [], "legal role",
             [Claim("played by", Value("item", "lexflow:agency:va:dgs"))], exists=True),
        Item("lexflow:agency:va:dgs", "Department of General Services", "", [], "lexflow:class:government-agency", [
            Claim("part of", Value("item", "lexflow:agency:va:government")),
            Claim("email address", Value("url", "mailto:foia@dgs.virginia.gov"),
                  references=[[("source URL", Value("url", "https://dgs.virginia.gov/foia")),
                               ("retrieved", Value("time", "2026-10-01"))]]),
            Claim("Wikidata item ID", Value("external-id", "Q5260000"))]),
        Item("lexflow:agency:va:government", "Commonwealth of Virginia", "", [], "lexflow:class:government-agency", []),
        Item("lexflow:step:va.records:submit_request", "Submit a request", "", [], "legal process step", [
            Claim("part of", Value("item", "lexflow:process:va.records")),
            Claim("bearer", Value("item", "lexflow:role:va:records:requester")),
            Claim("fee", Value("quantity", "0", unit="lexflow:vocab:currency:usd"))], exists=True),
        Item("lexflow:step:va.records:respond", "Respond within five working days", "", [], "legal process step", [
            Claim("part of", Value("item", "lexflow:process:va.records")),
            Claim("follows", Value("item", "lexflow:step:va.records:submit_request")),
            Claim("bearer", Value("item", "lexflow:role:va:records:custodian")),
            Claim("time limit", Value("quantity", "5"),
                  qualifiers=[("time unit", Value("item", "lexflow:vocab:time-unit:working-days")),
                              ("counted from", Value("string", "receiving a request"))],
                  references=[[("source section", Value("item", "lexflow:statute:va:2.2-3704")),
                               ("pinpoint", Value("string", "B")), ("quoted text", Value("string", quote))]]),
            Claim("escalates to", Value("item", "lexflow:rung:va:records:2.2-3713:court-petition"))], exists=True),
        Item("lexflow:rung:va:records:2.2-3713:court-petition", "petition the circuit court", "", [],
             "lexflow:class:escalation-mechanism", [
                 Claim("part of", Value("item", "lexflow:process:va.records")),
                 Claim("escalates to", Value("item", "lexflow:agency:va:circuit_court")),
                 Claim("references", Value("item", "lexflow:statute:va:2.2-3704")),
                 Claim("time limit", Value("quantity", "30"), qualifiers=[("time unit", Value("item", "lexflow:vocab:time-unit:working-days"))])]),
        Item("lexflow:agency:va:circuit_court", "circuit court", "", [], "lexflow:class:court", []),
        Item("lexflow:private-party", "private party", "", [], "legal role", []),
    ]


@pytest.fixture()
def idmap(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "t.db")        # no live wikibase_items table here
    monkeypatch.setattr(I, "IDS_PATH", tmp_path / "ids.json")
    m = I.IdMap()
    monkeypatch.setattr(I, "_default", m)
    return m


@pytest.fixture()
def store(tmp_path, idmap):
    out = rdf.write(hand_made(), tmp_path / "lexipedia.ttl", idmap)
    return rdf.memory_store(out)


def q(store, text, idmap=None, **params):
    return rdf.query(store, SQ.prepare(text, params, idmap or I.default())).simple()


# ------------------------------------------------------------------- turtle
def test_turtle_round_trip(tmp_path, idmap):
    out = rdf.write(hand_made(), tmp_path / "lexipedia.ttl", idmap)
    ttl = out.read_text(encoding="utf-8")
    assert ttl.startswith("@prefix lx: <https://lexipedia.wikibase.cloud/entity/> .")
    assert 'rdfs:label "Va. Code Ann. § 2.2-3704"@en' in ttl
    assert 'skos:altLabel "§ 2.2-3704"@en' in ttl and 'schema:description "a section"@en' in ttl
    assert '\\"quoted\\" words' in ttl                                  # strings are escaped
    store = rdf.memory_store(out)
    # existing ids are reused: the section is a Q10, the process a Q7, P25 carries the key, P9 the chapter
    rows = q(store, "SELECT ?cls ?key ?unit WHERE { ?s lxt:{P:legal identifier} ?key ; lxt:P5 ?cls ; lxt:{P:part of} ?unit . "
                    "FILTER(?key = 'lexflow:statute:va:2.2-3704') }")
    assert rows == [{"cls": "lx:Q10", "key": "lexflow:statute:va:2.2-3704", "unit": "lx:" + idmap.qid("lexflow:unit:va:t2.2-sii-pb-c37")}]
    # the full statement form: statement node, qualifier, reference with the quote; the direct form agrees
    rows = q(store, "SELECT ?other ?type ?quote ?pin WHERE { lx:{Q:lexflow:statute:va:2.2-3704} lxp:{P:references} ?st . "
                    "?st a wikibase:Statement ; lxps:{P:references} ?other ; lxpq:{P:reference type} ?t . ?t rdfs:label ?type . "
                    "?st prov:wasDerivedFrom ?ref . ?ref a wikibase:Reference ; lxpr:{P:quoted text} ?quote ; lxpr:{P:pinpoint} ?pin }")
    assert len(rows) == 1 and rows[0]["pin"] == "A" and rows[0]["quote"].startswith("As used in this chapter")
    assert rows[0]["other"] == "lx:" + idmap.qid("lexflow:statute:va:2.2-3701")
    direct = q(store, "SELECT ?o WHERE { lx:{Q:lexflow:statute:va:2.2-3704} lxt:{P:references} ?o }")
    assert direct == [{"o": rows[0]["other"]}]
    # typed literals: time, quantity with its unit value node, monolingual, url
    rows = q(store, "SELECT ?from ?until ?heading ?text WHERE { lx:{Q:lexflow:statute:va:2.2-3704} lxt:{P:effective date} ?from ; "
                    "lxt:{P:effective until} ?until ; lxt:{P:heading text} ?heading ; lxt:{P:official text} ?text }")
    assert rows[0]["from"] == "2024-07-01T00:00:00Z" and rows[0]["until"] == "2030-01-01T00:00:00Z"
    assert rows[0]["text"] == "https://law.lis.virginia.gov/vacode/2.2-3704/"
    raw = rdf.query(store, SQ.prepare("SELECT ?from ?heading WHERE { lx:{Q:lexflow:statute:va:2.2-3704} lxt:{P:effective date} ?from ; "
                                      "lxt:{P:heading text} ?heading }", {}, idmap))
    assert raw[0]["from"]["datatype"].endswith("#dateTime") and raw[0]["heading"]["xml:lang"] == "en"
    rows = q(store, "SELECT ?fee ?unit WHERE { lx:{Q:lexflow:step:va.records:submit_request} lxp:{P:fee} ?st . ?st lxpsv:{P:fee} ?v . "
                    "?v wikibase:quantityAmount ?fee ; wikibase:quantityUnit ?unit }")
    assert rows == [{"fee": "0", "unit": "lx:" + idmap.qid("lexflow:vocab:currency:usd")}]
    # normalised external ids: Wikidata item ID as a Wikidata IRI beside the string
    rows = q(store, "SELECT ?s ?n WHERE { lx:{Q:lexflow:jurisdiction:va} lxt:{P:Wikidata item ID} ?s ; lxn:{P:Wikidata item ID} ?n }")
    assert rows == [{"s": "Q1370", "n": "wd:Q1370"}]
    # the properties are entities with their types; a class item carries its label
    rows = q(store, "SELECT ?t WHERE { lx:{P:time limit} a wikibase:Property ; wikibase:propertyType ?t ; wikibase:directClaim lxt:{P:time limit} }")
    assert rows == [{"t": "wikibase:Quantity"}]
    assert q(store, "SELECT ?l WHERE { lx:Q7 rdfs:label ?l }") == [{"l": "legal process"}]
    # the persisted store loads the same graph
    persisted = rdf.load(out, tmp_path / "store")
    n = lambda s: int(next(iter(s.query("SELECT (COUNT(*) AS ?n) WHERE { ?s ?p ?o }")))["n"].value)  # noqa: E731
    assert n(persisted) == n(store) > 200


def test_turtle_is_deterministic(tmp_path, idmap):
    a = rdf.write(hand_made(), tmp_path / "a.ttl", idmap).read_text(encoding="utf-8")
    b = rdf.write(hand_made(), tmp_path / "b.ttl", idmap).read_text(encoding="utf-8")
    assert a == b


# -------------------------------------------------------------------- tokens
def test_token_expansion(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "t.db")
    monkeypatch.setattr(I, "IDS_PATH", tmp_path / "none.json")
    m = I.IdMap()
    assert m.expand("lxt:{P:bearer} lx:{Q:legal process} lxt:{P:instance of}") == "lxt:P17 lx:Q7 lxt:P5"
    # provisional ids follow sorted order, from P900 / Q900000, and stay put when more keys arrive
    m.assign(keys=["lexflow:b", "lexflow:a"], labels=["zeta", "alpha"])
    assert m.qid("lexflow:a") == "Q900000" and m.qid("lexflow:b") == "Q900001"
    assert m.pid("alpha") == "P900" and m.pid("zeta") == "P901"
    m.assign(keys=["lexflow:0"])
    assert m.qid("lexflow:0") == "Q900002" and m.qid("lexflow:a") == "Q900000"
    assert m.expand("{Q:lexflow:a} {P:alpha} {Q:Q12} {P:P25}") == "Q900000 P900 Q12 P25"
    # an unknown token gets a provisional id and is reported
    assert re.match(r"^Q9\d{5}$", m.expand("{Q:lexflow:new}")) and "Q:lexflow:new" in m.unresolved
    # the provisional map is remembered between runs
    m.save_provisional()
    again = I.IdMap()
    assert again.qid("lexflow:a") == "Q900000" and again.pid("alpha") == "P900"
    # ids.json (either layout) wins over provisional ids
    (tmp_path / "ids.json").write_text(json.dumps({"items": {"lexflow:a": "Q1500"}, "properties": {"alpha": "P40"}}))
    monkeypatch.setattr(I, "IDS_PATH", tmp_path / "ids.json")
    r = I.IdMap()
    assert r.resolved and r.qid("lexflow:a") == "Q1500" and r.pid("alpha") == "P40" and r.qid("lexflow:b") == "Q900001"
    (tmp_path / "ids.json").write_text(json.dumps({"lexflow:a": "Q1501", "alpha": "P41"}))
    flat = I.IdMap()
    assert flat.qid("lexflow:a") == "Q1501" and flat.pid("alpha") == "P41"
    # schema classes resolve by key and by label
    assert m.qid("lexflow:class:jurisdiction") == "Q21" and m.qid("jurisdiction") == "Q21"


def test_database_ids_come_first(tmp_path, monkeypatch):
    """wikibase_items and wikibase_props (what the push records) win over ids.json and provisional ids; a missing
    or unreadable database gives nothing."""
    from lexflow.store import db
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "t.db")
    monkeypatch.setattr(I, "IDS_PATH", tmp_path / "ids.json")
    assert I.database_ids(tmp_path / "missing.db") == ({}, {})
    con = db.connect(tmp_path / "t.db")
    con.execute("INSERT INTO wikibase_items(key, qid, label) VALUES ('lexflow:process:va.records', 'Q1620', 'x')")
    con.execute("INSERT INTO wikibase_items(key, qid, label) VALUES ('lexflow:statute:va:2.2-3704', NULL, 'pending')")
    con.execute("INSERT INTO wikibase_props(label, pid, datatype) VALUES ('step kind', 'P34', 'item')")
    con.commit()
    con.close()
    props, items = I.database_ids(tmp_path / "t.db")
    assert props == {"step kind": "P34"} and items == {"lexflow:process:va.records": "Q1620"}
    (tmp_path / "ids.json").write_text(json.dumps({"items": {"lexflow:process:va.records": "Q562", "lexflow:other": "Q77"},
                                                   "properties": {"step kind": "P900", "topic": "P48"}}))
    m = I.IdMap()
    assert m.resolved and m.from_database == 2
    assert m.qid("lexflow:process:va.records") == "Q1620" and m.pid("step kind") == "P34"     # the database wins
    assert m.qid("lexflow:other") == "Q77" and m.pid("topic") == "P48"                       # ids.json fills the rest
    assert m.qid("lexflow:statute:va:2.2-3704").startswith("Q9") and "Q:lexflow:statute:va:2.2-3704" in m.unresolved
    assert m.expand("{Q:lexflow:process:va.records} {P:step kind}") == "Q1620 P34"
    off = I.IdMap(database=False)
    assert off.qid("lexflow:process:va.records") == "Q562" and off.pid("step kind") == "P900"
    assert I.IdMap.for_turtle().qid("lexflow:process:va.records") == "Q1620"               # no Turtle map yet


def test_local_queries_keep_the_ids_the_turtle_was_written_with(tmp_path, monkeypatch, idmap):
    out = rdf.write(hand_made(), tmp_path / "wikibase" / "lexipedia.ttl", idmap)
    provisional = idmap.qid("lexflow:process:va.records")
    assert provisional.startswith("Q9")
    # the resolver then learns the wiki's id for the process: live queries use it, local ones keep the Turtle's
    (tmp_path / "ids.json").write_text(json.dumps({"items": {"lexflow:process:va.records": "Q562"}, "properties": {}}))
    assert I.IdMap().qid("lexflow:process:va.records") == "Q562"
    local = I.IdMap.for_turtle()
    assert local.turtle and local.qid("lexflow:process:va.records") == provisional
    assert I.IdMap.turtle_stale(out)
    rows = rdf.query(rdf.memory_store(out), SQ.prepare(SQ.get("process-steps"), {}, local))
    assert len(rows) == 2


def test_param_terms_and_values_substitution(idmap):
    assert SQ.term("Q24") == "lx:Q24"
    assert SQ.term("lexflow:jurisdiction:va") == "lx:{Q:lexflow:jurisdiction:va}"
    assert SQ.term("2026-10-15") == '"2026-10-15T00:00:00Z"^^xsd:dateTime'
    assert SQ.term("5") == "5" and SQ.term('records "x"') == '"records \\"x\\""' and SQ.term("") == "UNDEF"
    text = 'SELECT * WHERE { VALUES ?a { lx:{Q:lexflow:jurisdiction:va} }\n VALUES ?d { "2026-10-15T00:00:00Z"^^xsd:dateTime } }'
    out = SQ.prepare(text, {"a": "Q33", "d": "2020-01-01"}, idmap)
    assert "VALUES ?a { lx:Q33 }" in out and 'VALUES ?d { "2020-01-01T00:00:00Z"^^xsd:dateTime }' in out
    assert out.startswith("PREFIX lx:")
    with pytest.raises(KeyError):
        SQ.prepare(text, {"nope": "1"}, idmap)
    parsed = SQ.parse("# question: why\n# params: a=lexflow:x, b=\n# live-only: yes\nSELECT * WHERE { VALUES ?c { UNDEF } }")
    assert parsed.question == "why" and parsed.params == {"a": "lexflow:x", "b": "", "c": ""} and parsed.live_only


# -------------------------------------------------------------- the queries
def test_every_query_has_the_header_and_prefixes():
    names = {p.stem for p in SQ.DIR.glob("*.rq")}
    assert names == {"law-in-order", "law-tree", "law-neighbours", "law-in-force", "who-does-what", "process-steps",
                     "deadlines", "escalation", "body-contacts", "by-topic", "find-process", "federated-body", "coverage"}
    for query in SQ.catalogue():
        assert query.question, query.name
        for p in ("lx", "lxt", "lxp", "lxps", "lxpq", "lxpr", "lxn", "wikibase", "schema", "rdfs", "skos"):
            assert f"PREFIX {p}: <{rdf.PREFIXES[p]}>" in query.text, (query.name, p)
        assert "wd:Q" not in query.text.replace("wd:Q1985727", "") or query.name == "federated-body"
        for name in query.params:
            assert re.search(r"VALUES\s+\?%s\s*\{" % name, query.text), (query.name, name)


# with the queries' default parameters: body-contacts and escalation point at keys the tiny store lacks (0 rows)
# and are run with their own parameters below
EXPECTED_LOCAL = {"law-in-order": 1, "law-tree": 2, "law-neighbours": 2, "law-in-force": 1, "who-does-what": 2,
                  "process-steps": 2, "deadlines": 2, "escalation": 0, "body-contacts": 0, "by-topic": 1,
                  "find-process": 3, "coverage": 5}


def test_every_query_parses_and_runs_on_the_tiny_store(store, idmap):
    for query in SQ.catalogue():
        text = SQ.prepare(query, {}, idmap)
        assert "{P:" not in text and "{Q:" not in text, query.name
        if query.live_only:
            store.query(text)                       # parses; SERVICE is not run locally
            continue
        rows = rdf.query(store, text)
        assert len(rows) == EXPECTED_LOCAL[query.name], (query.name, rows.simple())
        assert rows.vars == rdf.projection(query.text)
    steps = rdf.query(store, SQ.prepare(SQ.get("process-steps"), {}, idmap)).simple()
    assert [s["stepLabel"] for s in steps] == ["Submit a request", "Respond within five working days"]
    assert steps[1]["deadline"] == "5" and steps[1]["unit"] == "working days" and steps[0]["feeUSD"] == "0"
    chain = rdf.query(store, SQ.prepare(SQ.get("escalation"), {"step": "lexflow:step:va.records:respond"}, idmap)).simple()
    assert {c["targetLabel"] for c in chain} == {"petition the circuit court", "circuit court"}
    assert any(c.get("bodyLabel") == "circuit court" and c.get("limit") == "30" for c in chain)
    tree = rdf.query(store, SQ.prepare(SQ.get("law-tree"), {}, idmap)).simple()
    assert [t["ancestorLabel"] for t in tree] == ["Virginia Code", "Va. Code Title 2.2, Chapter 37"]
    assert [t.get("level") for t in tree] == ["code", "chapter"]
    gone = rdf.query(store, SQ.prepare(SQ.get("law-in-force"), {"date": "2031-01-01"}, idmap))
    assert len(gone) == 0
    contacts = rdf.query(store, SQ.prepare(SQ.get("body-contacts"), {"body": "lexflow:agency:va:dgs"}, idmap)).simple()
    assert {c["kind"] for c in contacts} == {"email", "process"}
    assert any(c.get("value") == "mailto:foia@dgs.virginia.gov" and c.get("retrieved", "").startswith("2026-10-01") for c in contacts)
    found = rdf.query(store, SQ.prepare(SQ.get("find-process"), {"text": "how do i"}, idmap)).simple()
    assert found and all("how do i" in f["matched"].lower() for f in found)
    cov = rdf.query(store, SQ.prepare(SQ.get("coverage"), {}, idmap)).simple()
    assert {"classLabel": "legal process", "status": "reviewed", "n": "1", "class": "lx:Q7"} in cov


# ----------------------------------------------------------------------- api
def test_api_endpoints(con, tmp_path, monkeypatch, idmap):
    from fastapi.testclient import TestClient
    from lexflow.api import app as A
    monkeypatch.setattr(A.runner, "start", lambda: None)
    monkeypatch.setattr(rdf, "TTL_PATH", tmp_path / "wikibase" / "lexipedia.ttl")
    monkeypatch.setattr(rdf, "STORE_DIR", tmp_path / "wikibase" / "store")
    with TestClient(A.app) as c:
        cat = c.get("/api/sparql/queries").json()
        assert len(cat["queries"]) == 13 and cat["prefixes"].startswith("PREFIX lx:") and cat["local_built"] is False
        assert cat["max_rows"] == 2000 and cat["timeout"] == 30
        byname = {x["name"]: x for x in cat["queries"]}
        assert byname["process-steps"]["params"] == {"process": "lexflow:process:va.records"}
        assert byname["federated-body"]["live_only"] and byname["coverage"]["question"]
        assert c.get("/api/sparql", params={"q": "coverage"}).status_code == 409          # nothing built yet
        rdf.load(rdf.write(hand_made(), rdf.TTL_PATH, idmap))
        r = c.get("/api/sparql", params={"q": "process-steps", "param": ["process=lexflow:process:va.records"]})
        assert r.status_code == 200
        body = r.json()
        assert body["n"] == 2 and body["vars"][:2] == ["step", "stepLabel"] and body["live"] is False and not body["truncated"]
        assert body["rows"][0]["stepLabel"] == {"type": "literal", "value": "Submit a request", "xml:lang": "en"}
        assert body["name"] == "process-steps" and "VALUES ?process { lx:Q" in body["query"]
        r = c.get("/api/sparql", params={"q": "SELECT ?s WHERE { ?s a wikibase:Item } ORDER BY ?s", "limit": 3}).json()
        assert r["n"] == 3 and r["truncated"] and r["name"] is None
        assert c.get("/api/sparql", params={"q": "SELECT ?s WHERE { ?s a wikibase:Item "}).status_code == 400
        assert c.get("/api/sparql", params={"q": "federated-body"}).status_code == 400
        assert c.get("/api/sparql", params={"q": "law-in-force", "param": ["nope=1"]}).status_code == 400
        assert c.get("/api/sparql", params={"q": "ASK { ?s a wikibase:Item }"}).json()["rows"] == [{"result": {"type": "literal", "value": "true"}}]
        assert c.post("/api/sparql", json={"q": "coverage"}).status_code == 405


# ------------------------------------------------------------------- privacy
def _no_reprint_hosts():
    return tuple(quotes.NO_REPRINT)


def test_privacy_scan_of_the_turtle_built_from_the_database(tmp_path, monkeypatch):
    """Every mailbox in the Turtle is an office mailbox, every phone a main line, and no quote comes from a site whose
    terms forbid reprinting.  Runs on data/wikibase/lexipedia.ttl when it was built from the live database, else
    builds it from the database when graph.py and the database exist."""
    ttl = rdf.TTL_PATH
    if not ttl.exists():
        pytest.importorskip("lexflow.publish.graph")
        if not config.DB_PATH.exists():
            pytest.skip("no database to build the Turtle from")
        from lexflow.publish import graph
        from lexflow.store import db
        con = db.connect(config.DB_PATH)
        try:
            items = graph.build(con)
        finally:
            con.close()
        monkeypatch.setattr(config, "DATA_DIR", tmp_path)
        ttl = rdf.write(items, tmp_path / "lexipedia.ttl", I.IdMap())
    text = ttl.read_text(encoding="utf-8")
    store = rdf.memory_store(ttl)
    idmap = I.IdMap()
    mailboxes = [m for m in re.findall(r"<mailto:([^>]+)>", text)]
    bad = [m for m in mailboxes if not privacy.is_office_mailbox(m)]
    assert not bad, f"personal-looking mailboxes in the Turtle: {bad[:5]}"
    phones = rdf.query(store, SQ.prepare("SELECT ?v WHERE { ?s lxt:{P:phone number} ?v }", {}, idmap)).simple()
    bad = [p["v"] for p in phones if privacy.office_phone_value(p["v"]) is None]
    assert not bad, f"phone values that are not main lines: {bad[:5]}"
    refs = rdf.query(store, SQ.prepare("SELECT ?url ?quote WHERE { ?ref lxpr:{P:source URL} ?url ; lxpr:{P:quoted text} ?quote }", {}, idmap)).simple()
    hosts = _no_reprint_hosts()
    leaked = [r["url"] for r in refs if quotes.policy(r["url"])]
    assert not leaked, f"quotes from no-reprint sites: {leaked[:5]}"
    assert all(urlsplit(u).hostname for u in [r["url"] for r in refs]) and hosts
    # nothing names a person: labels of bodies and roles carry no "Mr/Ms/Dr" titles or staff-page links
    labels = rdf.query(store, SQ.prepare("SELECT ?l WHERE { ?s a wikibase:Item ; rdfs:label ?l }", {}, idmap)).simple()
    titled = [l["l"] for l in labels if re.search(r"\b(Mr|Mrs|Ms|Dr|Hon)\.?\s+[A-Z]", l["l"])]
    assert not titled, titled[:5]
    urls = re.findall(r"<(https?://[^>]+)>", text)
    staff = [u for u in urls if not privacy.is_office_url(u) and "wikidata.org" not in u and "lexipedia" not in u]
    assert not staff, f"person-level links in the Turtle: {staff[:5]}"


def test_turtle_carries_the_ontology_mapping_triples(tmp_path, idmap):
    eli_lrs, sch_leg = "http://data.europa.eu/eli/ontology#LegalResourceSubdivision", "https://schema.org/Legislation"
    items = [Item("lexflow:class:statute", "statute", "a class", [], None, [
        Claim("exact match", Value("url", "http://www.wikidata.org/entity/Q820655")),
        Claim("exact match", Value("url", eli_lrs)),
        Claim("close match", Value("url", sch_leg))])]
    out = rdf.write(items, tmp_path / "lexipedia.ttl", idmap)
    ttl = out.read_text(encoding="utf-8")
    assert "@prefix owl: <http://www.w3.org/2002/07/owl#> ." in ttl
    assert f"skos:exactMatch <{eli_lrs}>" in ttl and f"skos:closeMatch <{sch_leg}>" in ttl
    assert f"lxt:P8 <{eli_lrs}>" in ttl, "the claim itself is still written"
    # the properties: owl:equivalentProperty for the existing and the new ones with equivalents, none for the rest
    assert "owl:equivalentProperty <http://data.europa.eu/eli/ontology#is_part_of>" in ttl
    assert "owl:equivalentProperty <https://schema.org/about>" in ttl
    store = rdf.memory_store(out)
    rows = q(store, "SELECT ?o WHERE { ?s lxt:{P:legal identifier} 'lexflow:class:statute' ; skos:exactMatch ?o } ORDER BY ?o")
    assert [r["o"] for r in rows] == [eli_lrs, "wd:Q820655"]
    rows = q(store, "SELECT ?o WHERE { ?s lxt:{P:legal identifier} 'lexflow:class:statute' ; skos:closeMatch ?o }")
    assert [r["o"] for r in rows] == [sch_leg]
