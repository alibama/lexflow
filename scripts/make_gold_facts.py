"""Answer key: the LegalProcessFacts a good model should extract from Albemarle § 17-211.

Used to (1) test the facts->BPMN compiler and (2) score local Ollama models.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lexflow.extract.ollama import check_facts  # noqa: E402
from lexflow.extract.schema import LegalProcessFacts  # noqa: E402
from lexflow.gold import albemarle_17_211  # noqa: E402


def q(sub, quote, section="17-211"):
    return {"section": section, "subsection": sub, "quote": quote}


facts = {
    "process_name": "Review of administrator's action; judicial review",
    "trigger": "A person is aggrieved by an action or inaction of the VESMP administrator",
    "trigger_source": q(None, "Any person aggrieved by an action or inaction of the administrator may request that the County review the action or inaction"),
    "actors": [
        {"id": "appellant", "name": "Appellant (aggrieved person with standing)", "kind": "private-party",
         "source": q("C", 'Any person who has standing under subsection (B) (hereinafter, the "appellant")')},
        {"id": "county", "name": "Albemarle County", "kind": "public-body",
         "source": q(None, "request that the County review the action or inaction")},
        {"id": "administrator", "name": "VESMP administrator", "kind": "official",
         "source": q("A", "Any of the following actions by the administrator may be reviewed")},
        {"id": "clerk", "name": "Clerk of the Board of Supervisors", "kind": "official",
         "source": q("C", "the clerk of the board of supervisors")},
        {"id": "hearing_officer", "name": "Director of Community Development (hearing officer)", "kind": "official",
         "source": q("D.1", "the Director of Community Development, who will act as the hearing officer for the County")},
        {"id": "circuit_court", "name": "Circuit court", "kind": "court",
         "source": q("F", "an appeal is filed by the person aggrieved in the circuit court")},
    ],
    "steps": [
        {"id": "file_request", "actor": "appellant", "action": "File written request for hearing",
         "kind": "filing", "modality": "permission", "after": [], "recipient": "clerk",
         "deadline": {"amount": 30, "unit": "days", "anchor": "date of notice of the action",
                      "consequence": "right-lapses", "source": q("C.1", "Within 30 days after the date of notice of the action")},
         "source": q("C", "may request in writing that the County conduct a hearing, provided that the request is filed with the clerk of the board of supervisors")},
        {"id": "determine_standing", "actor": "hearing_officer", "action": "Determine reviewability and standing",
         "kind": "decision", "modality": "none", "after": ["file_request"], "decision": "standing",
         "source": q("B", "has standing to seek review under this section")},
        {"id": "hold_hearing", "actor": "hearing_officer", "action": "Hold hearing with appellant and administrator",
         "kind": "hearing", "modality": "obligation", "after": ["determine_standing"], "condition": "has_standing",
         "deadline": {"amount": 30, "unit": "days", "anchor": "receipt of the petition requesting a hearing",
                      "consequence": "directory-only",
                      "source": q("D.2", "The failure of the hearing officer to conduct the hearing within the 30-day period or any extension thereof does not divest the hearing officer of jurisdiction to consider the appeal.")},
         "source": q("D.2", "The hearing will be held within 30 days after receipt of the petition requesting a hearing.")},
        {"id": "consider_evidence", "actor": "hearing_officer", "action": "Consider relevant law and evidence",
         "kind": "review", "modality": "obligation", "after": ["hold_hearing"],
         "source": q("D.3", "the hearing officer will consider relevant and material laws and evidence")},
        {"id": "keep_record", "actor": "hearing_officer", "action": "Compile the hearing record",
         "kind": "record", "modality": "obligation", "after": ["hold_hearing"],
         "source": q("D.4", "The record of the hearing will be composed of relevant files, a recording of the hearing, and other writings.")},
        {"id": "issue_decision", "actor": "hearing_officer", "action": "Issue written decision",
         "kind": "notice", "modality": "obligation", "after": ["consider_evidence", "keep_record"], "recipient": "appellant",
         "source": q("F", "the hearing officer's written decision")},
        {"id": "appeal_to_court", "actor": "appellant", "action": "File appeal in circuit court",
         "kind": "filing", "modality": "right", "after": ["issue_decision"], "recipient": "circuit_court",
         "deadline": {"amount": 30, "unit": "days", "anchor": "date of the hearing officer's written decision",
                      "consequence": "right-lapses", "source": q("F", "within 30 days after the date of the hearing officer's written decision")},
         "source": q("F", "provided that an appeal is filed by the person aggrieved in the circuit court within 30 days after the date of the hearing officer's written decision")},
        {"id": "transcribe", "actor": "county", "action": "Transcribe the hearing recording",
         "kind": "record", "modality": "obligation", "after": ["appeal_to_court"],
         "source": q("D.4", "The recording of the hearing will be transcribed only if judicial review of the decision is sought under subsection (F).")},
    ],
    "decisions": [{
        "id": "standing", "question": "Is the action reviewable and does this person have standing?", "hit_policy": "FIRST",
        "inputs": [{"name": "action_type", "label": "Administrator action", "type": "string"},
                   {"name": "person_role", "label": "Person's role", "type": "string"},
                   {"name": "aggrieved", "label": "Aggrieved?", "type": "boolean"}],
        "outputs": [{"name": "reviewable", "label": "Reviewable", "type": "boolean"},
                    {"name": "has_standing", "label": "Has standing", "type": "boolean"}],
        "rules": [
            {"when": ['"disapproval","conditional_approval","variance_disapproval","status_determination","general_permit_decision","enforcement_decision","failure_to_act"',
                      '"applicant","permitted_operator","general_permit_subject"', "true"], "then": ["true", "true"],
             "source": q("B", "who is aggrieved by any action or inaction under subsections (A)(i) through (vii) has standing to seek review")},
            {"when": ['"approval_downstream_issue"', '"downstream_owner"', "true"], "then": ["true", "true"],
             "source": q("B", "Any downstream owner who is aggrieved by an action under subsection (A)(viii) has standing to seek review under this section.")},
            {"when": ['not("other")', "-", "-"], "then": ["true", "false"],
             "source": q("A", "Any of the following actions by the administrator may be reviewed")},
            {"when": ["-", "-", "-"], "then": ["false", "false"],
             "source": q("A", "Any of the following actions by the administrator may be reviewed")},
        ]}],
    "outcomes": [],
    "cross_references": [
        {"citation": "Va. Code § 62.1-44.15:46", "role": "governs judicial review",
         "source": q("F", "Judicial review will be conducted as provided in Virginia Code § 62.1-44.15:46.")},
        {"citation": "9VAC25-875-560(19)", "role": "downstream-owner compliance issue reviewable under (A)(viii)",
         "source": q("A", "compliance with 9VAC25-875-560(19)")},
        {"citation": "Albemarle County Code §§ 17-300 to 17-306", "role": "determinations reviewable under (A)(iv)",
         "source": q("A", "any determination made under sections 17-300 through 17-306")},
    ],
    "gaps": ["Subsection E is missing from the source chunks; the written decision is presupposed by (F).",
             "The section does not say who determines standing.",
             "The consequence of an untimely request is not stated."],
}

model = LegalProcessFacts.model_validate(facts)
text = albemarle_17_211().texts[0].text
problems = check_facts(model, text)
assert not problems, problems
out = ROOT / "fixtures" / "gold" / "albemarle_17_211.facts.json"
out.write_text(json.dumps(json.loads(model.model_dump_json()), indent=2, ensure_ascii=False))
print(out, "steps:", len(model.steps), "quotes ok")
