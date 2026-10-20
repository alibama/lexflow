"""lexflow.compute: the node list and allow-list, health checks with back-off, the dispatcher (slots, drain, pin,
failover, the calls log), the Ollama client's hook, the relabel migration, the overlay adapters, the API and the
Compute page's static shape.  Ollama is a stub on a random localhost port; nothing touches a real server."""
from __future__ import annotations

import json
import shutil
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from lexflow import config
from lexflow.compute import health as H
from lexflow.compute import migrate as MG
from lexflow.compute import nodes as N
from lexflow.compute import overlay as O
from lexflow.compute import pool as P
from lexflow.extract.ollama import OllamaClient
from lexflow.store import db

ROOT = Path(__file__).resolve().parents[1]


class FakeOllama:
    """GET /api/version, /api/tags, /api/ps; POST /api/chat (echoes a reply with token counts) and /api/embed."""

    def __init__(self, tags=("qwen3:1.7b", "nomic-embed-text:latest"), version="0.40.9", fail=0, slow=0.0):
        self.tags, self.version, self.fail, self.slow = list(tags), version, fail, slow
        self.requests: list[dict] = []
        self.loaded: list[str] = []
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
                    return self._send(200, {"version": fake.version})
                if self.path == "/api/tags":
                    return self._send(200, {"models": [{"name": t, "model": t, "size": 1_400_000_000, "digest": "abc123def456789",
                                                        "details": {"parameter_size": "2.0B", "quantization_level": "Q4_K_M"}} for t in fake.tags]})
                if self.path == "/api/ps":
                    return self._send(200, {"models": [{"name": t, "size": 1, "context_length": 4096} for t in fake.loaded]})
                self._send(404, {"error": "no"})

            def do_POST(self):
                n = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(n) or b"{}")
                fake.requests.append({"path": self.path, "body": body})
                if fake.fail > 0:
                    fake.fail -= 1
                    return self._send(503, {"error": "busy"})
                if fake.slow:
                    import time
                    time.sleep(fake.slow)
                if self.path == "/api/chat":
                    if body.get("model") not in fake.tags:
                        return self._send(404, {"error": f"model '{body.get('model')}' not found"})
                    fake.loaded = list(dict.fromkeys(fake.loaded + [body["model"]]))
                    return self._send(200, {"message": {"role": "assistant", "content": json.dumps({"ok": True, "n": len(fake.requests)})},
                                            "prompt_eval_count": 120, "prompt_eval_duration": 2_000_000_000, "eval_count": 12,
                                            "eval_duration": 1_500_000_000, "total_duration": 3_600_000_000, "load_duration": 100_000_000})
                if self.path == "/api/embed":
                    return self._send(200, {"embeddings": [[0.1, 0.2, 0.3] for _ in body.get("input", [])]})
                self._send(404, {"error": "no"})

        self.server = HTTPServer(("127.0.0.1", 0), Hd)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"

    def close(self):
        self.server.shutdown()


@pytest.fixture()
def ollama():
    f = FakeOllama()
    yield f
    f.close()


@pytest.fixture()
def ollama2():
    f = FakeOllama(tags=("qwen3:1.7b", "qwen3:8b", "nomic-embed-text:latest"), version="0.40.4")
    yield f
    f.close()


@pytest.fixture()
def pool_env(con, monkeypatch, ollama, ollama2):
    """A two-node pool over the stubs, in the temp data dir; compute.db is fresh."""
    monkeypatch.setattr(config, "LLM_NODES", f"a={ollama.url}|embed|max=1, b={ollama2.url}|threads=3|max=2")
    monkeypatch.setattr(config, "OLLAMA_URL", ollama.url)
    monkeypatch.setattr(config, "EMBED_URL", "")
    monkeypatch.setattr(config, "LLM_ONLY", "")
    monkeypatch.setattr(config, "OVERLAY", "none")
    monkeypatch.setattr(config, "LLM_WAIT", 3)
    P._synced.clear()
    c = N.connect()
    N.sync_env(c)
    H.check_due(c)
    yield c
    c.close()


# ---------------------------------------------------------------------------------------------- the node list
def test_parse_env_and_the_allow_list(monkeypatch):
    monkeypatch.setattr(config, "OVERLAY_RANGE", "10.231.0.0/16")
    good, bad = N.parse_env("local=http://ollama:11434|embed|max=1, ollama2=http://lexflow-ollama2:11434|threads=4, "
                            "shop=http://100.98.35.19:11434|threads=7|max=1|models=qwen3:8b+nomic-embed-text|status=http://100.98.35.19:9101/status.json, "
                            "mac=http://mac.tail1234.ts.net:11434|part_time, nb=http://10.231.4.2:11434, "
                            "v6=http://[fd7a:115c:a1e0::1]:11434, bad=http://example.com:11434, pub=http://8.8.8.8:11434, "
                            "Bad_Name=http://ollama:11434, odd=http://ollama:11434|what=1, ftp=ftp://ollama:11434")
    assert [n["name"] for n in good] == ["local", "ollama2", "shop", "mac", "nb", "v6"]
    assert good[0]["embed"] == 1 and good[1]["threads"] == 4 and good[2]["max_concurrency"] == 1
    assert good[2]["models_wanted"] == ["qwen3:8b", "nomic-embed-text"] and good[2]["status_url"].endswith("status.json")
    assert good[3]["part_time"] == 1
    assert len(bad) == 5 and any("example.com" in b for b in bad) and any("8.8.8.8" in b for b in bad)
    assert N.url_allowed("http://host.docker.internal:11434") and N.url_allowed("http://localhost:11434")
    assert N.url_allowed("http://100.127.255.254:11434") and not N.url_allowed("http://100.128.0.1:11434")
    assert N.url_allowed("http://x.mesh.lexipedia.xyz:11434") and not N.url_allowed("http://lexipedia.xyz:11434")
    assert not N.url_allowed("http://ollama.example.org:11434") and not N.url_allowed("not a url")


def test_pool_is_off_and_untouched_when_nothing_is_configured(con, monkeypatch):
    monkeypatch.setattr(config, "LLM_NODES", "")
    monkeypatch.setattr(config, "OVERLAY", "none")
    monkeypatch.setattr(config, "EMBED_URL", "")
    assert not N.pool_on() and not P.routes(config.OLLAMA_URL) and P.node_count() == 0
    assert N.names() == [] and N.url_of("shop") is None
    assert N.name_for_url("http://ollama:11434") == "ollama"
    assert not N.db_path().exists()
    from lexflow.pipeline import jobs
    assert jobs.groups() == jobs.GROUPS


def test_sync_env_keeps_edits_and_drops_removed_nodes(pool_env, monkeypatch, ollama):
    c = pool_env
    assert [n["name"] for n in N.load_nodes(c)] == ["a", "b"]
    N.set_edited(c, "b", draining=1, threads=5)
    monkeypatch.setattr(config, "LLM_NODES", f"b={ollama.url}|threads=3|max=2")
    N.sync_env(c)
    rows = N.load_nodes(c)
    assert [n["name"] for n in rows] == ["b"]
    assert rows[0]["draining"] == 1 and rows[0]["threads"] == 5 and rows[0]["url"] == ollama.url
    assert N.names(c) == ["b"] and N.url_of("b", c) == ollama.url
    assert N.embed_node(c) == ("b", ollama.url)


# ------------------------------------------------------------------------------------------------ health
def test_probe_check_and_backoff(pool_env, ollama, monkeypatch):
    c = pool_env
    res = H.probe(ollama.url)
    assert res["ok"] and res["version"] == "0.40.9" and {m["name"] for m in res["models"]} == {"qwen3:1.7b", "nomic-embed-text:latest"}
    a = N.get_node(c, "a")
    assert a["status"] == "online" and a["fails"] == 0 and a["version"] == "0.40.9" and a["checked_at"]
    dead = FakeOllama()
    dead.close()
    dead.server.server_close()
    for i in range(1, 6):
        H.record(c, "a", H.probe(dead.url, timeout=0.5))
        n = N.get_node(c, "a")
        assert n["fails"] == i and n["backoff_until"] and n["status"] == ("offline" if i >= H.OFFLINE_AFTER else "backoff")
    assert not H.due(n)                                    # waits until backoff_until
    assert H.check(c, "a")["status"] == "online"           # one good check restores it
    assert N.get_node(c, "a")["fails"] == 0
    assert 30 * 0.8 <= H.backoff_seconds(1) <= 30 * 1.2 and H.backoff_seconds(20) <= 900 * 1.2


# ------------------------------------------------------------------------------------------- the dispatcher
def test_dispatcher_picks_a_node_with_the_model_and_a_free_slot(pool_env, ollama, ollama2):
    c = pool_env
    r, node = P.call("/api/chat", {"model": "qwen3:8b", "messages": [], "options": {"num_ctx": 4096}}, model="qwen3:8b", timeout=5)
    assert r.ok and node == "b" and ollama2.requests[-1]["body"]["options"]["num_thread"] == 3     # threads from the node
    with pytest.raises(P.NoNode):
        P.call("/api/chat", {"model": "qwen3:30b", "messages": []}, model="qwen3:30b", timeout=5)
    # least busy first: a lease on b sends the next qwen3:1.7b call to a; b's second slot still takes one
    lease = P.claim_slot(c, N.get_node(c, "b"), "qwen3:1.7b", "chat")
    assert lease
    r, node = P.call("/api/chat", {"model": "qwen3:1.7b", "messages": []}, model="qwen3:1.7b", timeout=5)
    assert node == "a"
    lease2 = P.claim_slot(c, N.get_node(c, "a"), "qwen3:1.7b", "chat")
    assert lease2
    assert P.claim_slot(c, N.get_node(c, "a"), "qwen3:1.7b", "chat") is None      # max_concurrency 1
    r, node = P.call("/api/chat", {"model": "qwen3:1.7b", "messages": []}, model="qwen3:1.7b", timeout=5)
    assert node == "b"                                                           # b has a second slot
    assert P.free_slots(c) == 1 and P.busy_counts(c) == {"a": 1, "b": 1}
    P.release(c, lease)
    P.release(c, lease2)
    assert P.free_slots(c) == 3 and P.node_count(c) == 2
    # the pin, and a pinned model the node lacks
    r, node = P.call("/api/chat", {"model": "qwen3:1.7b", "messages": []}, model="qwen3:1.7b", timeout=5, pin="b")
    assert node == "b"
    with pytest.raises(P.NoNode):
        P.call("/api/chat", {"model": "qwen3:8b", "messages": []}, model="qwen3:8b", timeout=5, pin="a")
    rows = db.rows(c, "SELECT node, model, kind, ok, prompt_tokens, out_tokens, out_s, wait_s FROM calls ORDER BY id")
    assert len(rows) == 4 and all(r["ok"] for r in rows) and rows[0]["prompt_tokens"] == 120 and rows[0]["out_tokens"] == 12
    assert rows[0]["out_s"] == 1.5 and P.speed(c, "b", "qwen3:8b")["gen_tps"] == 8.0


def test_draining_and_disabled_nodes_take_no_new_work(pool_env, monkeypatch):
    c = pool_env
    N.set_edited(c, "b", draining=1)
    with pytest.raises(P.NoFreeSlot) as e:
        P.call("/api/chat", {"model": "qwen3:8b", "messages": []}, model="qwen3:8b", timeout=5, wait=0)
    assert "b: draining" in str(e.value)
    N.set_edited(c, "b", draining=0, enabled=0)
    with pytest.raises(P.NoFreeSlot) as e:
        P.call("/api/chat", {"model": "qwen3:8b", "messages": []}, model="qwen3:8b", timeout=5, wait=0)
    assert "b: disabled" in str(e.value)
    N.set_edited(c, "b", enabled=1)
    assert P.call("/api/chat", {"model": "qwen3:8b", "messages": []}, model="qwen3:8b", timeout=5)[1] == "b"


def test_failover_moves_the_call_and_backs_the_node_off(pool_env, ollama, ollama2, monkeypatch):
    c = pool_env
    dead = FakeOllama(tags=("qwen3:1.7b",))
    dead.close()
    dead.server.server_close()
    monkeypatch.setattr(config, "LLM_NODES", f"a={ollama.url}|embed, b={ollama2.url}|max=2, z={dead.url}|priority=90")
    N.sync_env(c)
    H.check_due(c)
    # z looks online (a stale check), then refuses the connection: the call moves on, z backs off
    con2 = N.connect()
    con2.execute("UPDATE nodes SET status='online', fails=0, checked_at=?, models=? WHERE name='z'",
                 (N.now(), json.dumps([{"name": "qwen3:1.7b"}])))
    con2.commit()
    con2.close()
    r, node = P.call("/api/chat", {"model": "qwen3:1.7b", "messages": []}, model="qwen3:1.7b", timeout=5)
    assert r.ok and node in ("a", "b")
    z = N.get_node(c, "z")
    assert z["status"] == "backoff" and z["fails"] == 1 and z["backoff_until"] and "Connection" in (z["last_error"] or "")
    calls = db.rows(c, "SELECT node, ok, attempt, error FROM calls ORDER BY id")
    assert [x["ok"] for x in calls] == [0, 1] and calls[0]["node"] == "z" and calls[1]["attempt"] == 2
    # a 5xx moves the call too; the stale /api/tags of a node that 404s drops the model until the next check
    ollama2.fail = 1
    with pytest.raises(P.NoNodeLeft):                  # only b has qwen3:8b: its 5xx leaves no other node
        P.call("/api/chat", {"model": "qwen3:8b", "messages": []}, model="qwen3:8b", timeout=5, wait=0)
    assert N.get_node(c, "b")["status"] == "backoff"
    with pytest.raises(P.NoFreeSlot) as e:             # and while it backs off, nothing takes the model
        P.call("/api/chat", {"model": "qwen3:8b", "messages": []}, model="qwen3:8b", timeout=5, wait=0)
    assert "b: backoff" in str(e.value)


def test_calls_table_is_rolling_and_capped(pool_env, monkeypatch):
    c = pool_env
    monkeypatch.setattr(config, "LLM_CALLS_MAX", 5)
    for i in range(8):
        P.record_call(c, "a", "qwen3:1.7b", "chat", data={"eval_count": i}, ok=True)
    c.execute("UPDATE calls SET at='2020-01-01T00:00:00Z' WHERE id=8")
    c.commit()
    P.prune_calls(c)
    rows = db.rows(c, "SELECT id FROM calls ORDER BY id")
    assert [r["id"] for r in rows] == [3, 4, 5, 6, 7]
    P.reap_leases(c)


def test_stale_leases_are_reaped(pool_env):
    c = pool_env
    c.execute("INSERT INTO leases(node, model, kind, runner, pid, started_at, beat_at) VALUES ('a','m','chat',?,999999,'2020-01-01T00:00:00Z','2020-01-01T00:00:00Z')",
              (P._runner(),))
    c.execute("INSERT INTO leases(node, model, kind, runner, pid, started_at, beat_at) VALUES ('a','m','chat','elsewhere',1,?,?)", (N.now(), N.now()))
    c.commit()
    assert P.reap_leases(c) == 1 and db.scalar(c, "SELECT count(*) FROM leases") == 1


# ------------------------------------------------------------------------------------- the client's hook
def test_ollama_client_goes_through_the_pool_and_records_the_node(pool_env, ollama, ollama2):
    client = OllamaClient(base_url=config.OLLAMA_URL, model="qwen3:8b", num_ctx=4096, timeout=5)
    out = client.chat([{"role": "user", "content": "hi"}], schema={"type": "object"})
    assert json.loads(out)["ok"] and client.log[-1]["node"] == "b" and client.log[-1]["prompt_eval_count"] == 120
    assert client.nodes_used() == {"b": 1}
    pinned = OllamaClient(base_url=ollama2.url, model="qwen3:1.7b", timeout=5, node="b")
    pinned.chat([{"role": "user", "content": "hi"}])
    assert pinned.nodes_used() == {"b": 1}
    with pytest.raises(P.NoNode):
        OllamaClient(base_url=config.OLLAMA_URL, model="qwen3:8b", timeout=5, node="a").chat([])
    # an embed call lands on the embed node (a), whatever the base URL
    assert client.embed(["x"], model="nomic-embed-text") == [[0.1, 0.2, 0.3]]
    assert db.rows(pool_env, "SELECT node, kind FROM calls WHERE kind='embed'") == [{"node": "a", "kind": "embed"}]


def test_ollama_client_is_direct_with_no_pool(con, monkeypatch, ollama):
    monkeypatch.setattr(config, "LLM_NODES", "")
    monkeypatch.setattr(config, "OVERLAY", "none")
    monkeypatch.setattr(config, "EMBED_URL", "")
    client = OllamaClient(base_url=ollama.url, model="qwen3:1.7b", timeout=5)
    client.chat([{"role": "user", "content": "hi"}])
    assert client.log[-1]["node"] == "127.0.0.1" and ollama.requests[-1]["path"] == "/api/chat"
    assert not N.db_path().exists()                     # nothing configured: compute.db is never created


def test_embedder_pins_to_the_embed_node(pool_env, ollama, ollama2, monkeypatch):
    from lexflow.extract.selector import Embedder
    e = Embedder(model="nomic-embed-text")
    assert e.node == "a" and e.base_url == ollama.url
    m = e(["a clause", "another"])
    assert m.shape == (2, 3) and ollama.requests[-1]["path"] == "/api/embed" and not any(r["path"] == "/api/embed" for r in ollama2.requests)
    monkeypatch.setattr(config, "EMBED_URL", ollama2.url)
    assert Embedder(model="nomic-embed-text").node == "b"


# ------------------------------------------------------------------------------------------- the migration
def test_relabel_is_idempotent_and_keeps_the_version(con, tmp_path):
    m = {"case": "q1.va", "arm": "local+llm", "version": "2-1bbcb0aed8c9", "composite": 0.5}
    rows = [("q1.va", "local+llm", {**m}), ("q1.va", "local+llmplan", {**m, "arm": "local+llmplan"}),
            ("q1.va", "local", {**m, "arm": "local"}), ("q2.dc", "oracle+llm", {**m, "arm": "oracle+llm"}),
            ("q1.va", "local+llm@qwen3:8b", {**m, "arm": "local+llm@qwen3:8b", "model": "qwen3:8b"})]
    for case, arm, met in rows:
        con.execute("INSERT INTO ask_bench(case_id, arm, metrics, ref_hash, created_at) VALUES (?,?,?,?,?)", (case, arm, json.dumps(met), "h", db.now()))
    con.execute('INSERT INTO benchmarks("case", strategy, model, created_at) VALUES (?,?,?,?)', ("va.records", "oneshot", "qwen3:1.7b", db.now()))
    con.execute('INSERT INTO benchmarks("case", strategy, model, created_at) VALUES (?,?,?,?)', ("va.records", "rules", "-", db.now()))
    con.commit()
    docs = tmp_path / "askbench.json"
    docs.write_text(json.dumps({"version": "2-1bbcb0aed8c9", "summary": {"local+llm": {"cases": 1}, "local": {"cases": 1}},
                                "rows": [{"case": "q1.va", "arm": "local+llm", "version": "2-1bbcb0aed8c9"}]}), encoding="utf-8")
    out = MG.relabel(con, "qwen3:1.7b", "ollama", docs_path=docs)
    assert out["ask_bench"] == 3 and out["skipped"] == 0 and out["benchmarks"] == 1 and out["docs"] == 1
    arms = sorted(r["arm"] for r in db.rows(con, "SELECT arm FROM ask_bench"))
    assert arms == ["local", "local+llm@qwen3:1.7b", "local+llm@qwen3:8b", "local+llmplan@qwen3:1.7b", "oracle+llm@qwen3:1.7b"]
    met = json.loads(db.one(con, "SELECT metrics FROM ask_bench WHERE arm='local+llm@qwen3:1.7b'")["metrics"])
    assert met["version"] == "2-1bbcb0aed8c9" and met["model"] == "qwen3:1.7b" and met["node"] == "ollama" and met["arm"] == "local+llm@qwen3:1.7b"
    assert db.one(con, "SELECT node FROM benchmarks WHERE model='qwen3:1.7b'")["node"] == "ollama"
    assert db.one(con, "SELECT node FROM benchmarks WHERE model='-'")["node"] is None
    again = MG.relabel(con, "qwen3:1.7b", "ollama", docs_path=docs)
    assert again["ask_bench"] == 0 and again["benchmarks"] == 0 and again["docs"] == 0
    d = json.loads(docs.read_text(encoding="utf-8"))
    assert d["version"] == "2-1bbcb0aed8c9" and set(d["summary"]) == {"local+llm@qwen3:1.7b", "local"} and d["rows"][0]["arm"] == "local+llm@qwen3:1.7b"
    assert MG.relabel(con, "qwen3:1.7b", "ollama", docs_path=docs, dry=True)["dry"]
    bak = MG.backup(config.DB_PATH, tmp_path / "backup")
    import sqlite3
    b = sqlite3.connect(str(bak))
    assert b.execute("SELECT count(*) FROM ask_bench").fetchone()[0] == 5 and b.execute("SELECT count(*) FROM benchmarks").fetchone()[0] == 2
    b.close()
    assert "node" in db.columns(con, "benchmarks")


def test_askbench_arm_names_carry_the_model():
    from lexflow.ask.bench import arm_name
    assert arm_name("local", "loqo", None, None, None) == "local"
    assert arm_name("local", "missing", None, None, "qwen3:1.7b") == "local-unlearned"
    assert arm_name("local", "loqo", object(), None, "qwen3:1.7b") == "local+llmplan@qwen3:1.7b"
    assert arm_name("oracle", "none", object(), object(), "qwen3:8b") == "oracle+llm@qwen3:8b"
    assert MG.relabel_arm("local+llm", "qwen3:1.7b") == "local+llm@qwen3:1.7b" and MG.relabel_arm("local", "x") == "local"


# -------------------------------------------------------------------------------------------- the overlay
class FakePeers:
    """A NetBird-shaped GET /api/peers (and a Headscale GET /api/v1/node) that checks the token."""

    def __init__(self, peers, token="tok", headscale=None):
        self.peers, self.token, self.headscale = peers, token, headscale or []
        self.calls = []
        fake = self

        class Hd(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                fake.calls.append((self.path, self.headers.get("Authorization")))
                if self.path == "/api/peers" and self.headers.get("Authorization") == f"Token {fake.token}":
                    data = json.dumps(fake.peers).encode()
                elif self.path == "/api/v1/node" and self.headers.get("Authorization") == f"Bearer {fake.token}":
                    data = json.dumps({"nodes": fake.headscale}).encode()
                else:
                    data = b'{"message":"unauthorized"}'
                    self.send_response(401)
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        self.server = HTTPServer(("127.0.0.1", 0), Hd)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"

    def close(self):
        self.server.shutdown()


PEERS = [
    {"id": "1", "dns_label": "shop.mesh.lexipedia.xyz", "ip": "10.231.4.2", "connected": True, "last_seen": "2026-10-19T10:00:00Z",
     "groups": [{"id": "g1", "name": "compute"}], "user_id": "ops@example.org", "os": "Ubuntu 26.04"},
    {"id": "2", "dns_label": "mac", "ip": "10.231.4.3", "connected": False, "last_seen": "2026-10-18T14:16:00Z",
     "groups": [{"id": "g1", "name": "compute"}], "user_id": "ops@example.org", "os": "macOS"},
    {"id": "3", "dns_label": "wordpress", "ip": "10.231.4.4", "connected": True, "groups": [{"id": "g2", "name": "members"}]},
    {"id": "4", "dns_label": "Not_Valid", "ip": "10.231.4.5", "connected": True, "groups": [{"id": "g1", "name": "compute"}]},
    {"id": "5", "dns_label": "faraway", "ip": "192.168.1.9", "connected": True, "groups": [{"id": "g1", "name": "compute"}]},
]


def test_netbird_overlay_upserts_compute_peers(con, monkeypatch):
    srv = FakePeers(PEERS)
    try:
        monkeypatch.setattr(config, "LLM_NODES", "")
        monkeypatch.setattr(config, "OVERLAY", "netbird")
        monkeypatch.setattr(config, "OVERLAY_URL", srv.url)
        monkeypatch.setattr(config, "OVERLAY_TOKEN", "tok")
        monkeypatch.setattr(config, "OVERLAY_COMPUTE_GROUP", "compute")
        monkeypatch.setattr(config, "OVERLAY_RANGE", "10.231.0.0/16")
        assert N.pool_on()
        peers = O.NetBirdOverlay().list_nodes()
        assert [p.name for p in peers] == ["shop", "mac", "not_valid", "faraway"]
        c = N.connect()
        log = []
        out = O.sync(c, log=log.append)
        assert out == {"kept": 2, "skipped": 2, "gone": 0} and len(log) == 2
        rows = {n["name"]: n for n in N.load_nodes(c)}
        assert set(rows) == {"shop", "mac"}
        assert rows["shop"]["url"] == "http://10.231.4.2:11434" and rows["shop"]["status_url"] == "http://10.231.4.2:9101/status.json"
        assert rows["shop"]["source"] == "overlay" and rows["shop"]["overlay"]["connected"] is True
        assert rows["mac"]["status"] == "offline" and rows["mac"]["overlay"]["last_seen"].startswith("2026-10-18")
        assert H.check(c, "mac")["status"] == "offline"             # disconnected: no request is made
        assert N.names(c) == ["mac", "shop"]
        # a drained node stays drained across a re-read; a peer that leaves the group goes
        N.set_edited(c, "shop", draining=1)
        srv.peers = [p for p in PEERS if p["dns_label"] != "mac"]
        out = O.sync(c)
        assert out["gone"] == 1 and {n["name"] for n in N.load_nodes(c)} == {"shop"}
        assert N.get_node(c, "shop")["draining"] == 1
        # with a lease, the leaving peer is only marked gone until its call finishes
        c.execute("INSERT INTO leases(node, model, kind, runner, pid, started_at, beat_at) VALUES ('shop','m','chat','r',1,?,?)", (N.now(), N.now()))
        c.commit()
        srv.peers = []
        O.sync(c)
        assert N.get_node(c, "shop")["gone"] == 1 and N.names(c) == []
        c.execute("DELETE FROM leases")
        c.commit()
        O.sync(c)
        assert N.load_nodes(c) == []
        # a bad token is logged, not raised
        monkeypatch.setattr(config, "OVERLAY_TOKEN", "wrong")
        assert "error" in O.sync(c, log=log.append)
        c.close()
    finally:
        srv.close()


def test_headscale_adapter_maps_tags_the_same_way(con, monkeypatch):
    srv = FakePeers([], headscale=[
        {"id": "1", "name": "shop", "givenName": "shop", "ipAddresses": ["10.231.4.2", "fd7a:115c:a1e0::2"], "online": True,
         "lastSeen": "2026-10-19T10:00:00Z", "validTags": ["tag:compute"], "user": {"name": "ops"}},
        {"id": "2", "name": "wp", "givenName": "wp", "ipAddresses": ["10.231.4.9"], "online": True, "validTags": ["tag:web"]}])
    try:
        monkeypatch.setattr(config, "OVERLAY", "headscale")
        monkeypatch.setattr(config, "OVERLAY_URL", srv.url)
        monkeypatch.setattr(config, "OVERLAY_TOKEN", "tok")
        monkeypatch.setattr(config, "OVERLAY_COMPUTE_GROUP", "tag:compute")
        monkeypatch.setattr(config, "LLM_NODES", "")
        nodes = O.adapter().list_nodes()
        assert len(nodes) == 1 and nodes[0].name == "shop" and nodes[0].ip == "10.231.4.2" and nodes[0].online
        assert srv.calls[-1] == ("/api/v1/node", "Bearer tok")
        assert O.adapter("none") is None
    finally:
        srv.close()


# ------------------------------------------------------------------------------------------------ the API
@pytest.fixture()
def client(pool_env):
    from fastapi.testclient import TestClient
    from lexflow.api.app import app
    return TestClient(app)


def test_compute_endpoints(client, pool_env, con, ollama2):
    d = client.get("/api/compute").json()
    assert d["pool"] and d["embed_node"] == "a" and d["totals"]["nodes"] == 2 and d["totals"]["online"] == 2 and d["totals"]["slots"] == 3
    b = next(n for n in d["nodes"] if n["name"] == "b")
    assert b["version"] == "0.40.4" and {m["name"] for m in b["models"]} >= {"qwen3:8b"} and b["threads"] == 3 and b["busy"] == 0
    assert all("qwen3:8b" != p["model"] for p in b["pullable"]) and any(p["model"] == "qwen3:14b" for p in b["pullable"])
    assert client.get("/api/compute/nodes/zzz").status_code == 404
    assert client.post("/api/compute/nodes/b/drain").json()["draining"] is True
    assert client.get("/api/compute/nodes/b").json()["draining"] is True
    assert client.post("/api/compute/nodes/b/resume").json()["draining"] is False
    assert client.put("/api/compute/nodes/b", json={"max_concurrency": 9}).status_code == 400
    assert client.put("/api/compute/nodes/b", json={"max_concurrency": 1, "threads": 2}).json()["max_concurrency"] == 1
    assert client.post("/api/compute/nodes/b/check").json()["status"] == "online"
    assert client.post("/api/compute/check").json()["checked"] == ["a", "b"]
    # pulls: a bad name, a node that is not online, then a queued models job
    assert client.post("/api/compute/nodes/b/pull", json={"model": "../x"}).status_code == 400
    pool_env.execute("UPDATE nodes SET status='offline' WHERE name='a'")
    pool_env.commit()
    assert client.post("/api/compute/nodes/a/pull", json={"model": "qwen3:8b"}).status_code == 409
    pool_env.execute("UPDATE nodes SET host=? WHERE name='b'", (json.dumps({"ram_total_gb": 8.0}),))
    pool_env.commit()
    r = client.post("/api/compute/nodes/b/pull", json={"model": "qwen3:14b"})
    assert r.status_code == 409 and "confirm" in r.json()["detail"]
    r = client.post("/api/compute/nodes/b/pull", json={"model": "qwen3:14b", "confirm": True}).json()
    assert r["gb"] == 9.3 and "9.3 GB" in r["message"] and r["job_id"]
    job = db.one(con, "SELECT step, args FROM jobs WHERE id=?", r["job_id"])
    assert job["step"] == "models" and json.loads(job["args"]) == {"node": "b", "models": "qwen3:14b"}
    # calls, filterable
    P.call("/api/chat", {"model": "qwen3:8b", "messages": []}, model="qwen3:8b", timeout=5)
    rows = client.get("/api/compute/calls?node=b&model=qwen3:8b").json()
    assert len(rows) == 1 and rows[0]["gen_tps"] == 8.0 and rows[0]["prefill_tps"] == 60.0 and rows[0]["ok"]
    assert client.get("/api/compute/calls?node=a").json() == []
    assert client.get("/api/compute").json()["totals"]["calls_1h"] == 1
    # a job pinned to an unknown node is refused; a known one is queued
    assert client.post("/api/jobs", json={"step": "coverage", "args": {"states": "va", "node": "nope"}}).status_code == 400
    assert client.post("/api/jobs", json={"step": "coverage", "args": {"states": "va", "node": "b"}}).status_code == 200
    s = client.get("/api/setup").json()["services"]["ollama"]
    assert s["pool"]["nodes"] == 2 and "qwen3:8b" in s["models"]


def test_compute_page_with_no_pool_shows_the_one_ollama(con, monkeypatch, ollama):
    from fastapi.testclient import TestClient
    from lexflow.api.app import app
    monkeypatch.setattr(config, "LLM_NODES", "")
    monkeypatch.setattr(config, "OVERLAY", "none")
    monkeypatch.setattr(config, "EMBED_URL", "")
    monkeypatch.setattr(config, "OLLAMA_URL", ollama.url)
    d = TestClient(app).get("/api/compute").json()
    assert d["pool"] is False and d["totals"] == {"nodes": 1, "online": 1, "slots": 1, "busy": 0, "calls_1h": 0}
    assert d["nodes"][0]["name"] == "127.0.0.1" and d["nodes"][0]["version"] == "0.40.9" and d["note"]
    assert TestClient(app).post("/api/compute/nodes/x/drain").status_code == 409
    assert not N.db_path().exists()


# ------------------------------------------------------------------------------------------ jobs and steps
def test_jobs_env_pins_and_the_heavy_rule_relaxes_with_a_pool(pool_env, monkeypatch):
    from lexflow.pipeline import jobs
    assert jobs.job_env(7, "coverage", '{"states": "va", "node": "b"}') == {"LEXFLOW_JOB_ID": "7", "LEXFLOW_JOB_STEP": "coverage", "LEXFLOW_LLM_ONLY": "b"}
    assert "LEXFLOW_LLM_ONLY" not in jobs.job_env(8, "ask", {"question": "x"})
    assert jobs.groups() == (jobs.PULLS, jobs.INDEXING)            # two nodes: only pulls stay exclusive
    assert not jobs._clash("build", "coverage") and jobs._clash("index", "ask") and jobs._clash("models", "models")
    monkeypatch.setattr(config, "LLM_ONLY", "b")
    from lexflow.extract import benchmark as BM
    assert BM.workers_for(["qwen3:1.7b"]) == 1                      # pinned: sequential
    monkeypatch.setattr(config, "LLM_ONLY", "")
    assert BM.workers_for(["qwen3:1.7b"]) == 3 and BM.workers_for(["qwen3:8b"]) == 2 and BM.workers_for(["qwen3:1.7b"], node="a") == 1


def test_steps_take_a_node(pool_env, ollama2):
    from lexflow.pipeline import steps as ST
    from lexflow.ask import coverage as CV
    from lexflow.ask import pipeline as AP
    assert "node" in ST.COMPOSITE["ask"].params and "node" in ST.COMPOSITE["benchmark"].params
    assert CV.node_of("b") == ("b", ollama2.url)
    with pytest.raises(ValueError):
        CV.node_of("nope")
    asker = AP.asker_for("qwen3:8b", "b")
    assert asker and asker.client.node == "b"
    assert AP.asker_for("qwen3:30b", "b") is None
    with pytest.raises(ValueError):
        AP.asker_for("qwen3:8b", "nope")
    a2 = CV.asker_at(ollama2.url, "qwen3:8b")
    assert a2 and a2.client.node == "b"
    assert ST.ollama_state()["pool"]["online"] == 2
    from lexflow.municipal.build import ollama_models
    assert "qwen3:8b" in ollama_models()


# ----------------------------------------------------------------------------------------- the dashboard
def test_dashboard_has_the_compute_page_and_never_calls_a_node():
    js = (ROOT / "dashboard" / "app.js").read_text(encoding="utf-8")
    html = (ROOT / "dashboard" / "index.html").read_text(encoding="utf-8")
    assert '<a href="#/compute">Compute</a>' in html
    assert "compute: viewCompute" in js and "async function viewCompute" in js and '"#/compute"' in js
    for s in ("/api/compute", "/api/compute/calls", 'act("check")', 'act("drain")', 'act("resume")', "/pull", "/api/compute/check"):
        assert s in js
    assert "api/peers" not in js and "11434" not in js and "OVERLAY" not in js     # the browser never calls a node or the overlay
    assert "Pull a model" in js and "Check all now" in js
    node = shutil.which("node")
    if node:
        subprocess.run([node, "--check", str(ROOT / "dashboard" / "app.js")], check=True)
