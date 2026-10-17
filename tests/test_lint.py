"""The cleanliness gate (lexflow/publish/lint.py): deterministic checks on hand-made items, the Ollama pass with a
stubbed client, the HELD rule and the report."""
from __future__ import annotations

import json
from datetime import date

from lexflow.publish import lint, schema as SC
from lexflow.publish.graph import Claim, Item, Value

TODAY = date(2026, 10, 15)


def item(key, label, desc="", cls="legal process step", claims=(), exists=False, aliases=()):
    return Item(key, label, desc, list(aliases), cls, list(claims), exists)


def codes(findings):
    return sorted({f["code"] for f in findings})


def test_bare_labels_and_drafting_words():
    keys = set()
    assert codes(lint.check_item(item("lexflow:unit:mn:p13_13c", "unit p13_13c", "Part 13C"), TODAY, keys)) == \
        ["label-bare-key"]
    assert codes(lint.check_item(item("lexflow:role:va:records:x", "records_custodian", "x"), TODAY, keys)) == \
        ["label-bare-key"]
    assert codes(lint.check_item(item("lexflow:agency:va:court_vactapp", "Virginia court vactapp", "Court"), TODAY,
                                 keys)) == ["label-bare-key"]
    assert codes(lint.check_item(item("lexflow:statute:va:2.2-3704", "2.2-3704", "Virginia statute"), TODAY,
                                 keys)) == ["label-bare-key"]
    assert codes(lint.check_item(item("lexflow:step:x:y", "", "x"), TODAY, keys)) == ["label-empty"]
    assert codes(lint.check_item(item("lexflow:form:x:y:f1", "Form 12", "x"), TODAY, keys)) == ["label-bare-key"]
    for label in ("process outcome", "step kind", "unit level", "Form used by applicants"):
        assert not lint.check_item(item("lexflow:class:x", label, "A class."), TODAY, keys), label
    assert not lint.check_item(item("lexflow:statute:va:2.2-3704", "Va. Code Ann. § 2.2-3704",
                                    "Public records to be open to inspection"), TODAY, keys)
    f = lint.check_item(item("lexflow:process:wy.records", "Records (Wyoming)",
                             "Process model by lexflow, unreviewed draft from one extraction."), TODAY, keys)
    assert codes(f) == ["drafting-words"] and "'draft'" in f[0]["detail"]
    for word in ("checked by Claude", "the AI verifier passed", "lexflow index row 7", "discovery file",
                 "User-Agent lexflow", "qwen3 extraction"):
        assert codes(lint.check_item(item("lexflow:step:x:y", "Respond", word), TODAY, keys)) == ["drafting-words"]
    # the schema's own terms are exempt
    assert not lint.check_item(item(SC.vocab_key("determination-method", "ai-verifier"), "AI verifier",
                                    "An AI verifier checked the claim.", SC.class_key("determination-method")),
                               TODAY, {SC.class_key("determination-method")})
    assert not lint.check_item(item(SC.vocab_key("review-status", "draft"), "draft", "One extraction, unreviewed.",
                                    SC.class_key("review-status")), TODAY, {SC.class_key("review-status")})


def test_people_mailboxes_and_lines():
    keys = set()
    for text in ("Attn: Jane Doe, Room 12", "Records request, c/o Jane Doe", "Hon. Jane Doe", "Dr. John Q. Adams",
                 "Jane Doe, FOIA Officer", "Jane Doe, Deputy Records Custodian"):
        f = lint.check_item(item("lexflow:agency:va:x", "Records Office", text), TODAY, keys)
        assert codes(f) == ["person-name"], text
    for text in ("Office of the Deputy Clerk", "Public Records, FOIA Office", "Mayor's Office", "City Council, Clerk",
                 "Judge Advocate General", "Sheriff Civil Division", "Virginia Department of Taxation, Commissioner"):
        assert not lint.check_item(item("lexflow:agency:va:x", "Records Office", text), TODAY, keys), text
    # party names in a case caption are not persons; a titled name in a case description is
    assert not lint.check_item(item("courtlistener:cluster:1", "Smith v. Jones", "Supreme Court of Virginia, 2001",
                                    "court decision"), TODAY, keys)
    f = lint.check_item(item("lexflow:agency:va:x", "Records Office", "write to jane.doe@charlottesville.gov"), TODAY, keys)
    assert codes(f) == ["personal-mailbox"]
    assert not lint.check_item(item("lexflow:agency:va:x", "Records Office", "write to foia@charlottesville.gov"),
                               TODAY, keys)
    f = lint.check_item(item("lexflow:agency:va:x", "Records Office", "call 434-555-0100"), TODAY, keys)
    assert codes(f) == ["direct-line"] and "marked" not in f[0]["detail"]
    f = lint.check_item(item("lexflow:agency:va:x", "Records Office", "cell 434-555-0100"), TODAY, keys)
    assert "marked as a person's line" in f[0]["detail"]
    f = lint.check_item(item("lexflow:agency:va:x", "Records Office", "x",
                             claims=[Claim("email address", Value("url", "mailto:jane.doe@charlottesville.gov"))]),
                        TODAY, keys)
    assert codes(f) == ["personal-mailbox"]


def test_values_limits_times_quotes_and_dangling():
    keys = {"lexflow:statute:va:2.2-3704"}
    it = item("lexflow:step:x:y", "Respond", "x", claims=[
        Claim("quoted text", Value("string", "a" * 401)),
        Claim("checked on", Value("time", "2027-01-01", precision=11)),
        Claim("checked on", Value("time", "2026-10-15", precision=11)),
        Claim("effective until", Value("time", "2027-01-01", precision=11)),      # in force until then: fine
        Claim("part of", Value("item", "lexflow:process:nowhere")),
        Claim("fee", Value("quantity", "5", unit="lexflow:vocab:currency:nope")),
        Claim("references", Value("item", "lexflow:statute:va:2.2-3704"), [], [[
            ("source URL", Value("url", "https://library.municode.com/va/x")),
            ("quoted text", Value("string", "words of the site"))]]),
        Claim("references", Value("item", "lexflow:statute:va:2.2-3704"), [], [[
            ("source URL", Value("url", "https://law.lis.virginia.gov/vacode/2.2-3704/")),
            ("quoted text", Value("string", "words of the law"))]]),
        Claim("deontic modality", Value("item", "Obligation")),
        Claim("official text", Value("url", "https://a.gov/" + "b" * 500)),
    ])
    f = lint.check_item(it, TODAY, keys)
    assert codes(f) == ["dangling-reference", "future-time", "no-reprint-quote", "too-long"]
    assert sum(1 for x in f if x["code"] == "too-long") == 2
    assert sum(1 for x in f if x["code"] == "dangling-reference") == 2
    assert sum(1 for x in f if x["code"] == "future-time") == 1
    assert sum(1 for x in f if x["code"] == "no-reprint-quote") == 1
    long = item("lexflow:step:x:y", "L" * 251, "x")
    assert codes(lint.check_item(long, TODAY, keys)) == ["too-long"]


def test_deterministic_checks_new_and_relabelled_items_and_duplicates():
    items = [
        item("lexflow:step:a:1", "Respond", "Step of A"),
        item("lexflow:step:a:2", "Respond", "Step of A"),
        item("lexflow:step:a:3", "Respond", "Step of B"),
        item("lexflow:statute:va:1", "1", "kept bare", exists=True),            # relabelled: stored label differs
        item("lexflow:statute:va:2", "Va. Code § 2", "fine", exists=True),      # unchanged
        item("lexflow:statute:va:3", "3", "bare but unchanged", exists=True),   # stored label equal: not checked
    ]
    stored = {"lexflow:statute:va:1": "Va. Code § 1", "lexflow:statute:va:2": "Va. Code § 2", "lexflow:statute:va:3": "3"}
    findings, checked = lint.deterministic(items, stored, TODAY)
    assert checked == {"lexflow:step:a:1": "new", "lexflow:step:a:2": "new", "lexflow:step:a:3": "new",
                       "lexflow:statute:va:1": "changed"}
    assert codes(findings["lexflow:step:a:1"]) == ["duplicate-label-description"]
    assert codes(findings["lexflow:step:a:2"]) == ["duplicate-label-description"]
    assert "lexflow:step:a:3" not in findings
    assert codes(findings["lexflow:statute:va:1"]) == ["label-bare-key"]
    assert "lexflow:statute:va:3" not in findings


class StubClient:
    model = "qwen3:1.7b"

    def __init__(self, verdicts=None, fail=False):
        self.calls = []
        self.verdicts = verdicts or {}
        self.fail = fail

    def chat(self, messages, schema=None, temperature=0.0, max_tokens=None):
        self.calls.append({"messages": messages, "schema": schema})
        if self.fail:
            raise ConnectionError("ollama down")
        rows = []
        for n, line in enumerate(messages[1]["content"].split("\n")[1:], 1):
            if not line[:1].isdigit():
                continue
            v = {"n": n, "readable": True, "person": False, "jargon": False, "suggested_label": ""}
            for label, verdict in self.verdicts.items():
                if repr(label) in line:
                    v.update(verdict)
            rows.append(v)
        return json.dumps({"items": rows})


def test_ollama_pass_batches_parses_and_only_person_holds(con, tmp_path):
    items = [item(f"lexflow:step:a:{i}", f"Step {i} of the process", "Step of A") for i in range(60)]
    items += [item("lexflow:agency:va:bad", "Virginia court xyz", "Court"),                # deterministic hold
              item("lexflow:agency:va:p", "Records Office", "Ask the clerk"),              # ollama: person
              item("lexflow:agency:va:j", "RO-7 node", "x"),                               # ollama: jargon, unreadable
              item("lexflow:statute:va:1", "Va. Code § 1", "fine", exists=True)]
    client = StubClient({"Records Office": {"person": True},
                         "RO-7 node": {"readable": False, "jargon": True, "suggested_label": "Records Office node 7"}})
    report = lint.run(con, items=items, client=client, sample=1.0, cap=150, out_dir=tmp_path, today=TODAY,
                      log=lambda *a: None)
    assert len(client.calls) == 3 and client.calls[0]["schema"] == lint.SCHEMA
    assert client.calls[0]["messages"][0]["content"] == lint.SYSTEM
    assert "1. label: 'Virginia court xyz'" in client.calls[0]["messages"][1]["content"]   # touched items first
    held = {h["key"]: h["reasons"] for h in report["held"]}
    assert set(held) == {"lexflow:agency:va:bad", "lexflow:agency:va:p"}
    assert held["lexflow:agency:va:p"] == ["ollama: person"]
    assert held["lexflow:agency:va:bad"][0].startswith("label-bare-key")
    assert report["suggested_labels"] == [{"key": "lexflow:agency:va:j", "label": "RO-7 node",
                                           "suggested_label": "Records Office node 7"}]
    o = report["ollama"]
    assert o["model"] == "qwen3:1.7b" and o["prompt_hash"] == lint.PROMPT_HASH and len(o["calls"]) == 3
    assert o["items_sent"] == 63 and o["items_answered"] == 63 and all(c["seconds"] >= 0 for c in o["calls"])
    assert {f["key"] for f in o["flags"]} == {"lexflow:agency:va:p", "lexflow:agency:va:j"}
    md = (tmp_path / lint.REPORT_MD).read_text(encoding="utf-8")
    assert "HELD: 2 items" in md and "Records Office node 7" in md and "`lexflow:agency:va:bad`" in md
    js = json.loads((tmp_path / lint.REPORT_JSON).read_text(encoding="utf-8"))
    assert js["held_count"] == 2 and js["checked"] == {"new": 63, "changed": 0}
    # the sample and the cap
    client = StubClient()
    lint.run(con, items=items, client=client, sample=0.1, cap=1, out_dir=tmp_path, today=TODAY, log=lambda *a: None)
    assert len(client.calls) == 1
    chosen = lint.select_for_ollama(items, {"lexflow:agency:va:bad": [{"code": "x"}]}, sample=0.1, seed=1, cap=150)
    assert chosen[0].key == "lexflow:agency:va:bad" and len(chosen) == 1 + round(62 * 0.1)
    assert [c.key for c in chosen] == [c.key for c in lint.select_for_ollama(
        items, {"lexflow:agency:va:bad": [{"code": "x"}]}, sample=0.1, seed=1, cap=150)]
    # a dead model is a report line, not a crash, and holds nothing
    report = lint.run(con, items=items, client=StubClient(fail=True), sample=0.1, cap=2, out_dir=tmp_path,
                      today=TODAY, log=lambda *a: None)
    assert report["ollama"]["calls"][0]["error"].startswith("ConnectionError") and report["held_count"] == 1
    report = lint.run(con, items=items, ollama=False, out_dir=tmp_path, today=TODAY, log=lambda *a: None)
    assert report["held_count"] == 1 and "Ollama: not run" in (tmp_path / lint.REPORT_MD).read_text(encoding="utf-8")
    # --reuse keeps the flags of the report on disk without calling the model
    lint.run(con, items=items, client=StubClient({"Records Office": {"person": True}}), sample=1.0, out_dir=tmp_path,
             today=TODAY, log=lambda *a: None)
    report = lint.run(con, items=items, client=StubClient(fail=True), reuse=True, out_dir=tmp_path, today=TODAY,
                      log=lambda *a: None)
    assert report["held_count"] == 2 and report["ollama"]["reused_from"] and report["ollama"]["flags"][0]["person"]


def test_parse_verdicts_is_forgiving():
    assert lint.parse_verdicts('{"items": [{"n": 2, "readable": false, "person": false, "jargon": true, '
                               '"suggested_label": "x"}, {"n": 1, "readable": true, "person": true, "jargon": false, '
                               '"suggested_label": ""}]}', 2) == {
        2: {"readable": False, "person": False, "jargon": True, "suggested_label": "x"},
        1: {"readable": True, "person": True, "jargon": False, "suggested_label": ""}}
    assert lint.parse_verdicts("not json", 3) == {}
    assert lint.parse_verdicts('text {"items": [{"readable": true, "person": false, "jargon": false, '
                               '"suggested_label": ""}]} more', 1)[1]["readable"] is True
    assert lint.parse_verdicts('{"items": [{"n": 9, "readable": true}]}', 2) == {}
