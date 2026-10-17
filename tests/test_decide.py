"""lexflow.extract.decide: the /v1/systemone client, its chat fallback, the cache, and one bench data loader."""
from __future__ import annotations

import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from lexflow.extract import decide as D  # noqa: E402

QUESTIONS = {
    "team": {"type": "choice", "question": "Which team handles this?",
             "criteria": {"billing": "Payments and refunds", "technical": "Bugs and outages", "other": "Anything else"}},
    "refund": {"type": "noul", "question": "Does the customer ask for a refund?"},
    "urgency": {"type": "score", "question": "How urgent is it?", "criteria": ["Routine", "Soon", "Urgent"]},
}
ANSWERS = {
    "team": {"type": "choice", "choice": "billing", "probabilities": {"billing": 0.91, "technical": 0.05, "other": 0.04},
             "confidence": 0.86},
    "refund": {"type": "noul", "noul": 0.997},
    "urgency": {"type": "score", "score": 0.815, "legend": {"0": "Routine", "1": "Soon", "2": "Urgent"},
                "probabilities": {"0": 0.02, "1": 0.33, "2": 0.65}, "confidence": 0.7},
}


class FakeOllama:
    """A fake Ollama: POST /v1/systemone answers ANSWERS, GET /api/tags lists ``tags``; records every request."""

    def __init__(self, tags: list[str], fail_first: int = 0):
        self.tags = tags
        self.fail_first = fail_first
        self.requests: list[dict] = []
        fake = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):          # quiet
                pass

            def _send(self, code: int, body: dict | str):
                data = (json.dumps(body) if isinstance(body, dict) else body).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self):
                if self.path == "/api/tags":
                    return self._send(200, {"models": [{"name": t, "model": t} for t in fake.tags]})
                self._send(404, {"error": "no"})

            def do_POST(self):
                n = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(n) or b"{}")
                fake.requests.append({"path": self.path, "body": body})
                if self.path != "/v1/systemone":
                    return self._send(404, {"error": "no"})
                if fake.fail_first > 0:
                    fake.fail_first -= 1
                    return self._send(503, {"error": "busy"})
                if not D.is_decision_model(body.get("model", "")):
                    return self._send(400, {"error": f"model {body.get('model')!r} is not a decision model"})
                answers = {k: v for k, v in ANSWERS.items() if k in body.get("questions", {})}
                self._send(200, {"model": body["model"], "answers": answers,
                                 "usage": {"input_tokens": 841, "output_tokens": 4}})

        self.server = HTTPServer(("127.0.0.1", 0), H)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"

    def close(self):
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture()
def fake():
    f = FakeOllama(tags=["qwen3:1.7b", "nomic-embed-text:latest", "tev1:0.8b"])
    yield f
    f.close()


# --------------------------------------------------------------------------- request shape
def test_request_body_shape():
    body = D.request_body("tev1:0.8b", "I was charged twice.", QUESTIONS)
    assert body["model"] == "tev1:0.8b"
    assert body["state"] == "I was charged twice."                  # one text, as the server takes it
    qs = body["questions"]
    assert qs["team"] == {"type": "choice", "instructions": "Which team handles this?",
                          "criteria": {"billing": "Payments and refunds", "technical": "Bugs and outages",
                                       "other": "Anything else"}}
    assert qs["refund"] == {"type": "noul", "instructions": "Does the customer ask for a refund?"}
    assert qs["urgency"] == {"type": "score", "instructions": "How urgent is it?",
                             "criteria": ["Routine", "Soon", "Urgent"]}
    # a list of options becomes a map; 'instructions' is accepted as well as 'question'; dict states pass through
    body2 = D.request_body("nimble", {"ticket": "x", "n": 3},
                           {"k": {"type": "choice", "instructions": "Kind?", "criteria": ["a", "b"]}})
    assert body2["state"] == "ticket: x\nn: 3"                       # named fields become lines
    assert body2["questions"]["k"]["criteria"] == {"a": "a", "b": "b"}
    with pytest.raises(ValueError):
        D.normalise_questions({"k": {"type": "choice", "question": "?", "criteria": ["only"]}})
    with pytest.raises(ValueError):
        D.normalise_questions({"k": {"type": "ranking", "question": "?"}})
    with pytest.raises(ValueError):
        D.normalise_questions({})


# --------------------------------------------------------------------------- the endpoint
def test_decide_against_fake_server(fake):
    out = D.decide("I was charged twice. Please refund the extra payment.", QUESTIONS, "tev1:0.8b", base_url=fake.url)
    sent = fake.requests[-1]
    assert sent["path"] == "/v1/systemone"
    assert sent["body"]["model"] == "tev1:0.8b" and set(sent["body"]["questions"]) == {"team", "refund", "urgency"}
    assert sent["body"]["state"] == "I was charged twice. Please refund the extra payment."
    assert isinstance(sent["body"]["questions"]["team"]["criteria"], dict)     # the server rejects a list
    a = out["answers"]
    assert a["team"]["choice"] == "billing" and a["team"]["confidence"] == 0.86
    assert a["team"]["probabilities"]["technical"] == 0.05 and a["team"]["type"] == "choice"
    assert a["refund"]["type"] == "noul" and a["refund"]["probability"] == 0.997 and a["refund"]["choice"] is True
    assert a["refund"]["probabilities"]["yes"] == 0.997 and a["refund"]["confidence"] is None
    u = a["urgency"]
    assert u["type"] == "score" and u["score"] == 0.815 and u["legend"]["2"] == "Urgent"
    assert u["choice"] == "Urgent" and u["probabilities"]["2"] == 0.65 and u["confidence"] == 0.7
    assert out["usage"] == {"input_tokens": 841, "output_tokens": 4} and out["model"] == "tev1:0.8b"
    assert out["ms"] >= 0 and out["attempts"] == 1


def test_decide_retries_once_then_fails(fake):
    fake.fail_first = 1
    out = D.decide("x", QUESTIONS, "tev1:0.8b", base_url=fake.url)
    assert out["attempts"] == 2 and out["answers"]["team"]["choice"] == "billing"
    fake.fail_first = 2
    with pytest.raises(D.DecisionError):
        D.decide("x", QUESTIONS, "tev1:0.8b", base_url=fake.url)
    with pytest.raises(D.DecisionError):                 # a 4xx is not retried
        D.decide("x", QUESTIONS, "qwen3:1.7b", base_url=fake.url)
    assert len([r for r in fake.requests if r["body"]["model"] == "qwen3:1.7b"]) == 1
    out = D.decide("x", QUESTIONS, "", base_url=fake.url)                # no model named: the default one
    assert fake.requests[-1]["body"]["model"] == D.DECISION_MODEL == out["model"]


def test_parse_answer_without_choice_or_legend():
    a = D.parse_answer("choice", {"probabilities": {"a": 0.2, "b": 0.8}})
    assert a["choice"] == "b" and a["confidence"] is None
    q = D.normalise_questions({"s": {"type": "score", "question": "?", "criteria": ["low", "mid", "high"]}})["s"]
    s = D.parse_answer("score", {"score": 0.9}, q)
    assert s["legend"] == {"0": "low", "1": "mid", "2": "high"} and s["choice"] == "high"
    with pytest.raises(D.DecisionError):
        D.parse_response({"answers": {"team": ANSWERS["team"]}}, D.normalise_questions(QUESTIONS))


# --------------------------------------------------------------------------- backend
def test_backend_reports_decision_or_chat(fake):
    b = D.backend(fake.url)
    assert b["kind"] == "decision" and b["model"] == "tev1:0.8b" and "qwen3:1.7b" in b["models"]
    fake.tags = ["qwen3:4b", "qwen3:1.7b", "nomic-embed-text:latest"]
    b = D.backend(fake.url, chat_model="qwen3:1.7b")
    assert b["kind"] == "chat" and b["model"] == "qwen3:1.7b"          # not the other qwen3 tag
    assert D.backend(fake.url, chat_model="qwen3")["model"] == "qwen3:4b"   # a bare name: any tag of it
    assert D.find_tag("nomic-embed-text", fake.tags) == "nomic-embed-text:latest"
    assert D.find_tag("qwen3:8b", fake.tags) is None
    fake.tags = ["nomic-embed-text:latest"]
    assert D.backend(fake.url, chat_model="qwen3:1.7b")["kind"] == "none"
    fake.tags = ["nimble:latest", "tev1:4b"]
    assert D.backend(fake.url)["model"] == "tev1:4b"                 # a sized tag before ':latest'
    assert D.backend(fake.url, model="nimble:latest")["model"] == "nimble:latest"
    assert D.backend("http://127.0.0.1:9")["kind"] == "none"         # nothing listening: no tags, no error


# --------------------------------------------------------------------------- the chat fallback
class StubChat:
    model = "qwen3:1.7b"

    def __init__(self, reply: str):
        self.reply = reply
        self.calls: list[dict] = []

    def chat(self, messages, schema=None, temperature=0.0, max_tokens=None):
        self.calls.append({"messages": messages, "schema": schema, "temperature": temperature, "max_tokens": max_tokens})
        return self.reply


def test_fallback_chat_same_shape():
    stub = StubChat(json.dumps({"team": "Billing", "refund": True, "urgency": "Soon"}))
    out = D.fallback_chat("I was charged twice.", QUESTIONS, client=stub)
    call = stub.calls[0]
    assert call["temperature"] == 0.0
    assert call["schema"]["properties"]["team"]["enum"] == ["billing", "technical", "other"]
    assert call["schema"]["properties"]["refund"] == {"type": "boolean"}
    assert call["schema"]["properties"]["urgency"]["enum"] == ["Routine", "Soon", "Urgent"]
    assert call["schema"]["required"] == ["team", "refund", "urgency"]
    user = call["messages"][-1]["content"]
    assert "I was charged twice." in user and "billing: Payments and refunds" in user and "Routine, Soon, Urgent" in user
    a = out["answers"]
    assert a["team"]["choice"] == "billing" and a["team"]["confidence"] is None       # case-folded to the option
    assert a["team"]["probabilities"] == {"billing": 1.0, "technical": 0.0, "other": 0.0}
    assert a["refund"]["choice"] is True and a["refund"]["probability"] == 1.0 and a["refund"]["confidence"] is None
    assert a["urgency"]["choice"] == "Soon" and a["urgency"]["score"] == 0.5 and a["urgency"]["confidence"] is None
    assert out["fallback"] is True and out["model"] == "qwen3:1.7b"
    # an unparseable reply gives None choices rather than an exception
    out2 = D.fallback_chat("x", QUESTIONS, client=StubChat("not json"))
    assert out2["answers"]["team"]["choice"] is None and out2["answers"]["refund"]["choice"] is None


# --------------------------------------------------------------------------- cache + Decider
def test_decider_cache(tmp_path):
    calls = []

    def answer(state, questions):
        calls.append(state)
        return {"model": "stub", "answers": {"k": D.parse_answer("choice", {"choice": "a", "probabilities": {"a": 1}})},
                "usage": {}, "ms": 1.0}

    q = {"k": {"type": "choice", "question": "?", "criteria": ["a", "b"]}}
    d = D.Decider(cache_dir=tmp_path, backend_info={"kind": "decision", "model": "stub", "models": []}, answer=answer)
    r1 = d.decide("state one", q)
    r2 = d.decide("state one", q)
    assert r1["answers"]["k"]["choice"] == "a" and "cached" not in r1 and r2["cached"] is True
    assert calls == ["state one"] and d.stats["calls"] == 1 and d.stats["hits"] == 1
    d.decide("state two", q)
    d.decide("state one", {"k": {"type": "choice", "question": "different?", "criteria": ["a", "b"]}})
    assert len(calls) == 3                            # a new state or new questions: a new key
    assert (tmp_path / "decisions.sqlite").exists() and len(d.cache) == 3
    # a second Decider on the same directory reads the first one's entries
    d2 = D.Decider(cache_dir=tmp_path, backend_info={"kind": "decision", "model": "stub", "models": []}, answer=answer)
    assert d2.decide("state two", q)["cached"] is True and len(calls) == 3
    # the key: model, state hash, questions hash
    k = D.cache_key("tev1:0.8b", "state one", q)
    assert k.startswith("tev1:0.8b|") and len(k.split("|")) == 3
    assert D.cache_key("tev1:0.8b", "state one", q) == k and D.cache_key("nimble", "state one", q) != k


def test_decider_uses_server_and_decide_many(fake, tmp_path):
    d = D.Decider(base_url=fake.url, cache_dir=tmp_path)
    assert d.backend["kind"] == "decision" and d.model == "tev1:0.8b" and not d.is_fallback
    outs = D.decide_many(["one", "two", "one"], QUESTIONS, concurrency=2, decider=d)
    assert [o["answers"]["team"]["choice"] for o in outs] == ["billing"] * 3
    assert d.stats["calls"] == 2 and d.stats["hits"] == 1
    assert len([r for r in fake.requests if r["path"] == "/v1/systemone"]) == 2


# --------------------------------------------------------------------------- step kinds and the switch
def _stub(choice: str, confidence):
    def answer(state, questions):
        return {"model": "stub", "answers": {"kind": D.parse_answer("choice", {"choice": choice, "probabilities": {choice: 1.0},
                                                                         "confidence": confidence})}, "usage": {}, "ms": 1.0}
    return answer


def test_step_kind_uses_the_model_only_when_sure():
    from lexflow.publish import schema as SC
    # the criteria are the vocabulary's own words for the facts schema's nine kinds
    assert D.STEP_KINDS == {v.slug: v.description for v in SC.VOCAB["step-kind"] if v.slug in D.STEP_KINDS}
    assert set(D.STEP_KINDS) == {"act", "notice", "filing", "hearing", "decision", "payment", "inspection", "record", "review"}
    assert D.step_kind_state("Respond  in writing", "shall respond") == {"Step": "Respond in writing", "Law": "shall respond"}
    info = {"kind": "decision", "model": "stub", "models": []}
    sure = D.Decider(cache=False, backend_info=info, answer=_stub("notice", 0.91))
    assert D.step_kind(sure, "Respond in writing", "shall respond", "decision") == ("notice", "decision", 0.91)
    unsure = D.Decider(cache=False, backend_info=info, answer=_stub("notice", 0.5))
    assert D.step_kind(unsure, "Respond in writing", "shall respond", "decision") == ("decision", "rule", 0.5)
    none = D.Decider(cache=False, backend_info=info, answer=_stub("notice", None))      # the chat fallback's shape
    assert D.step_kind(none, "Respond", "x", "act") == ("act", "rule", None)
    odd = D.Decider(cache=False, backend_info=info, answer=_stub("delivery", 0.99))     # not one of the nine
    assert D.step_kind(odd, "Respond", "x", "act") == ("act", "rule", 0.99)

    def boom(state, questions):
        raise D.DecisionError("down")
    broken = D.Decider(cache=False, backend_info=info, answer=boom)
    assert D.step_kind(broken, "Respond", "x", "act") == ("act", "rule", None)


def test_shared_decider_follows_the_flag(monkeypatch):
    from lexflow import config
    D.reset()
    monkeypatch.setattr(config, "DECIDE", False)
    assert D.enabled() is False and D.shared() is None
    monkeypatch.setattr(config, "DECIDE", True)
    monkeypatch.setattr(D, "backend", lambda *a, **k: {"kind": "none", "model": None, "models": []})
    assert D.shared(cache=False) is None                   # on, but nothing pulled: the rules alone
    D.reset()
    monkeypatch.setattr(D, "backend", lambda *a, **k: {"kind": "decision", "model": "tev1:0.8b", "models": ["tev1:0.8b"]})
    d = D.shared(cache=False)
    assert d is not None and d.model == "tev1:0.8b" and D.shared() is d
    D.reset()
    assert config.DECIDE_MODEL == D.DECISION_MODEL and config.DECIDE_URL == D.DECIDE_URL


# --------------------------------------------------------------------------- one bench loader
def test_mailbox_loader_and_split():
    import decide_bench as B
    task = B.load_mailbox()
    assert len(task.examples) >= 100 and set(e.label for e in task.examples) == {"office", "personal"}
    for e in task.examples:
        addr = e.meta["address"]
        assert addr.split("@", 1)[1].endswith(("example.gov", "example.org", "example.com", "example.net"))
        assert e.state.startswith("Address: ") and "Office: " in e.state
    assert all(e.label in task.labels for e in task.examples)
    # deterministic split, both labels in both halves
    test, train = task.test, task.train
    assert 15 <= len(test) <= len(task.examples) // 2 and len(train) + len(test) == len(task.examples)
    assert {e.label for e in test} == {"office", "personal"} == {e.label for e in train}
    assert [e.state for e in B.load_mailbox().test] == [e.state for e in test]
    # the rule arm runs and the metrics come back whole
    r = B.run_rule(task, test)
    assert 0.0 <= r["accuracy"] <= 1.0 and r["n"] == len(test) and r["arm"] == "(a) rules"
    assert task.question["answer"]["type"] == "noul"
    m = B.metrics(["a", "a", "b"], ["a", "b", "b"], ["a", "b", "c"])
    assert m["accuracy"] == round(2 / 3, 4) and m["confusions"] == [{"gold": "a", "pred": "b", "count": 1}]
    assert m["macro_f1"] == round((2 / 3 + 2 / 3) / 2, 4)
