"""Who do I ask (lexflow.ask.who): routing, the answer's shape on the local store built from the live database
(read-only), a privacy scan of every channel shown, and the vocabulary links file."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from lexflow import config, privacy  # noqa: E402
from lexflow.ask import who as W  # noqa: E402
from lexflow.publish import rdf  # noqa: E402  (imported here, before any fixture moves DATA_DIR, so TTL_PATH is real)
from lexflow.publish import schema as SC  # noqa: E402
from lexflow.publish import vocab_links as VL  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]

GOVS = [("47210400100000", "va", "City of Charlottesville", "municipality", 46553, "Q123766", "http://www.charlottesville.org/"),
        ("47213000100000", "va", "City of Staunton", "municipality", 25750, "Q502250", "http://www.staunton.va.us/"),
        ("47100200200000", "va", "Albemarle County", "county", 112395, "Q488653", "https://www.albemarle.org/"),
        ("06100300000000", "ca", "Orange County", "county", 3186989, None, None)]


@pytest.fixture()
def small(con):
    """A few governments, the two Virginia models and three researched processes, in the empty store."""
    con.executemany("INSERT INTO governments (gov_id, state, name, kind, population, wikidata, website, updated_at) "
                    "VALUES (?,?,?,?,?,?,?, '2026-10-15T00:00:00Z')", GOVS)
    facts = {"actors": [{"id": "commission", "name": "State Corporation Commission", "kind": "public-body",
                         "source": {"section": "13.1-1004", "subsection": "A", "quote": "The Commission shall admit"}},
                        {"id": "organizer", "name": "Organizer", "kind": "private-party", "source": {}}],
             "steps": [{"id": "deliver", "actor": "organizer", "action": "Deliver articles", "source": {"quote": "signing"}},
                       {"id": "admit", "actor": "commission", "action": "Admit to record", "source": {"quote": "shall admit"}}]}
    for mid, q, title in (("va.business", "business", "Start a business in Virginia"),
                          ("va.records", "records", "Request public records")):
        con.execute("INSERT INTO process_models (model_id, state, question, tier, title, stages, facts, updated_at) "
                    "VALUES (?,?,?,'reviewed',?,'{}',?, '2026-10-15T00:00:00Z')", (mid, "va", q, title, json.dumps(facts)))
    spec = {"office": "City Treasurer", "steps": [{"id": "apply", "title": "Apply by mail"}],
            "legal_basis": [{"citation": "Va. Code Ann. § 3.2-6530", "quote": "shall obtain a license", "url": "https://law.lis.virginia.gov/vacode/3.2-6530/"}]}
    for gid, pid, title, cat in (("47213000100000", "dog_license", "Get a dog license", "animals"),
                                 ("47210400100000", "building_permit_residential", "Get a residential building permit", "permits_construction"),
                                 ("47100200200000", "public_records_request", "Request public records (Virginia FOIA)", "records")):
        con.execute("INSERT INTO place_processes (gov_id, state, process, title, category, office, verified, spec, updated_at) "
                    "VALUES (?,?,?,?,?,?,1,?, '2026-10-15T00:00:00Z')", (gid, "va", pid, title, cat, "City Treasurer", json.dumps(spec)))
    con.execute("INSERT INTO contacts (gov_id, state, question, kind, value, label, source, updated_at) VALUES "
                "('47213000100000','va','dog_license','page','https://www.ci.staunton.va.us/departments/city-treasurer/dog-license',"
                "'Dog license page','https://www.ci.staunton.va.us/departments/city-treasurer/dog-license','2026-10-11T00:00:00Z')")
    con.execute("INSERT INTO contacts (gov_id, state, question, kind, value, label, source, updated_at) VALUES "
                "('47213000100000','va','dog_license','phone','540-332-3800','Jane Doe direct line','x','2026-10-11T00:00:00Z')")
    con.commit()
    return con


# ------------------------------------------------------------------------------------------------- routing
PHRASINGS = [
    ("name all the people or roles involved in starting an LLC in Virginia", "business", "va", None),
    ("how do I form a corporation in Virginia?", "business", "va", None),
    ("who do I ask to get a business license in Charlottesville", "business", "va", "47210400100000"),
    ("who handles a FOIA request in Charlottesville", "public-records", "va", "47210400100000"),
    ("public records request, Albemarle County, Virginia", "public-records", "va", "47100200200000"),
    ("I need a building permit for a deck in Charlottesville VA", "building-and-zoning", "va", "47210400100000"),
    ("dog license in Staunton", "animals", "va", "47213000100000"),
    ("Who issues dog licences for the City of Staunton?", "animals", "va", "47213000100000"),
    ("register to vote in Virginia", "voting", "va", None),
    ("voter registration in Orange County, California", "voting", "ca", "06100300000000"),
]


@pytest.mark.parametrize("q,topic,st,gid", PHRASINGS)
def test_routing(small, q, topic, st, gid):
    r = W.route(q, con=small)
    assert r["topic"] == topic and r["topic_by"] == "rule"
    assert r["jurisdiction"] == st
    assert r["gov_id"] == gid
    assert all(k.startswith("lexflow:process:") for k in r["process_keys"])


def test_routing_picks_the_processes(small):
    r = W.route("dog license in Staunton", con=small)
    assert r["process_keys"] == ["lexflow:process:47213000100000:dog_license"]
    r = W.route("starting an LLC in Virginia", con=small)
    assert r["process_keys"] == ["lexflow:process:va.business"]
    r = W.route("FOIA request in Charlottesville", con=small)       # Charlottesville has no researched records process
    assert r["process_keys"] == ["lexflow:process:va.records"]
    r = W.route("building permit", place="47210400100000", con=small)
    assert r["jurisdiction"] == "va" and r["process_keys"] == ["lexflow:process:47210400100000:building_permit_residential"]
    assert W.route("what do I do", place="Virginia", con=small)["jurisdiction"] == "va"


def test_decision_model_only_when_rules_fail(small):
    from lexflow.extract import decide as D
    calls = []

    def stub(state, questions):
        calls.append(state)
        return {"model": "stub", "answers": {"topic": {"type": "choice", "choice": "benefits", "confidence": 0.95,
                                                        "probabilities": {"benefits": 0.95}}}}
    d = D.Decider(answer=stub, cache=False, backend_info={"kind": "stub", "model": "stub"})
    assert W.route("dog license in Staunton", con=small, decider=d)["topic_by"] == "rule" and not calls
    r = W.route("help with my groceries in Staunton", con=small, decider=d)
    assert r["topic"] == "benefits" and r["topic_by"] == "decision" and r["confidence"] == 0.95 and calls
    low = D.Decider(answer=lambda s, q: {"answers": {"topic": {"choice": "benefits", "confidence": 0.5}}}, cache=False,
                    backend_info={"kind": "stub", "model": "stub"})
    r = W.route("help with my groceries", con=small, decider=low)
    assert r["topic"] is None and r["topic_by"] is None


# --------------------------------------------------------------------------------------- the answer's shape
ROLE_KEYS = {"iri", "key", "label", "lexipedia", "process", "played_by", "steps", "quotes", "missing"}


def scan_channels(a: dict) -> list[dict]:
    """Every channel the answer shows, each checked by the privacy shape checks."""
    out = []
    cards = list(a["roles"]) + list(a["local"]) + ([a["place"]] if a.get("place") else [])
    for c in cards:
        pb = c.get("played_by") or c
        owner = [pb.get("label") or ""] + [x.get("label") or "" for x in (pb.get("chain") or [])[:1]]
        for ch in pb.get("channels") or []:
            v = ch["value"]
            if ch["kind"] in ("website", "page"):
                assert privacy.is_office_url(v), v
            elif ch["kind"] == "email":
                assert privacy.is_office_mailbox(v, owner), v
            elif ch["kind"] == "phone":
                assert privacy.office_phone_value(v, owner) == v, v
            elif ch["kind"] == "postal":
                assert privacy.office_value(v, owner) == v, v
            else:
                raise AssertionError(ch["kind"])
            if ch.get("label"):
                assert privacy.office_label(ch["label"], owner) == ch["label"]
            if ch.get("source"):
                assert privacy.office_source(ch["source"]) == ch["source"]
            out.append(ch)
    return out


def test_answer_from_facts_when_no_store(small, monkeypatch):
    monkeypatch.setattr(rdf, "TTL_PATH", Path("/nonexistent/lexipedia.ttl"))
    a = W.answer(W.route("starting an LLC in Virginia", con=small), small)
    assert a["source"] == "facts" and len(a["roles"]) == 2
    roles = {r["label"]: r for r in a["roles"]}
    assert set(roles["Organizer (Virginia)"]) >= ROLE_KEYS
    assert roles["Organizer (Virginia)"]["played_by"]["kind"] == "private-party"
    scc = roles["State Corporation Commission (Virginia)"]
    assert scc["played_by"]["label"] == "Virginia State Corporation Commission"
    assert scc["played_by"]["links"]["wikidata"] == "https://www.wikidata.org/wiki/Q7603136"
    assert scc["quotes"][0]["text"] == "The Commission shall admit"
    assert [s["label"] for s in scc["steps"]] == ["Admit to record"]
    a = W.answer(W.route("dog license in Staunton", con=small), small)
    assert a["source"] == "facts" and a["roles"] == [] and len(a["local"]) == 2
    office = a["local"][0]
    assert office["played_by"]["label"] == "City Treasurer" and office["played_by"]["chain"][0]["label"] == "City of Staunton, Virginia"
    assert [c["kind"] for c in office["played_by"]["channels"]] == ["page"]      # the personal line is refused
    assert office["quotes"][0]["section"] == "Va. Code Ann. § 3.2-6530"
    assert a["place"]["label"] == "City of Staunton, Virginia" and a["place"]["links"]["wikidata_qid"] == "Q502250"
    scan_channels(a)
    text = W.render(a)
    assert "Jane Doe" not in text and "City Treasurer" in text


def live_db() -> Path | None:
    p = Path(config.DB_PATH)
    return p if p.exists() else None


@pytest.fixture()
def live(monkeypatch):
    """The live database read-only and the local store built from it; skipped where either is missing."""
    pytest.importorskip("pyoxigraph")
    if not live_db() or not rdf.TTL_PATH.exists():
        pytest.skip(f"needs the live database ({config.DB_PATH}: {bool(live_db())}) and a built local store "
                    f"({rdf.TTL_PATH}: {rdf.TTL_PATH.exists()}; lexflow sparql --build)")
    con = sqlite3.connect(f"file:{live_db().as_posix()}?mode=ro", uri=True, timeout=30)
    con.row_factory = sqlite3.Row
    yield con
    con.close()


def test_answer_shape_on_the_local_store(live):
    a = W.answer(W.route("name all the people or roles involved in starting an LLC in Virginia", con=live), live)
    assert a["source"] == "store"
    assert a["sparql"] == {"query": "who-does-what", "params": {"jurisdiction": "lexflow:jurisdiction:va"}}
    assert a["roles"], "the Virginia business model has roles in the store"
    for r in a["roles"]:
        assert set(r) >= ROLE_KEYS
        assert r["process"]["key"] == "lexflow:process:va.business"
        assert r["played_by"]["kind"] in ("body", "unit", "court", "office type", "post", "post type", "government",
                                          "private-party", "unknown")
        if r["played_by"]["kind"] not in ("private-party", "unknown"):
            assert {"chain", "channels", "links", "head", "key"} <= set(r["played_by"])
    scc = next(r for r in a["roles"] if r["played_by"].get("key") == "lexflow:agency:va:state_corporation_commission")
    assert scc["played_by"]["links"]["wikidata"] == "https://www.wikidata.org/wiki/Q7603136"
    assert any(c["kind"] == "website" for c in scc["played_by"]["channels"])
    assert scc["quotes"] and scc["quotes"][0]["section"].startswith("Va. Code")
    assert any(q["text"] for q in scc["quotes"])
    b = W.answer(W.route("dog license in Staunton", con=live), live)
    assert b["local"] and b["place"]["gov_id"] == "47213000100000"
    office = next(r for r in b["local"] if r["played_by"]["kind"] == "body")
    assert office["played_by"]["chain"][0]["label"] == "City of Staunton, Virginia"
    assert office["played_by"]["channels"] and len(office["played_by"]["channels"]) <= W.CHANNELS_MAX
    assert all(c.get("source") for c in office["played_by"]["channels"])
    for a_ in (a, b):
        for ch in scan_channels(a_):
            assert ch["retrieved"] is None or len(ch["retrieved"]) == 10


def test_office_type_resolves_to_the_place_and_steps_carry_their_law(live):
    """The coordinator's example: "starting an LLC in Charlottesville" is the Virginia LLC path with the city's
    Commissioner of the Revenue for the local licence step, plus the city's business-topic local processes."""
    r = W.route("starting an LLC in Charlottesville", con=live)
    assert r["gov_id"] == "47210400100000" and "lexflow:process:va.business" in r["process_keys"]
    assert all(p["topic"] == "business" for p in r["processes"] if p["scope"] == "local")
    a = W.answer(r, live)
    cor = next(x for x in a["roles"] if x["label"].lower().startswith("commissioner of the revenue"))
    assert cor["played_by"]["kind"] != "unknown"
    assert cor["played_by"]["resolved_for"] == "City of Charlottesville"
    assert cor["played_by"]["chain"] and cor["played_by"]["chain"][0]["label"] == "City of Charlottesville, Virginia"
    assert cor["played_by"]["channels"], "the city's office has channels"
    scc = next(x for x in a["roles"] if x["played_by"].get("key") == "lexflow:agency:va:state_corporation_commission")
    assert scc["played_by"].get("resolved_for") is None        # a state body stays the state body
    for role in a["roles"] + a["local"]:
        for s in role["steps"]:
            assert {"sections", "forms", "fees"} <= set(s)
            for c in s["sections"]:
                assert c["section"] and {"pinpoint", "text", "url"} <= set(c)
            for f in s["forms"]:
                assert f["label"] and (f["url"] is None or privacy.is_office_url(f["url"]))
            for fee in s["fees"]:
                assert fee["amount"]
    assert any(s["sections"] for x in a["roles"] for s in x["steps"]), "state steps cite their sections"
    assert any(s["forms"] or s["fees"] for x in a["local"] for s in x["steps"]), "local steps carry forms or fees"
    scan_channels(a)


def test_privacy_scan_of_every_channel_shown(live):
    for q in ("starting an LLC in Virginia", "FOIA request in Charlottesville", "dog license in Staunton",
              "pay property taxes in Charlottesville", "voter registration in Albemarle County"):
        a = W.answer(W.route(q, con=live), live)
        shown = scan_channels(a)
        text = json.dumps(a)
        assert "@" not in text or all(privacy.is_office_mailbox(c["value"]) for c in shown if c["kind"] == "email")


# ----------------------------------------------------------------------------------------------- vocab links
def test_vocab_links_targets_cover_the_schema():
    keys = {t["key"] for t in VL.targets()}
    assert set(SC.VOCAB_BY_KEY) <= keys
    assert all(SC.key_for("class", c.slug) in keys for c in SC.CLASSES if not c.wikidata)
    assert not any(SC.key_for("class", c.slug) in keys for c in SC.CLASSES if c.wikidata)


def test_vocab_links_file_shape():
    path = ROOT / "fixtures" / "entities" / "vocab_links.json"
    if not path.exists():
        pytest.skip("fixtures/entities/vocab_links.json not built (python -m lexflow.publish.vocab_links --build)")
    data = json.loads(path.read_text(encoding="utf-8"))
    entries = {k: v for k, v in data.items() if not k.startswith("_")}
    assert entries and set(entries) <= {t["key"] for t in VL.targets()}
    for key, e in entries.items():
        assert {"qid", "label", "relation", "p", "reviewed", "term"} <= set(e), key
        assert e["reviewed"] is False or e["reviewed"] is True
        assert e["relation"] in ("exact", "close", "broad", None)
        assert (e["qid"] is None) == (e["relation"] is None)
        assert e["qid"] is None or (e["qid"].startswith("Q") and e["qid"][1:].isdigit())
        assert 0.0 <= e["p"] <= 1.0
        w = VL.writable(key, path)
        assert w is None or (e["relation"] == "exact" and e["p"] >= VL.WRITE_P and w == e["qid"])
    assert VL.get("lexflow:vocab:topic:courts", path) is not None


def test_vocab_relation_and_suggest_offline():
    court = {"qid": "Q41487", "label": "court", "description": "judicial institution with authority to resolve legal disputes",
             "aliases": ["courts", "court of law"], "p31": [], "p279": [{"qid": "Q1", "label": "judicial organization"}],
             "jurisdiction": [], "sitelinks": 120, "rank": 1, "label_lang": "en"}
    assert VL.relation("courts", court) == "exact"
    assert VL.relation("calendar days", {"label": "day", "aliases": []}) == "broad"
    assert VL.relation("business days", {"label": "working time", "aliases": []}) == "close"
    s = VL.suggest("courts", [court])
    assert s["qid"] == "Q41487" and s["relation"] == "exact" and 0 <= s["p"] <= 1
    assert VL.suggest("courts", [])["qid"] is None


def test_govdirectory_candidates():
    from lexflow.publish import govdirectory as GD
    assert GD.candidates("Q1553390")[0] == "https://www.govdirectory.org/united-states/Q1553390/"
    assert GD.candidates("Q136481241", "nc")[0] == "https://www.govdirectory.org/united-states/north-carolina/Q136481241/"
    assert GD.candidates("x") == []
    assert GD.page_url("Q0", check=False) is None
