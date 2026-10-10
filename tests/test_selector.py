"""The learned selector: wide candidates, actor inference, held-out training, and the stacked model."""
from lexflow.extract import selector as SEL
from lexflow.extract import strategies as ST
from lexflow.extract.ollama import check_facts
from lexflow.extract.segment import segment

TEXT = """(a) A person may submit a written application to the custodian.
(b) A custodian who denies the application shall:
(1) within 10 working days, give the applicant a written statement of the reasons for the denial;
(2) allow inspection of any part of the record that is subject to inspection.
(c) Any reasonably segregable portion of a public record shall be provided to any person requesting the record.
(d) If the Mayor decides the record is public, he shall order the public body to disclose the record.
(e) Failure to respond within the time allowed shall be deemed a denial of the request."""


def test_wide_candidates_cover_list_items_passives_and_pronouns():
    clauses = segment(TEXT)
    rules = {d["clause"].id for d in ST.rule_drafts(clauses, "records")}
    wide = SEL.wide_drafts(clauses, "records")
    by_text = {d["clause"].text[:30]: d for d in wide}
    assert len(wide) > len(rules)
    item = next(d for t, d in by_text.items() if t.startswith("within 10 working days"))
    assert item["origin"] == "list" and "custodian" in item["actor"] and item["modality"] == "obligation"
    assert item["deadline"]["amount"] == 10 and item["deadline"]["unit"] == "business_days"
    passive = next(d for t, d in by_text.items() if t.startswith("Any reasonably segregable"))
    assert passive["actor_src"] == "default"
    mayor = next(d for t, d in by_text.items() if t.startswith("If the Mayor"))
    assert mayor["actor"].lower() == "mayor"
    deemed = next(d for t, d in by_text.items() if t.startswith("Failure to respond"))
    assert deemed["modality"] == "none" and deemed["deemed"]


def test_actor_kinds_follow_the_references():
    ref = SEL.Reference("zz", "records", "", [], [], {"Official custodian": "official", "Requester": "private-party"})
    assert SEL.actor_kind("custodian", [ref]) == "official"
    assert SEL.actor_kind("custodian", [ref], exclude_state="zz") == "official"      # the rules agree here
    assert SEL.actor_kind("public body") == "public-body"
    assert SEL.actor_kind("Superior Court") == "court"
    assert SEL.actor_kind("County, city or town") == "other-government"


def test_stacked_selector_holds_out_the_state_and_quotes_exactly(va_statutes):
    from lexflow.extract import benchmark as B
    refs = SEL.references()
    assert refs and all(len(r.labels) == len(r.cands) for r in refs)
    state, question, texts, text, gold, _ = B.load_case("va.records")
    sel = SEL.Selector(question, state, None, use_embeddings=False).fit()
    assert all(r.state != "va" for r in sel.refs)
    r = ST.run("stack_nb", text, section=texts[0].section, title=texts[0].title, code=texts[0].code,
               jurisdiction="Virginia", question=question, state=state)
    assert r.facts is not None and not check_facts(r.facts, text)
    assert B.equivalence(r.facts, gold)["value"] > 0.3
    o = B.oracle("va.records")
    assert o["wide"]["recall"] >= o["rules"]["recall"]


def test_hard_wrapped_lines_are_joined_into_exact_clauses():
    text = ("§ 89. General provisions.\nThe provisions of this section apply to access to all records, except as\n"
            "hereinafter specified:\n  1. (a) The committee on open government is continued and shall consist\n"
            "of the lieutenant governor or the delegate of such officer.\n  2. The agency shall respond.")
    clauses = segment(text)
    assert all(text[c.start:c.start + len(c.text)] == c.text for c in clauses)
    committee = next(c for c in clauses if c.text.startswith("The committee"))
    assert committee.text.endswith("such officer.") and committee.label == "1.a"
    assert any(c.text == "The agency shall respond." and c.label == "2" for c in clauses)


def test_procedure_without_a_duty_word_becomes_a_candidate():
    text = ("(a) The department files a document by stamping it as filed.\n"
            "(b) Upon receipt of the complaint, the public office has three business days to cure the failure.\n"
            "(c) For filing articles of organization, $100.\n"
            "(d) A limited liability company is formed when the articles become effective.\n"
            "(e) This chapter applies to every company.")
    by_origin = {d["origin"]: d for d in SEL.wide_drafts(segment(text), "business")}
    assert by_origin["present"]["actor"] == "department"
    assert by_origin["has_time"]["deadline"]["amount"] == 3
    assert by_origin["fee"]["kind"] == "payment" and by_origin["fee"]["actor"] == "organizer"
    assert by_origin["effect"]["modality"] == "none"
    assert not any(d["clause"].text.startswith("This chapter") for d in by_origin.values())


def test_labels_pair_steps_and_candidates_by_actor_kind():
    clause = segment("(c) A public body, upon request reasonably describing any public record, shall respond.")[0]
    primary = {"clause": clause, "actor": "public body", "origin": "rule"}
    trigger = {"clause": clause, "actor": "requester", "origin": "trigger"}
    facts = {"actors": [{"id": "req", "kind": "private-party"}, {"id": "pb", "kind": "public-body"}],
             "steps": [{"actor": "pb", "source": {"section": None, "quote": "shall respond"}}]}
    labels, kinds = SEL.labels_for([trigger, primary], facts)
    assert labels == [False, True] and kinds[1] == "public-body"      # one step: the response, not the request
    facts["steps"].insert(0, {"actor": "req", "source": {"section": None, "quote": "upon request"}})
    assert SEL.labels_for([trigger, primary], facts)[0] == [True, True]


def test_list_items_carry_their_lead_in_and_deadlines_are_borrowed():
    text = ("(a) A custodian who denies the application shall:\n"
            "(1) within 10 working days, give the applicant a written statement of the reasons;\n"
            "(2) allow inspection of any part of the record.\n"
            "(b) The custodian shall notify the applicant of the delay.\n"
            "(c) Within 30 days after receiving the application, the custodian shall:\n"
            "(1) grant or deny the application.")
    cands = SEL.wide_drafts(segment(text), "records")
    item = next(d for d in cands if d["clause"].text.startswith("allow inspection"))
    assert item["lead_in"].startswith("A custodian who denies") and SEL.view(item).startswith("A custodian")
    assert item["deadline"] is None              # the 10 days belong to item (1), not to its sibling
    grant = next(d for d in cands if d["clause"].text.startswith("grant or deny"))
    assert grant["deadline"]["amount"] == 30 and grant.get("deadline_src") == "parent"
    lead = next(d for d in cands if d["clause"].text.startswith("A custodian who denies"))
    assert lead["deadline"]["amount"] == 10 and lead.get("deadline_src") == "first item"
    plain = next(d for d in cands if d["clause"].text.startswith("The custodian shall notify"))
    assert SEL.view(plain) == plain["clause"].text


def test_deadline_words_and_compounds():
    for t, want in [("The notice shall be published within one hundred twenty days after filing.", (120, "days")),
                    ("Such extension shall not exceed 10 days (except Saturdays, Sundays, and legal holidays).",
                     (10, "business_days")),
                    ("Review is complete at the end of the second business day after the denial.", (2, "business_days")),
                    ("The requestor shall be advised within seven or 14 business days after receipt.",
                     (7, "business_days")),
                    ("The board shall decide within forty-five days of the hearing.", (45, "days"))]:
        c = segment(t)[0]
        assert c.deadline and (c.deadline["amount"], c.deadline["unit"]) == want, t


def test_knn_votes_with_the_nearest_labels():
    import numpy as np
    train = np.eye(4, dtype="float32")
    y = np.array([1, 0, 1, 0], dtype="float32")
    x = np.array([[0.9, 0.1, 0, 0], [0, 0.95, 0, 0.05]], dtype="float32")
    x /= np.linalg.norm(x, axis=1, keepdims=True)
    s = SEL.knn(x, train, y, k=2)
    assert s[0] > 0.9 and s[1] < 0.1
