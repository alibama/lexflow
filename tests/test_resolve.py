"""lexflow.resolve: the queue over a fake Glass Database, the evidence from canned Wikidata facts, the judge's
parsing and sanity checks, ResolveBench's rows and summary, the live run's consensus and write-back, the API and
the page.  Ollama and the Glass Database are stubs on random localhost ports; nothing touches a real server."""
from __future__ import annotations

import json
import re
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

from lexflow import config
from lexflow.resolve import bench as RB
from lexflow.resolve import evidence as E
from lexflow.resolve import judge as J
from lexflow.resolve.source import Case, GlassDatabase
from lexflow.store import db

ROOT = Path(__file__).resolve().parents[1]

# the lookup's rows, as the Glass Database's /api/wikibase/wikidata answers them
ROWS = [
    {"key": "gdb:artists:1", "kind": "person", "label": "Theo Park", "status": "unsure", "qid": "",
     "why": "2 items carry the name", "item_description": "glass artist, Norfolk, Virginia",
     "candidates": [{"qid": "Q901", "label": "Theo Park", "description": "British sculptor", "types": ["human"]},
                    {"qid": "Q902", "label": "Theo Park", "description": "Canadian ice hockey player", "types": ["human"]}]},
    {"key": "gdb:artists:2", "kind": "person", "label": "Nadia Okonkwo", "status": "unsure", "qid": "",
     "why": "2 people in Wikidata's glass occupations carry this name", "item_description": "glass artist, Portland, Oregon",
     "candidates": [{"qid": "Q911", "label": "Nadia Okonkwo", "description": "Nigerian glass artist", "types": ["human"]},
                    {"qid": "Q912", "label": "Nadia Okonkwo", "description": "Nigerian novelist (1901-1960)", "types": ["human"]}]},
    {"key": "gdb:place:crozet-virginia", "kind": "place", "label": "Crozet", "status": "matched", "qid": "Q1141856",
     "why": "the one item of that name and kind", "item_description": "Virginia, United States",
     "candidates": [{"qid": "Q1141856", "label": "Crozet", "description": "census designated place in Albemarle County, Virginia", "types": ["CDP"]},
                    {"qid": "Q777", "label": "Crozet", "description": "island group in the Indian Ocean", "types": ["archipelago"]}]},
    {"key": "gdb:artists:3", "kind": "person", "label": "Rae Sutter", "status": "none", "qid": "",
     "why": "namesakes exist, but none is described in terms of glass", "item_description": "glass artist, Crozet, Virginia",
     "candidates": [{"qid": "Q921", "label": "Rae Sutter", "description": "American politician", "types": ["human"]}]},
    {"key": "gdb:artists:4", "kind": "person", "label": "Bea Lindqvist", "status": "confirmed", "qid": "Q931",
     "why": "linked by boss on the page", "item_description": "glass artist, Bristol, United Kingdom",
     "candidates": [{"qid": "Q931", "label": "Bea Lindqvist", "description": "Swedish glass sculptor", "types": ["human"]}]},
    {"key": "gdb:colour:red", "kind": "colour", "label": "red", "status": "known", "qid": "Q3142", "why": "hand list",
     "item_description": "red glass", "candidates": []},
    {"key": "gdb:artists:5", "kind": "person", "label": "Pike Example", "status": "none", "qid": "",
     "why": "Wikidata has no item of that name and kind", "item_description": "glass artist, Crozet, Virginia", "candidates": []},
]
ITEMS = {
    "gdb:artists:1": {"item": {"aliases": ["T. Park"], "url": "https://glassdatabase.test/explore/?q=Theo",
                               "claims": [{"p": "work location", "v": {"k": "item", "v": "gdb:place:norfolk-virginia"}},
                                          {"p": "technique", "v": {"k": "item", "v": "gdb:technique:offhand-blown"}},
                                          {"p": "Instagram username", "v": {"k": "external-id", "v": "theo.glass"}},
                                          {"p": "Glass Database ID", "v": {"k": "external-id", "v": "gdb:artists:1"}}]},
                      "refs": {"gdb:place:norfolk-virginia": {"label": "Norfolk", "qid": ""},
                               "gdb:technique:offhand-blown": {"label": "Offhand Blown Glass", "qid": ""}}},
    "gdb:artists:4": {"item": {"aliases": [], "url": "https://glassdatabase.test/explore/?q=Bea",
                               "claims": [{"p": "work location", "v": {"k": "item", "v": "gdb:place:bristol-england"}},
                                          {"p": "official website", "v": {"k": "url", "v": "https://www.bealindqvist.example/"}},
                                          {"p": "Instagram username", "v": {"k": "external-id", "v": "bea.glass"}}]},
                      "refs": {"gdb:place:bristol-england": {"label": "Bristol", "qid": ""}}},
    "gdb:artists:5": {"item": {"aliases": [], "url": "https://glassdatabase.test/explore/?q=Pike",
                               "claims": [{"p": "work location", "v": {"k": "item", "v": "gdb:place:crozet-virginia"}}]},
                      "refs": {"gdb:place:crozet-virginia": {"label": "Crozet", "qid": ""}}},
}
# what a web search says (evidence.search is replaced by this in the enrich tests), by a word of the query
HITS = {
    "pike example": [
        {"title": "Pike Example Glass – hot shop in Crozet, Virginia", "url": "https://pikeexampleglass.com/about",
         "snippet": "Pike Example blows glass in Crozet, Virginia. Follow @pikeexample on Instagram."},
        {"title": "Pike Example (@pikeexample) • Instagram photos", "url": "https://www.instagram.com/pikeexample/", "snippet": "glass artist in Crozet"},
        {"title": "Pike Example - Facebook", "url": "https://www.facebook.com/pikeexample", "snippet": "posts"},
        {"title": "Pike - Wikipedia", "url": "https://en.wikipedia.org/wiki/Pike", "snippet": "a fish"},
        {"title": "Pike Example | Saatchi Art", "url": "https://www.saatchiart.com/pikeexample", "snippet": "buy art"}],
    "bea lindqvist": [
        {"title": "Bea Lindqvist Glass", "url": "https://bealindqvist.example/", "snippet": "Bea Lindqvist, glass sculptor, Bristol. Instagram @bea.glass"},
        {"title": "bea.glass on Instagram", "url": "https://www.instagram.com/bea.glass/", "snippet": "Bristol based glass"}],
    "rae sutter": [{"title": "Rae Sutter for Council", "url": "https://raesutter.vote/", "snippet": "Vote Rae Sutter"}],
}


def fake_search(q, limit=5):
    key = next((k for k in HITS if k in q.lower()), None)
    return list(HITS.get(key, []))
# what Wikidata says about the candidates (evidence.entity_facts is replaced by this in the tests)
WD = {
    "Q901": {"label": "Theo Park", "description": "British sculptor", "aliases": [], "enwiki": "",
             "facts": {"instance of": ["human"], "occupation": ["sculptor"], "citizenship": ["United Kingdom"]}},
    "Q902": {"label": "Theo Park", "description": "Canadian ice hockey player", "aliases": [], "enwiki": "",
             "facts": {"instance of": ["human"], "occupation": ["ice hockey player"]}},
    "Q911": {"label": "Nadia Okonkwo", "description": "Nigerian glass artist", "aliases": [], "enwiki": "Nadia Okonkwo",
             "facts": {"instance of": ["human"], "occupation": ["glass artist"], "work location": ["Portland"]}},
    "Q912": {"label": "Nadia Okonkwo", "description": "Nigerian novelist (1901-1960)", "aliases": [], "enwiki": "",
             "facts": {"instance of": ["human"], "occupation": ["novelist"], "born": ["1901"], "died": ["1960"]}},
    "Q1141856": {"label": "Crozet", "description": "census designated place in Albemarle County, Virginia", "aliases": [],
                 "enwiki": "Crozet, Virginia", "facts": {"instance of": ["census-designated place"], "country": ["United States"], "located in": ["Albemarle County"]}},
    "Q777": {"label": "Crozet", "description": "island group in the Indian Ocean", "aliases": [], "enwiki": "",
             "facts": {"instance of": ["archipelago"], "country": ["France"]}},
    "Q921": {"label": "Rae Sutter", "description": "American politician", "aliases": [], "enwiki": "",
             "facts": {"instance of": ["human"], "occupation": ["politician"]}},
    "Q931": {"label": "Bea Lindqvist", "description": "Swedish glass sculptor", "aliases": [], "enwiki": "",
             "facts": {"instance of": ["human"], "occupation": ["glass artist"], "work location": ["Bristol"]}},
}


def _json_server(handler_factory):
    server = HTTPServer(("127.0.0.1", 0), handler_factory)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"


class FakeGlass:
    """The Glass Database's API: the lookup's rows by status, one item, and the admin route that takes a decision
    or a suggestion with the right X-API-Key."""

    def __init__(self, token="k"):
        self.token, self.posts = token, []
        fake = self

        class Hd(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _send(self, code, body):
                data = json.dumps(body).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self):
                u = urlparse(self.path)
                qs = parse_qs(u.query)
                if u.path == "/wikibase/wikidata":
                    want = [s for s in (qs.get("status", [""])[0]).split(",") if s]
                    rows = [r for r in ROWS if not want or r["status"] in want]
                    return self._send(200, {"items": rows, "total": len(rows), "page": 1, "per": 200})
                if u.path.startswith("/wikibase/items/"):
                    key = u.path[len("/wikibase/items/"):]
                    if key in ITEMS:
                        return self._send(200, ITEMS[key])
                    row = next((r for r in ROWS if r["key"] == key), None)
                    if row:
                        return self._send(200, {"item": {"aliases": [], "claims": [], "url": ""}, "refs": {}})
                    return self._send(404, {"detail": "no such staged item"})
                self._send(404, {"detail": "no"})

            def do_POST(self):
                n = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(n) or b"{}")
                if self.headers.get("X-API-Key") != fake.token:
                    return self._send(401, {"detail": "no"})
                if self.path.startswith("/wikibase/items/"):
                    key = self.path[len("/wikibase/items/"):]
                    fake.posts.append({"key": key, "body": body})
                    return self._send(200, {"key": key, "enrich": body.get("enrich")})
                key = self.path[len("/wikibase/wikidata/"):]
                fake.posts.append({"key": key, "body": body})
                if "suggest" in body:
                    return self._send(200, {"key": key, "status": "unsure", "suggestion": body["suggest"]})
                return self._send(200, {"key": key, "status": "confirmed" if body.get("qid") else "rejected", "qid": body.get("qid", "")})

        self.server, self.url = _json_server(Hd)

    def close(self):
        self.server.shutdown()


class FakeJudge:
    """An Ollama whose /api/chat reads the prompt and answers like a careful judge: the candidate whose block says
    glass, else none; a model named ``gemma3:1b`` is always unsure (the panel's doubter)."""

    def __init__(self, tags=("qwen3:1.7b", "gemma3:1b")):
        self.tags, self.requests = list(tags), []
        fake = self

        class Hd(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _send(self, code, body):
                data = json.dumps(body).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self):
                if self.path == "/api/version":
                    return self._send(200, {"version": "0.40.9"})
                if self.path == "/api/tags":
                    return self._send(200, {"models": [{"name": t, "model": t, "size": 1} for t in fake.tags]})
                if self.path == "/api/ps":
                    return self._send(200, {"models": []})
                self._send(404, {})

            def do_POST(self):
                n = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(n) or b"{}")
                fake.requests.append(body)
                content = body["messages"][-1]["content"]
                if "CANDIDATE SITES" in content:                       # the enrich step's question
                    if "Pike Example" in content:
                        reply = {"website": "https://pikeexampleglass.com/", "instagram": "pikeexample", "city": "Crozet", "region": "Virginia",
                                 "country": "United States", "confidence": {"website": 0.9, "instagram": 0.9, "city": 0.8}, "because": "the site and the account name Crozet"}
                    elif "Bea Lindqvist" in content:
                        reply = {"website": "https://bealindqvist.example/", "instagram": "@bea.glass", "city": "Bristol", "region": "", "country": "",
                                 "confidence": {"website": 0.9, "instagram": 0.9, "city": 0.9}, "because": "her site names Bristol"}
                    else:                                              # an answer the hits do not bear out
                        reply = {"website": "https://evil.example.com/", "instagram": "rae_fake", "city": "Crozet", "region": "", "country": "",
                                 "confidence": {"website": 0.9, "instagram": 0.9, "city": 0.9}, "because": "made up"}
                elif body.get("model") == "gemma3:1b":
                    reply = {"verdict": "unsure", "confidence": 0.3, "because": "nothing ties them together"}
                else:
                    blocks = re.split(r"\n(?=CANDIDATE Q\d+)", content)
                    glassy = [re.match(r"CANDIDATE (Q\d+)", b).group(1) for b in blocks
                              if b.startswith("CANDIDATE") and "glass" in b.lower() and "novelist" not in b.lower()]
                    placey = [re.match(r"CANDIDATE (Q\d+)", b).group(1) for b in blocks
                              if b.startswith("CANDIDATE") and "Virginia" in b]
                    pick = glassy or placey
                    reply = ({"verdict": pick[0], "confidence": 0.92, "because": "the candidate's description and work agree with the record"}
                             if pick else {"verdict": "none", "confidence": 0.88, "because": "no candidate is in the glass field"})
                self._send(200, {"message": {"role": "assistant", "content": json.dumps(reply)}, "prompt_eval_count": 500,
                                 "eval_count": 40, "total_duration": 2_000_000_000, "eval_duration": 1_000_000_000})

        self.server, self.url = _json_server(Hd)

    def close(self):
        self.server.shutdown()


@pytest.fixture()
def glass():
    g = FakeGlass()
    yield g
    g.close()


@pytest.fixture()
def judge_server():
    j = FakeJudge()
    yield j
    j.close()


@pytest.fixture()
def wired(con, glass, judge_server, monkeypatch, tmp_path):
    """Everything pointed at the fakes: the Glass Database, one Ollama with no pool, no web search, canned Wikidata."""
    monkeypatch.setattr(config, "GLASSDB_URL", glass.url)
    monkeypatch.setattr(config, "GLASSDB_ADMIN_TOKEN", "k")
    monkeypatch.setattr(config, "OLLAMA_URL", judge_server.url)
    monkeypatch.setattr(config, "LLM_NODES", "")
    monkeypatch.setattr(config, "OVERLAY", "none")
    monkeypatch.setattr(config, "LLM_ONLY", "")
    monkeypatch.setattr(config, "SEARXNG_URL", "")
    monkeypatch.setattr(config, "RESOLVE_THRESHOLD", 0.8)
    monkeypatch.setattr(config, "RESOLVE_MODELS", ["qwen3:1.7b"])
    monkeypatch.setattr(config, "JOB_RUNNER", False)        # the app's runner thread starts once per process
    monkeypatch.setattr(E, "entity_facts", lambda ids, log=None: {q: dict(WD[q]) for q in ids if q in WD})
    monkeypatch.setattr(E, "wikipedia_summary", lambda title: f"{title} is an article." if title else "")
    monkeypatch.setattr(RB, "DOCS", tmp_path / "resolvebench.json")
    return con


# ------------------------------------------------------------------------------------------------ the queue
def test_queue_rows_facts_and_gold(glass):
    src = GlassDatabase(base=glass.url, token="")
    cases = src.cases(("unsure",))
    assert [c.key for c in cases] == ["gdb:artists:1", "gdb:artists:2"]
    assert [c.key for c in src.cases(("none",), with_facts=False)] == ["gdb:artists:3", "gdb:artists:5"]
    theo = cases[0]
    assert theo.description == "glass artist, Norfolk, Virginia" and theo.aliases == ["T. Park"]
    assert theo.facts == {"work location": ["Norfolk"], "technique": ["Offhand Blown Glass"], "Instagram username": ["theo.glass"]}
    assert theo.url.startswith("https://glassdatabase.test/") and theo.gold() is None and theo.candidate_ids() == ["Q901", "Q902"]
    gold = {c.key: (c.gold(), c.human()) for c in src.cases(RB.GOLD_STATUSES, with_facts=False)}
    assert gold == {"gdb:place:crozet-virginia": ("Q1141856", False), "gdb:artists:3": ("none", False), "gdb:artists:4": ("Q931", True),
                    "gdb:artists:5": ("none", False)}
    kinds = src.cases(("unsure",), kinds=["place"], with_facts=False)
    assert kinds == []
    # the cache of an earlier fetch is reused when label and candidates are unchanged
    again = src.cases(("unsure",), known={c.key: c for c in cases})
    assert again[0].facts == theo.facts
    back = Case.from_row(theo.to_row() | {"aliases": json.dumps(theo.aliases), "facts": json.dumps(theo.facts),
                                          "candidates": json.dumps(theo.candidates)})
    assert back.label == theo.label and back.facts == theo.facts and back.candidates == theo.candidates
    with pytest.raises(PermissionError):
        src.decide("gdb:artists:1", "Q901")
    assert GlassDatabase(base=glass.url, token="k").decide("gdb:artists:1", "Q901")["status"] == "confirmed"
    with pytest.raises(PermissionError):
        GlassDatabase(base=glass.url, token="wrong").suggest("gdb:artists:1", {"qid": "Q901"})


# ------------------------------------------------------------------------------------------------ the judge
def test_prompt_parse_and_sanity():
    case = Case("gdb:artists:2", "person", "Nadia Okonkwo", "glass artist, Portland, Oregon", [],
                {"work location": ["Portland"], "Instagram username": ["nadia.glass"]}, ROWS[1]["candidates"])
    ev = {"candidates": {q: dict(WD[q], wikipedia="") for q in ("Q911", "Q912")}, "search": {'"Nadia Okonkwo" glass': [
        {"title": "Nadia Okonkwo Glass", "url": "https://nadia.example", "snippet": "hot shop in Portland"}]}, "searched": True}
    msgs = J.prompt(case, ev)
    assert msgs[0]["role"] == "system" and "RECORD (Glass Database, kind: person)" in msgs[1]["content"]
    assert "CANDIDATE Q911: Nadia Okonkwo" in msgs[1]["content"] and "WEB SEARCH" in msgs[1]["content"]
    assert "hot shop in Portland" in msgs[1]["content"] and msgs[1]["content"].rstrip().endswith("}")
    # answers in every shape a model gives them
    v = J.parse('{"verdict": "Q911", "confidence": 0.9, "because": "glass artist in Portland"}', case)
    assert (v.verdict, v.confidence, v.ok) == ("Q911", 0.9, True)
    v = J.parse('<think>hmm</think>\nSure! {"verdict": "none", "confidence": "80", "because": "no"}', case)
    assert (v.verdict, v.confidence, v.ok) == ("none", 0.8, True)
    v = J.parse('{"verdict": "Nadia Okonkwo", "confidence": 1, "because": "same name"}', case)   # a label, not an id
    assert v.verdict == "Q911"
    v = J.parse('{"verdict": "Q999", "confidence": 0.9, "because": "x"}', case)                  # not a candidate
    assert v.verdict == "unsure" and v.ok is False and "not one of the candidates" in v.flags[0]
    v = J.parse("I cannot decide.", case)
    assert v.verdict == "unsure" and v.ok is False and v.confidence == 0.0
    v = J.parse('{"verdict": "unsure", "confidence": 0.95, "because": "could be"}', case)
    assert v.verdict == "unsure" and v.confidence == 0.5                                           # unsure is never confident
    v = J.parse('verdict: Q912, confidence: 0.7, because: "same name"', case)                      # no JSON at all
    assert v.verdict == "Q912" and v.confidence == 0.7
    # sanity: the dead novelist is not the maker with an Instagram account
    v = J.sanity(case, J.Verdict(verdict="Q912", confidence=0.9), ev)
    assert v.confidence <= 0.2 and "died in 1960" in v.flags[0]
    place = Case("gdb:place:x", "place", "Crozet", "Virginia, United States", [], {}, [{"qid": "Q921", "label": "Rae Sutter"}])
    v = J.sanity(place, J.Verdict(verdict="Q921", confidence=0.9), {"candidates": {"Q921": WD["Q921"]}})
    assert v.verdict == "unsure" and "is a person" in v.flags[0]
    person = Case("gdb:artists:9", "person", "Crozet", "", [], {}, [{"qid": "Q777", "label": "Crozet"}])
    v = J.sanity(person, J.Verdict(verdict="Q777", confidence=0.9), {"candidates": {"Q777": WD["Q777"]}})
    assert v.verdict == "unsure" and "the record is a person" in v.flags[0]
    # a small model's reasons name one candidate and its verdict another (Kiki Smith): no verdict, a flag
    kiki = Case("gdb:museum_artists:1", "person", "Kiki Smith", "glass artist held in museum collections", [],
                {"collection": ["Corning Museum of Glass"]},
                [{"qid": "Q447300", "label": "Kiki Smith"}, {"qid": "Q119565041", "label": "KiKi Smith"}])
    kev = {"candidates": {"Q447300": {"label": "Kiki Smith", "facts": {"instance of": ["human"], "occupation": ["sculptor", "painter"]}},
                          "Q119565041": {"label": "KiKi Smith", "facts": {"instance of": ["human"], "occupation": ["basketball player"]}}}}
    v = J.sanity(kiki, J.Verdict(verdict="Q119565041", confidence=0.95, because="Candidate Q447300 is the German-born artist whose work the museum holds."), kev)
    assert v.verdict == "unsure" and v.confidence <= 0.3 and "the reasons name Q447300" in v.flags[0]
    # a candidate Wikidata records only as an athlete is not the maker, whatever the model said
    v = J.sanity(kiki, J.Verdict(verdict="Q119565041", confidence=0.95, because="same name"), kev)
    assert v.verdict == "unsure" and "only as basketball player" in v.flags[0]
    # a sculptor is how Wikidata often records a glass artist: no downgrade (Te Rongo Kirkwood)
    v = J.sanity(kiki, J.Verdict(verdict="Q447300", confidence=0.9, because="the artist whose work Corning holds"), kev)
    assert v.verdict == "Q447300" and v.confidence == 0.9 and v.flags == []
    # the record's facts are shown in words a reader takes rightly: a collection is a museum holding the work
    assert "work held in the collection of: Corning Museum of Glass" in J.record_text(kiki)
    assert "the candidate your reasons point at" in J.SYSTEM and "work held in the collection of" in J.SYSTEM
    assert RB.arm_name("qwen3:8b", True) == "judge@qwen3:8b+search" and RB.arm_name("x", False, "schema") == "judge@x+schema"
    assert re.fullmatch(r"1-[0-9a-f]{12}", RB.version())


# ------------------------------------------------------------------------------------------------ the bench
def test_bench_rows_summary_and_docs(wired, judge_server):
    con = wired
    lines = []
    cases = RB.fetch_cases(con, RB.GOLD_STATUSES, log=lines.append)
    assert {c.key for c in cases} == {"gdb:place:crozet-virginia", "gdb:artists:3", "gdb:artists:4", "gdb:artists:5"}   # known rows are not gold
    out = RB.run_bench(con, ["qwen3:1.7b"], cases + [Case("gdb:colour:red", "colour", "red", status="known", qid="Q3142")], log=lines.append)
    arm = out["arms"]["judge@qwen3:1.7b"]
    assert out["cases"] == 3                                   # red has no candidates: not a question
    assert arm["cases"] == 3 and arm["accuracy"] == 1.0 and arm["decided"] == 1.0 and arm["precision_decided"] == 1.0
    assert arm["human_cases"] == 1 and arm["human_accuracy"] == 1.0 and arm["by_kind"]["place"]["accuracy"] == 1.0
    rows = db.rows(con, "SELECT case_id, arm, metrics FROM resolve_bench")
    assert len(rows) == 3 and all(r["arm"] == "judge@qwen3:1.7b" for r in rows)
    m = json.loads(next(r for r in rows if r["case_id"] == "gdb:artists:3")["metrics"])
    assert m["verdict"] == "none" and m["gold"] == "none" and m["correct"] and m["gold_source"] == "rule" and m["searched"] is False
    assert m["version"] == RB.version() and m["model"] == "qwen3:1.7b" and m["prompt_tokens"] == 500
    docs = json.loads(RB.DOCS.read_text(encoding="utf-8"))
    assert docs["cases"] == 3 and docs["summary"]["judge@qwen3:1.7b"]["accuracy"] == 1.0 and docs["version"] == RB.version()
    assert len(RB.stored(con)) == 3
    # the evidence was read once per candidate and is in the cache; the judge saw the Wikipedia lead
    assert db.scalar(con, "SELECT count(*) FROM resolve_evidence WHERE kind='wd'") == 4
    assert any("Crozet, Virginia is an article." in r["messages"][-1]["content"] for r in judge_server.requests)
    # the doubter arm: unsure everywhere is accuracy 0, decided 0, precision undefined
    out2 = RB.run_bench(con, ["gemma3:1b"], cases, log=lines.append)
    g = out2["arms"]["judge@gemma3:1b"]
    assert g["accuracy"] == 0.0 and g["decided"] == 0.0 and g["precision_decided"] is None and g["unsure"] == 1.0
    assert len(RB.stored(con)) == 6 and any("precision there" in ln for ln in lines)
    # the panel as an arm, from the stored rows: with the doubter in it nothing is settled; two agreeing copies settle all
    s = RB.summarize(RB.stored(con))
    p = s["panel(judge@gemma3:1b+judge@qwen3:1.7b)"]
    assert p["cases"] == 3 and p["decided"] == 0.0 and p["accuracy"] == 0.0 and p["precision_decided"] is None
    twin = [dict(r, arm="judge@twin") for r in RB.stored(con) if r["arm"] == "judge@qwen3:1.7b"]
    s = RB.summarize([r for r in RB.stored(con) if r["arm"] == "judge@qwen3:1.7b"] + twin)
    p = s["panel(judge@qwen3:1.7b+judge@twin)"]
    assert p["decided"] == 1.0 and p["precision_decided"] == 1.0 and p["accuracy"] == 1.0
    assert RB.panel_rows(twin) == []                                   # one arm is no panel
    # a changed gold makes the stored row stale
    con.execute("UPDATE resolve_cases SET gold_qid='Q777' WHERE key='gdb:place:crozet-virginia'")
    con.commit()
    assert len(RB.stored(con)) == 4


# ------------------------------------------------------------------------------------------------ the live run
def test_live_consensus_suggestions_and_apply(wired, glass, judge_server):
    con = wired
    lines = []
    # one model: Nadia settles (the glass artist), Theo is none (sculptor and hockey player are not glass)
    out = RB.run_live(con, ["qwen3:1.7b"], log=lines.append)
    assert out["cases"] == 2 and out["settled"] == 2 and out["open"] == 0 and out["suggested"] == 2 and out["applied"] == 0
    rows = {r["key"]: r for r in RB.queue_rows(con)}
    assert rows["gdb:artists:2"]["verdict"] == "Q911" and rows["gdb:artists:2"]["settled"] == 1
    assert rows["gdb:artists:1"]["verdict"] == "none" and rows["gdb:artists:1"]["settled"] == 1
    sug = [p for p in glass.posts if "suggest" in p["body"]]
    assert len(sug) == 2 and not [p for p in glass.posts if "qid" in p["body"]]
    s = next(p["body"]["suggest"] for p in sug if p["key"] == "gdb:artists:2")
    assert s["qid"] == "Q911" and s["settled"] is True and s["models"]["qwen3:1.7b"]["verdict"] == "Q911" and s["confidence"] >= 0.8
    # a panel with the doubter: nothing settles, the suggestion is the best guess
    glass.posts.clear()
    out = RB.run_live(con, ["qwen3:1.7b", "gemma3:1b"], log=lines.append)
    assert out["settled"] == 0 and out["open"] == 2
    rows = {r["key"]: r for r in RB.queue_rows(con, "open")}
    assert rows["gdb:artists:2"]["verdict"] == "Q911" and rows["gdb:artists:2"]["settled"] == 0
    assert set(rows["gdb:artists:2"]["verdicts"]) == {"qwen3:1.7b", "gemma3:1b"}
    assert all(p["body"]["suggest"]["settled"] is False for p in glass.posts)
    # apply: only settled cases at or above apply_above, through the decide route (none at 0.88 stays below 0.9)
    glass.posts.clear()
    out = RB.run_live(con, ["qwen3:1.7b"], apply=True, apply_above=0.9, log=lines.append)
    decided = [p for p in glass.posts if "qid" in p["body"]]
    assert out["applied"] == 1 and {p["key"]: p["body"]["qid"] for p in decided} == {"gdb:artists:2": "Q911"}
    out = RB.run_live(con, ["qwen3:1.7b"], apply=True, apply_above=0.85, log=lines.append)   # reuses the verdicts, applies the one left
    decided = [p for p in glass.posts if "qid" in p["body"]]
    assert out["applied"] == 1 and out["reused"] == 2
    assert {p["key"]: p["body"]["qid"] for p in decided} == {"gdb:artists:2": "Q911", "gdb:artists:1": ""}
    assert len(RB.queue_rows(con, "applied")) == 2 and all(r["applied_at"] for r in RB.queue_rows(con, "applied"))
    # the consensus rules on their own
    V = J.Verdict
    assert RB.consensus([V("Q1", 0.9, model="a"), V("Q1", 0.85, model="b")], 0.8)["settled"] is True
    assert RB.consensus([V("Q1", 0.9, model="a"), V("Q1", 0.7, model="b")], 0.8)["settled"] is False
    tie = RB.consensus([V("Q1", 0.9, model="a"), V("Q2", 0.9, model="b")], 0.8)
    assert tie["verdict"] == "unsure" and "disagree" in tie["because"]
    maj = RB.consensus([V("Q1", 0.9, model="a"), V("Q1", 0.6, model="b"), V("none", 0.9, model="c")], 0.8)
    assert maj["verdict"] == "Q1" and maj["settled"] is False
    assert RB.consensus([V("unsure", 0.0, model="a")], 0.8)["verdict"] == "unsure"


def test_live_without_a_token_only_reports(wired, glass, monkeypatch):
    monkeypatch.setattr(config, "GLASSDB_ADMIN_TOKEN", "")
    out = RB.run_live(wired, ["qwen3:1.7b"], apply=True, log=lambda *_: None)
    assert out["settled"] == 2 and out["suggested"] == 0 and out["applied"] == 0 and glass.posts == []


def test_live_and_bench_resume_without_asking_again(wired, glass, judge_server, monkeypatch):
    """A run that died, or one started without a token: the next run reuses what this code and panel already
    decided, asks the models only about what is new, and writes the suggestions it could not write before."""
    con = wired
    monkeypatch.setattr(config, "GLASSDB_ADMIN_TOKEN", "")
    out = RB.run_live(con, ["qwen3:1.7b"], log=lambda *_: None)
    n_calls = len(judge_server.requests)
    assert out["cases"] == 2 and out["suggested"] == 0 and n_calls >= 2
    monkeypatch.setattr(config, "GLASSDB_ADMIN_TOKEN", "k")                 # the token arrives later
    lines = []
    out = RB.run_live(con, ["qwen3:1.7b"], log=lines.append)
    assert out["reused"] == 2 and out["suggested"] == 2 and len(judge_server.requests) == n_calls
    assert any("reused" in ln for ln in lines) and {p["key"] for p in glass.posts} == {"gdb:artists:1", "gdb:artists:2"}
    out = RB.run_live(con, ["qwen3:1.7b"], log=lambda *_: None)             # nothing new: nothing written twice
    assert out["reused"] == 2 and out["suggested"] == 0 and len(glass.posts) == 2
    out = RB.run_live(con, ["qwen3:1.7b", "gemma3:1b"], log=lambda *_: None)   # another panel is another question
    assert out["reused"] == 0 and len(judge_server.requests) > n_calls
    n_calls = len(judge_server.requests)
    out = RB.run_live(con, ["qwen3:1.7b", "gemma3:1b"], force=True, log=lambda *_: None)
    assert out["reused"] == 0 and len(judge_server.requests) > n_calls
    # the bench keeps the rows this code already stored and judges only the rest
    cases = RB.fetch_cases(con, RB.GOLD_STATUSES, log=lambda *_: None)
    RB.run_bench(con, ["qwen3:1.7b"], cases[:2], log=lambda *_: None)
    n_calls = len(judge_server.requests)
    lines = []
    out = RB.run_bench(con, ["qwen3:1.7b"], cases, log=lines.append)
    judged_before = sum(1 for c in cases[:2] if c.gold() is not None and c.candidates)
    assert len(judge_server.requests) == n_calls + (out["cases"] - judged_before)
    assert out["arms"]["judge@qwen3:1.7b"]["cases"] == out["cases"] and any("already judged" in ln for ln in lines)
    out = RB.run_bench(con, ["qwen3:1.7b"], cases, force=True, log=lambda *_: None)
    assert len(judge_server.requests) == n_calls + (out["cases"] - judged_before) + out["cases"]


def test_wikidata_throttled_still_judges_from_the_lookups_descriptions(wired, monkeypatch):
    """A 429 from Wikidata (a throttled address) is not the end of the run: the candidates keep the label,
    description and classes the lookup saw, the case is judged, the row says so, and nothing is cached."""
    con = wired

    def refuse(ids, log=None):
        raise RuntimeError("no answer from https://www.wikidata.org/w/api.php (429 from www.wikidata.org)")
    monkeypatch.setattr(E, "entity_facts", refuse)
    case = Case("gdb:artists:2", "person", "Nadia Okonkwo", "glass artist, Portland, Oregon", [], {}, ROWS[1]["candidates"])
    lines = []
    ev = E.gather(con, case, use_search=False, log=lines.append)
    assert ev["partial"] is True and ev["candidates"]["Q911"]["description"] == "Nigerian glass artist"
    assert ev["candidates"]["Q911"]["facts"] == {"instance of": ["human"]} and any("not read" in ln for ln in lines)
    assert db.scalar(con, "SELECT count(*) FROM resolve_evidence WHERE kind='wd'") == 0
    text = J.prompt(case, ev)[1]["content"]
    assert "CANDIDATE Q911: Nadia Okonkwo" in text and "Nigerian glass artist" in text
    out = RB.run_live(con, ["qwen3:1.7b"], log=lines.append)
    assert out["settled"] >= 1 and any("could not be read" in ln for ln in lines)
    # the pacing and cooldown: a host that keeps answering 429 is left alone instead of stalling every case
    import lexflow.resolve.evidence as EV

    class R:
        status_code, headers, text = 429, {"Retry-After": "0"}, "slow down"

        def json(self):
            return {}

        def raise_for_status(self):
            pass

    class S:
        def get(self, *a, **k):
            return R()
    monkeypatch.setattr(EV, "session", lambda: S())
    monkeypatch.setattr(EV.time, "sleep", lambda s: None)
    EV._cool.clear()
    with pytest.raises(RuntimeError):
        EV._get("https://www.wikidata.org/w/api.php", action="wbgetentities")
    assert EV._cool.get("www.wikidata.org", 0) > 0
    with pytest.raises(RuntimeError, match="left alone"):
        EV._get("https://www.wikidata.org/w/api.php", action="wbgetentities")
    EV._cool.clear()


# ------------------------------------------------------------------------------------------------ enrichment
def test_enrich_sifting_and_verification():
    from lexflow.resolve import enrich as EN
    pike = Case("gdb:artists:5", "person", "Pike Example", "glass artist, Crozet, Virginia", [], {"work location": ["Crozet"]})
    hits = HITS["pike example"]
    webs = EN.website_candidates(pike, hits)
    assert [w["host"] for w in webs] == ["pikeexampleglass.com"] and webs[0]["url"] == "https://pikeexampleglass.com/" and webs[0]["score"] >= 4
    igs = EN.instagram_candidates(pike, hits)
    assert igs[0]["handle"] == "pikeexample" and "https://www.instagram.com/pikeexample/" in igs[0]["evidence"] and len(igs) == 1
    assert EN.queries_for(pike) == ['"Pike Example" glass artist', '"Pike Example" Crozet glass', '"Pike Example" glass instagram']
    assert EN.queries_for(pike, {"city"}) == ['"Pike Example" glass artist', '"Pike Example" glass instagram']
    assert EN.site_of("https://user.wixsite.com/mysite/about") == "https://user.wixsite.com/mysite/"
    assert EN.host("https://www.Example.com:443/x") == "example.com"
    # the model's answer is kept only where the hits bear it out
    answer = EN.parse(json.dumps({"website": "https://pikeexampleglass.com/about", "instagram": "@pikeexample", "city": "Crozet",
                                  "region": "Virginia", "country": "France", "confidence": {"website": 90, "instagram": 0.8, "city": 0.7},
                                  "because": "the site says so"}))
    kept = EN.verify(pike, answer, hits, webs, igs)
    assert kept["website"]["value"] == "https://pikeexampleglass.com/" and kept["website"]["confidence"] == 0.9
    assert kept["instagram"]["value"] == "pikeexample" and kept["city"]["value"] == "Crozet" and kept["city"]["region"] == "Virginia"
    assert "country" not in kept["city"] and kept["city"]["evidence"]           # France is in no hit
    bogus = EN.parse(json.dumps({"website": "https://evil.example.com/", "instagram": "someone_else", "city": "Atlantis",
                                 "confidence": {"website": 1, "instagram": 1, "city": 1}, "because": "x"}))
    assert EN.verify(pike, bogus, hits, webs, igs) == {}
    det = EN.deterministic(pike, webs, igs)
    assert det["website"] == "https://pikeexampleglass.com/" and det["instagram"] == "pikeexample" and det["city"] == ""
    rae = Case("gdb:artists:3", "person", "Rae Sutter", "glass artist, Crozet, Virginia", [], {})
    assert EN.deterministic(rae, EN.website_candidates(rae, HITS["rae sutter"]), [])["website"] == ""   # her name, not her site
    assert EN.parse("no json here")["ok"] is False
    assert re.fullmatch(r"1-[0-9a-f]{12}", EN.version())
    # the campaign site is a candidate (the name is in the host); it is the model's or the glass rule's to refuse
    webs = EN.website_candidates(rae, HITS["rae sutter"])
    assert webs and webs[0]["host"] == "raesutter.vote"


def test_enrich_live_check_and_api(wired, glass, judge_server, monkeypatch):
    from fastapi.testclient import TestClient
    from lexflow.api.app import app
    from lexflow.pipeline import jobs
    from lexflow.pipeline.steps import get_step
    from lexflow.resolve import enrich as EN
    con = wired
    assert get_step("enrich").params[:2] == ["models", "node"] and "enrich" in jobs.EXCLUSIVE
    lines = []
    out = EN.run(con, ["qwen3:1.7b"], log=lines.append)                  # no SEARXNG_URL: nothing to search with
    assert out["cases"] == 0 and out["error"] == "no SEARXNG_URL" and glass.posts == []
    monkeypatch.setattr(config, "SEARXNG_URL", "http://searxng.test:8080")
    monkeypatch.setattr(E, "search", fake_search)
    out = EN.run(con, ["qwen3:1.7b"], log=lines.append)
    # Pike (none; has a place, lacks a site and an account) gets the site and the account, not the town he has;
    # Rae's made-up answer is dropped whole
    assert out["cases"] == 2 and out["proposed"] == {"website": 1, "instagram": 1, "city": 0} and out["suggested"] == 1
    rows = {r["key"]: r for r in EN.rows(con)}
    pike = rows["gdb:artists:5"]
    assert pike["fields"]["website"]["value"] == "https://pikeexampleglass.com/" and pike["fields"]["instagram"]["value"] == "pikeexample"
    assert "city" not in pike["fields"] and pike["suggested_at"] and pike["model"] == "qwen3:1.7b"
    assert rows["gdb:artists:3"]["fields"] == {} and not rows["gdb:artists:3"].get("suggested_at")
    sent = next(p for p in glass.posts if p["key"] == "gdb:artists:5")["body"]["enrich"]
    assert sent["fields"]["website"]["value"] == "https://pikeexampleglass.com/" and sent["searched"] is True and sent["version"] == EN.version()
    # the check: records that have the fields (Bea everything, Theo an account and a town, Pike a town), hidden;
    # the search finds Bea's and Pike's again, and nothing for Theo, whom the web does not know
    glass.posts.clear()
    out = EN.run(con, ["qwen3:1.7b"], check=True, log=lines.append)
    assert out["cases"] == 3 and out["check"]["website"] == {"had": 1, "proposed": 1, "right": 1, "precision": 1.0, "recall": 1.0}
    assert out["check"]["instagram"] == {"had": 2, "proposed": 1, "right": 1, "precision": 1.0, "recall": 0.5}
    assert out["check"]["city"]["had"] == 3 and out["check"]["city"]["right"] == 2 and glass.posts == []
    rows = {r["key"]: r for r in EN.rows(con)}
    bea = rows["gdb:artists:4"]
    assert bea["check"]["website"]["match"] is True and bea["check"]["website"]["actual"] == ["https://www.bealindqvist.example/"]
    assert rows["gdb:artists:1"]["check"]["instagram"] == {"proposed": "", "actual": ["theo.glass"], "match": None}
    summary = EN.check_summary(EN.rows(con))
    assert summary["enrich@qwen3:1.7b"]["cases"] == 3 and summary["enrich@qwen3:1.7b"]["website"]["precision"] == 1.0
    assert summary["enrich@qwen3:1.7b"]["city"]["recall"] == 0.667
    # without a model: the deterministic part only
    out = EN.run(con, [], no_llm=True, log=lines.append)
    pike = {r["key"]: r for r in EN.rows(con)}["gdb:artists:5"]
    assert out["proposed"]["website"] == 1 and out["proposed"]["city"] == 0 and pike["model"] == "" and pike["fields"]["website"]["confidence"] == 0.7
    with TestClient(app) as c:
        j = c.get("/api/resolve/enrich").json()
        assert j["search"] is True and len(j["rows"]) == 4 and j["check"]["enrich@qwen3:1.7b"]["website"]["precision"] == 1.0
    js = (ROOT / "dashboard" / "app.js").read_text(encoding="utf-8")
    assert "/api/resolve/enrich" in js and "Check the search" in js


# ------------------------------------------------------------------------------------------------ API, steps, page
def test_api_and_page(wired, glass, monkeypatch):
    from fastapi.testclient import TestClient
    from lexflow.api.app import app
    from lexflow.pipeline import jobs
    from lexflow.pipeline.steps import get_step
    con = wired
    assert get_step("resolve").run and get_step("resolve-bench").params == ["models", "node", "limit", "status", "kinds", "no_search", "force"]
    assert {"resolve", "resolve-bench"} <= jobs.EXCLUSIVE
    RB.run_live(con, ["qwen3:1.7b"], log=lambda *_: None)
    with TestClient(app) as c:
        o = c.get("/api/resolve").json()
        assert o["configured"]["token"] is True and o["queue"]["settled"] == 2 and o["configured"]["models"] == ["qwen3:1.7b"]
        rows = c.get("/api/resolve/cases", params={"state": "settled"}).json()["rows"]
        assert len(rows) == 2 and rows[0]["evidence"] and all("verdicts" in r for r in rows)
        nadia = next(r for r in rows if r["key"] == "gdb:artists:2")
        assert nadia["evidence"]["Q911"]["description"] == "Nigerian glass artist" and nadia["url"] == ""
        assert c.get("/api/resolve/cases", params={"state": "bogus"}).status_code == 400
        assert c.post("/api/resolve/cases/gdb:nobody:1", json={"qid": "Q1"}).status_code == 404
        assert c.post("/api/resolve/cases/gdb:artists:2", json={"qid": "nope"}).status_code == 400
        glass.posts.clear()
        r = c.post("/api/resolve/cases/gdb:artists:2", json={"qid": "q911"})
        assert r.status_code == 200 and r.json()["qid"] == "Q911" and glass.posts[-1]["body"] == {"qid": "Q911"}
        assert c.get("/api/resolve/cases", params={"state": "applied"}).json()["rows"][0]["applied_qid"] == "Q911"
        b = c.get("/api/resolve/bench").json()
        assert b["version"] == RB.version() and b["rows"] == []
        monkeypatch.setattr(config, "GLASSDB_ADMIN_TOKEN", "")
        assert c.post("/api/resolve/cases/gdb:artists:1", json={"qid": ""}).status_code == 409
    page = (ROOT / "dashboard" / "index.html").read_text(encoding="utf-8")
    js = (ROOT / "dashboard" / "app.js").read_text(encoding="utf-8")
    assert '#/resolve' in page and "function viewResolve" in js and "resolve: viewResolve" in js
    for must in ("/api/resolve/cases", "/api/resolve", "Judge the open queue", "Benchmark the models", "Precision when decided",
                 "Apply ${c.qid}", "Not on Wikidata"):
        assert must in js, must
    env = (ROOT / ".env.example").read_text(encoding="utf-8")
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "GLASSDB_ADMIN_TOKEN" in env and "LEXFLOW_RESOLVE_MODELS" in env and "GLASSDB_ADMIN_TOKEN" in compose
    assert (ROOT / "docs" / "resolve.md").exists()
