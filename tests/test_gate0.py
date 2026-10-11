"""Gate 0 (docs/strategy/adoption-strategy.md §1.9) in the publisher: rows 4 (public labels and named review), 5 (time
limits in the law's words), 8 (lexflow:start says what is there), 9 (asked answers on the wiki only with a named
reviewer) and 12 (builder notes on lexflow:method), with the fixes from docs/design/verify-gate0.md: timer labels
on the process map, units in the DC table and the place pages, the method page's claims, reviewers only from the
list the operator keeps (the AI-name check a warning at `reviewer add`), reviews bound to the text they read,
plain reader notes, "N of M quotes matched" on every page type, local quotes matched by software where they cite
the state code and the AI verifier's count told apart, plain path labels on the maps, real corrections addresses,
and the namespace rule for every writer.  No network, no wiki: pages are rendered from a temp store."""
import importlib.util
import json
import re

import pytest

from lexflow import config, signoff
from lexflow.law import wording as W
from lexflow.publish import lexipedia as LX
from lexflow.publish import notes as N
from lexflow.store import db
from lexflow.store import turso as T

CURATED = config.ROOT / "curated"
PERSON = "Ana Villamar"             # a made-up reviewer (no real person)
# the operator's reviewer list as signoff reads it (lexflow.reviewers.roster): id -> row
ROSTER = {"rv-0000000a": {"id": "rv-0000000a", "name": PERSON, "role": "attorney", "licensed_in": "Virginia"},
          "rv-0000000b": {"id": "rv-0000000b", "name": PERSON, "role": "researcher", "licensed_in": None},
          "rv-0000000c": {"id": "rv-0000000c", "name": PERSON, "role": "other person", "licensed_in": None},
          "rv-0000000d": {"id": "rv-0000000d", "name": PERSON, "role": "municipal attorney", "licensed_in": "Virginia"}}
# review records: a reviewer id from the list, the date and the reviewer's own statement (lexflow/signoff.py)
ATTORNEY = {"reviewer": "rv-0000000a", "date": "2026-10-01", "attested": True}
RESEARCHER = {"reviewer": "rv-0000000b", "date": "2026-10-01", "attested": True}
# no model name or score on a reader page; "checked by" only as the AI verifier's check of a local page
FORBIDDEN = re.compile(r"claude|quality \d|confidence \d|checked by(?! an AI verifier)|every us county|opus|sonnet",
                       re.I)
COPY = "Open US Law's copy of the official text"
LABEL = re.compile(r"\*\*Drafted with an AI system from [^·]+ · (?:(?:Every quote|\d+ of \d+ quotes)(?: from the statute)? "
                   r"matched to Open US Law's copy of the official text(?: on \d{1,2} \w+ \d{4}| between [^·]+)?|"
                   r"(?:\d+ of \d+ quotes? from the [^·]+ matched by lexflow's software|[^·]*checked by an AI verifier "
                   r"against the cited page|[^·]*not matched by lexflow's software|Sources retrieved)[^·]*|"
                   r"Researched from the official pages[^·]*) · "
                   r"(?:Not yet reviewed by a person|[^*]*Reviewed by[^*]+|[^*]*reviewed by a person[^*]*)\*\*", re.I)
EXC = "(except Saturdays, Sundays, and legal public holidays)"


def _spec(state, question):
    return json.loads((CURATED / state / f"{question}.json").read_text(encoding="utf-8"))


def _facts(state, question):
    return _spec(state, question)["facts"]


def _step(facts, sid):
    return next(s for s in facts["steps"] if s["id"] == sid)


def _no_bpmn(text):
    return re.sub(r"<bpmnio.*?</bpmnio>", "", text, flags=re.S)


def _bpmn(text):
    return "".join(re.findall(r"<bpmnio.*?</bpmnio>", text, flags=re.S))


def _timer_names(xml):
    return [m.group(1) for m in re.finditer(r'<(?:bpmn:)?(?:boundaryEvent|intermediateCatchEvent)\b[^>]*\bname="([^"]*)"',
                                            xml) if re.search(r"_(?:deadline|timeout)\"", m.group(0))]


def _build(con, state, question="records"):
    from lexflow.municipal import build, locator
    from lexflow.municipal.questions import QUESTIONS
    locator.run(con, QUESTIONS[question], [state], log=lambda *_: None)
    return build.build(con, state, question, use_llm=False, log=lambda *_: None)


def _place_files(tmp_path, monkeypatch, *names):
    from lexflow.municipal import places
    for name in names:
        st = name.split("/")[0]
        (tmp_path / "places" / st).mkdir(parents=True, exist_ok=True)
        (tmp_path / "places" / f"{name}.json").write_bytes((CURATED / "places" / f"{name}.json").read_bytes())
    monkeypatch.setattr(places, "PLACES_DIR", tmp_path / "places")


@pytest.fixture()
def va_pages(con, va_statutes, tmp_path, monkeypatch):
    """The Virginia records model built from curated/va/records.json, and Charlottesville's local answers (only the
    place file: the researched processes beside it are other work in progress)."""
    from lexflow.municipal import places, scoring
    from test_places_strategies import _govs
    _place_files(tmp_path, monkeypatch, "va/charlottesville")
    _govs(con)
    _build(con, "va")
    places.load_local(con, log=lambda *_: None)
    scoring.run(con, "va", log=lambda *_: None)
    return con


@pytest.fixture()
def dc_pages(con, va_statutes, tmp_path, monkeypatch):
    """The District of Columbia records model and Washington's place file."""
    from lexflow.municipal import places, scoring
    from test_places_strategies import _govs
    _place_files(tmp_path, monkeypatch, "dc/washington")
    _govs(con)
    _build(con, "dc")
    places.load_local(con, log=lambda *_: None)
    scoring.run(con, "dc", log=lambda *_: None)
    return con


# ------------------------------------------------------------------ row 4: named review
# names of AI systems and products: the warning at `reviewer add` flags them (it is not a gate: the operator vouches
# for each reviewer on the list, and lexflow cannot check that a reviewer is a person)
AI_NAMES = ("Claude", "claude", "CLAUDE", "Claude Code", "claude.ai", "Claude (claude-opus-5-5)", "claude-opus-5-5",
            "Claude (Anthropic)", "Anthropic", "GPT", "GPT-4o", "gpt-4o", "ChatGPT", "Chat GPT", "OpenAI", "Open AI",
            "Gemini", "Google Gemini", "Bard", "Gemma", "gemma3:1b", "Llama", "llama3.1", "Qwen", "qwen3:1.7b",
            "Mistral", "Grok", "DeepSeek", "Deep Seek", "Copilot", "GitHub Copilot", "Fable", "Perplexity", "xAI",
            "lexflow", "AI reviewer", "Example AI", "an ai", "A.I. Reviewer", "language model")
# the 29 names verify-gate0.md (Re-check 2) found accepted, look-alike spellings among them, and more model families,
# assistants and agent products
RECHECK_ACCEPTED = ("Ollama", "AutoGPT", "ChatGLM", "Codex", "Bing Chat", "PaLM 2", "LaMDA", "Le Chat", "Codestral",
                    "HuggingChat", "Command R", "Amazon Q", "Watsonx", "Assistant", "a bot", "Kimi", "Devin", "Pi",
                    "C1aude", "Cl aude", "Ｃｌａｕｄｅ", "Сlаudе", "Claude in Cyrillic: Сlаudе", "C.l.a.u.d.e", "ClaudeBot",
                    "claudebot", "Cl@ude", "0llama", "Gem1ni")
MORE_AI_NAMES = ("Siri", "Alexa", "Cortana", "Google Assistant", "Cursor", "Windsurf", "Manus", "OpenHands", "SWE-agent",
                 "Aider", "Replit", "Tabnine", "Codeium", "CoCounsel", "Phi-3", "Mixtral", "Midjourney", "Sonnet", "Opus",
                 "Haiku", "DALL-E", "PaLM-E", "Stable Diffusion", "Hugging Face", "Ernie Bot", "Doubao", "Hunyuan",
                 "Baichuan", "Nemotron", "Granite 3", "IBM Watson", "Character.AI", "BabyAGI", "LangChain", "CrewAI",
                 "Chat-GPT", "o1-mini", "Large Language Model", "chatbot", "robot", "Example Reviewer (drafted by Claude)")
# made-up people whose names contain the letters of a product, or a product's name in another form
PEOPLE = ("Example Reviewer", "Bernard Lombardi", "Ana Villamar", "Maria Llamas", "Ai Weiwei", "Max Aiello",
          "Claudette Moreau", "Anne Claudel", "Ingrid Palme", "Marc Dalle", "Ruth Watson", "Bing Liu", "Meena Patel",
          "Dana Bixby", "June Cline", "Harvey Stone", "Jasper Jones", "Ravi Pichai", "Kimiko Ito", "Devine Lopez",
          "Pierce Brown", "Alexander Reyes", "Talbot Smith", "Abbott Lee", "José Pérez", "Mary-Jane O'Neil")


def _listed(con, role="researcher", licensed_in=None, name=PERSON, **kw):
    """Put a made-up reviewer on the test store's list, as `lexflow reviewer add` does; their row, with their token
    (shown once) under "token"."""
    from lexflow import reviewers as RV
    return RV.add(con, name, role, licensed_in=licensed_in, added_by="operator", **kw)


def _review(row, date="2026-10-01"):
    """A review record naming a reviewer on the list (what a curated file or the review API records)."""
    return {"reviewer": row["id"], "date": date, "attested": True}


def test_a_person_on_the_list_signs_and_a_typed_name_never_does():
    """A page names a reviewer only from the operator's list: the review records the reviewer's id, and the name,
    role and licence a page prints come from the list."""
    p = signoff.person
    assert signoff.line(p(RESEARCHER, ROSTER)) == f"Reviewed by {PERSON}, researcher, on 1 October 2026"
    assert signoff.line(p(ATTORNEY, ROSTER)) == f"Reviewed by {PERSON}, attorney licensed in Virginia, on 1 October 2026"
    assert signoff.line(p(dict(ATTORNEY, reviewer="rv-0000000d"), ROSTER)) == (
        f"Reviewed by {PERSON}, municipal attorney licensed in Virginia, on 1 October 2026")
    assert signoff.line(p(dict(RESEARCHER, reviewer="rv-0000000c"), ROSTER)) == f"Reviewed by {PERSON} on 1 October 2026"
    # the older curated strings record the AI system that drafted the model: never a person's sign-off
    assert p("Claude (claude-opus-5-5), 2026-10-10; every quote checked against open-us-law", ROSTER) is None
    # a name, role or state typed into a review is refused, whatever it says: they come from the list
    for typed in ({"name": PERSON, "role": "attorney", "date": "2026-10-01", "attested": True},
                  dict(RESEARCHER, name=PERSON), dict(RESEARCHER, role="attorney"), dict(RESEARCHER, licensed_in="va")):
        assert p(typed, ROSTER) is None, typed
    assert any("does not carry name" in x for x in signoff.problems(dict(RESEARCHER, name="Claude"), ROSTER))
    # someone not on the list (never added, or removed since) is not a reviewer
    assert p(dict(RESEARCHER, reviewer="rv-deadbeef"), ROSTER) is None
    assert signoff.NOT_ON_LIST in signoff.problems(dict(RESEARCHER, reviewer="rv-deadbeef"), ROSTER)
    assert p(RESEARCHER, {}) is None
    for bad in ("Ana Villamar", "", None, "rv-1", "RV-0000000A"):
        assert p(dict(RESEARCHER, reviewer=bad), ROSTER) is None, bad
    assert p(dict(RESEARCHER, date="2999-01-01"), ROSTER) is None                 # not in the future
    assert signoff.problems(RESEARCHER, ROSTER, not_before="2026-10-08T10:00:00Z") == [
        "the review date is before the text it reviews (2026-10-08)"]
    assert signoff.long_date("2026-10-09") == "9 October 2026"
    # a line is printed only for a reviewer as the list gives them
    assert signoff.line(RESEARCHER) is None and signoff.line({"name": PERSON, "role": "AI attorney",
                                                              "date": "2026-10-01"}) is None


def test_a_reviewer_gives_a_role_from_the_list_and_attests_to_the_text():
    """The role is one of a short list, kept on the reviewer list (not in the review); and the reviewer states
    that they, a person, read this exact text."""
    assert signoff.ROLES == ("attorney", "paralegal", "law student", "clerk", "records officer", "planner",
                             "municipal attorney", "researcher", "student", "volunteer", "other person")
    for role in signoff.ROLES:
        entry = {"id": "rv-0000000e", "name": PERSON, "role": role.upper(), "licensed_in": None}
        assert signoff.entry_problems(entry) == [], role
    for role in ("AI attorney", "attorney (drafted by Claude)", "staff attorney", "law librarian", "lawyer", "counsel",
                 "reviewer", "AI", "Claude", "attorney, assisted by an AI system", "attorneys"):
        entry = {"id": "rv-0000000e", "name": PERSON, "role": role, "licensed_in": None}
        assert any("role must be one of" in x for x in signoff.entry_problems(entry)), role
    # licensed_in is an attorney's, and names a state
    assert signoff.entry_problems(dict(ROSTER["rv-0000000b"], licensed_in="va"))
    assert signoff.entry_problems(dict(ROSTER["rv-0000000a"], licensed_in="Narnia"))
    for attested in (None, False, "yes", 1, "true"):                     # only the reviewer's own true
        rev = {k: v for k, v in RESEARCHER.items() if k != "attested"} if attested is None else \
            dict(RESEARCHER, attested=attested)
        assert signoff.person(rev, ROSTER) is None, attested
        assert any("read this exact text" in x for x in signoff.problems(rev, ROSTER)), attested
    assert signoff.person(RESEARCHER, ROSTER)["attested"] is True
    # the record bound to a text keeps the statement, so a stored review without it does not count either
    text = {"answer": 1}
    assert signoff.bind(RESEARCHER, text)["attested"] is True
    assert signoff.bound({k: v for k, v in signoff.bind(RESEARCHER, text).items() if k != "attested"}, text,
                         ROSTER) is None


def test_a_review_applies_only_to_the_text_it_reviewed():
    text = {"answer": {"steps": [1]}, "status": "answered"}
    signed = signoff.bind(RESEARCHER, text)
    assert set(signed) == {"reviewer", "date", "attested", "text_hash"}            # no name stored with it
    assert signed["text_hash"] == signoff.text_hash(text) and len(signed["text_hash"]) == 64
    assert signoff.bound(signed, text, ROSTER)["name"] == PERSON
    assert signoff.bind(signoff.person(RESEARCHER, ROSTER), text) == signed         # a person binds as a record
    assert signoff.bound(signed, {"answer": {"steps": [1, 2]}, "status": "answered"}, ROSTER) is None   # other text
    assert signoff.bound(RESEARCHER, text, ROSTER) is None                                    # no hash: no review
    assert signoff.bound(signed, text, ROSTER, not_before="2026-10-02") is None              # older than the text
    assert signoff.fits(signed, text) and not signoff.fits(signed, {"answer": 2})             # sync: without the list
    # the same text however it was stored: key order, JSON text or parsed, an empty list stored as NULL
    row = {"question_text": "Q", "status": "answered", "answer": json.dumps({"b": 1, "a": [2]}), "sections": "[]"}
    same = {"question_text": "Q", "status": "answered", "answer": {"a": [2], "b": 1}, "sections": None}
    assert signoff.row_text(row, signoff.ASKED_TEXT) == signoff.row_text(same, signoff.ASKED_TEXT)
    spec = {"facts": {"x": 1}, "reviewed_by": signed, "answers": {"records": {"reviewed_by": "x", "summary": "s"}}}
    assert signoff.file_hash(spec) == signoff.text_hash({"facts": {"x": 1}, "answers": {"records": {"summary": "s"}}})


def test_labels_compose_the_three_facts():
    assert LX.label(["2026-10-10"], LX.NOT_REVIEWED) == (
        f"Drafted with an AI system from the statute text · Every quote matched to {COPY} on 10 October 2026 · Not yet "
        "reviewed by a person")
    assert "between 9 October 2026 and 10 October 2026" in LX.label(["2026-10-09", "2026-10-10T03:00:00Z"], "x")
    assert f"21 of 23 quotes matched to {COPY}" in LX.label(["2026-10-10"], "x", matched=(21, 23))
    assert f"Every quote from the statute matched to {COPY}" in LX.label([], "x", scope=" from the statute")
    assert "Sources retrieved on 9 October 2026; no quotes to match" in LX.label(
        [], "x", check=LX.local_check({}, ["2026-10-09"]))
    attorney = signoff.person(ATTORNEY, ROSTER)
    assert LX.review_text([("", attorney)]).startswith(f"Reviewed by {PERSON}, attorney licensed in Virginia")
    both = LX.review_text([("state law", attorney), ("local procedure", None)])
    assert both == (f"state law: reviewed by {PERSON}, attorney licensed in Virginia, on 1 October 2026; "
                    "local procedure: not yet reviewed by a person")
    assert LX.review_summary([None, "Claude (claude-opus-5-5)"]) == LX.NOT_REVIEWED
    assert LX.review_summary([None, RESEARCHER]) == LX.NOT_REVIEWED                  # a record is not a reviewer
    assert LX.review_summary([signoff.person(RESEARCHER, ROSTER), None]).startswith("1 of 2 reviewed by a person")


def test_public_pages_carry_the_label_and_no_model_name_or_score(va_pages):
    pages = LX.all_pages(va_pages)
    assert {"lexflow:start", "lexflow:method", "lexflow:va", "lexflow:va:records", "lexflow:va:charlottesville",
            "lexflow:va:charlottesville:records"} <= set(pages)
    for pid, text in pages.items():
        assert pid.startswith("lexflow:")                                            # the namespace rule holds
        assert f"[[{LX.METHOD}|" in text, pid                                        # every footer links the method
        if pid == LX.METHOD:
            continue
        assert not FORBIDDEN.search(_no_bpmn(text)), (pid, FORBIDDEN.search(_no_bpmn(text)).group(0))
        assert LABEL.search(text), pid
        assert "to the official text" not in text, pid                              # always "Open US Law's copy of"
    model = pages["lexflow:va:records"]
    assert f"Every quote matched to {COPY} on" in model and "Not yet reviewed by a person" in model
    assert "Information, not legal advice" in model
    place = pages["lexflow:va:charlottesville:records"]
    assert f"Drafted with an AI system from the statute text and the official pages · Every quote from the statute " \
           f"matched to {COPY}" in place
    assert "Confidence" not in place and "confidence" not in pages["lexflow:va:charlottesville"]


def _curated_signed(con, tmp_path, monkeypatch, rev=None, edit=None):
    """Write curated/va/records.json to a temp curated folder, with its drafting note kept as drafted_by, edited by
    ``edit`` and signed with ``rev`` (and the file's text_hash) as whoever edits the file would, and build it; the
    build log."""
    from lexflow.municipal import build
    spec = _spec("va", "records")
    spec["drafted_by"] = spec.pop("reviewed_by")
    if edit:
        edit(spec)
    if rev is not None:
        spec["reviewed_by"] = dict(rev, text_hash=signoff.file_hash(spec))
    (tmp_path / "cur" / "va").mkdir(parents=True, exist_ok=True)
    (tmp_path / "cur" / "va" / "records.json").write_text(json.dumps(spec), encoding="utf-8")
    monkeypatch.setattr(config, "CURATED_DIR", tmp_path / "cur")
    said = []
    build.build(con, "va", "records", use_llm=False, force=True, log=said.append)
    return said


def test_a_curated_reviewer_is_shown_by_name_only_for_the_text_they_read(va_pages, tmp_path, monkeypatch):
    from lexflow import reviewers as RV
    who = _listed(va_pages, "attorney", "va")
    m = db.one(va_pages, "SELECT metrics, facts FROM process_models WHERE model_id='va.records'")
    assert json.loads(m["metrics"])["first_built"] == "2026-10-10"          # the date the drafting note opens with
    # dated before the model was first built: not a review of it
    _curated_signed(va_pages, tmp_path, monkeypatch, _review(who))
    assert "Reviewed by" not in LX.all_pages(va_pages)["lexflow:va:records"]
    _curated_signed(va_pages, tmp_path, monkeypatch, _review(who, "2026-10-10"))
    pages = LX.all_pages(va_pages)
    assert f"Reviewed by {PERSON}, attorney licensed in Virginia, on 10 October 2026" in pages["lexflow:va:records"]
    assert (f"state law: reviewed by {PERSON}, attorney licensed in Virginia, on 10 October 2026; local procedure: "
            "not yet reviewed by a person") in pages["lexflow:va:charlottesville:records"]
    # the operator takes the reviewer off the list: their name leaves every page
    RV.remove(va_pages, who["id"])
    page = LX.all_pages(va_pages)["lexflow:va:records"]
    assert "Reviewed by" not in page and "Not yet reviewed by a person" in page
    # back on the list (as someone new), signing again; then the stored text changes: the review no longer applies
    again = _listed(va_pages, "attorney", "va", name="Ana M. Villamar")
    _curated_signed(va_pages, tmp_path, monkeypatch, _review(again, "2026-10-10"))
    assert "Reviewed by Ana M. Villamar, attorney" in LX.all_pages(va_pages)["lexflow:va:records"]
    facts = json.loads(db.one(va_pages, "SELECT facts FROM process_models WHERE model_id='va.records'")["facts"])
    facts["gaps"] = facts["gaps"] + ["A note the reviewer never read."]
    va_pages.execute("UPDATE process_models SET facts=? WHERE model_id='va.records'", (json.dumps(facts),))
    va_pages.commit()
    page = LX.all_pages(va_pages)["lexflow:va:records"]
    assert "Reviewed by" not in page and "Not yet reviewed by a person" in page


def test_a_curated_reviewer_object_builds(con, va_statutes, tmp_path, monkeypatch):
    """A curated file signed by someone on the list (with the file's text_hash) builds and names them; a sign-off
    of another version of the file, a typed name, or a reviewer not on the list does not, and the drafting note is
    not mistaken for one."""
    from lexflow.municipal import build
    who = _listed(con)
    spec = _spec("va", "records")
    spec["drafted_by"] = spec.pop("reviewed_by")             # the drafting note is kept when a person signs
    spec["reviewed_by"] = dict(_review(who, "2026-10-10"), text_hash=signoff.file_hash(spec))
    (tmp_path / "va").mkdir()
    (tmp_path / "va" / "records.json").write_text(json.dumps(spec), encoding="utf-8")
    monkeypatch.setattr(config, "CURATED_DIR", tmp_path)
    assert _build(con, "va")["tier"] == "reviewed"
    page = LX.render_state_model(con, "va", "records")
    assert f"Reviewed by {PERSON}, researcher, on 10 October 2026" in page
    assert build.rebuild(con, "va.records").provenance.model is None
    stored = json.loads(db.one(con, "SELECT metrics FROM process_models WHERE model_id='va.records'")["metrics"])
    assert set(stored["reviewed_by"]) == {"reviewer", "date", "attested", "text_hash"}      # the id, not the name
    for bad, why in ((dict(spec["reviewed_by"], name="Claude", role="attorney"), "does not carry name"),
                     (dict(spec["reviewed_by"], reviewer="rv-deadbeef"), "not on the operator's list")):
        spec["reviewed_by"] = bad
        (tmp_path / "va" / "records.json").write_text(json.dumps(spec), encoding="utf-8")
        said = []
        build.build(con, "va", "records", use_llm=False, force=True, log=said.append)
        assert "Reviewed by" not in LX.render_state_model(con, "va", "records")
        assert any(why in s for s in said), (why, said)
    # not before the model was first built (the drafting note's date), and not in the future, like asked answers
    for when, why in (("2001-01-01", "before the text it reviews (2026-10-10)"), ("2999-01-01", "in the future")):
        spec["reviewed_by"] = dict(_review(who, when), text_hash=signoff.file_hash(spec))
        (tmp_path / "va" / "records.json").write_text(json.dumps(spec), encoding="utf-8")
        said = []
        build.build(con, "va", "records", use_llm=False, force=True, log=said.append)
        assert "Reviewed by" not in LX.render_state_model(con, "va", "records"), when
        assert any(why in x for x in said), (when, said)
    # without a drafting note, the first build this copy recorded is the date
    assert build.first_built(con, {"facts": {}}, "va", "records") == "2026-10-10"
    assert build.first_built(con, {"facts": {}}, "va", "business") == db.now()[:10]
    spec["reviewed_by"] = dict(_review(who, "2026-10-10"), text_hash=signoff.file_hash(spec))
    spec["facts"]["gaps"].append("Edited after the review.")             # the file changes; the sign-off does not
    (tmp_path / "va" / "records.json").write_text(json.dumps(spec), encoding="utf-8")
    said = []
    build.build(con, "va", "records", use_llm=False, force=True, log=said.append)
    assert "Reviewed by" not in LX.render_state_model(con, "va", "records")
    assert any("not a sign-off of this text" in s and "review-hash" in s for s in said)


def test_a_place_file_reviewer_is_read_and_bound_to_the_answer(con, tmp_path, monkeypatch):
    from lexflow.municipal import places
    from test_places_strategies import _govs
    _govs(con)
    who = _listed(con)
    spec = json.loads((CURATED / "places" / "va" / "charlottesville.json").read_text(encoding="utf-8"))
    signed = dict(_review(who, "2026-10-10"), text_hash=signoff.file_hash(spec))
    spec["reviewed_by"] = signed
    (tmp_path / "va").mkdir()
    (tmp_path / "va" / "charlottesville.json").write_text(json.dumps(spec), encoding="utf-8")
    monkeypatch.setattr(places, "PLACES_DIR", tmp_path)
    places.load_local(con, log=lambda *_: None)
    row = db.one(con, "SELECT * FROM local_answers WHERE question='records'")
    stored = json.loads(row["reviewed_by"])
    assert stored == {"reviewer": who["id"], "date": "2026-10-10", "attested": True,
                      "text_hash": signoff.text_hash(signoff.row_text(row, signoff.LOCAL_TEXT))}   # bound to the row
    assert LX.local_reviewer(row, con)["name"] == PERSON
    # dated before the research, signed for another version of the file, or naming a typed person: not a review
    for bad in (dict(signed, date="2026-10-01"), dict(signed, text_hash="0" * 64),
                {"name": PERSON, "role": "researcher", "date": "2026-10-10", "attested": True,
                 "text_hash": signoff.file_hash(spec)}):
        spec["reviewed_by"] = bad
        (tmp_path / "va" / "charlottesville.json").write_text(json.dumps(spec), encoding="utf-8")
        places.load_local(con, log=lambda *_: None)
        assert db.one(con, "SELECT reviewed_by FROM local_answers WHERE question='records'")["reviewed_by"] is None
    g = db.one(con, "SELECT * FROM governments WHERE name='City of Charlottesville'")
    proc = {"title": "T", "sources": [{"url": "https://a", "retrieved": "2026-10-09"}]}
    proc["reviewed_by"] = dict(_review(who), text_hash=signoff.file_hash(proc))
    # a sign-off counts only while this copy's own process file carries it
    assert LX.process_reviewer(proc, con) is None
    (tmp_path / "va" / "charlottesville").mkdir()
    (tmp_path / "va" / "charlottesville" / "p.json").write_text(json.dumps(proc), encoding="utf-8")
    assert LX.process_reviewer(proc, con)["name"] == PERSON
    text = LX.render_local_process(con, g, {"process": "p", "spec": proc})
    assert f"· Reviewed by {PERSON}" in text
    proc["title"] = "T, edited"
    assert "Reviewed by" not in LX.render_local_process(con, g, {"process": "p", "spec": proc})


# ------------------------------------------------------------------ row 5: time limits in the law's words
def test_time_limits_are_the_statutes_own_words():
    va = _facts("va", "records")
    assert W.describe(_step(va, "respond"), va)["text"] == "“within five working days”"
    assert W.describe(_step(va, "respond_extended"), va)["text"] == "“an additional seven work days”"
    assert W.describe(_step(va, "respond"), va)["wording"] == "relabelled"           # stored business_days
    md = _facts("md", "records")
    assert W.describe(_step(md, "notify_delay"), md)["text"] == "“within 10 working days”"
    tx = _facts("tx", "records")
    assert W.describe(_step(tx, "submit_to_ag"), tx)["text"] == "“not later than the 15th business day”"
    ny = _facts("ny", "records")
    assert W.describe(_step(ny, "decide_later"), ny)["text"] == "no number of days in the text"


def test_derived_figures_are_marked_as_lexflows_count():
    dc = _facts("dc", "records")
    d = W.describe(_step(dc, "respond_extended"), dc)
    assert d["count"] == "15 + up to 10" and d["text"].startswith(f"lexflow's count: 15 + up to 10, from “within 15 days "
                                                                    f"{EXC}”")
    assert W.describe(_step(dc, "respond"), dc)["text"] == f"“within 15 days {EXC}”"
    ca = _facts("ca", "records")
    assert W.describe(_step(ca, "determine_extended"), ca)["count"] == "10 + up to 14"
    lone = {"id": "x", "deadline": {"amount": 12, "unit": "business_days", "source": {"quote": "promptly"}},
            "source": {"quote": "shall answer"}}
    assert W.describe(lone, {"steps": [lone]})["text"] == "lexflow's count: 12 business days"


def test_text_deadlines_keep_their_quote_or_say_they_are_lexflows():
    assert W.describe_text("5 business days", "shall respond within five working days of receipt") == \
        "“within five working days”"
    assert W.describe_text("5 business days", None) == "lexflow's count: 5 business days"
    assert W.describe_text("Within 30 days of the decision letter (city)", "appeal it.") == \
        "in lexflow's words: Within 30 days of the decision letter (city)"
    assert W.describe_text("within 30 days", "must appeal within 30 days of the decision") == "“within 30 days”"


def test_every_curated_deadline_is_rechecked_against_its_quote():
    rows = W.audit(CURATED)
    assert len(rows) >= 53
    by = {(r["model"], r["step"]): r for r in rows}
    assert not [r for r in rows if r["wording"] == "disagrees"]                     # no unit of another kind
    assert {k for k, r in by.items() if r["wording"] == "relabelled"} >= {
        ("va.records", "respond"), ("va.records", "respond_extended"), ("md.records", "redirect_applicant"),
        ("md.records", "notify_delay"), ("md.records", "send_denial_statement"), ("dc.records", "respond"),
        ("dc.records", "mayor_review")}
    assert {k for k, r in by.items() if r["wording"] == "derived"} >= {("dc.records", "respond_extended"),
                                                                        ("ca.records", "determine_extended")}
    assert by[("il.records", "respond_extended")]["in_deadline_quote"] is False


def test_timers_on_the_process_map_are_named_in_the_statutes_words():
    """The compiler names each timer from the same reading as the step list: the statute's phrase, "lexflow's
    count" for a sum, no number where the law gives none; never the stored amount and unit."""
    from lexflow.bpmn_xml import to_bpmn_xml
    from lexflow.extract.compile import compile_facts
    from lexflow.extract.schema import LegalProcessFacts
    from lexflow.ir import SectionText
    want = {"va": {"“within five working days”", "“an additional seven work days”"},
            "dc": {f"“within 15 days {EXC}”", "lexflow's count: 15 + up to 10",
                   "“within 10 days (excluding Saturdays, Sundays, and legal holidays)”"},
            "ny": {W.NO_FIGURE, "“within five business days”"},
            "ca": {"lexflow's count: 10 + up to 14", "“within 10 days”"},
            "md": {"“within 10 working days”"}}
    stored_unit = re.compile(r"^\d+ (?:business days|days|hours|weeks|months|years)(?: pass)?$")
    for st, names in want.items():
        facts = LegalProcessFacts.model_validate(_facts(st, "records"))
        text = SectionText(code="Code", section="1", title="t", jurisdiction=st, text="", url="https://example.invalid")
        xml = to_bpmn_xml(compile_facts(facts, model_id=f"{st}-records", jurisdiction=st, jurisdiction_name=st,
                                        code="Code", text=text))
        got = set(_timer_names(xml))
        assert names <= got, (st, got)
        assert not [n for n in got if stored_unit.match(n)], (st, got)
    # a wait for a party's own act reads as the time limit passing
    tx = _facts("tx", "records")
    assert W.timer_label(_step(tx, "submit_to_ag"), tx, waiting=True) == \
        "Time limit passes: “not later than the 15th business day”"
    # a map stored before the fix (or pulled from elsewhere) is relabelled on the page from the same reading
    va = _facts("va", "records")
    old = ('<bpmn:boundaryEvent id="respond_deadline" name="5 business days" attachedToRef="respond">'
           '<bpmn:timerEventDefinition/></bpmn:boundaryEvent><bpmn:task id="respond" name="Respond"/>')
    new = LX.relabel_timers(old, va)
    assert 'name="“within five working days”"' in new and 'name="Respond"' in new and "5 business days" not in new


def test_pages_print_the_law_words_not_the_normalised_unit(va_pages):
    pages = LX.all_pages(va_pages)
    for pid in ("lexflow:va:records", "lexflow:va:charlottesville:records"):
        assert "time limit: “within five working days”" in pages[pid], pid
        assert "time limit: “an additional seven work days”" in pages[pid], pid
        assert "business days" not in _no_bpmn(pages[pid]), pid
    bpmn = _bpmn(pages["lexflow:va:records"])
    assert set(_timer_names(bpmn)) == {"“within five working days”", "“an additional seven work days”"}
    assert "business days" not in bpmn                       # the map the reader sees first says it too


def test_the_dc_table_notes_and_place_page_use_the_laws_words(dc_pages):
    spec = _spec("dc", "records")
    outputs = [str(c) for d in spec["facts"]["decisions"] for r in d["rules"] for c in r["then"]]
    assert f"\"No extension: answer within 15 days {EXC} of receipt\"" in outputs
    assert f"\"Written notice with reasons and expected date; the extension shall not exceed 10 days {EXC}\"" in outputs
    assert not re.search(r"working days?|working-day", json.dumps(spec, ensure_ascii=False))
    pages = LX.all_pages(dc_pages)
    model = pages["lexflow:dc:records"]
    assert f"No extension: answer within 15 days {EXC} of receipt" in model
    assert "working day" not in model and "business day" not in model
    assert "lexflow's count: 15 + up to 10" in _bpmn(model)
    place = pages["lexflow:dc:washington_dc:records"]
    assert "In lexflow's words" in place and "lexflow's words, not the law's" in place
    for gone in ("Agencies must answer within 15 business days", "15 business days, with a possible 10-business-day",
                 "The 15-day clock is in business days", "add 10 more business days"):
        assert gone not in place, gone
    assert f"within 15 days {EXC}" in place and "dc.gov/foia calls" in place
    md = json.loads((CURATED / "places" / "md" / "baltimore.json").read_text(encoding="utf-8"))
    assert "Within 10 days of receipt, DPW sends" not in json.dumps(md, ensure_ascii=False)
    assert "within 10 working days after receipt of the request (GP § 4-203(b)(2))" in json.dumps(md, ensure_ascii=False)


# ------------------------------------------------------------------ row 8: lexflow:start
def test_start_says_what_is_there_and_claims_no_breadth(va_pages):
    start = LX.all_pages(va_pages)["lexflow:start"]
    assert "They cover 1 jurisdiction: Virginia." in start
    assert "none has yet been reviewed by a person" in start
    assert f"every quote in it was matched to {COPY}" in start
    assert "Other states, places and questions are not covered here." in start
    assert not re.search(r"every US|county, city and town|38,|confidence", start, re.I)
    assert "  * How do I request public records? — 1 jurisdiction" in start
    assert "[[start|" not in start and "Lexipedia home" not in start     # no link out of the lexflow: namespace
    assert start.rstrip().endswith(f"[[{LX.METHOD}|How these pages are made, sources and corrections]]")


def test_start_names_the_eleven_curated_jurisdictions(con):
    states = sorted(p.name for p in CURATED.iterdir() if p.is_dir() and (p / "records.json").exists())
    assert len(states) == 11
    start = LX.render_index(con, states, [], {st: ["records", "business"] for st in states})
    assert "They cover 11 jurisdictions: California, the District of Columbia, Florida," in start
    assert "Virginia and Washington. Each map was drafted with an AI system" in start


# ------------------------------------------------------------------ "N of M quotes matched" on every page type
def _stored_quotes(con, mid, *quotes, metrics=None):
    """Put ``quotes`` in place of the first step quotes of a stored model (as a pull from a shared database someone
    wrote could), and optionally overwrite its stored metrics."""
    row = db.one(con, "SELECT facts, metrics FROM process_models WHERE model_id=?", mid)
    facts = json.loads(row["facts"])
    for step, q in zip(facts["steps"], quotes):
        step["source"]["quote"] = q
    con.execute("UPDATE process_models SET facts=?, metrics=? WHERE model_id=?",
                (json.dumps(facts), json.dumps(metrics if metrics is not None else json.loads(row["metrics"])), mid))
    con.commit()


def test_every_page_type_with_quotes_says_how_many_matched(va_pages):
    # two step quotes that are not in the statute text; the stored metrics still say every quote matched, and pages
    # count again when they are made (model_matched), so they say 21 of 23
    metrics = json.loads(db.one(va_pages, "SELECT metrics FROM process_models WHERE model_id='va.records'")["metrics"])
    _stored_quotes(va_pages, "va.records", "words that are not in the statute", "nor are these words",
                   metrics=dict(metrics, quotes_checked=23, quote_misses=0))
    # an asked answer whose stored count says every quote matched: the page counts again, and 4 of its 5 are there
    words = _law_text("va")["Va. Code Ann. § 2.2-3704"].split()
    quotes = [{"id": f"Q{i}", "section": "2.2-3704", "text": " ".join(words[i * 12:i * 12 + 10])} for i in range(4)]
    db.upsert(va_pages, "asked_answers", [dict(_asked(1, None), metrics=json.dumps(
        {"answered_at": "2026-10-08T10:00:00Z", "quotes_checked": 5, "quote_misses": 0}),
        sections=json.dumps({"chosen": [{"ref": "2.2-3704", "citation": "Va. Code Ann. § 2.2-3704", "title": "T"}]}),
        answer=json.dumps({"quotes": quotes + [{"id": "Q9", "section": "2.2-3704", "text": "not in the section"}],
                           "steps": []}))])
    row = db.one(va_pages, "SELECT * FROM asked_answers")
    _record(va_pages, row, _signed(row, con=va_pages))
    pages = LX.all_pages(va_pages)
    for pid in ("lexflow:va:records", "lexflow:va:charlottesville:records", "lexflow:va:charlottesville",
                "lexflow:va", "lexflow:start"):
        assert re.search(r"\d+ of \d+ quotes(?: from the statute)? matched to Open US Law", pages[pid]), pid
    assert f"21 of 23 quotes matched to {COPY}" in pages["lexflow:va:records"]
    assert "21 of 23 quotes from the statute matched" in pages["lexflow:va:charlottesville:records"]
    assert "21 of 23 quotes from the statute matched" in pages["lexflow:va:charlottesville"]
    assert "25 of 28 quotes from the statute matched" in pages["lexflow:va"]          # the model and the answer
    assert "21 of their 23 quotes were matched" in pages["lexflow:start"]
    assert f"4 of 5 quotes matched to {COPY}" in pages["lexflow:va:deck_permit"]


def test_asked_answers_count_their_quotes():
    from lexflow.ask import pipeline as AP
    text = "The body shall respond within five working days of receiving a request."
    got = AP.quote_counts([{"text": "shall respond within five  working days"}],
                          [{"quote": "within ten days"}, {"quote": None}], text)
    assert got == {"quotes_checked": 2, "quote_misses": 1}
    assert AP.quote_counts([], [], text) == {}


# ------------------------------------------------------------------ row 9: asked answers need a named reviewer
def _asked(published=1, reviewed_by=None):
    return {"question_id": "deck_permit", "target": "va", "state": "va", "gov_id": None,
            "question_text": "Do I need a permit for a deck?", "status": "answered",
            "answer": json.dumps({"quotes": [], "steps": [{"actor": "Owner", "action": "Apply", "section": "36-98",
                                                           "quote": "shall apply within five working days",
                                                           "deadline": "5 business days"}]}),
            "metrics": json.dumps({"answered_at": "2026-10-08T10:00:00Z"}),
            "published": published, "reviewed_by": reviewed_by}


def _signed(row, rev=None, con=None):
    """A sign-off of this answer's text (what the review API stores), by a reviewer on ``con``'s list."""
    if rev is None:
        rev = _review(_listed(con), "2026-10-09")
    return signoff.bind(rev, signoff.row_text(row, signoff.ASKED_TEXT))


def _record(con, row, rev):
    """Store the review ``rev`` of an asked answer as this copy's review API does: in its reviewed_by column, and as
    the answer's last review_log entry (a page names the reviewer only for a review this copy recorded)."""
    from lexflow import reviewers as RV
    con.execute("UPDATE asked_answers SET reviewed_by=? WHERE question_id=? AND target=?",
                (json.dumps(rev), row["question_id"], row["target"]))
    RV.log_review(con, "review", row["question_id"], row["target"], rev["reviewer"], rev["text_hash"],
                  at=f"{rev['date']}T12:00:00Z")
    con.commit()


def test_asked_answers_reach_the_wiki_only_when_reviewed(con):
    from lexflow import reviewers as RV
    row = _asked()
    other = dict(row, status="partial")
    who = _listed(con)
    today = _review(who, "2026-10-09")
    # a well-formed review of this text by someone on the list, but not one this copy's review API recorded (no
    # review_log entry: pulled, or written by hand): not a review here
    db.upsert(con, "asked_answers", [_asked(1, _signed(row, today))])
    con.commit()
    assert "lexflow:va:deck_permit" not in LX.all_pages(con)
    RV.log_review(con, "review", "deck_permit", "va", who["id"], _signed(row, today)["text_hash"],
                  at="2026-10-09T12:00:00Z")
    for pub, rev, shown in ((1, None, False), (0, _signed(row, today), False),
                            (1, {"name": "Claude", "role": "AI", "date": "2026-10-09", "attested": True}, False),
                            (1, dict(today, reviewer="rv-deadbeef", text_hash=_signed(row, today)["text_hash"]),
                             False),                                                  # not on the list
                            (1, today, False),                                        # no text_hash
                            (1, _signed(other, today), False),                        # a review of other text
                            (1, _signed(row, _review(who)), False),                   # older than the answer
                            (1, _signed(row, today), True)):
        db.upsert(con, "asked_answers", [_asked(pub, rev)])
        con.commit()
        pages = LX.all_pages(con)
        assert ("lexflow:va:deck_permit" in pages) is shown, (pub, rev)
        assert ("lexflow:va" in pages) is shown, (pub, rev)
    page = pages["lexflow:va:deck_permit"]
    # its sections' text is not at hand here, so the software made no count, and the page says so
    assert f"Quotes not matched by lexflow's software: the statute text was not at hand when this page was made · " \
           f"Reviewed by {PERSON}, researcher" in page and "Every quote" not in page
    assert "time limit: “within five working days”" in page and "5 business days" not in page
    assert "[[lexflow:va:deck_permit|Do I need a permit for a deck?]]" in pages["lexflow:va"]


def test_the_review_column_exists_here_and_on_the_shared_database(con):
    assert "reviewed_by" in db.columns(con, "asked_answers") and "reviewed_by" in db.columns(con, "local_answers")
    assert "quote_check" in db.columns(con, "place_processes")
    assert set(T.remote_migrations()) == {"ALTER TABLE asked_answers ADD COLUMN reviewed_by TEXT",
                                          "ALTER TABLE local_answers ADD COLUMN reviewed_by TEXT",
                                          "ALTER TABLE place_processes ADD COLUMN quote_check TEXT"}

    class Client:
        def __init__(self):
            self.sent = []

        def pipeline(self, statements):
            self.sent += [s for s, _ in statements]
            if statements[0][0].startswith("ALTER"):
                raise T.TursoError("statement 1 failed: SQLite error: duplicate column name: reviewed_by")
            return [{}]
    c = Client()
    T.ensure_schema(c)                                       # a column that is already there is not an error
    assert sum(s.startswith("ALTER") for s in c.sent) == 3
    assert not any("reviewers" in s for s in c.sent)                     # the list is this copy's own


class _Remote:
    """A shared database with a read-only token and no reviewed_by column: pull reads the columns it has."""

    def __init__(self, con, rows):
        self.con, self.rows, self.selects = con, rows, []

    def pipeline(self, statements):
        raise T.TursoError("read-only")

    def query(self, sql, *args):
        if sql.startswith("PRAGMA"):
            table = sql[sql.index("(") + 1:-1]
            return [{"name": c} for c in db.columns(self.con, table) if c != "reviewed_by"]
        self.selects.append(sql)
        if args and args[0]:
            return []
        return [dict(r, _rowid=i + 1) for i, r in enumerate(self.rows)]


def test_pull_selects_only_the_columns_the_shared_database_has(con):
    """A remote that has not got the new column yet (a read-only token cannot add it) still pulls."""
    c = _Remote(con, [])
    T.pull(con, c, tables=["asked_answers"], log=lambda *_: None)
    assert c.selects and "reviewed_by" not in c.selects[0] and "published" in c.selects[0]


def test_sync_keeps_the_reviewer_with_the_text_they_read(con):
    """A newer copy of a reviewed answer pulled from a shared database without the column (or pushed there by a
    machine on older code) keeps the local reviewer beside new text: the hash shows it, the page does not name
    them, and pull clears the stale review so push sends the reviewer and the text together."""
    row = _asked()
    db.upsert(con, "asked_answers", [dict(row, updated_at="2026-10-09T00:00:00Z")])
    _record(con, row, _signed(row, con=con))
    assert f"Reviewed by {PERSON}" in LX.all_pages(con)["lexflow:va:deck_permit"]
    newer = {k: v for k, v in _asked().items() if k != "reviewed_by"}
    newer.update(status="partial", updated_at="2026-10-10T00:00:00Z", origin="elsewhere")
    T.pull(con, _Remote(con, [newer]), tables=["asked_answers"], log=lambda *_: None)
    stored = db.one(con, "SELECT * FROM asked_answers")
    assert stored["status"] == "partial" and stored["reviewed_by"] is None
    assert "lexflow:va:deck_permit" not in LX.all_pages(con)
    # a pull of the same text keeps the review, even by a reviewer this copy's list does not hold (yet)
    rev = dict(_review({"id": "rv-0123abcd"}, "2026-10-09"))
    db.upsert(con, "asked_answers", [dict(stored, reviewed_by=_signed(stored, rev))])
    con.commit()
    again = {k: v for k, v in db.one(con, "SELECT * FROM asked_answers").items() if k != "reviewed_by"}
    again["updated_at"] = "2026-10-11T00:00:00Z"
    T.pull(con, _Remote(con, [again]), tables=["asked_answers"], full=True, log=lambda *_: None)
    assert db.one(con, "SELECT reviewed_by FROM asked_answers")["reviewed_by"] is not None
    # ... but it names no one here: this copy did not record it
    assert LX.asked_reviewer(db.one(con, "SELECT * FROM asked_answers"), con) is None


def test_reasking_drops_the_review(con, monkeypatch):
    from lexflow.ask import pipeline as AP
    from lexflow.ask.plan import Plan
    monkeypatch.setattr(AP.statutes, "have", lambda state: False)
    db.upsert(con, "asked_answers", [_asked(1, _signed(_asked(), con=con))])
    con.commit()
    plan = Plan(text="Do I need a permit for a deck?", groups=[["deck"]], kind="process")
    AP.answer_state(con, "deck_permit", plan, "va", log=lambda *_: None)
    row = db.one(con, "SELECT published, reviewed_by FROM asked_answers WHERE question_id='deck_permit'")
    assert row["reviewed_by"] is None and row["published"] == 1                      # the tick stays, the sign-off goes
    assert "lexflow:va:deck_permit" not in LX.all_pages(con)


def test_review_api_gates_the_wiki_tick(con, monkeypatch):
    """The review API takes a reviewer id from the operator's list, the reviewer's statement and the hash of the
    text they read, and nothing else: no typed name, role, licence or date."""
    from fastapi.testclient import TestClient
    from lexflow import reviewers as RV
    from lexflow.api import app as API
    monkeypatch.setattr(config, "JOB_RUNNER", False)
    db.upsert(con, "asked_answers", [_asked(0, None)])
    con.commit()
    who = _listed(con, "attorney", "Virginia")
    other = _listed(con, "researcher", name="Ben Okoro")
    mine = {RV.TOKEN_HEADER: who["token"]}
    base = "/api/ask/deck_permit/va"
    with TestClient(API.app) as c:
        r = c.post(f"{base}/publish", json={"published": True})
        assert r.status_code == 409 and "named reviewer" in r.json()["detail"]
        shown = c.get(base).json()
        assert shown["reviewed_by"] is None and len(shown["text_hash"]) == 64 and "review_roles" not in shown
        assert sorted(c.get("/api/reviewers").json(), key=lambda x: x["name"]) == [
            {"id": who["id"], "name": PERSON, "role": "attorney", "licensed_in": "Virginia",
             "label": f"{PERSON}, attorney licensed in Virginia"},
            {"id": other["id"], "name": "Ben Okoro", "role": "researcher", "licensed_in": None,
             "label": "Ben Okoro, researcher"}]
        ok = {"reviewer": who["id"], "attested": True, "text_hash": shown["text_hash"]}
        # free text never goes through the API: a name, role, licence or date is refused, whatever it says
        for extra in ({"name": PERSON}, {"name": "Claude"}, {"role": "attorney"}, {"licensed_in": "va"},
                      {"date": "2026-10-09"}, {"note": "x"}):
            got = c.put(f"{base}/review", json={**ok, **extra}, headers=mine)
            assert got.status_code == 400 and "a review takes only reviewer" in got.json()["detail"], extra
        old_style = {"name": PERSON, "role": "attorney", "date": "2026-10-09", "licensed_in": "Virginia",
                     "attested": True, "text_hash": shown["text_hash"]}
        assert c.put(f"{base}/review", json=old_style, headers=mine).status_code == 400
        for bad in ("rv-deadbeef", PERSON, "", None, 7):                    # not someone on the list
            got = c.put(f"{base}/review", json=dict(ok, reviewer=bad), headers=mine)
            assert got.status_code == 400 and "list" in got.json()["detail"], bad
        # the reviewer's own statement that a person read this exact text
        for attested in (False, None, "true", 1):
            got = c.put(f"{base}/review", json={k: v for k, v in dict(ok, attested=attested).items() if v is not None},
                        headers=mine)
            assert got.status_code == 400 and "read this exact text" in got.json()["detail"], attested
        # the hash of the text the reviewer read is required and well formed (400), and must be the stored text's
        got = c.put(f"{base}/review", json={k: v for k, v in ok.items() if k != "text_hash"}, headers=mine)
        assert got.status_code == 400 and "text_hash" in got.json()["detail"]
        for malformed in ("", "abc", shown["text_hash"].upper(), " " + shown["text_hash"], 5):
            got = c.put(f"{base}/review", json=dict(ok, text_hash=malformed), headers=mine)
            assert got.status_code == 400 and "text_hash" in got.json()["detail"], malformed
        # the named reviewer's own token: none is a 401, one that is no reviewer's or another reviewer's a 403
        got = c.put(f"{base}/review", json=ok)
        assert got.status_code == 401 and RV.TOKEN_HEADER in got.json()["detail"]
        for wrong in ("x", who["token"][:-1] + ("A" if who["token"][-1] != "A" else "B"), who["token"] + "x",
                      who["token"].replace(who["id"], other["id"]), "rv-deadbeef." + who["token"].split(".")[1]):
            got = c.put(f"{base}/review", json=ok, headers={RV.TOKEN_HEADER: wrong})
            assert got.status_code == 403 and "not the token of a reviewer" in got.json()["detail"], wrong
        got = c.put(f"{base}/review", json=ok, headers={RV.TOKEN_HEADER: other["token"]})
        assert got.status_code == 403 and "another reviewer's" in got.json()["detail"]
        assert c.put(f"{base}/review", json=dict(ok, text_hash="0" * 64), headers=mine).status_code == 409
        assert c.get(base).json()["reviewed_by"] is None                                      # none of these was kept
        assert db.scalar(con, "SELECT count(*) FROM review_log") == 0
        r = c.put(f"{base}/review", json=ok, headers=mine)
        assert r.status_code == 200 and r.json()["text_hash"] == shown["text_hash"]
        assert r.json()["recorded_by"] == who["id"]
        logged = db.one(con, "SELECT * FROM review_log")
        assert (logged["action"], logged["reviewer"], logged["text_hash"]) == ("review", who["id"], shown["text_hash"])
        assert r.json()["reviewed_by"]["attested"] is True and r.json()["reviewed_by"]["reviewer"] == who["id"]
        today = signoff.long_date(db.now())
        assert r.json()["review_line"] == f"Reviewed by {PERSON}, attorney licensed in Virginia, on {today}"
        stored = json.loads(db.one(con, "SELECT reviewed_by FROM asked_answers")["reviewed_by"])
        assert set(stored) == {"reviewer", "date", "attested", "text_hash"}                    # no name stored
        assert c.post(f"{base}/publish", json={"published": True}).status_code == 200
        brief = c.get("/api/ask/deck_permit").json()["answers"][0]
        assert brief["published"] == 1 and brief["reviewed_by"]["name"] == PERSON
        listed = c.get("/api/ask").json()[0]
        assert (listed["reviewed"], listed["published"], listed["review_stale"]) == (1, 1, 0)
        assert c.get(base).json()["review_line"].startswith(f"Reviewed by {PERSON}")
    pages = LX.all_pages(con)
    assert "lexflow:va:deck_permit" in pages
    # signing and ticking move updated_at, but not the date the answer was made (its answered_at); the page's count
    # is the software's, made when the page is (here the sections' text is not at hand, and the page says so)
    stored_metrics = json.loads(db.one(con, "SELECT metrics FROM asked_answers")["metrics"])
    assert stored_metrics["answered_at"] == "2026-10-08T10:00:00Z"
    assert "Quotes not matched by lexflow's software" in pages["lexflow:va:deck_permit"]
    # the operator takes the reviewer off the list: the page and the API no longer name them
    RV.remove(con, who["id"])
    assert "lexflow:va:deck_permit" not in LX.all_pages(con)
    with TestClient(API.app) as c:
        seen = c.get(base).json()
        assert seen["reviewed_by"] is None and seen["review_stale"] is True
        assert [x["id"] for x in c.get("/api/reviewers").json()] == [other["id"]]
        assert "token" not in json.dumps(c.get("/api/reviewers").json())          # no token or hash is shown
        assert c.put(f"{base}/review", json=ok, headers=mine).status_code == 400  # a removed reviewer cannot sign
        assert c.delete(f"{base}/review", headers=mine).status_code == 403        # and their token no longer works
    again = _listed(con, "attorney", "Virginia", name="Ana M. Villamar")
    with TestClient(API.app) as c:
        assert c.put(f"{base}/review", json=dict(ok, reviewer=again["id"]),
                     headers={RV.TOKEN_HEADER: again["token"]}).status_code == 200
    assert "lexflow:va:deck_permit" in LX.all_pages(con)
    # the text changes under the review (here by hand, as an older machine's push would): it no longer counts
    con.execute("UPDATE asked_answers SET status='partial'")
    con.commit()
    assert "lexflow:va:deck_permit" not in LX.all_pages(con)
    with TestClient(API.app) as c:
        seen = c.get(base).json()
        assert seen["reviewed_by"] is None and seen["review_stale"] is True
        # the dashboard's question list counts a review only while its hash fits the text: none is current now
        listed = c.get("/api/ask").json()[0]
        assert (listed["reviewed"], listed["published"], listed["review_stale"]) == (0, 0, 1)
        assert c.get("/api/ask/deck_permit").json()["answers"][0]["review_stale"] is True
        assert c.post(f"{base}/publish", json={"published": True}).status_code == 409
        assert c.delete(f"{base}/review").status_code == 401                     # removing a review needs a token too
        assert c.delete(f"{base}/review", headers={RV.TOKEN_HEADER: other["token"]}).json() == {
            "reviewed_by": None, "published": False, "removed_by": other["id"]}
        assert db.one(con, "SELECT action, reviewer FROM review_log ORDER BY id DESC LIMIT 1") == {
            "action": "unreview", "reviewer": other["id"]}
        assert c.post(f"{base}/publish", json={"published": False}).status_code == 200   # withdrawing always works
    assert "lexflow:va:deck_permit" not in LX.all_pages(con)
    # nothing in the API adds a reviewer to the list
    assert not [r for r in API.app.routes if "reviewer" in getattr(r, "path", "") and
                set(getattr(r, "methods", ())) & {"POST", "PUT", "PATCH", "DELETE"}]


def test_the_dashboard_box_waits_for_a_reviewer():
    js = (config.ROOT / "dashboard" / "app.js").read_text(encoding="utf-8")
    assert "disabled: !ok" in js and "needs a named reviewer" in js and "/review`" in js
    assert "text_hash: r.text_hash" in js and "review_stale" in js       # the review is for the text on screen
    assert "attested: attest.checked" in js and "I am a person, and I read this exact text against the law" in js
    # a reviewer is picked from the operator's list, never typed in: no name, role or date field
    assert 'api("/api/reviewers")' in js and "reviewer: pick.value" in js
    assert "Choose a reviewer from the list" in js and "lexflow reviewer add" in js
    # the reviewer's own token goes with the review, in the header the API reads, and is not kept in the browser
    assert '"X-Lexflow-Reviewer-Token": token.value.trim()' in js and "Your reviewer token" in js
    assert 'withToken("PUT"' in js and 'withToken("DELETE")' in js
    assert "lexflow cannot check that a reviewer is a person" in js
    card = js[js.index("function reviewCard"):js.index("// AskBench")]
    for gone in ("Reviewer's name", "Full name", "REVIEW_ROLES", "Reviewer's role", "Licensed in", "type: \"date\"",
                 "name: name.value", "role: role.value"):
        assert gone not in card, gone


def test_review_hash_prints_what_a_reviewer_records(capsys):
    from lexflow import cli
    assert cli.main(["review-hash", str(CURATED / "va" / "records.json"),
                     str(CURATED / "places" / "dc" / "washington.json")]) == 0
    out = capsys.readouterr().out
    assert f"text_hash {signoff.file_hash(_spec('va', 'records'))}  (the whole file)" in out
    assert "answers.records  text_hash " in out and "answers.business  text_hash " in out


# ------------------------------------------------------------------ row 12: builder notes on lexflow:method
def test_notes_keep_the_readers_part():
    note = ("Extension (B.4): the extra time is available only if the B.4 response is made within five working days, "
            "which the model reflects by reaching respond_extended only from a timely respond. The text says 'an "
            "additional seven work days' without saying whether they run from the end of the five-day period or "
            "from the B.4 response; the timer is a boundary event on respond_extended, so it runs from the B.4 "
            "response. Criminal investigative files (§ 2.2-3706.1) get 60 work days instead; the timer shows only "
            "the seven-day figure.")
    out = N.for_readers(note)
    assert out == ("Extension (B.4): The extra time is available only if the B.4 response is made within five working "
                   "days. The text says 'an additional seven work days' without saying whether they run from the end of "
                   "the five-day period or from the B.4 response. Criminal investigative files (§ 2.2-3706.1) get 60 "
                   "work days instead.")
    assert N.for_readers("The first response and the B.4 response rejoin as exclusive merges (join 'any').") is None
    plain = "No deadline for petitioning the Mayor or for suing is stated in these sections."
    assert N.for_readers(plain) == plain
    assert N.for_readers("'respond' stands for the whole answer under § 2-532(c)(1).", {"respond"}) is None
    assert N.split({"gaps": [note, plain], "reader_gaps": ["Own words."]}) == (["Own words."], [note])
    # a clause that says what the text leaves open keeps it, without the builder words after it
    assert N.for_readers("The printed text does not say what happens if it is late (penalties are elsewhere), so "
                         "the deadline's consequence is 'unstated' and a missed deadline rejoins the branch.") == \
        "The printed text does not say what happens if it is late (penalties are elsewhere)."
    # a note put in plain words in the curated file replaces the cut, and the full note stays for builders
    own = N.split({"gaps": [note, plain], "reader_notes": {"Extension (B.4)": "In plain words."}})
    assert own == (["In plain words.", plain], [note])
    assert N.stale_reader_notes([note, plain], {"Extension (B.4)": "x", "Gone": "y"}) == ["Gone"]


BUILDER_WORDS = re.compile(r"\blanes?\b|\bfires?\b|falls? through|table's (?:input|output)|\binputs?\b|\boutputs?\b|"
                           r"consequence ['‘\"“]|['‘\"“]unstated['’\"”]|\brouted\b|\bthe flow\b|\bactor\b|"
                           r"\banchor\b|\btask\b|\bmodell?ed\b|_[a-z]+_|local layer|\bcorpus\b|word budget", re.I)


def test_reader_notes_are_in_plain_words_and_keep_the_gaps():
    """Every curated model's notes, as its page shows them: no builder language (the verifier's list included),
    every plain-words override still opens exactly one note, and the open questions the cut used to lose stay."""
    readers = {}
    for path in sorted(CURATED.glob("*/*.json")):
        if path.parent.name == "places":
            continue
        spec = json.loads(path.read_text(encoding="utf-8"))
        facts = spec["facts"]
        assert N.stale_reader_notes(facts.get("gaps") or [], spec.get("reader_notes")) == [], path
        notes, _ = N.split({"gaps": facts.get("gaps"), "reader_gaps": spec.get("reader_gaps"),
                            "reader_notes": spec.get("reader_notes")}, facts)
        readers[f"{path.parent.name}.{path.stem}"] = notes
        for n in notes:
            assert not BUILDER_WORDS.search(n), (path.name, BUILDER_WORDS.search(n).group(0), n)
    text = {k: " ".join(v) for k, v in readers.items()}
    for model, kept in (
            ("va.records", "the text does not say whether the later duty to notify the requester of charges before a "
                           "search still applies to such requests"),          # the scholastic-records question
            ("va.records", "For the B.4 extension it is an inference: by then a written B.4 response"),
            ("fl.records", "must disclose the designee's identity to the requester"),
            ("il.records", "the text states no consequence for missing the counselor's 7 business days"),
            ("il.records", "this page treats that officer as part of the public body"),
            ("md.business", "the comparison table points to the limited partnership before the LLC"),
            ("tx.records", "the table goes straight to release"),
            ("wa.records", "may instead answer an unclear request"),
            ("ny.records", "where neither applies, § 89 says nothing about fees"),
            ("ca.records", "The '10 days' and '14 days' are not stated to be business days; lexflow counts them as "
                           "calendar days"),
            ("dc.records", "The text does not say that the Mayor loses the power to decide late"),
            ("ca.business", "The printed text does not say what happens if it is late")):
        assert kept in text[model], (model, kept)


def test_builder_language_moves_to_the_method_page(va_pages):
    pages = LX.all_pages(va_pages)
    model = _no_bpmn(pages["lexflow:va:records"])
    for term in ("respond_extended", "deemed_denied", "no_records_released", "boundary event", "join 'any'",
                 "exclusive merge", "hit policy", "DMN", "bpmnlint", "Petri", "===== Checks"):
        assert term not in model, term
    assert "an additional seven work days' without saying whether they run" in model     # the reader's caveat stays
    assert f"[[{LX.METHOD}#notes_for_builders|" in model
    method = pages[LX.METHOD]
    assert "==== va.records: " in method and "respond_extended" in method and "boundary event" in method
    assert "| [[lexflow:va:records|va.records]] | 23 | 0 |" in method                   # the machine checks, by model


def test_the_method_page_explains_licences_affiliation_and_corrections(va_pages, monkeypatch):
    monkeypatch.setattr(config, "CORRECTIONS", "")
    method = LX.all_pages(va_pages)[LX.METHOD]
    for must in ("What the checks do not prove", "Passing every check is not a legal review",
                 "Open US Law", "CC BY-NC 4.0", "LOCUS-v1", "CC0 1.0", "CourtListener", "allowed API usage policy",
                 "Census of Governments", "Public domain (US government work)",
                 "not affiliated with, or endorsed by, the Wikimedia Foundation",
                 "Corrections: <address to be set by the operator>", "Licences vary by source",
                 "does not mean its maker has reviewed or endorsed lexflow",
                 "**lexflow cannot check that a reviewer is a person**"):
        assert must in method, must
    assert "open-source" not in method.lower() and "open source" not in method.lower()


def test_the_method_page_says_what_was_checked_against_what(va_pages):
    method = LX.all_pages(va_pages)[LX.METHOD]
    # the snapshot is the release (with its date), not the page's date; quotes are matched to that copy
    assert "Open US Law's release v2026.09.1 of 30 September 2026" in method
    assert "the date on each page is when its quotes were matched to that copy" in method
    assert "a snapshot as of the date on the page" not in method
    assert "**Every quote matched to Open US Law's copy of the official text on <date>.**" in method
    # the drafting system is named once, not on every row; who did what is said
    assert method.count("claude-opus-5-5") == 1 and "every quote checked against open-us-law" not in method
    assert "| 10 October 2026 |" in method and "lexflow's software matched their quotes" in method
    # links, local pages and the diagram checks as they are
    assert "Every section links" not in method and "the other sections it cites are named, not linked" in method
    assert "compared each quote with the page it came from" not in method
    assert "the second AI pass is the only check" not in method
    assert ("lexflow's software does not match the words quoted from local pages, other offices' pages, city codes or "
            "regulations: for those, an AI verifier's check against the cited page is the only check") in method
    assert "must pass a diagram checker" not in method
    assert "Two are warnings" in method and "even if one of these checks fails or warns" in method
    assert "Today every model passes all of them, with no errors and no warnings." in method
    # who may be named as a reviewer: the operator's list, which lexflow cannot vouch for
    assert "lexflow refuses a reviewer whose name contains" not in method
    assert ("A page names a reviewer only from the list of reviewers that the operator of this lexflow copy keeps"
            in method)
    assert "and so vouches that each reviewer on it is a person with that role" in method
    assert "warns the operator when the name contains that of an AI system, which proves nothing either way" in method
    assert ("with a role from a fixed list (attorney, paralegal, law student, clerk, records officer, planner, "
            "municipal attorney, researcher, student, volunteer, other person)") in method
    # which quotes the software checks, and that the words quoted in notes are not among them
    assert "found every quoted phrase on the page" not in method
    assert ("the **step quotes** (the words of the law under each step), the **deadline quotes** (the words each time "
            "limit is read from) and the **law quotes** behind each decision table and each of its rows") in method
    assert "Words in quotation marks inside the notes on what the text leaves open are not checked" in method
    assert "Every step quote, deadline quote and law quote in a state process map must appear" in method
    assert "Quoted words in the notes are not checked by the software" in method
    assert "lexflow's notes for builders and its own day counts are left out of it" in method
    # local processes: the software's count and the AI verifier's are told apart
    assert ('"checked by an AI verifier against the cited page on <date>; not matched by lexflow\'s software"'
            in method)
    assert "a researched local process says that its quotes are not matched by lexflow's software" not in method
    assert "lexflow does not turn an AI system's count into \"Every quote matched\"" in method


def test_the_method_page_counts_a_warning_as_not_passing(va_pages):
    """"Today every model passes all of them" covers the two warning rules too: a warning is not a pass."""
    m = db.one(va_pages, "SELECT metrics FROM process_models WHERE model_id='va.records'")
    metrics = json.loads(m["metrics"])
    assert LX._passes(metrics) and not LX._passes(dict(metrics, lint_warnings=1))
    assert not LX._passes(dict(metrics, lint_errors=1)) and not LX._passes(dict(metrics, quote_misses=1))
    va_pages.execute("UPDATE process_models SET metrics=? WHERE model_id='va.records'",
                     (json.dumps(dict(metrics, lint_warnings=1)),))
    va_pages.commit()
    method = LX.all_pages(va_pages)[LX.METHOD]
    assert "Today every model passes" not in method
    assert "Today 0 of the 1 models pass all of them with no errors and no warnings." in method
    assert "| [[lexflow:va:records|va.records]] | 23 | 0 | 0 / 0 | 0 / 1 |" in method


def test_asked_pages_name_locus_rightly(con):
    row = dict(_asked(), local=json.dumps({"name": "Virginia", "locus": [{"header": "Sec. 5-1. Decks."}]}))
    page = LX.render_asked(con, row)
    assert "LOCUS-v1, LocalLaws' dataset of local ordinances (the Local Ordinance Corpus for the United States)" in page
    assert "Local Laws Observatory" not in page


# ------------------------------------------------------------------ the namespace rule for every writer
def test_the_publish_step_keeps_to_the_namespace_and_writes_nothing_without_the_corrections_address(va_pages,
                                                                                                    monkeypatch):
    from lexflow.pipeline import steps
    from lexflow.publish import dokuwiki as D
    saved = []

    class Wiki(D.DokuWiki):
        def whoami(self):
            return {"login": "bot"}

        def get_page(self, page):
            return None

        def call(self, method, **params):
            if not self.dry_run:
                saved.append(params.get("page") or params.get("media"))
            return True
    monkeypatch.setattr(D, "DokuWiki", Wiki)
    pages = sorted(LX.all_pages(va_pages))
    # every page links lexflow:method for corrections: while its address is the placeholder, not an address, or an
    # address that reaches no one (the .env.example value, a reserved name), nothing at all is written, a dry run
    # included, and one log line says why
    for value in ("", "<address to be set by the operator>", "TBD", "corrections at example dot org", "ftp://x.org",
                  "corrections@example.org", "you@example.com", "https://example.com/corrections",
                  "https://www.example.net/x", "fix@sub.example.org", "a@b.example", "a@lexflow.invalid",
                  "https://lexflow.test/report", "a@box.localhost", "https://printer.local/x", "http://localhost:8080/x",
                  "http://127.0.0.1/report", "https://10.0.0.7/corrections", "http://[::1]/x", "javascript:alert(1)",
                  # Re-check 4: special-use and private names, placeholders on placeholder domains
                  "corrections@localhost.localdomain", "a@router.home.arpa", "http://wiki.internal/r", "a@nas.lan",
                  "user@domain.com"):
        for dry in (False, True):
            monkeypatch.setattr(config, "CORRECTIONS", value)
            said = []
            out = steps.run_publish(va_pages, {"dry_run": dry}, said.append, lambda *_: None)
            assert saved == [] and out["written"] == [] and out["refused"] == pages, (value, dry)
            assert len(said) == 1 and said[0].startswith("publish refused: no page") and "LEXFLOW_CORRECTIONS" in said[0]
            assert LX.CORRECTIONS_PLACEHOLDER in LX.all_pages(va_pages)[LX.METHOD]
    monkeypatch.setattr(config, "CORRECTIONS", "corrections@example.org")
    assert "the example value from .env.example" in LX.corrections_problem()
    assert "reserved for examples and tests" in LX.corrections_problem("you@example.com")
    assert "an IP address, not a domain name readers can reach" in LX.corrections_problem("http://127.0.0.1/x")
    # the right reason for a local URL, not "not an e-mail address or an http(s) URL"
    for value in ("http://localhost:8080/report", "http://localhost/", "corrections@localhost",
                  "corrections@localhost.localdomain", "https://x.localhost/r"):
        why = LX.corrections_problem(value)
        assert "a name for the operator's own machine that no reader can reach" in why and "not an e-mail" not in why
    for value in ("http://0x7f000001/", "http://2130706433/", "http://0177.0.0.1/"):
        assert "an IP address" in LX.corrections_problem(value), value
    for value in ("a@router.home.arpa", "http://wiki.internal/r", "a@nas.lan", "a@mail.corp", "http://abc.onion/",
                  "https://x.alt/", "a@pc.localdomain", "a@printer.local"):
        assert "special-use or private name" in LX.corrections_problem(value), value
    for value in ("http://lvh.me/report", "http://127.0.0.1.nip.io/report", "http://192.168.1.10.sslip.io/report"):
        assert "points back to the operator's machine" in LX.corrections_problem(value), value
    for value in ("user@domain.com", "name@email.com", "foo@bar.com", "test@test.com", "your.name@yourdomain.com",
                  "corrections@your-domain.org"):
        assert "a placeholder address" in LX.corrections_problem(value), value
    # a real-looking address on a real domain is accepted: the operator answers for whether anyone reads it
    for value in ("corrections@email.com", "fixes@lexipedia.xyz", "https://lexipedia.xyz/report", "https://123.com/x"):
        assert LX.corrections_problem(value) is None, value
    env = (config.ROOT / ".env.example")
    if env.exists():                                             # the refused example is the one .env.example shows
        assert f"# LEXFLOW_CORRECTIONS={LX.ENV_EXAMPLE_CORRECTIONS}" in env.read_text(encoding="utf-8")
    assert steps.st_publish(va_pages)["detail"].startswith("Set DOKUWIKI_URL")      # no wiki configured here
    monkeypatch.setattr(config, "DOKUWIKI_URL", "http://example.invalid")
    monkeypatch.setattr(config, "DOKUWIKI_TOKEN", "x")
    assert "LEXFLOW_CORRECTIONS" in steps.st_publish(va_pages)["detail"]
    # an e-mail address or a URL on a real domain: every page is written, lexflow:method gives it, and the log names
    # it before anything is written (a dry run too), so the operator sees what will be printed
    for value in ("corrections@lexipedia.xyz", "https://lexipedia.xyz/lexflow-corrections"):
        for dry in (True, False):
            saved.clear()
            monkeypatch.setattr(config, "CORRECTIONS", value)
            said = []
            out = steps.run_publish(va_pages, {"dry_run": dry}, said.append, lambda *_: None)
            assert out["refused"] == [] and (sorted(saved) == pages if not dry else saved == [])
            assert f"Corrections: {value}" in LX.all_pages(va_pages)[LX.METHOD]
            # the first line names the address, before the wiki is signed in to or any page is written
            assert said[0] == (f"{LX.METHOD} {'would print' if dry else 'prints'} 'Corrections: {value}': readers "
                               f"will write to {value}"), said[:3]
    assert "LEXFLOW_CORRECTIONS" not in steps.st_publish(va_pages)["detail"]
    assert 'CORRECTIONS = _env("LEXFLOW_CORRECTIONS")' in (config.ROOT / "lexflow" / "config.py").read_text(
        encoding="utf-8")
    # a page id outside lexflow: stops the run before anything is written
    saved.clear()
    monkeypatch.setattr(LX, "all_pages", lambda con: {"lexflow:a": "x", "start": "y"})
    with pytest.raises(D.NamespaceError, match="refusing to write start"):
        steps.run_publish(va_pages, {}, lambda *_: None, lambda *_: None)
    assert saved == []


def test_the_legacy_writer_goes_through_the_same_namespace_rule(monkeypatch, capsys):
    from lexflow import gold
    from lexflow.publish import dokuwiki as D
    wiki = D.DokuWiki("http://example.invalid", dry_run=True)
    for bad in ("process:va:albemarle_county:17-211", "law:va:17-211", "start"):
        with pytest.raises(D.NamespaceError):
            wiki.save_page(bad, "x")
    with pytest.raises(D.NamespaceError):
        wiki.save_media("process:va:x.bpmn", b"x")
    wiki.save_page("lexflow:va:records", "x")
    assert [c[1]["page"] for c in wiki.calls] == ["lexflow:va:records"]
    # scripts/build_all.py --publish refuses before it builds anything
    spec = importlib.util.spec_from_file_location("build_all", config.ROOT / "scripts" / "build_all.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    monkeypatch.setattr(gold, "ALL", {"boom": lambda: (_ for _ in ()).throw(AssertionError("built a model"))})
    with pytest.raises(SystemExit) as e:
        mod.main(["--publish"])
    assert e.value.code == 2
    assert "--publish is refused" in capsys.readouterr().err


# ------------------------------------------------------------------ the third round (verify-gate0.md, Re-check 2)
def _reader_notes():
    """Every curated model's notes as its page shows them, with the model's own sections."""
    out = {}
    for path in sorted(CURATED.glob("*/*.json")):
        if path.parent.name == "places":
            continue
        spec = json.loads(path.read_text(encoding="utf-8"))
        facts = spec["facts"]
        notes, _ = N.split({"gaps": facts.get("gaps"), "reader_gaps": spec.get("reader_gaps"),
                            "reader_notes": spec.get("reader_notes")}, facts)
        out[f"{spec['state']}.{spec['question']}"] = (notes, spec.get("sections") or [])
    return out


def _law_text(state):
    d = json.loads((config.ROOT / "fixtures" / "statutes" / f"{state}_sections.json").read_text(encoding="utf-8"))
    return {s["citation"]: s["text"] for s in d["sections"]}


def _plain(text):
    text = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"\s+", " ", text).strip().lower()


NOTE_QUOTE = re.compile(r"“([^”]+)”|\"([^\"]+)\"|(?<![A-Za-z])'([^']+?)'(?![A-Za-z])|‘([^’]+)’")
TAIL = re.compile(r"([\w.\-/]+)$")


def test_words_quoted_in_reader_notes_are_the_cited_sections_words():
    """The software checks step, deadline and law quotes, not the notes (the method page says so); so every quoted
    fragment in a reader note was read against the model's sections, and is in one of them word for word.  Where
    the words were lexflow's own, the quotation marks went."""
    seen = 0
    for model, (notes, sections) in _reader_notes().items():
        own = {TAIL.search(c).group(1) for c in sections}
        texts = [_plain(t) for c, t in _law_text(model.split(".")[0]).items() if TAIL.search(c).group(1) in own]
        for note in notes:
            for m in NOTE_QUOTE.finditer(note):
                q = _plain(next(g for g in m.groups() if g)).rstrip(".,;:")
                seen += 1
                assert any(q in t for t in texts), (model, q, note[:120])
    assert seen >= 80
    every = " ".join(n for notes, _ in _reader_notes().values() for n in notes)
    for gone in ("'no formation filing'", "'See § 29-102.12'", "'no record located'", "'certificate of organization'",
                 "'See 1-204'", "'the clerk'", "'otherwise addresses'", "'effective until January 1, 2027'",
                 "'uses a trade name'"):
        assert gone not in every, gone
    assert "'cure or otherwise address the failure'" in " ".join(_reader_notes()["oh.records"][0])
    assert "'transacts business in this state under any trade name'" in " ".join(_reader_notes()["wa.business"][0])


def test_reader_notes_keep_the_laws_unit_and_no_builder_leftovers():
    notes = _reader_notes()
    # "five-day" drops the unit where the law says working or business days (NC's § 55D-15(c) says "five days")
    for model in ("va.records", "ny.records", "oh.records", "wa.records"):
        assert not [n for n in notes[model][0] if "five-day" in n], model
    assert "the end of the five-working-day period" in " ".join(notes["va.records"][0])
    assert "a missed five-business-day response" in " ".join(notes["wa.records"][0])
    for model, (ns, _) in notes.items():
        for n in ns:
            for left in ("scored separately", "outside the sections used", "not cited in sections"):
                assert left not in n, (model, left, n[:120])


def test_place_caveats_speak_of_lexflow_not_of_an_unnamed_i(dc_pages):
    """Next to "drafted with an AI system", an unnamed "I" reads like a person who checked: the place files say
    "lexflow did not verify" and "the research checked".  Quoted words stay as the source wrote them."""
    def strings(value, key=None):
        if isinstance(value, dict):
            for k, v in value.items():
                yield from strings(v, k)
        elif isinstance(value, list):
            for v in value:
                yield from strings(v, key)
        elif isinstance(value, str) and key not in ("quote", "url", "value"):
            yield value
    for name in ("dc/washington", "va/charlottesville"):
        spec = json.loads((CURATED / "places" / f"{name}.json").read_text(encoding="utf-8"))
        for s in strings(spec.get("answers")):
            assert not re.search(r"\b(?:I|I'm|I've|I'd|me|my|myself)\b", s), (name, s[:120])
    dc = json.dumps(json.loads((CURATED / "places" / "dc" / "washington.json").read_text(encoding="utf-8")),
                    ensure_ascii=False)
    # Re-check 5: the caveats describe the place, not the drafting ("the research did not fetch ..."), and keep
    # each warning
    for gone in ("the research", "lexflow did not verify"):
        assert gone not in dc, gone
    for said in ("Those are not checked here.", "the portal's own pages are not described here",
                 "so it is confirmed only through the dc.gov/foia link", "the DLCP fee page cited here",
                 "shows only the title 'Public Portal'", "that are not covered here"):
        assert said in dc, said
    cville = (CURATED / "places" / "va" / "charlottesville.json").read_text(encoding="utf-8")
    assert "The home-occupation standards are in the city's Development Code" in cville     # the place (Re-check 4)
    place = LX.all_pages(dc_pages)["lexflow:dc:washington_dc:records"]
    assert "Those are not checked here." in place and "I did not verify" not in place and "I confirmed" not in place
    assert "the research" not in place


def test_pages_embed_the_diagram_without_the_builders_layer(va_pages):
    """DokuWiki indexes the page source: the embedded map keeps the diagram and its timers (named in the law's
    words) and drops lex:gap and every other builder-only extension, attribute and machine duration."""
    from lexflow import validate as V
    pages = LX.all_pages(va_pages)
    stored = db.one(va_pages, "SELECT bpmn FROM process_models WHERE model_id='va.records'")["bpmn"]
    assert "<lex:gap>" in stored and "camunda:decisionRef" in stored and ">P5D<" in stored    # the model keeps them
    for pid, text in pages.items():
        for x in re.findall(r"<bpmnio[^>]*>\n(.*?)\n</bpmnio>", text, flags=re.S):
            for gone in ("lex:", "xmlns:lex", "extensionElements", "spiffworkflow", "camunda", "timeDuration",
                         "checked by the", "fees_paid"):
                assert gone not in x, (pid, gone)
            assert not re.search(r">P\d+[DWMY]<", x), pid
            assert V.xsd_errors(x) == [], pid                         # still valid BPMN 2.0
    bpmn = _bpmn(pages["lexflow:va:records"])
    assert set(_timer_names(bpmn)) == {"“within five working days”", "“an additional seven work days”"}
    assert bpmn.count("<bpmn:timerEventDefinition") == 2 and "<bpmndi:BPMNShape" in bpmn     # timers and diagram
    assert "Subsection E: failure to respond" not in bpmn                 # the gap is on the page, in plain words
    assert "Subsection E: failure to respond" in _no_bpmn(pages["lexflow:va:records"])
    # an asked answer's draft map gets the same copy
    xml = ('<?xml version="1.0" encoding="UTF-8"?><bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/'
           '20100524/MODEL" xmlns:lex="https://lexipedia.xyz/ns/lex/1.0" xmlns:xsi="http://www.w3.org/2001/'
           'XMLSchema-instance" id="d" targetNamespace="x"><bpmn:process id="p"><bpmn:task id="respond" name="Respond">'
           '<bpmn:extensionElements><lex:gap>a builder note</lex:gap></bpmn:extensionElements></bpmn:task>'
           '<bpmn:boundaryEvent id="respond_deadline" name="5 business days" attachedToRef="respond">'
           '<bpmn:timerEventDefinition id="t"><bpmn:timeDuration xsi:type="bpmn:tFormalExpression">P5D'
           '</bpmn:timeDuration></bpmn:timerEventDefinition></bpmn:boundaryEvent></bpmn:process></bpmn:definitions>')
    out = LX.reader_bpmn(xml, _facts("va", "records"))
    assert "a builder note" not in out and "P5D" not in out and "xmlns:lex" not in out
    assert 'name="“within five working days”"' in out and '<bpmn:timerEventDefinition id="t"/>' in out


DESIGN_ADDRESSES = {           # e-mail-shaped strings in docs/design that are not made-up examples
    "CDB.BuildingCodes@illinois.gov": "the Illinois Capital Development Board's office mailbox, cited as a source",
    "leap@leg.wa.gov": "the Washington LEAP office's mailbox, cited as a source",
    "records@1760100000.txt": "a file name",
    "xml_usc26@119-102.zip": "a file name",
    # values verify-gate0.md (Re-check 4) tried as LEXFLOW_CORRECTIONS: the check's inputs, not anyone's address
    **{a: "a value Re-check 4 tried as LEXFLOW_CORRECTIONS" for a in (
        "a@b.co", "changeme@lexflow.org", "corrections@lexipedia.xyz", "corrections@localhost.localdomain",
        "corrections@your-domain.org", "foo@bar.com", "name@email.com", "noreply@lexipedia.xyz", "test@test.com",
        "todo@todo.com", "user@domain.com", "user@example.edu", "x@y.zz", "your.name@yourdomain.com")},
}


def test_design_notes_write_example_addresses_and_numbers_on_reserved_ones():
    """Made-up e-mail addresses go on example.org or example.com, and made-up phone numbers in 555-0100 to
    555-0199, never on a real government's domain or exchange."""
    email = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
    phone = re.compile(r"(?<![\w/.-])(?:\+?1[-. ])?\(?\d{3}\)?[-. ]\d{3}[-. ]\d{4}(?![\w-])")
    found = 0
    for path in sorted((config.ROOT / "docs" / "design").glob("*.md")):
        text = path.read_text(encoding="utf-8")
        for a in email.findall(text):
            found += 1
            assert re.search(r"@(?:[A-Za-z0-9-]+\.)*example\.(?:org|com)$", a, re.I) or a in DESIGN_ADDRESSES, \
                (path.name, a)
        for n in phone.findall(text):
            assert re.sub(r"\D", "", n)[-7:].startswith("55501"), (path.name, n)
    assert found
    lab = (config.ROOT / "docs" / "design" / "verify-lab.md").read_text(encoding="utf-8")
    assert "charlottesville.gov" not in lab and "will.page@example.org" in lab and "foia@example.org" in lab


def test_the_ai_name_check_is_a_warning_the_operator_overrides(con, capsys):
    """A list of AI names can never prove that a reviewer is a person, so it is not a gate: at `reviewer add` it is
    a warning, and the operator confirms that the reviewer is a person (--confirm-person) or does not add them."""
    from lexflow import cli
    from lexflow import reviewers as RV
    for name in AI_NAMES + RECHECK_ACCEPTED + MORE_AI_NAMES:     # still flagged, in any case or spelling
        assert signoff.is_ai_name(name), name
    for name in ("Cʟaude", "ᴄlaude", "Ϲlaude", "Ꮯlaude",       # look-alikes Re-check 3 found
                 "Clɑude", "ɡemini", "Cօpilot", "Llɑma"):         # and Re-check 4
        assert signoff.is_ai_name(name), name
    for name in PEOPLE:
        assert not signoff.is_ai_name(name), name
    # people whose names contain a product's: a warning the operator overrides, not a refusal
    for name in ("Wenxin Li", "Marie Lechat", "Qianwen Zhang", "A. I. Okafor", "Ben Bot"):
        with pytest.raises(RV.ReviewerError, match="--confirm-person"):
            RV.add(con, name, "researcher", added_by="operator")
        assert RV.add(con, name, "researcher", added_by="operator", confirm_person=True)["name"] == name
        assert cli.main(["reviewer", "add", name, "--role", "student", "--added-by", "operator"]) == 1
        assert "--confirm-person" in capsys.readouterr().err
        assert cli.main(["reviewer", "add", name, "--role", "student", "--added-by", "operator",
                         "--confirm-person"]) == 0
        assert "contains the name of an AI system" in capsys.readouterr().out
    roster = RV.roster(con)
    assert {r["name"] for r in roster.values()} == {"Wenxin Li", "Marie Lechat", "Qianwen Zhang", "A. I. Okafor",
                                                    "Ben Bot"}
    rev = {"reviewer": next(i for i, r in roster.items() if r["name"] == "Wenxin Li" and r["role"] == "researcher"),
           "date": "2026-10-01", "attested": True}
    assert signoff.line(signoff.person(rev, roster)) == "Reviewed by Wenxin Li, researcher, on 1 October 2026"
    # the module says what the check is, and no longer that a name check keeps AI systems out
    doc = signoff.__doc__
    assert "Reviewers come from a list the operator keeps" in doc and "proves nothing either way" in doc
    assert "is refused" not in doc.split("A name is cleaned")[1].split("``is_ai_name``")[1]


CLEAN = {"Ａｎａ Ｖｉｌｌａｍａｒ": "Ana Villamar", "  Ana   Villamar ": "Ana Villamar", "Ana\tVillamar": "Ana Villamar",
         "Mary-Jane O’Neil": "Mary-Jane O'Neil", "José Pérez": "José Pérez", "J.D. Okafor": "J.D. Okafor",
         "李明": "李明", "Клод Петров": "Клод Петров", "Ai Weiwei": "Ai Weiwei", "P. I. Moreno": "P. I. Moreno",
         "Ruth Watson": "Ruth Watson", "Ines Law": "Ines Law", "Omar Judge": "Omar Judge", "Hon Wai Ming": "Hon Wai Ming",
         "Ana Villamar-Ríos": "Ana Villamar-Ríos", "Nguyễn Thị Lan": "Nguyễn Thị Lan",
         "देवनागरी नाम": "देवनागरी नाम", "山田たろう": "山田たろう", "김민준": "김민준",
         "Γιώργος Παπαδόπουλος": "Γιώργος Παπαδόπουλος", "محمد علي": "محمد علي", "Anna de Bar": "Anna de Bar"}


NOT_NAMES = ("", "A", "..", "12", "N/A", "NA", "n.a.", "Anonymous", "Reviewer", "test", "Test User", "Staff", "Unknown",
             "Admin", "Legal team", "Jane Doe", "Ana Villamar, attorney licensed in Virginia",
             "Ana Villamar attorney licensed in all fifty states", "Attorney Ana Villamar", "Ana Villamar Esq.",
             "Dr. Ana Villamar", "Ana Villamar J.D.", "Ana Villamar PhD", "Ana Villamar (attorney)", "Ana_Villamar",
             "Ana@Villamar", "Ana Villamar 3", "-Ana Villamar", "Ana Villamar law student", "Records Officer Smith",
             "Ana <b>Villamar</b>", "x" * 81, "Ana " * 750,
             # invisible characters are refused, not removed (Re-check 3 removed them)
             "Ana​ Villamar", "Ana Villamar ‮edualC‬", "⁦Ana Villamar⁩", "Ana­Villamar")


def test_reviewer_names_are_cleaned_when_added(con):
    """NFKC, bidirectional and zero-width controls removed, 2 to 80 characters of letters (any script), spaces,
    hyphens, apostrophes and full stops, no role or credential words, no placeholders."""
    from lexflow import reviewers as RV
    for raw, clean in CLEAN.items():
        got, bad = signoff.clean_name(raw)
        assert (got, bad) == (clean, []), (raw, got, bad)
    for raw in NOT_NAMES:
        assert signoff.clean_name(raw)[1], raw
    # a name with an invisible or reversing character is refused: a reversed name never shows as "Claude"
    with pytest.raises(RV.ReviewerError, match="no invisible characters"):
        RV.add(con, "Ana Villamar ‮edualC‬", "researcher", added_by="operator")
    row = RV.add(con, "Ana Villamar Edual", "researcher", added_by="operator")
    for raw in ("Ana Villamar, attorney licensed in Virginia", "N/A", "Reviewer", "x" * 3000):
        with pytest.raises(RV.ReviewerError):
            RV.add(con, raw, "other person", added_by="operator")
    # the role is from the list, and licensed_in only for an attorney's role, naming a state
    for role, lic in (("AI attorney", None), ("lawyer", None), ("paralegal", "va"), ("attorney", "Narnia"),
                      ("other person", "Virginia")):
        with pytest.raises(RV.ReviewerError):
            RV.add(con, PERSON, role, licensed_in=lic, added_by="operator")
    with pytest.raises(RV.ReviewerError, match="added-by"):
        RV.add(con, PERSON, "researcher", added_by=" ​ ")
    a = RV.add(con, PERSON, "Municipal  Attorney", licensed_in="va", added_by="operator")
    assert (a["role"], a["licensed_in"], a["added_by"]) == ("municipal attorney", "Virginia", "operator")
    assert re.fullmatch(r"rv-[0-9a-f]{8}", a["id"]) and a["added_at"] and a["removed_at"] is None
    with pytest.raises(RV.ReviewerError, match="already on the list"):
        RV.add(con, PERSON, "municipal attorney", licensed_in="Virginia", added_by="operator")
    # a row written past the list's own checks (by hand, or by other code through sync) is not shown
    db.upsert(con, "reviewers", [{"id": "rv-00000bad", "name": "Ana Villamar, attorney licensed in all 50 states",
                                  "role": "other person", "added_by": "x", "added_at": db.now()},
                                 {"id": "rv-00000bae", "name": "Claude‮", "role": "attorney", "added_by": "x",
                                  "added_at": db.now()},
                                 {"id": "rv-00000baf", "name": PERSON, "role": "AI attorney", "added_by": "x",
                                  "added_at": db.now()}])
    con.commit()
    assert set(RV.roster(con)) == {row["id"], a["id"]}


def test_the_reviewer_list_is_kept_with_the_cli(con, capsys):
    from lexflow import cli
    from lexflow import reviewers as RV
    assert cli.main(["reviewer", "add", PERSON, "--role", "attorney", "--licensed-in", "va",
                     "--added-by", "operator"]) == 0
    out = capsys.readouterr().out
    rid = re.search(r"added (rv-[0-9a-f]{8}): Ana Villamar, attorney licensed in Virginia", out).group(1)
    assert "You vouch that this reviewer is a person: lexflow cannot check it" in out
    # the token is printed once and only its hash is stored
    token = re.search(r"reviewer token \(shown this once; lexflow keeps only its hash\): (rv-[0-9a-f]{8}\.\S+)",
                      out).group(1)
    stored = db.one(con, "SELECT token_hash FROM reviewers WHERE id=?", rid)["token_hash"]
    assert token.startswith(rid + ".") and token not in stored and stored.startswith("scrypt$16384$8$1$")
    assert RV.token_fits(token, stored) and not RV.token_fits(token + "x", stored)
    assert RV.holder(con, token)["id"] == rid and RV.holder(con, token[:-2]) is None
    assert cli.main(["reviewer", "token", rid]) == 0
    fresh = re.search(r"reviewer token \(shown this once; lexflow keeps only its hash\): (\S+)",
                      capsys.readouterr().out).group(1)
    assert fresh != token and RV.holder(con, token) is None and RV.holder(con, fresh)["id"] == rid
    assert cli.main(["reviewer", "add", "Jane Roe, attorney licensed in Virginia", "--role", "other person",
                     "--added-by", "operator"]) == 1
    assert "no role or credential words" in capsys.readouterr().err
    assert cli.main(["reviewer", "add", "Lee Park", "--role", "paralegal", "--licensed-in", "va",
                     "--added-by", "operator"]) == 1
    assert "licensed_in is for an attorney" in capsys.readouterr().err
    assert cli.main(["reviewer", "list"]) == 0
    listed = capsys.readouterr().out
    assert f"{rid}  {PERSON}  attorney licensed in Virginia  added by operator on " in listed
    assert "1 reviewer on the list" in listed
    assert cli.main(["reviewer", "remove", rid]) == 0
    assert "Not yet reviewed by a person" in capsys.readouterr().out
    assert RV.roster(con) == {} and cli.main(["reviewer", "remove", rid]) == 1
    capsys.readouterr()
    assert cli.main(["reviewer", "list", "--all"]) == 0
    assert "removed on " in capsys.readouterr().out
    row = db.one(con, "SELECT * FROM reviewers WHERE id=?", rid)
    assert row["removed_at"] and row["updated_at"] == row["removed_at"] and row["token_hash"] is None
    assert RV.holder(con, fresh) is None and cli.main(["reviewer", "token", rid]) == 1
    assert cli.main(["reviewer", "remove", "rv-deadbeef"]) == 1


def test_the_reviewer_list_is_this_copys_own(con, caplog):
    """Re-check 4: once a database was shared, whoever could write its reviewers table could add a "Claude" or
    rename a reviewer on every page they signed.  The list is now this copy's own: it is not synced, a pull never
    touches it, and a pulled review naming an id that is not on this copy's list counts as not reviewed, with a log
    line."""
    import logging
    from lexflow import reviewers as RV
    assert "reviewers" not in db.SYNCED and "review_log" not in db.SYNCED and db.LOCAL_KEYS["reviewers"] == ("id",)
    assert not any("reviewers" in s or "review_log" in s for s in T.remote_schema())
    assert not any("reviewers" in m for m in T.remote_migrations())
    who = _listed(con)

    class Remote:
        def __init__(self):
            self.sent = []

        def pipeline(self, statements):
            self.sent += statements
            return [{"cols": [], "rows": [], "affected": 0} for _ in statements]

        def query(self, sql, *args):
            return []
    r = Remote()
    T.push(con, r, log=lambda *_: None)                              # every shared table, all states
    assert r.sent and not any("reviewers" in s or "review_log" in s for s, _ in r.sent)
    # a pull of everything reads no reviewer table, so a row added or renamed elsewhere never arrives
    pulled = _Remote(con, [])
    T.pull(con, pulled, log=lambda *_: None)
    assert pulled.selects and not any("reviewers" in s for s in pulled.selects)
    # an answer signed elsewhere, by someone this copy's list does not hold, arrives with its review: the page does
    # not name anyone, and a log line says why
    row = _asked()
    rev = _signed(row, {"reviewer": "rv-0abc1234", "date": "2026-10-09", "attested": True})
    db.upsert(con, "asked_answers", [dict(row, reviewed_by=rev, origin="another machine")])
    con.commit()
    with caplog.at_level(logging.WARNING, logger="lexflow.signoff"):
        pages = LX.all_pages(con)
    assert "lexflow:va:deck_permit" not in pages
    assert any("rv-0abc1234" in m and "not on this copy's reviewer list" in m and "not reviewed" in m
               for m in caplog.messages)
    # the same answer signed by someone on this copy's list is named, from this copy's row, once this copy has
    # recorded that review (Re-check 5: a review that arrives through sync names no one, whoever it names)
    _record(con, row, _signed(row, _review(who, "2026-10-09")))
    assert f"Reviewed by {PERSON}, researcher" in LX.all_pages(con)["lexflow:va:deck_permit"]
    assert set(RV.roster(con)) == {who["id"]}


def test_the_docs_say_the_operator_vouches_for_each_reviewer(va_pages):
    method = LX.all_pages(va_pages)[LX.METHOD]
    readme = (config.ROOT / "README.md").read_text(encoding="utf-8") if (config.ROOT / "README.md").exists() else None
    core = (config.ROOT / "docs" / "core.md").read_text(encoding="utf-8")
    for text in [method, core] + ([readme] if readme else []):
        flat = " ".join(text.split())
        assert "vouches" in flat and "cannot check that a reviewer is a person" in flat
    for text in [core] + ([readme] if readme else []):          # where the operator reads how to keep the list
        assert "lexflow reviewer add" in text and "lexflow reviewer remove" in text
    if readme:
        flat = " ".join(readme.split())
        assert "A name containing the name of an AI system, model family, assistant or agent product is refused" \
            not in flat
        assert "`name`, a `role` from the list" not in flat
    # Re-check 4: the claims say what the code does, and that the operator answers for the rest
    flat_method = " ".join(method.split())
    assert "The list is this copy's own: it is not shared with other copies" in flat_method
    assert "Those lists catch only what they hold, and the operator answers for every name on the list" in flat_method
    assert "carries their own statement" not in flat_method and "with the reviewer's own token" in flat_method
    assert "no role or credential words and no placeholders such as" not in flat_method
    assert "the Code of Virginia or the D.C. Code" in flat_method
    for text in [core] + ([readme] if readme else []):
        flat = " ".join(text.split())
        assert "not synced" in flat and "shared through sync like the other tables" not in flat
        assert "the operator answers for every name on the list" in flat
        assert "X-Lexflow-Reviewer-Token" in flat and "lexflow reviewer token" in flat and "127.0.0.1" in flat
        assert "with no role or credential words and no placeholders" not in flat
        assert "bidirectional and zero-width controls are removed" not in flat
    assert "readers can reach the publish step writes" not in " ".join(core.split())
    assert "the operator answers for that" in " ".join(core.split())
    if readme:
        flat = " ".join(readme.split())
        assert "every quote matched to Open US Law's copy of the official text" in flat
        assert "every quote matched to the official text" not in flat
        assert "the reviewer's own statement" not in flat


def test_the_method_page_opens_with_its_own_three_part_label(va_pages):
    method = LX.all_pages(va_pages)[LX.METHOD]
    head = method.split("\n")
    assert head[0] == "====== How lexflow pages are made ======"
    assert head[2] == ("**Drafted with an AI system from lexflow's code and records · Quotes on this page are not "
                       "matched by lexflow's software · Not yet reviewed by a person**")
    assert LABEL.search(method)
    assert "Every lexflow page, this one included, opens with three facts" in method


def _proc(quotes):
    """A researched process with one quote from each place: legal_basis, steps, fees and escalation."""
    return {"title": "Ask for a record", "researched": "2026-10-09", "verified": True,
            "legal_basis": [{"level": "state", "citation": c, "url": u, "quote": q} for c, u, q in quotes],
            "steps": [{"step": "Ask", "source": "https://www.charlottesville.gov/foia", "quote": "Submit a request online"}],
            "fees": [{"item": "Copies", "basis": "https://www.charlottesville.gov/fees", "quote": "10 cents a page"}],
            "escalation": [{"trigger": "No answer", "basis": "12VAC5-105-30(A); Va. Code § 2.2-3704(B)",
                            "quote": "a rule the regulation states"}],
            "sources": [{"url": "https://www.charlottesville.gov/foia", "retrieved": "2026-10-09"}],
            "checks": {"verified_by": "an AI verifier", "date": "2026-10-10", "quotes_checked": 6,
                       "quotes_confirmed": 5}}


def _cache_page(url, text, **kw):
    """A page as lexflow's quote fetch caches it (lexflow/municipal/quotes.py)."""
    from lexflow.municipal import quotes as Q
    Q._save({"url": Q.key(url), "via": kw.get("via", "live"), "fetched": kw.get("fetched", "2026-10-11"),
             "capture": kw.get("capture"), "status": 200, "error": None, "text": text})


LOCAL_LABEL = re.compile(r"\*\*\d+ of \d+ quotes? matched by lexflow's software[^·]* · Drafted with an AI system · "
                         r"(?:Not yet reviewed by a person|Reviewed by [^*]+)\*\*")


def test_local_process_pages_count_only_lexflows_own_match(con, va_statutes, tmp_path, monkeypatch):
    """Re-check 5: every quote of a researched local process is matched by lexflow's software, to Open US Law's copy
    of the Code of Virginia or to the page it cites (fetched and cached by lexflow/municipal/quotes.py); the label
    gives that count, never an AI verifier's, and a quote that did not match keeps the file from counting as
    verified."""
    from lexflow.municipal import places
    from test_places_strategies import _govs
    _govs(con)
    law = _law_text("va")["Va. Code Ann. § 2.2-3704"]
    good = " ".join(law.split()[10:22])
    _cache_page("https://www.charlottesville.gov/foia", "<p>You may Submit a request online.</p>")
    _cache_page("https://www.charlottesville.gov/fees", "Copies are 10 cents a page.", via="archive",
                capture="20260801000000")
    spec = _proc([("Va. Code § 2.2-3704(B)", "https://law.lis.virginia.gov/vacode/2.2-3704/", good),
                  ("Va. Code § 2.2-3704(B)", "https://law.lis.virginia.gov/vacode/2.2-3704/", "words not in the law"),
                  ("City Code § 4-37(a)", "https://library.municode.com/x", "a city code's words")])
    qc = places.check_quotes(spec, "va", "2026-10-11")
    assert (qc["quotes"], qc["matched"], qc["by_code"], qc["by_page"], qc["by_archive"]) == (6, 3, 1, 2, 1)
    assert qc["hash"] == signoff.text_hash(spec) and qc["code"] == "Code of Virginia"
    assert [x["where"] for x in qc["unmatched"]] == ["legal_basis[1]", "legal_basis[2]", "escalation[0]"]
    text = LX.local_check(spec, ["2026-10-10"], qc)
    assert text == ("3 of 6 quotes matched by lexflow's software: 1 to Open US Law's copy of the Code of Virginia, 2 to "
                    "the cited pages (1 from an Internet Archive copy) on 11 October 2026; 3 not matched (listed below)")
    assert "Every quote" not in text and "verifier" not in text
    assert not places.is_verified(spec, qc)
    # loaded from a file: the check is stored with the hash of that file, and the page made anyway uses it
    (tmp_path / "places" / "va" / "charlottesville").mkdir(parents=True)
    body = dict(spec, place="va:charlottesville", process="records_request")
    (tmp_path / "places" / "va" / "charlottesville" / "records_request.json").write_text(json.dumps(body),
                                                                                       encoding="utf-8")
    monkeypatch.setattr(places, "PLACES_DIR", tmp_path / "places")
    places.load_processes(con, log=lambda *_: None)
    row = db.one(con, "SELECT * FROM place_processes")
    stored = json.loads(row["quote_check"])
    assert row["verified"] == 0 and (stored["quotes"], stored["matched"]) == (6, 3)
    assert "lexflow:va:charlottesville:records_request" not in LX.all_pages(con)
    g = db.one(con, "SELECT * FROM governments WHERE name='City of Charlottesville'")
    page = LX.render_local_process(con, g, {**row, "spec": body})
    assert LOCAL_LABEL.search(page) and "Every quote" not in page and "AI verifier" not in page
    assert "===== Quotes not matched =====" in page and "“words not in the law”" in page
    # a stored check for another version of the file is not used: the page matches the quotes again
    forged = {**row, "spec": body, "quote_check": json.dumps(dict(stored, matched=6, hash="0" * 64))}
    assert "3 of 6 quotes matched by lexflow's software" in LX.render_local_process(con, g, forged)


def test_a_researched_charlottesville_process_never_says_every_quote_matched(con, va_statutes, tmp_path,
                                                                             monkeypatch):
    """The researched Charlottesville files (read here, never changed), loaded with no page read yet by lexflow's
    quote fetch: none counts as verified, each says why, and a page made anyway lists the quotes not matched; no
    page gives an AI verifier's count or says "Every quote"."""
    from lexflow.municipal import places
    from test_places_strategies import _govs
    _govs(con)
    src = CURATED / "places" / "va" / "charlottesville"
    files = []
    for p in sorted(src.glob("*.json")):
        try:                                     # another workflow may be writing these: skip a half-written one
            if json.loads(p.read_text(encoding="utf-8")).get("verified"):
                files.append(p)
        except ValueError:
            continue
    files = files[:4]
    if not files:
        pytest.skip("no verified Charlottesville process file here")
    (tmp_path / "places" / "va" / "charlottesville").mkdir(parents=True)
    for p in files:
        (tmp_path / "places" / "va" / "charlottesville" / p.name).write_bytes(p.read_bytes())
    monkeypatch.setattr(places, "PLACES_DIR", tmp_path / "places")
    said = []
    assert places.load_processes(con, log=said.append)["verified"] == 0
    assert sum("were not matched by lexflow's software, so it is loaded as not verified" in x
               for x in said) == len(files)
    assert not [k for k in LX.all_pages(con) if k.startswith("lexflow:va:charlottesville:")]
    g = db.one(con, "SELECT * FROM governments WHERE name='City of Charlottesville'")
    for row in db.rows(con, "SELECT * FROM place_processes"):
        row["spec"] = json.loads(row["spec"])
        text = LX.render_local_process(con, g, row)
        head = text.split("\n")[2]
        assert LOCAL_LABEL.search(head) and "not matched (listed below)" in head, row["process"]
        assert "Every quote" not in text and "AI verifier" not in text, row["process"]
        assert "===== Quotes not matched =====" in text, row["process"]


QUOTE_HASH = {"va/charlottesville": "aadb54baf033cdfb5c47befd27b74c353236dbd81f0c690437c5c7278cef342a",
              "md/baltimore": "5386c032c0740d9bbcafa0a206536cb284a2ff234e1be722e71829c2e33857d3",
              "dc/washington": "7247c69ae9cedf9f45cd9eb503be261ba508ece60d948e5e556dcfe9657cf7f1"}


def _quotes(value, out):
    if isinstance(value, dict):
        for k, v in value.items():
            if k == "quote" and isinstance(v, str):
                out.append(v)
            else:
                _quotes(v, out)
    elif isinstance(value, list):
        for v in value:
            _quotes(v, out)
    return out


def test_place_files_say_the_laws_unit_and_describe_the_place_with_quotes_unchanged():
    """Charlottesville's deposit step says the law's "five working days" in lexflow's own words; Baltimore's
    caveats describe the place, not how the research was drafted; every quote is as it was."""
    import hashlib
    cville = json.loads((CURATED / "places" / "va" / "charlottesville.json").read_text(encoding="utf-8"))
    text = json.dumps(cville, ensure_ascii=False)
    assert "five-day" not in text and "five day" not in text
    assert "The five working days the city has to respond do not run while the deposit request is pending." in text
    md = json.dumps(json.loads((CURATED / "places" / "md" / "baltimore.json").read_text(encoding="utf-8")),
                    ensure_ascii=False)
    for gone in ("arrived cut off", "were rebuilt", "original research", "original business research"):
        assert gone not in md, gone
    assert "each come from a different office. Each step above links that office's own page." in md
    for name, want in QUOTE_HASH.items():
        spec = json.loads((CURATED / "places" / f"{name}.json").read_text(encoding="utf-8"))
        got = hashlib.sha256(json.dumps(_quotes(spec, []), ensure_ascii=False).encode()).hexdigest()
        assert got == want, name


def _compiled(state, question):
    from lexflow.bpmn_xml import to_bpmn_xml
    from lexflow.extract.compile import compile_facts
    from lexflow.extract.schema import LegalProcessFacts
    from lexflow.ir import SectionText
    facts = LegalProcessFacts.model_validate(_facts(state, question))
    text = SectionText(code="Code", section="1", title="t", jurisdiction=state, text="", url="https://example.invalid")
    return to_bpmn_xml(compile_facts(facts, model_id=f"{state}-{question}", jurisdiction=state, jurisdiction_name=state,
                                     code="Code", text=text))


DRAWN = re.compile(r'<bpmn:(exclusiveGateway|eventBasedGateway|endEvent|startEvent|sequenceFlow|intermediateCatchEvent)'
                   r'\b[^>]*?\bname="([^"]*)"')


def test_process_maps_label_paths_in_plain_words_never_condition_ids():
    """Gateway, flow and end labels are the law's words or a plain sentence from the facts (the step or outcome a
    path leads to), never a snake_case condition id, and never cut mid-word."""
    import html as H
    from lexflow.extract import compile as CF
    for path in sorted(CURATED.glob("*/*.json")):
        if path.parent.name == "places":
            continue
        st, q = path.parent.name, path.stem
        facts = _facts(st, q)
        conds = {x.get("condition") or x.get("when") for x in facts["steps"] + facts.get("outcomes", [])} - {None}
        plain = {x.get("action") for x in facts["steps"]} | {x.get("description") for x in facts.get("outcomes", [])} \
            | {facts["trigger"]}
        xml = _compiled(st, q)
        for tag, name in DRAWN.findall(xml):
            name = H.unescape(name)
            assert "_" not in name, (st, q, tag, name)
            for c in conds:
                assert name.rstrip("?") != c.replace("_", " ") and name != f"Not {c.replace('_', ' ')}", (st, q, name)
            if name.endswith("…"):                               # cut at a word boundary of a plain sentence
                head = name[:-1]
                assert any(p and p.startswith(head) and p[len(head)] in " ,;:-–—(" for p in plain | {
                    f"Deadline missed: {a}" for a in plain if a} | {f"{a} in time" for a in plain if a}), (st, q, name)
    assert CF.short("word " * 30, 20) == "word word word…" and CF.short("x" * 200) == "x" * 200
    assert CF.ask("Issue certificate of organization") == "Issue certificate of organization?"
    va = _compiled("va", "business")
    assert 'name="Issue certificate of organization?"' in va and 'name="Otherwise this map ends here"' in va
    assert "articles ok" not in va and "Not articles" not in va
    # each conditional flow out of "Which path?" is named for the step it leads to
    assert 'name="Supply inspection or copies at lowest cost"' in _compiled("va", "records")


def test_reader_maps_drop_condition_ids_and_grounding_tags_and_rename_old_labels(va_pages):
    from lexflow import validate as V
    pages = LX.all_pages(va_pages)
    stored = db.one(va_pages, "SELECT bpmn FROM process_models WHERE model_id='va.records'")["bpmn"]
    assert "<bpmn:conditionExpression" in stored                      # the stored model keeps its conditions
    for pid, text in pages.items():
        for x in re.findall(r"<bpmnio[^>]*>\n(.*?)\n</bpmnio>", text, flags=re.S):
            assert "conditionExpression" not in x and "[implied]" not in x and "[assumed]" not in x, pid
            assert not re.search(r'name="[^"]*_[^"]*"', x), pid
            assert V.xsd_errors(x) == [], pid
    bpmn = _bpmn(pages["lexflow:va:records"])
    assert 'name="Supply inspection or copies at lowest cost"' in bpmn               # flows keep their names
    # a map stored by older code (condition ids as labels, names cut at 60 characters) is renamed on the page
    facts = _facts("va", "business")
    old = ('<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" id="d" targetNamespace="x">'
           '<bpmn:process id="p"><bpmn:startEvent id="start" name="' + facts["trigger"][:60] + '"/>'
           '<bpmn:exclusiveGateway id="review_articles_gw" name="articles ok?"/>'
           '<bpmn:endEvent id="review_articles_not_issue_certificate" name="Not articles ok"/>'
           '<bpmn:task id="issue_certificate" name="Issue certificate of organization"/>'
           '<bpmn:sequenceFlow id="sf1" sourceRef="review_articles_gw" targetRef="issue_certificate" name="Yes">'
           '<bpmn:conditionExpression>articles_ok</bpmn:conditionExpression></bpmn:sequenceFlow>'
           '<bpmn:exclusiveGateway id="record_certificate_gw" name="Which path?"/>'
           '<bpmn:task id="local_license" name="Issue local business licence"/>'
           '<bpmn:sequenceFlow id="sf2" sourceRef="record_certificate_gw" targetRef="local_license" '
           'name="locality requires license"><bpmn:conditionExpression>locality_requires_license'
           '</bpmn:conditionExpression></bpmn:sequenceFlow>'
           '<bpmn:task id="g" name="Give commissioner evidence of the filing"/>'
           '<bpmn:task id="file_assumed_name" name="x"/>'
           '<bpmn:sequenceFlow id="sf3" sourceRef="file_assumed_name" targetRef="give_filing_evidence" '
           'name="locality requires license"><bpmn:conditionExpression>locality_requires_license'
           '</bpmn:conditionExpression></bpmn:sequenceFlow>'
           '<bpmn:task id="supply" name="S"><bpmn:documentation>Code § 1(E) [implied]: “q”</bpmn:documentation>'
           '</bpmn:task></bpmn:process></bpmn:definitions>')
    out = LX.reader_bpmn(old, facts)
    assert 'name="Issue certificate of organization?"' in out and 'name="Otherwise this map ends here"' in out
    assert 'id="sf2" sourceRef="record_certificate_gw" targetRef="local_license" name="Issue local business licence"' \
        in out
    assert 'targetRef="give_filing_evidence" name="Give commissioner evidence of the filing"' in out
    assert f'name="{facts["trigger"]}"' in out and 'name="Yes"' in out
    assert "articles ok" not in out and "locality requires" not in out and "conditionExpression" not in out
    assert "[implied]" not in out and "Code § 1(E): “q”" in out


# ------------------------------------------------------------------ the fifth round (verify-gate0.md, Re-check 4)
RECHECK4_REFUSED = ("Pat Roe Аttorney Lіcensed In Virginia", "Jane Doe Lawyеr", "Jane Doe Еsq", "Jane Doe Еѕԛ",
                    "Jane Doe Atty", "Jane Doe Juris Doctor", "Jane Doe Virginia Bar", "Jane Doe Member Virginia Bar",
                    "Jane Doe Advocate", "Jane Doe Abogada", "Jane Doe Avocat", "Jane Doe Rechtsanwältin",
                    "Fact Checker", "Wiki Editor", "Moderator", "Cօpilot", "Ϲlaude",
                    "\u3164\u3164", "Ana\u115fVillamar", "Ana\u1160Villamar", "Ana\uffa0Villamar", "Ana Vi\u17b4llamar",
                    "Ana Vi\u17b5llamar", "Ana\u034fVillamar", "Ana Villamar\ufe0f", "Ana\u2060Villamar",
                    "Ana\u180eVillamar", "Ana Villamar\U000e0041")


def test_names_refuse_look_alikes_invisible_letters_and_the_words_re_check_4_found(con):
    """Each word in one script (UTS #39, Common and Inherited allowed), no default-ignorable code point (the Hangul
    fillers and Khmer inherent vowels among them), and the role and credential words read in plain letters."""
    from lexflow import reviewers as RV
    for name in RECHECK4_REFUSED:
        assert signoff.clean_name(name)[1], name
        with pytest.raises(RV.ReviewerError):
            RV.add(con, name, "other person", added_by="operator")
    assert RV.listing(con) == []
    why = " ".join(signoff.clean_name("Pat Roe Аttorney Lіcensed In Virginia")[1])
    assert "in one script" in why and "attorney" in why and "licensed" in why
    assert any("no invisible characters (not U+1160 U+3164)" in x for x in signoff.clean_name("\u3164\u3164")[1])
    for c in ("\u115f", "\u1160", "\u3164", "\uffa0", "\u17b4", "\u17b5", "\u00ad", "\u200b", "\u202e", "\u2066",
              "\ufeff", "\ufe00", "\U000e0001", "\U000e01ef", "\u061c", "\u180b"):
        assert signoff.ignorable(c), hex(ord(c))
    for c in "aZ é李-' .\u0301":
        assert not signoff.ignorable(c), c
    assert signoff.mixed_script("Аttorney") and signoff.mixed_script("Cօpilot") and signoff.mixed_script("Σlaude")
    for word in ("Клод", "Villamar", "山田たろう", "김민준", "Nguyễn", "O'Neil", "Mary-Jane", "José", "देवनागरी"):
        assert not signoff.mixed_script(word), word
    assert signoff.skeleton("Аttorney") == "attorney" and signoff.skeleton("Еѕԛ") == "esq"
    assert signoff.skeleton("Rechtsanwältin") == "rechtsanwaltin"
    # names in many scripts, and words that are only part of a role phrase, are still names
    for name in CLEAN.values():
        assert signoff.clean_name(name) == (name, []), name
    assert RV.add(con, "Anna de Bar", "researcher", added_by="operator")["name"] == "Anna de Bar"
    # the module says what the check is: lists that catch only what they hold, the operator answering for the rest
    doc = " ".join(signoff.__doc__.split())
    assert "The lists catch only what they hold: the operator answers for every name on the list." in doc


def test_asked_answers_count_their_quotes_when_the_page_is_made(con, va_statutes):
    """Re-check 4: the asked answers carried no quotes_checked, so a reviewed one said "Every quote matched" with no
    count behind it.  Now lexflow's software counts its quotes when the page is made (ask.pipeline.recount, the
    matcher the answer was made with) and the page prints the count; never "Every quote matched"."""
    from lexflow.ask import pipeline as AP
    law = _law_text("va")["Va. Code Ann. § 2.2-3704"]
    words = law.split()
    good, also = " ".join(words[5:20]), " ".join(words[30:42])
    row = dict(_asked(), sections=json.dumps({"chosen": [{"ref": "2.2-3704", "citation": "Va. Code Ann. § 2.2-3704",
                                                          "title": "Right to inspect", "url": "u"}]}),
               answer=json.dumps({"quotes": [{"id": "Q1", "section": "2.2-3704", "text": good},
                                             {"id": "Q2", "section": "2.2-3704", "text": "words that are not there"}],
                                  "steps": [{"actor": "Body", "action": "Respond", "section": "2.2-3704",
                                             "quote": also}]}),
               metrics=json.dumps({"answered_at": "2026-10-08T10:00:00Z"}))       # no stored count at all
    assert AP.recount(row) == {"quotes_checked": 3, "quote_misses": 1}
    who = _listed(con)
    db.upsert(con, "asked_answers", [row])
    _record(con, row, _signed(row, _review(who, "2026-10-09")))
    pages = LX.all_pages(con)
    page = pages["lexflow:va:deck_permit"]
    today = signoff.long_date(db.now())
    assert f"**Drafted with an AI system from the statute text · 2 of 3 quotes matched to {COPY} on {today} · " \
           f"Reviewed by {PERSON}, researcher, on 9 October 2026**" in page
    assert "Every quote" not in page and LABEL.search(page)
    assert f"2 of 3 quotes matched to {COPY}" in pages["lexflow:va"]
    # all of them found: still the count, never "Every quote matched"
    fine = dict(row, answer=json.dumps({"quotes": [{"id": "Q1", "section": "2.2-3704", "text": good}], "steps": []}))
    assert LX.asked_check(fine) == f"1 of 1 quotes matched to {COPY} on {today}"
    # no text at hand: no count, and the page says the quotes were not matched
    lost = dict(row, sections=json.dumps({"chosen": [{"ref": "99.9-9999"}]}))
    assert AP.recount(lost) is None and "not matched by lexflow's software" in LX.asked_check(lost)
    assert LX.asked_check(dict(row, answer=json.dumps({"quotes": [], "steps": []}))) == \
        "No quotes from the statute to match"


def test_asked_maps_draw_the_question_not_its_id():
    """Re-check 4: every stored asked-answer map starts "A criminal_record_expunged_sealed process begins", since
    the trigger is made from the question id.  The page's map gives the question's plain words."""
    from lxml import etree
    xml = ("<?xml version='1.0' encoding='UTF-8'?>"
           '<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" id="d" targetNamespace="x">'
           '<bpmn:process id="p"><bpmn:documentation>A deck_permit process begins</bpmn:documentation>'
           '<bpmn:startEvent id="start" name="A deck_permit process b"/>'
           '<bpmn:task id="apply" name="Apply"/><bpmn:endEvent id="process_complete" name="Process complete"/>'
           '<bpmn:endEvent id="other_end" name="deck_permit ends"/></bpmn:process></bpmn:definitions>')
    facts = {"process_name": "Do I need a permit for a deck", "trigger": "A deck_permit process begins",
             "steps": [], "outcomes": [{"id": "process_complete", "description": "Process complete"}]}
    for kw in ({"question": "Do I need a permit for a deck?", "question_id": "deck_permit"}, {}):
        out = LX.reader_bpmn(xml, facts, **kw)
        names = {e.get("id"): e.get("name") for e in etree.fromstring(out.encode()).iter() if e.get("name")}
        assert names["start"] == "Do I need a permit for a deck?", kw
        assert names["other_end"] == "“Do I need a permit for a deck?” ends", kw
        assert names["process_complete"] == "Process complete"
        assert not re.search(r'name="[^"]*_[^"]*"', out), kw
        assert "process begins" not in out and "<bpmn:documentation>Do I need a permit for a deck?<" in out, kw
    # a state model's map (no id in its labels) is unchanged
    state = xml.replace("A deck_permit process b", "A records process begins").replace("deck_permit ends", "Ends")
    assert 'name="A records process begins"' in LX.reader_bpmn(state, dict(facts, trigger="A records process begins"))


def test_a_process_file_checked_before_its_sources_were_read_is_not_verified(con, va_statutes, tmp_path,
                                                                           monkeypatch):
    """Re-check 4 and 5: 33 verified files date the AI check 10 October while some sources were retrieved on 11
    October.  Such a file loads as verified only when lexflow's software matched every one of its quotes on or after
    those dates; otherwise it loads as not verified, with a log line, and a row loaded by older code as verified is
    checked again on the page.  The page never gives the AI check's date."""
    from lexflow.municipal import places
    from test_places_strategies import _govs
    _govs(con)
    law = _law_text("va")["Va. Code Ann. § 2.2-3704"]
    good = " ".join(law.split()[10:22])
    for url, text in (("https://www.charlottesville.gov/foia", "Submit a request online"),
                      ("https://www.charlottesville.gov/fees", "10 cents a page"),
                      ("https://www.charlottesville.gov/rules", "a rule the regulation states")):
        _cache_page(url, text, fetched="2026-10-11")
    base = _proc([("Va. Code § 2.2-3704(B)", "https://law.lis.virginia.gov/vacode/2.2-3704/", good)])
    spec = dict(base, place="va:charlottesville", process="records_request",
                sources=base["sources"] + [{"url": "https://www.charlottesville.gov/rules", "retrieved": "2026-10-10"}])
    late = dict(spec, sources=spec["sources"] + [{"url": "https://www.charlottesville.gov/fees",
                                                  "retrieved": "2026-10-11"}])
    later = dict(spec, sources=spec["sources"] + [{"url": "https://www.charlottesville.gov/fees",
                                                   "retrieved": "2026-10-12"}])
    assert places.check_date_problem(spec) is None and places.is_verified(spec)
    assert "dated 2026-10-10, before some of its sources were retrieved (the latest on 2026-10-11)" in \
        places.check_date_problem(late)
    assert places.is_verified(late)                 # lexflow's software matched every quote on 2026-10-11 or later
    assert not places.is_verified(later)            # its pages were read on 2026-10-11, before that source
    assert places.check_date_problem(dict(late, verified=False)) is None
    (tmp_path / "places" / "va" / "charlottesville").mkdir(parents=True)
    path = tmp_path / "places" / "va" / "charlottesville" / "records_request.json"
    monkeypatch.setattr(places, "PLACES_DIR", tmp_path / "places")
    for body, verified in ((later, 0), (late, 1), (spec, 1)):
        path.write_text(json.dumps(body), encoding="utf-8")
        said = []
        got = places.load_processes(con, log=said.append)
        assert db.one(con, "SELECT verified FROM place_processes")["verified"] == verified
        assert got["verified"] == verified
        assert any("records_request.json: its AI check is dated 2026-10-10" in x and "lexflow's software did not "
                   "match every quote on or after that, so it is loaded as not verified" in x
                   for x in said) is (not verified)
        page = LX.all_pages(con).get("lexflow:va:charlottesville:records_request")
        assert (page is not None) is bool(verified)
        if page:
            assert "10 October 2026" not in page.split("\n")[2] and LOCAL_LABEL.search(page)
    # a row loaded by older code as verified is checked again on the page
    con.execute("UPDATE place_processes SET verified=1, spec=?", (json.dumps(later),))
    con.commit()
    assert "lexflow:va:charlottesville:records_request" not in LX.all_pages(con)
    g = db.one(con, "SELECT * FROM governments WHERE name='City of Charlottesville'")
    text = LX.render_local_process(con, g, {"process": "records_request", "spec": later})
    assert "AI verifier" not in text and "4 of 4 quotes matched by lexflow's software" in text


def test_pages_print_process_caveats_as_written_and_log_drafting_words(con, tmp_path, monkeypatch, caplog):
    """Re-check 5: cutting drafting notes out of a process file's caveats took reader warnings with them, so the 60
    files were reworded at the source (tests/test_place_processes.py checks them) and a process page prints its
    caveats and source titles as the file words them, logging any drafting words left.  A place's own page (its
    local answers) still leaves such notes out."""
    import logging
    from test_places_strategies import _govs
    _govs(con)
    spec = {"title": "Small claims", "researched": "2026-10-09",
            "caveats": ["The form has only a partial text layer; the verifier rendered both pages to read it, so its "
                        "quotes are transcriptions.", "Fees change each July."],
            "sources": [{"url": "https://law.lis.virginia.gov/vacode/8.01-15.2/",
                         "title": "Va. Code § 8.01-15.2 (lexflow index row 30394)", "retrieved": "2026-10-09"}]}
    g = db.one(con, "SELECT * FROM governments WHERE name='City of Charlottesville'")
    with caplog.at_level(logging.WARNING, logger="lexflow.places"):
        page = LX.render_local_process(con, g, {"process": "small_claims", "spec": spec})
    assert "so its quotes are transcriptions." in page and "  * Fees change each July." in page
    assert "|Va. Code § 8.01-15.2 (lexflow index row 30394)]]" in page
    assert sum("describes the drafting" in r.getMessage() for r in caplog.records) == 2


def test_place_pages_leave_out_the_drafting_notes_in_place_files(con, tmp_path, monkeypatch):
    """Re-check 4: place files carried caveats and source titles about the drafting ("the verifier rendered both
    pages", "added by the verifier", "(lexflow index row 30394)", "declared research User-Agent").  A place's page
    leaves them out of its local answers; the file is not changed."""
    from test_places_strategies import _govs
    _govs(con)
    spec = {"title": "Small claims (lexflow index row 1), added by the verifier", "researched": "2026-10-09",
            "caveats": ["The form has only a partial text layer; the verifier rendered both pages to read it. It has "
                        "no fillable fields.",
                        "Staunton pages were read with a declared research User-Agent (lexflow-research/0.1).",
                        "The court's page (read for lexflow on 2026-10-10) gives the number (ECC; the verifier re-read "
                        "the page on 2026-10-11). Call 911 in an emergency.",
                        "Fees change each July."],
            "sources": [{"url": "https://law.lis.virginia.gov/vacode/8.01-15.2/",
                         "title": "Va. Code § 8.01-15.2 (lexflow index row 30394), added by the verifier",
                         "retrieved": "2026-10-09"},
                        {"url": "https://www.dmv.virginia.gov/x", "title": "FMS 210 (read in full by the verifier)"},
                        {"url": "https://www.ci.staunton.va.us/x",
                         "title": "Deeds (live page answered HTTP 403 to the research client; read from "
                                  "https://web.archive.org/web/1/x)"}]}
    before = json.dumps(spec, sort_keys=True)
    loc = {"caveats": spec["caveats"], "sources": spec["sources"]}
    kept = " ".join(LX.reader_caveats(loc["caveats"]))
    assert json.dumps(spec, sort_keys=True) == before                          # the file's text is unchanged
    for gone in ("verifier", "lexflow index", "index row", "User-Agent", "lexflow-research", "research client",
                 "read for lexflow", "Staunton pages were read"):
        assert gone not in kept, gone
    for said in ("The form has only a partial text layer. It has no fillable fields.",
                 "gives the number (ECC). Call 911 in an emergency."):
        assert said in kept, said
    assert LX.reader_caveats(loc["caveats"])[-1] == "Fees change each July."
    assert [LX.source_title(x) for x in loc["sources"]] == ["Va. Code § 8.01-15.2", "FMS 210",
                                                            "Deeds (read from https://web.archive.org/web/1/x)"]


def test_charlottesville_describes_the_place_not_the_drafting():
    """Re-check 4: the business caveat said "The research could not load ..." and printed the claims it said were
    removed.  The caveats now describe the place; the quotes are unchanged (QUOTE_HASH)."""
    cville = json.loads((CURATED / "places" / "va" / "charlottesville.json").read_text(encoding="utf-8"))
    caveats = " ".join(c for a in cville["answers"].values() for c in a.get("caveats") or [])
    for gone in ("The research", "earlier claim", "Two earlier claims", "removed or softened", "so it was removed",
                 "re-verified", "not verified here", "8 AM", "2 sq ft", "March 1", "Room A130"):
        assert gone not in caveats, gone
    assert "The home-occupation standards are in the city's Development Code" in caveats
    assert "one non-resident worker and no more than three clients at a time" in caveats


def _process_files():
    out = []
    for p in sorted((CURATED / "places" / "va").glob("*/*.json")):
        try:                                     # another workflow may be writing these: skip a half-written one
            out.append((p, json.loads(p.read_text(encoding="utf-8"))))
        except ValueError:
            continue
    return out


def test_researched_pages_never_reprint_the_words_of_sites_whose_terms_forbid_it(con):
    """Re-check 5, the quote policy: albemarle.org, eCode360 and Municode forbid reposting their pages' content.  On
    every page made from the 60 researched files, a quote from one of those sites (or an Internet Archive copy of
    it) is replaced by lexflow's paraphrase or the link and why; the words stay only in the file, as evidence.  The
    policy is one table (quotes.NO_REPRINT) with each site's reason and terms page."""
    from lexflow.municipal import places
    from lexflow.municipal import quotes as Q
    from test_places_strategies import _govs
    _govs(con)
    files = _process_files()
    if len(files) < 60:
        pytest.skip("another workflow may be writing these files")
    govs = {g["name"]: g for g in db.rows(con, "SELECT * FROM governments")}
    names = {"albemarle": "Albemarle County", "charlottesville": "City of Charlottesville", "staunton": "City of Staunton"}
    held = 0
    for path, spec in files:
        g = govs.get(names[path.parent.name]) or {"gov_id": spec.get("gov_id"), "state": "va",
                                                   "name": names[path.parent.name], "kind": "municipality"}
        text = LX.render_local_process(con, g, {"process": path.stem, "spec": spec})
        free = {q for _, q, cites in places.process_quotes(spec)
                if not any(Q.policy(u) for u in Q.cited_urls(cites))}
        for where, q, cites in places.process_quotes(spec):
            if any(Q.policy(u) for u in Q.cited_urls(cites)) and q not in free:
                held += 1
                assert f"“{LX.esc(q)}”" not in text and f"//{LX.esc(q)}//" not in text, (path.name, where, q[:80])
                assert len(q) < 40 or q not in text, (path.name, where, q[:80])       # nor copied elsewhere
        if held and any(Q.policy(u) for _, _, c in places.process_quotes(spec) for u in Q.cited_urls(c)):
            assert "words are not reprinted here" in text, path.name
        for i, x in enumerate(spec.get("legal_basis") or []):     # the law's words, in lexflow's own paraphrase
            if x.get("quote") and any(Q.policy(u) for u in Q.cited_urls([x.get("citation"), x.get("url")])):
                assert x.get("paraphrase") and f"in lexflow's words: {LX.esc(x['paraphrase'])}" in text, \
                    (path.name, i)
    assert held > 100                            # the Albemarle files quote their county's pages throughout
    for host in ("library.municode.com", "ecode360.com", "albemarle.org"):
        p = Q.NO_REPRINT[host]
        assert p["reason"] and p["terms"].startswith("https://") and f"[[{p['terms']}|{p['site']}]]" in \
            Q.method_policy()


def test_the_researched_files_lean_on_no_browser_read_and_keep_their_warnings():
    """Re-check 5: two Staunton files were first drafted from a desktop browser's read of the city site, and several
    caveats described the drafting.  The files now describe the place and the process: no browser, model, verifier
    or discovery file in what a reader sees, the sheriff's number and address, which came from that read, are now
    those of an Internet Archive copy of the sheriff's page, and the warnings stay (transcriptions a text search
    cannot confirm, fees that cannot be computed)."""
    files = _process_files()
    if len(files) < 60:
        pytest.skip("another workflow may be writing these files")
    seen = " ".join(json.dumps({k: v for k, v in spec.items() if k not in ("checks", "researched_by")},
                               ensure_ascii=False) for _, spec in files)
    for gone in ("browser pane", "desktop browser", "Claude", "the verifier", "discovery file", "fixtures/",
                 "lexflow index row", "research User-Agent", "the research did not", "for this research",
                 "earlier draft", "lexflow consulted", "lexflow read only"):
        assert gone not in seen, gone
    by = {f"{p.parent.name}/{p.stem}": spec for p, spec in files}
    small = " ".join(by["staunton/small_claims_civil"]["caveats"])
    assert "The Staunton City Sheriff's Office phone and address are those on the Internet Archive copy of the " \
        "Sheriff's page of 17 July 2026" in small and "check them before you rely on them" in small
    assert "which a text search cannot confirm" in " ".join(by["staunton/probate_will_qualify_executor"]["caveats"])
    assert "cannot be computed" in " ".join(by["charlottesville/building_permit_residential"]["caveats"])
    assert "Every quote" not in seen


# ------------------------------------------------------------------ the sixth round (verify-gate0.md, Re-check 5)
class _Shared:
    """A stand-in for a shared database that someone else can write: every column, the rows given, and a record of
    every statement sent and every SELECT made."""

    def __init__(self, con, rows):
        self.con, self.rows, self.sent, self.selects = con, rows, [], []

    def pipeline(self, statements):
        self.sent += statements
        return [{"cols": [], "rows": [], "affected": 0} for _ in statements]

    def query(self, sql, *args):
        if sql.startswith("PRAGMA"):
            table = sql[sql.index("(") + 1:-1]
            return [{"name": c} for c in db.columns(self.con, table)]
        self.selects.append(sql)
        if args and args[0]:
            return []
        return [dict(r, _rowid=i + 1) for i, r in enumerate(self.rows)]


def _label(page):
    """A page's three-fact label line."""
    return next(x for x in page.split("\n") if x.startswith("**Drafted with an AI system"))


NOT_SHARED = ("reviewers", "review_log", "jobs", "settings", "sync_log", "sync_marks", "meta", "asked_questions",
              "statute_files", "no_such_table")


def test_sync_takes_only_the_shared_tables(con, capsys, monkeypatch):
    """Re-check 5: `sync pull --tables reviewers` wrote the reviewer list (a reviewer renamed "Claude", her token
    hash replaced), as the CLI and as a job queued through POST /api/jobs, and `push --tables reviewers` raised
    KeyError.  Push and pull now take only db.SYNCED, and refuse any other table with a clear error before the
    shared database is reached."""
    from fastapi.testclient import TestClient
    from lexflow import cli
    from lexflow import reviewers as RV
    from lexflow.api import app as API
    from lexflow.pipeline import steps
    who = _listed(con, "attorney", "va")
    before = db.rows(con, "SELECT * FROM reviewers")
    assert T.check_tables(None) is None and T.check_tables("") is None and T.check_tables([]) is None
    assert T.check_tables("answers, contacts") == ["answers", "contacts"]
    assert T.check_tables(["process_models", "process_models"]) == ["process_models"]
    with pytest.raises(T.SyncTableError) as e:
        T.check_tables("answers,reviewers")
    assert "sync takes only the shared tables (governments, " in str(e.value) and "refused: reviewers" in str(e.value)
    assert "this copy's own, never synced" in str(e.value) and isinstance(e.value, ValueError)
    renamed = dict(before[0], name="Claude", token_hash=RV.hash_token("x"), updated_at="2999-01-01T00:00:00Z")
    for table in NOT_SHARED:
        with pytest.raises(T.SyncTableError, match=f"refused: {table}"):
            T.check_tables([table])
        for fn in (T.push, T.pull):
            shared = _Shared(con, [renamed])
            with pytest.raises(T.SyncTableError):
                fn(con, shared, tables=[table], log=lambda *_: None)
            assert shared.sent == [] and shared.selects == [], (fn.__name__, table)   # before the server is reached
    # the CLI and the job step: exit status 2 and one line saying why, the shared database never reached
    monkeypatch.setattr(T.Turso, "from_env", classmethod(lambda cls: pytest.fail("reached the shared database")))
    for direction in ("push", "pull"):
        assert cli.main(["sync", direction, "--tables", "reviewers"]) == 2
        err = capsys.readouterr().err
        assert f"sync {direction}: sync takes only the shared tables" in err and "refused: reviewers" in err
        assert cli.main(["run", "sync", "--direction", direction, "--tables", "review_log"]) == 2
        assert "refused: review_log" in capsys.readouterr().err
        for tables in ("reviewers", ["reviewers"], "answers,jobs"):
            with pytest.raises(T.SyncTableError):
                steps.run_sync(con, {"direction": direction, "tables": tables}, lambda *_: None, lambda *_: None)
    # POST /api/jobs refuses such a sync job (400) and queues nothing
    monkeypatch.setattr(config, "JOB_RUNNER", False)
    with TestClient(API.app) as c:
        for args in ({"direction": "pull", "tables": "reviewers"}, {"direction": "push", "tables": ["reviewers"]},
                     {"direction": "pull", "tables": "answers,review_log"}, {"direction": "sideways"}):
            r = c.post("/api/jobs", json={"step": "sync", "args": args})
            assert r.status_code == 400, args
        r = c.post("/api/jobs", json={"step": "sync", "args": {"direction": "pull", "tables": "reviewers"}})
        assert "refused: reviewers" in r.json()["detail"]
        assert db.scalar(con, "SELECT count(*) FROM jobs WHERE step='sync'") == 0
        ok = c.post("/api/jobs", json={"step": "sync", "args": {"direction": "pull", "tables": "answers"}})
        assert ok.status_code == 200 and db.scalar(con, "SELECT count(*) FROM jobs WHERE step='sync'") == 1
    # the list is as it was, and the reviewer's own token still works
    assert db.rows(con, "SELECT * FROM reviewers") == before and RV.holder(con, who["token"])["id"] == who["id"]


def test_a_review_that_arrives_through_sync_names_no_one(va_pages, monkeypatch, caplog):
    """Re-check 5: a review written into the shared database, with a listed reviewer's id and the hash of the
    edited text, was shown after a pull with no token, and so was a state model signed there "on 1 January 2001".
    A page now names a reviewer only for a review this copy recorded (its review_log) or a sign-off in this copy's
    own file; any other review field counts as not reviewed, with one log line per item.  The wiki tick and the
    dashboard say the same."""
    import logging
    from fastapi.testclient import TestClient
    from lexflow import reviewers as RV
    from lexflow.api import app as API
    con = va_pages
    monkeypatch.setattr(config, "JOB_RUNNER", False)
    monkeypatch.setattr(signoff, "_UNRECORDED", set())             # the once-per-item log, fresh for this test
    who = _listed(con, "attorney", "va")
    mine = {RV.TOKEN_HEADER: who["token"]}
    base = "/api/ask/deck_permit/va"
    # an asked answer, its quote edited on the shared copy and signed there in the listed reviewer's name
    row = dict(_asked(1, None), answer=json.dumps({"quotes": [{"id": "Q1", "section": "2.2-3704",
                                                              "text": "is FORGED STEP not authorized to"}],
                                                   "steps": []}), updated_at="2999-01-01T00:00:00Z", origin="elsewhere")
    row["reviewed_by"] = json.dumps(_signed(row, _review(who, "2026-10-09")))
    with caplog.at_level(logging.WARNING, logger="lexflow.signoff"):
        T.pull(con, _Shared(con, [row]), tables=["asked_answers"], log=lambda *_: None)
        stored = db.one(con, "SELECT * FROM asked_answers")
        assert stored["reviewed_by"] and stored["published"] == 1          # it arrived with its review and tick ...
        pages = LX.all_pages(con)
        LX.all_pages(con)
    assert "lexflow:va:deck_permit" not in pages and "deck" not in pages["lexflow:va"]   # ... and names no one
    said = [m for m in caplog.messages if "deck_permit" in m and "did not record" in m]
    assert len(said) == 1, said                                            # one log line per answer
    with TestClient(API.app) as c:
        seen = c.get(base).json()
        assert seen["reviewed_by"] is None and seen["review_stale"] is True
        assert c.post(f"{base}/publish", json={"published": True}).status_code == 409      # the wiki tick too
        assert c.get("/api/ask").json()[0]["reviewed"] == 0
        # the reviewer records the review on this copy, with their own token: now it counts
        assert c.put(f"{base}/review", json={"reviewer": who["id"], "attested": True, "text_hash": seen["text_hash"]},
                     headers=mine).status_code == 200
        assert c.post(f"{base}/publish", json={"published": True}).status_code == 200
    assert f"Reviewed by {PERSON}, attorney licensed in Virginia" in LX.all_pages(con)["lexflow:va:deck_permit"]
    # removed again; the column and the tick put back by hand: the last review_log entry is the removal
    recorded = db.one(con, "SELECT reviewed_by FROM asked_answers")["reviewed_by"]
    with TestClient(API.app) as c:
        assert c.delete(f"{base}/review", headers=mine).status_code == 200
    con.execute("UPDATE asked_answers SET reviewed_by=?, published=1", (recorded,))
    con.commit()
    assert "lexflow:va:deck_permit" not in LX.all_pages(con)
    # a state model signed on the shared copy (dated 2001-01-01 without first_built, or with an earlier one, or on a
    # day that would pass): not reviewed here, since this copy's curated file carries no such sign-off; and the
    # pull keeps this copy's first_built
    m = db.one(con, "SELECT * FROM process_models WHERE model_id='va.records'")
    metrics, facts = json.loads(m["metrics"]), json.loads(m["facts"])
    caplog.clear()
    for when, first in (("2001-01-01", None), ("2001-01-01", "2001-01-01"), ("2026-10-10", "2026-10-10")):
        forged = {k: v for k, v in metrics.items() if k != "first_built"}
        if first:
            forged["first_built"] = first
        forged["reviewed_by"] = signoff.bind(_review(who, when), signoff.model_text(facts, forged))
        with caplog.at_level(logging.WARNING, logger="lexflow.signoff"):
            T.pull(con, _Shared(con, [dict(m, metrics=json.dumps(forged), updated_at="2999-01-01T00:00:00Z",
                                           origin="elsewhere")]), tables=["process_models"], full=True,
                   log=lambda *_: None)
            page = LX.all_pages(con)["lexflow:va:records"]
        kept = json.loads(db.one(con, "SELECT metrics FROM process_models WHERE model_id='va.records'")["metrics"])
        assert kept["reviewed_by"]["reviewer"] == who["id"] and kept["first_built"] == "2026-10-10", (when, first)
        assert "Reviewed by" not in page and "Not yet reviewed by a person" in page, (when, first)
    assert any("va.records" in x and "did not record" in x for x in caplog.messages)
    # a place's local answer signed on the shared copy: not reviewed here either
    loc = db.one(con, "SELECT * FROM local_answers WHERE question='records'")
    signed = signoff.bind(_review(who, "2026-10-10"), signoff.row_text(loc, signoff.LOCAL_TEXT))
    T.pull(con, _Shared(con, [dict(loc, reviewed_by=json.dumps(signed), updated_at="2999-01-01T00:00:00Z")]),
           tables=["local_answers"], full=True, log=lambda *_: None)
    loc = db.one(con, "SELECT * FROM local_answers WHERE question='records'")
    assert json.loads(loc["reviewed_by"]) == signed and LX.local_reviewer(loc, con) is None
    assert "Reviewed by" not in _label(LX.all_pages(con)["lexflow:va:charlottesville:records"])


FABRICATED = "FABRICATED: the public body may refuse any request without giving a reason"


def test_state_model_quote_counts_are_made_when_the_page_is(va_pages, monkeypatch):
    """Re-check 5: a fabricated step quote written into the shared copy and pulled read "Every quote matched to Open
    US Law's copy of the official text", since a state model's count came from its stored metrics.  Pages now
    count a model's quotes when they are made, against this copy's statute text (as asked answers' are), and say
    so when that text is not at hand."""
    from lexflow.municipal import build, statutes
    con = va_pages
    m = db.one(con, "SELECT * FROM process_models WHERE model_id='va.records'")
    assert build.recount(m) == {"quotes_checked": 23, "quote_misses": 0} and LX.model_matched(m) == (23, 23)
    today = signoff.long_date(db.now())
    assert f"Every quote matched to {COPY} on {today}" in _label(LX.all_pages(con)["lexflow:va:records"])
    # the fabricated quote arrives through a pull, with metrics that still say every quote matched
    facts = json.loads(m["facts"])
    facts["steps"][0]["source"]["quote"] = FABRICATED
    metrics = dict(json.loads(m["metrics"]), quotes_checked=23, quote_misses=0, checked_on="2026-10-10")
    T.pull(con, _Shared(con, [dict(m, facts=json.dumps(facts), metrics=json.dumps(metrics),
                                   updated_at="2999-01-01T00:00:00Z", origin="elsewhere")]),
           tables=["process_models"], full=True, log=lambda *_: None)
    pages = LX.all_pages(con)
    head = _label(pages["lexflow:va:records"])
    assert f"22 of 23 quotes matched to {COPY} on {today}" in head and "Every quote" not in head
    assert FABRICATED in pages["lexflow:va:records"]          # the page shows its text, with the count made on it
    assert "22 of 23 quotes from the statute matched" in _label(pages["lexflow:va:charlottesville:records"])
    assert "22 of 23 quotes from the statute matched" in _label(pages["lexflow:va:charlottesville"])
    assert "22 of 23 quotes from the statute matched" in _label(pages["lexflow:va"])
    assert "22 of their 23 quotes were matched" in pages["lexflow:start"]
    method = pages[LX.METHOD]
    assert "| [[lexflow:va:records|va.records]] | 23 | 1 |" in method and "Today 0 of the 1 models pass" in method
    # without the statute text here there is no count, and the pages say so: never "Every quote matched"
    def gone(state):
        raise FileNotFoundError(f"statutes for {state} are not downloaded")
    monkeypatch.setattr(statutes, "load", gone)
    assert build.recount(m) is None and LX.model_matched(m) is None
    pages = LX.all_pages(con)
    assert f"Quotes not matched by lexflow's software: {LX.NOT_AT_HAND}" in _label(pages["lexflow:va:records"])
    for pid in ("lexflow:va:charlottesville:records", "lexflow:va:charlottesville", "lexflow:va"):
        assert f"Quotes from the statute not matched by lexflow's software: {LX.NOT_AT_HAND}" in _label(pages[pid]), pid
    assert f"Quotes not matched by lexflow's software: {LX.NOT_AT_HAND}" in _label(pages["lexflow:start"])
    assert "lexflow's software could not match their quotes when this page was made" in pages["lexflow:start"]
    assert "| [[lexflow:va:records|va.records]] | statute text not at hand |" in pages[LX.METHOD]
    for pid, page in pages.items():
        if pid != LX.METHOD:
            assert "Every quote" not in _label(page), pid


def test_the_curated_signoff_floor_is_stored_once_and_never_moves_back(con, va_statutes, tmp_path, monkeypatch):
    """Re-check 5: build.first_built took the earliest date anywhere in the drafting note and the stored one, so an
    edited note ("..., 2000-01-01; ...") or one that also named "a draft of 1999-01-01" moved the floor back, and the
    stored date followed it down.  It is now stored once (the date the note opens with, at the first build here)
    and never lowered; a stored row without it takes its earliest recorded build, on the page too."""
    from lexflow.municipal import build, locator
    from lexflow.municipal.questions import QUESTIONS
    locator.run(con, QUESTIONS["records"], ["va"], log=lambda *_: None)
    who = _listed(con, "attorney", "va")

    def floor():
        return json.loads(db.one(con, "SELECT metrics FROM process_models WHERE model_id='va.records'")["metrics"]
                          )["first_built"]

    def note(text):
        return lambda spec: spec.update(drafted_by=text)
    before = "before the text it reviews (2026-10-10)"
    _curated_signed(con, tmp_path, monkeypatch)                          # the first build here: the note's date
    assert floor() == "2026-10-10"
    # the note edited to an earlier date, signed after that date: refused, and the stored date stays
    said = _curated_signed(con, tmp_path, monkeypatch, _review(who, "2000-06-01"),
                           edit=note("Claude (claude-opus-5-5), 2000-01-01; every quote checked"))
    assert any(before in s for s in said), said
    assert floor() == "2026-10-10" and "Reviewed by" not in LX.render_state_model(con, "va", "records")
    # no note at all: the stored date still holds
    said = _curated_signed(con, tmp_path, monkeypatch, _review(who, "1999-07-01"), edit=lambda s: s.pop("drafted_by"))
    assert any(before in s for s in said) and floor() == "2026-10-10"
    # a fresh copy (no stored row): the date the note opens with, not an older one it mentions
    con.execute("DELETE FROM process_models")
    con.commit()
    mention = "Claude (claude-opus-5-5), 2026-10-10; rewritten from a draft of 1999-01-01; every quote checked"
    assert build.drafting_date({"drafted_by": mention}) == "2026-10-10"
    said = _curated_signed(con, tmp_path, monkeypatch, _review(who, "1999-06-01"), edit=note(mention))
    assert any(before in s for s in said) and floor() == "2026-10-10"
    said = _curated_signed(con, tmp_path, monkeypatch, _review(who, "2026-10-10"), edit=note(mention))
    assert "Reviewed by Ana Villamar, attorney" in LX.render_state_model(con, "va", "records")
    # a row stored without first_built (by older code): the earliest build it records, on the page and at the build
    row = db.one(con, "SELECT metrics, stages FROM process_models WHERE model_id='va.records'")
    metrics = {k: v for k, v in json.loads(row["metrics"]).items() if k != "first_built"}
    stages = dict(json.loads(row["stages"]), extracted="2026-10-11T09:00:00Z", compiled="2026-10-11T09:00:00Z")
    con.execute("UPDATE process_models SET metrics=?, stages=? WHERE model_id='va.records'",
                (json.dumps(metrics), json.dumps(stages)))
    con.commit()
    stored = db.one(con, "SELECT * FROM process_models WHERE model_id='va.records'")
    assert build.signoff_floor(stored) == "2026-10-11"
    assert build.first_built(con, {"drafted_by": mention}, "va", "records") == "2026-10-11"
    assert "Reviewed by" not in LX.render_state_model(con, "va", "records")           # 10 October is before it
    said = _curated_signed(con, tmp_path, monkeypatch, _review(who, "2026-10-10"), edit=note(mention))
    assert any("before the text it reviews (2026-10-11)" in s for s in said) and floor() == "2026-10-11"


def test_check_dates_in_the_future_are_refused():
    """Re-check 5: a verified file whose AI check is dated 2026-12-01 counted as verified, and its page said
    "checked by an AI verifier against the cited page on 1 December 2026".  No check is dated in the future."""
    from lexflow.municipal import places
    assert signoff.past_date("2999-12-01") is None and signoff.past_date("2026-10-10T09:00:00Z") == "2026-10-10"
    spec = {"title": "T", "verified": True, "researched": "2026-10-09",
            "sources": [{"url": "https://a", "retrieved": "2026-10-09"}],
            "checks": {"verified_by": "an AI verifier", "date": "2999-12-01"}}
    assert "in the future" in places.check_date_problem(spec)
    # wherever else a check date is read, a future one is not shown as when anything was checked
    assert LX.process_checked_on(dict(spec, verified=False, checked="2999-12-01")) == "2026-10-09"
    assert LX.model_checked_on({"metrics": {"checked_on": "2999-01-01"}, "updated_at": "2026-10-10T09:00:00Z"}) == \
        "2026-10-10"


def test_the_shared_server_and_the_test_dashboard_are_published_on_this_machine_only():
    """Re-check 5: the bundled libSQL server was published on every interface with no key, and the test dashboard
    (a job API) on 8001 too.  Both are bound to 127.0.0.1 by default; README and docs/core.md say the shared server
    must not be reachable from untrusted networks and that a pull is trusted only as far as the server is."""
    import yaml
    path = config.ROOT / "docker-compose.yml"
    if not path.exists():
        pytest.skip("no docker-compose.yml beside the code here")
    text = path.read_text(encoding="utf-8")
    services = yaml.safe_load(text)["services"]
    assert services["app"]["ports"] == ["127.0.0.1:${LEXFLOW_PORT:-8000}:8000"]
    assert services["libsql"]["ports"] == ["${LIBSQL_BIND:-127.0.0.1}:${LIBSQL_PORT:-8081}:8080"]
    assert services["test-ui"]["ports"] == ["127.0.0.1:${LEXFLOW_TEST_UI_PORT:-8001}:8000"]
    for name, svc in services.items():
        for p in svc.get("ports") or []:
            assert p.startswith(("127.0.0.1:", "${LIBSQL_BIND:-127.0.0.1}:")), (name, p)
    ui = services["test-ui"]
    assert ui["volumes"] == ["lexflow-test-data:/data"] and ui["environment"]["TURSO_DATABASE_URL"] == ""
    assert "SQLD_AUTH_JWT_KEY" in text and "network you control" in text
    env = config.ROOT / ".env.example"
    if env.exists():
        assert "# LIBSQL_BIND=127.0.0.1" in env.read_text(encoding="utf-8")
    core = " ".join((config.ROOT / "docs" / "core.md").read_text(encoding="utf-8").split())
    assert "The shared server must not be reachable from untrusted networks" in core
    assert "A pull is trusted data only as far as that server is" in core
    readme = config.ROOT / "README.md"
    if readme.exists():
        flat = " ".join(readme.read_text(encoding="utf-8").split())
        assert "The shared server must not be reachable from networks you do not trust." in flat
        assert "A pull is trusted data only as far as the server is" in flat and "LIBSQL_BIND" in flat


def test_the_docs_say_what_the_review_and_sync_code_does(va_pages):
    """Re-check 5's "claims the code does not back": each sentence is now true, or says what the code does; and a
    curated sign-off is said to be recorded by whoever edits the file, with no token."""
    from lexflow import reviewers as RV
    method = " ".join(LX.all_pages(va_pages)[LX.METHOD].split())
    for gone in ("counts only if it names someone on this copy's list",
                 "only after a person on the operator's reviewer list has reviewed them."):
        assert gone not in method, gone
    for said in ("The list is this copy's own: it is not shared with other copies, and a review that arrives from "
                 "another copy never counts here",
                 "only after a person on the operator's reviewer list has recorded on this copy, with their own token, "
                 "that they reviewed them",
                 "that sign-off is not bound to any token: whoever edits the file records it, and the operator answers "
                 "for it",
                 "lexflow's software matches them again each time the page is made, against the statute text this "
                 "copy of lexflow holds",
                 "a map that came from another copy through sync is counted here the same way",
                 "until someone on the list signs, on this copy, the text it shows"):
        assert said in method, said
    core = " ".join((config.ROOT / "docs" / "core.md").read_text(encoding="utf-8").split())
    texts = [core]
    readme = config.ROOT / "README.md"
    if readme.exists():
        texts.append(" ".join(readme.read_text(encoding="utf-8").split()))
    for text in texts:
        for gone in ("it is not synced, and nothing else writes it", "that note's date, or the first build this copy "
                     "recorded"):
            assert gone not in text, gone
        assert "never moves it back" in text and "not bound to" in text and "refuse" in text
    assert "a review that arrives through sync naming an id that is not on this copy's list counts" not in core
    assert "this copy recorded the review" in core and '"yourdomain" names as any label of the host' in core
    if readme.exists():
        assert "never counts" in texts[1] and "even when it names someone on the list" in texts[1]
    for doc in (signoff.__doc__, RV.__doc__, T.__doc__, db.__doc__):
        flat = " ".join(doc.split())
        assert "nothing else writes it" not in flat
        assert "a review that arrives through sync naming an id" not in flat
    sign = " ".join(signoff.__doc__.split())
    assert "push and pull refuse it" in sign and "so a curated sign-off is not bound to any token" in sign
    assert "A page names a reviewer only for a review this copy recorded." in sign
    rv = " ".join(RV.__doc__.split())
    assert "push and pull refuse any table that is not" in rv and "A sign-off in a curated file is not bound to a " \
        "token" in rv
    assert "A pull is trusted data only as far as the shared database is" in " ".join(T.__doc__.split())


def test_names_fold_case_before_the_look_alikes_and_keep_role_word_surnames(con):
    """Re-check 5: "Jane Doe ЕЅԚ" (Cyrillic capitals reading ESQ) and "Jane Doe ЈԀ" were stored, since the look-alike
    table was read before case was folded; and real surnames were refused (Jane Lawyer, Agnes Clerk, John Staff).
    A role word that is also a surname now passes as the surname after one given name, and only there."""
    from lexflow import reviewers as RV
    assert signoff.skeleton("ЕЅԚ") == "esq" and signoff.skeleton("ЈԀ") == "jd" and signoff.skeleton("ᎫᎠ") == "jd"
    for name in ("Jane Doe ЕЅԚ", "Jane Doe ЈԀ", "Jane Doe ᎫᎠ", "Jane Doe ESQ", "Lawyer", "Clerk", "Staff",
                 "Jane Doe Lawyer", "Clerk Smith", "Lawyer Jane", "City Clerk", "Legal Staff", "Jane Lawyers",
                 "Attorney Lawyer", "Anonymous Clerk"):
        assert signoff.clean_name(name)[1], name
    assert "esq" in " ".join(signoff.clean_name("Jane Doe ЕЅԚ")[1])
    for name in ("Jane Lawyer", "Agnes Clerk", "John Staff", "Mary-Jane Lawyer", "J. Clerk"):
        assert signoff.clean_name(name) == (name, []), name
    assert RV.add(con, "Agnes Clerk", "clerk", added_by="operator")["name"] == "Agnes Clerk"
    for name in RECHECK4_REFUSED:                                             # still refused
        assert signoff.clean_name(name)[1], name
    for name in CLEAN.values():                                               # still names
        assert signoff.clean_name(name) == (name, []), name
    # "yourdomain" as any label of the corrections address's host, not only the first
    for value in ("https://www.yourdomain.com/corrections", "corrections@mail.yourdomain.com",
                  "https://corrections.yourdomain.org/", "fix@lexflow.your-site.net", "https://www.mydomain.org/x"):
        assert "a placeholder address" in LX.corrections_problem(value), value
    for value in ("https://lexipedia.xyz/report", "corrections@notyourdomain.com", "fixes@lexipedia.xyz"):
        assert LX.corrections_problem(value) is None, value
