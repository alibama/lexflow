"""Hand-built "gold" models for two real Virginia provisions.

They exercise the full DOM (pools, lanes, message flows, event-based
gateways, interrupting and non-interrupting timers, nested and event
sub-processes, call activity, data objects/stores, business-rule tasks
bound to DMN) and double as the answer key for scoring local-LLM extraction.

Text comes from LOCUS-v1 rows rebuilt by :mod:`lexflow.text.sections`.
Every ``quote`` must be an exact substring of that rebuilt text; the test
suite enforces this (a cheap hallucination check that also applies to LLM
output).
"""
from __future__ import annotations

import json
from pathlib import Path

from .ir import (Actor, Annotation, DataRef, Decision, InputClause, LegalProcessModel, Lane,
                 MessageFlow, Node, OutputClause, Participant, Process, Provenance, Review, Rule,
                 SectionText, SequenceFlow, Source, Timer)
from .text.sections import resegment

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures" / "locus" / "va_samples.json"
LOCUS_NOTE = ("Text from LocalLaws/LOCUS-v1 (CC BY-NC 4.0), rebuilt and cleaned by lexflow; "
              "verify against the official code before publishing.")


def _sections(jurisdiction: str, code: str, key: str, value: str) -> dict[str, "object"]:
    rows = [r for r in json.loads(FIXTURE.read_text())["rows"] if r[key] == value]
    return {s.number: s for s in resegment(rows, code, jurisdiction)}


def _src_factory(code: str, jurisdiction: str, url: str):
    def S(section: str, sub: str | None, quote: str | None, grounding: str = "explicit",
          note: str | None = None) -> Source:
        sub_txt = "".join(f"({p})" for p in sub.split(".")) if sub else ""
        return Source(citation=f"{code} § {section}{sub_txt}", section=section, subsection=sub,
                      code=code, jurisdiction=jurisdiction, quote=quote, url=url,
                      grounding=grounding, note=note)
    return S


def va_code(section: str, quote: str | None, grounding: str = "explicit") -> Source:
    return Source(citation=f"Va. Code § {section}", section=section, code="Code of Virginia",
                  jurisdiction="va", quote=quote, grounding=grounding,
                  url=f"https://law.lis.virginia.gov/vacode/{section}/")


VA_62_1_44_15_46 = (
    "A final decision by a locality, when serving as a VESMP authority, shall be subject to judicial "
    "review, provided that an appeal is filed in the appropriate court within 30 days from the date of any "
    "written decision adversely affecting the rights, duties, or privileges of the person engaging in or "
    "proposing to engage in a land-disturbing activity.")


# =============================================================== Albemarle 17-211
def albemarle_17_211() -> LegalProcessModel:
    code, juris = "Albemarle County Code", "va/albemarle_county"
    secs = _sections(juris, code, "county", "albemarle_county")
    sec = secs["17-211"]
    S = _src_factory(code, juris, "https://library.municode.com/va/albemarle_county/codes/code_of_ordinances")
    win1 = S("17-211", "C.1", "Within 30 days after the date of notice of the action")
    win2 = S("17-211", "C.2", "Within 30 days after the date by which the administrator was required to act but failed to do so")
    win3 = S("17-211", "C.3", "Within 30 days after the date of the administrator's approval of the ESM plan or land-disturbance permit")
    gap_e = ("Subsection E is absent from the LOCUS chunks (letters jump D to F); the written decision "
             "is presupposed by subsection F.")
    actors = [
        Actor(id="appellant", name="Aggrieved person (appellant)", kind="private-party",
              description="Owner/applicant, permitted operator, general-permit subject, or downstream owner"),
        Actor(id="county", name="Albemarle County", kind="public-body", wikidata="Q488653"),
        Actor(id="administrator", name="VESMP administrator", kind="official"),
        Actor(id="clerk", name="Clerk of the Board of Supervisors", kind="official"),
        Actor(id="hearing_officer", name="Director of Community Development (hearing officer)", kind="official"),
        Actor(id="circuit_court", name="Circuit court", kind="court"),
    ]
    hearing = Node(
        id="ph_hearing", type="subProcess", name="Conduct hearing",
        sources=[S("17-211", "D.1", "The hearing before the County will be conducted by the Director of Community Development, who will act as the hearing officer for the County.")],
        nodes=[
            Node(id="h_start", type="startEvent", name="Hearing opens"),
            Node(id="h_evidence", type="userTask", name="Take evidence from owner, administrator, others",
                 sources=[S("17-211", "D.3", "evidence presented by the owner, the administrator, and any other person as the hearing officer deems to be necessary for a complete review of the matter")]),
            Node(id="h_consider", type="userTask", name="Consider relevant law and evidence",
                 deontic="obligation", bearer="hearing_officer",
                 sources=[S("17-211", "D.3", "the hearing officer will consider relevant and material laws and evidence")]),
            Node(id="h_record", type="task", name="Compile the hearing record", data_outputs=["hearing_record"],
                 sources=[S("17-211", "D.4", "The record of the hearing will be composed of relevant files, a recording of the hearing, and other writings.")]),
            Node(id="h_end", type="endEvent", name="Hearing closed"),
        ],
        flows=[SequenceFlow(id="hf1", source="h_start", target="h_evidence"),
               SequenceFlow(id="hf2", source="h_evidence", target="h_consider"),
               SequenceFlow(id="hf3", source="h_consider", target="h_record"),
               SequenceFlow(id="hf4", source="h_record", target="h_end")],
    )
    phase = Node(
        id="c_phase", type="subProcess", name="Hold hearing (30-day target)", lane="ln_ho",
        sources=[S("17-211", "D.2", "The hearing will be held within 30 days after receipt of the petition requesting a hearing.")],
        nodes=[
            Node(id="ph_start", type="startEvent", name="Petition with grounds received"),
            Node(id="ph_schedule", type="userTask", name="Set a date both parties can attend",
                 deontic="obligation", bearer="hearing_officer",
                 sources=[S("17-211", "D.2", "The hearing will be held on a date and at a time at which both the appellant and the administrator may be present.")]),
            Node(id="ph_ext", type="boundaryEvent", name="Appellant asks for extension", attached_to="ph_schedule",
                 interrupting=False, event="message", ref="Extension request",
                 sources=[S("17-211", "D.2", "At the request of the appellant, the hearing officer may extend the hearing date beyond the 30-day period.")]),
            Node(id="ph_extend", type="userTask", name="Decide whether to extend the date",
                 deontic="permission", bearer="hearing_officer",
                 sources=[S("17-211", "D.2", "the hearing officer may extend the hearing date beyond the 30-day period")]),
            Node(id="ph_ext_end", type="endEvent", name="Extension decided"),
            hearing,
            Node(id="ph_end", type="endEvent", name="Hearing held"),
        ],
        flows=[SequenceFlow(id="pf1", source="ph_start", target="ph_schedule"),
               SequenceFlow(id="pf2", source="ph_schedule", target="ph_hearing"),
               SequenceFlow(id="pf3", source="ph_hearing", target="ph_end"),
               SequenceFlow(id="pf4", source="ph_ext", target="ph_extend"),
               SequenceFlow(id="pf5", source="ph_extend", target="ph_ext_end")],
    )
    county = Process(
        id="proc_county", name="Albemarle County: review of administrator's action",
        documentation="Albemarle County Code § 17-211 (VESMP appeals).",
        lanes=[Lane(id="ln_admin", name="VESMP administrator", actor="administrator"),
               Lane(id="ln_clerk", name="Clerk of the Board of Supervisors", actor="clerk"),
               Lane(id="ln_ho", name="Hearing officer (Dir. of Community Development)", actor="hearing_officer")],
        data=[DataRef(id="hearing_record", name="Hearing record (files, recording, writings)",
                      sources=[S("17-211", "D.4", "The record of the hearing will be composed of relevant files, a recording of the hearing, and other writings.")]),
              DataRef(id="transcript", name="Transcript of hearing recording",
                      sources=[S("17-211", "D.4", "The recording of the hearing will be transcribed only if judicial review of the decision is sought under subsection (F).")])],
        nodes=[
            Node(id="c_start", type="startEvent", name="Reviewable action or failure to act", lane="ln_admin",
                 sources=[S("17-211", "A", "Any of the following actions by the administrator may be reviewed")]),
            Node(id="c_notify", type="sendTask", name="Give notice of the action", lane="ln_admin", ref="Notice of action",
                 sources=[S("17-211", "C.1", "Within 30 days after the date of notice of the action", "implied",
                            "Notice is presupposed by the C.1 filing window; notice rules are outside this section.")]),
            Node(id="c_await_request", type="eventBasedGateway", name="Request within 30 days?", lane="ln_clerk"),
            Node(id="c_request", type="intermediateCatchEvent", name="Request for hearing filed", lane="ln_clerk",
                 event="message", ref="Request for hearing",
                 sources=[S("17-211", "C", "may request in writing that the County conduct a hearing, provided that the request is filed with the clerk of the board of supervisors")]),
            Node(id="c_window", type="intermediateCatchEvent", name="30 days pass, no request", lane="ln_clerk",
                 event="timer", timer=Timer(value="P30D", anchor="notice date / required-action date / approval date"),
                 sources=[win1, win2, win3]),
            Node(id="c_lapsed", type="endEvent", name="Review unavailable (untimely)", lane="ln_clerk",
                 sources=[S("17-211", "C", "provided that the request is filed with the clerk of the board of supervisors", "implied",
                            "The section states the window but not the consequence of missing it.")]),
            Node(id="c_grounds_gw", type="exclusiveGateway", name="Request states grounds?", lane="ln_clerk", default="f8",
                 sources=[S("17-211", "C", "The request must specify the grounds for the appeal.")]),
            Node(id="c_await_grounds", type="intermediateCatchEvent", name="Grounds supplied", lane="ln_clerk",
                 event="message", ref="Grounds for appeal",
                 sources=[S("17-211", "C", "The 30-day period within which the hearing is held will not begin unless and until the request specifies the grounds for the appeal.")]),
            Node(id="c_grounds_join", type="exclusiveGateway", name="", lane="ln_clerk"),
            Node(id="c_review_rules", type="businessRuleTask", name="Determine reviewability and standing", lane="ln_ho",
                 decision_ref="d_review_standing",
                 documentation="Who decides standing is not stated in § 17-211; placed with the hearing officer (assumption).",
                 sources=[S("17-211", "A", "Any of the following actions by the administrator may be reviewed"),
                          S("17-211", "B", "has standing to seek review under this section")]),
            Node(id="c_standing_gw", type="exclusiveGateway", name="Reviewable and has standing?", lane="ln_ho", default="f13"),
            Node(id="c_dismiss", type="endEvent", name="Not reviewable or no standing", lane="ln_ho",
                 sources=[S("17-211", "B", "has standing to seek review under this section", "implied",
                            "Disposition of requests without standing is not specified.")]),
            phase,
            Node(id="c_target", type="boundaryEvent", name="30 days after receipt", attached_to="c_phase",
                 interrupting=False, event="timer",
                 timer=Timer(value="P30D", anchor="receipt of the petition (clock starts once grounds are stated)", strict=False),
                 sources=[S("17-211", "D.2", "The hearing will be held within 30 days after receipt of the petition requesting a hearing.")]),
            Node(id="c_target_end", type="endEvent", name="Target missed; jurisdiction kept", lane="ln_ho",
                 sources=[S("17-211", "D.2", "The failure of the hearing officer to conduct the hearing within the 30-day period or any extension thereof does not divest the hearing officer of jurisdiction to consider the appeal.")]),
            Node(id="c_decide", type="sendTask", name="Issue written decision", lane="ln_ho", ref="Written decision",
                 data_inputs=["hearing_record"], deontic="duty-to-decide", bearer="hearing_officer",
                 sources=[S("17-211", "F", "the hearing officer's written decision", "implied", gap_e)]),
            Node(id="c_after_gw", type="eventBasedGateway", name="Judicial review sought?", lane="ln_clerk"),
            Node(id="c_jr_notice", type="intermediateCatchEvent", name="Notice of appeal received", lane="ln_clerk",
                 event="message", ref="Notice of appeal",
                 sources=[S("17-211", "D.4", "The recording of the hearing will be transcribed only if judicial review of the decision is sought under subsection (F).", "implied")]),
            Node(id="c_transcribe", type="task", name="Transcribe the hearing recording", lane="ln_clerk",
                 data_inputs=["hearing_record"], data_outputs=["transcript"],
                 sources=[S("17-211", "D.4", "The recording of the hearing will be transcribed only if judicial review of the decision is sought under subsection (F).")]),
            Node(id="c_transmit", type="sendTask", name="Send record to circuit court", lane="ln_clerk", ref="Hearing record",
                 data_inputs=["transcript"],
                 sources=[S("17-211", "F", "Judicial review will be conducted as provided in Virginia Code § 62.1-44.15:46.", "assumed",
                            "How the record reaches the court is governed by court rules, not § 17-211.")]),
            Node(id="c_jr_end", type="endEvent", name="Record before the court", lane="ln_clerk"),
            Node(id="c_jr_window", type="intermediateCatchEvent", name="30 days after decision", lane="ln_clerk",
                 event="timer", timer=Timer(value="P30D", anchor="date of the hearing officer's written decision"),
                 sources=[S("17-211", "F", "within 30 days after the date of the hearing officer's written decision"),
                          va_code("62.1-44.15:46", "within 30 days from the date of any written decision adversely affecting the rights, duties, or privileges")]),
            Node(id="c_final", type="endEvent", name="County decision final", lane="ln_clerk",
                 sources=[S("17-211", "F", "A final decision by the hearing officer under this section may be subject to judicial review", "implied")]),
        ],
        flows=[
            SequenceFlow(id="f1", source="c_start", target="c_notify"),
            SequenceFlow(id="f2", source="c_notify", target="c_await_request"),
            SequenceFlow(id="f3", source="c_await_request", target="c_request"),
            SequenceFlow(id="f4", source="c_await_request", target="c_window"),
            SequenceFlow(id="f5", source="c_window", target="c_lapsed"),
            SequenceFlow(id="f6", source="c_request", target="c_grounds_gw"),
            SequenceFlow(id="f7", source="c_grounds_gw", target="c_grounds_join", name="Grounds stated", condition="grounds_stated"),
            SequenceFlow(id="f8", source="c_grounds_gw", target="c_await_grounds", name="Grounds missing"),
            SequenceFlow(id="f9", source="c_await_grounds", target="c_grounds_join"),
            SequenceFlow(id="f10", source="c_grounds_join", target="c_review_rules"),
            SequenceFlow(id="f11", source="c_review_rules", target="c_standing_gw"),
            SequenceFlow(id="f12", source="c_standing_gw", target="c_phase", name="Yes", condition="reviewable and has_standing"),
            SequenceFlow(id="f13", source="c_standing_gw", target="c_dismiss", name="No"),
            SequenceFlow(id="f14", source="c_phase", target="c_decide"),
            SequenceFlow(id="f15", source="c_target", target="c_target_end"),
            SequenceFlow(id="f16", source="c_decide", target="c_after_gw"),
            SequenceFlow(id="f17", source="c_after_gw", target="c_jr_notice"),
            SequenceFlow(id="f18", source="c_after_gw", target="c_jr_window"),
            SequenceFlow(id="f19", source="c_jr_notice", target="c_transcribe"),
            SequenceFlow(id="f20", source="c_transcribe", target="c_transmit"),
            SequenceFlow(id="f21", source="c_transmit", target="c_jr_end"),
            SequenceFlow(id="f22", source="c_jr_window", target="c_final"),
        ],
        annotations=[Annotation(id="note_soft", text="Soft deadline: missing it does not end the appeal (§ 17-211(D)(2)).",
                                attached_to=["c_target"]),
                     Annotation(id="note_gap", text="Subsection E missing from source; decision step inferred from (F).",
                                attached_to=["c_decide"])],
    )
    appellant = Process(
        id="proc_appellant", name="Appellant",
        nodes=[
            Node(id="a_start", type="startEvent", name="Aggrieved by action or inaction",
                 sources=[S("17-211", None, "Any person aggrieved by an action or inaction of the administrator may request that the County review the action or inaction")]),
            Node(id="a_decide", type="userTask", name="Decide whether to ask for County review",
                 deontic="permission", bearer="appellant",
                 sources=[S("17-211", "C", "may request in writing that the County conduct a hearing")]),
            Node(id="a_window", type="boundaryEvent", name="30-day window closes", attached_to="a_decide",
                 event="timer", timer=Timer(value="P30D", anchor="notice date / required-action date / approval date"),
                 sources=[win1, win2, win3]),
            Node(id="a_lapsed", type="endEvent", name="County review lapsed",
                 sources=[S("17-211", "C", "provided that the request is filed with the clerk of the board of supervisors", "implied")]),
            Node(id="a_gw", type="exclusiveGateway", name="Request review?", default="a4"),
            Node(id="a_no", type="endEvent", name="No review requested"),
            Node(id="a_file", type="sendTask", name="File written request stating grounds", ref="Request for hearing",
                 deontic="permission", bearer="appellant",
                 sources=[S("17-211", "C", "provided that the request is filed with the clerk of the board of supervisors"),
                          S("17-211", "C", "The request must specify the grounds for the appeal.")]),
            Node(id="a_wait", type="intermediateCatchEvent", name="Written decision received", event="message", ref="Written decision",
                 sources=[S("17-211", "F", "the hearing officer's written decision", "implied", gap_e)]),
            Node(id="a_decide_jr", type="userTask", name="Decide whether to seek judicial review",
                 deontic="right", bearer="appellant",
                 sources=[S("17-211", "F", "A final decision by the hearing officer under this section may be subject to judicial review")]),
            Node(id="a_jr_window", type="boundaryEvent", name="30 days after decision", attached_to="a_decide_jr",
                 event="timer", timer=Timer(value="P30D", anchor="date of the hearing officer's written decision"),
                 sources=[S("17-211", "F", "within 30 days after the date of the hearing officer's written decision"),
                          va_code("62.1-44.15:46", "within 30 days from the date of any written decision adversely affecting the rights, duties, or privileges")]),
            Node(id="a_time_barred", type="endEvent", name="Judicial review time-barred",
                 sources=[S("17-211", "F", "provided that an appeal is filed by the person aggrieved in the circuit court within 30 days after the date of the hearing officer's written decision", "implied")]),
            Node(id="a_gw2", type="exclusiveGateway", name="Seek judicial review?", default="a10"),
            Node(id="a_accept", type="endEvent", name="Decision accepted"),
            Node(id="a_appeal", type="sendTask", name="File appeal in circuit court", ref="Petition for appeal",
                 sources=[S("17-211", "F", "provided that an appeal is filed by the person aggrieved in the circuit court within 30 days after the date of the hearing officer's written decision")]),
            Node(id="a_notify", type="sendTask", name="Notify the County of the appeal", ref="Notice of appeal",
                 sources=[S("17-211", "D.4", "The recording of the hearing will be transcribed only if judicial review of the decision is sought under subsection (F).", "assumed",
                            "How the County learns of the appeal (service of process) is outside § 17-211.")]),
            Node(id="a_jr", type="callActivity", name="Judicial review (Va. Code § 62.1-44.15:46)",
                 called_element="va_62_1_44_15_46_judicial_review",
                 sources=[S("17-211", "F", "Judicial review will be conducted as provided in Virginia Code § 62.1-44.15:46."),
                          va_code("62.1-44.15:46", "A final decision by a locality, when serving as a VESMP authority, shall be subject to judicial review")]),
            Node(id="a_end", type="endEvent", name="Judicial review concluded"),
        ],
        flows=[
            SequenceFlow(id="a1", source="a_start", target="a_decide"),
            SequenceFlow(id="a2", source="a_decide", target="a_gw"),
            SequenceFlow(id="a3", source="a_gw", target="a_file", name="Yes", condition="request_review"),
            SequenceFlow(id="a4", source="a_gw", target="a_no", name="No"),
            SequenceFlow(id="a5", source="a_window", target="a_lapsed"),
            SequenceFlow(id="a6", source="a_file", target="a_wait"),
            SequenceFlow(id="a7", source="a_wait", target="a_decide_jr"),
            SequenceFlow(id="a8", source="a_decide_jr", target="a_gw2"),
            SequenceFlow(id="a9", source="a_gw2", target="a_appeal", name="Yes", condition="seek_judicial_review"),
            SequenceFlow(id="a10", source="a_gw2", target="a_accept", name="No"),
            SequenceFlow(id="a11", source="a_appeal", target="a_notify"),
            SequenceFlow(id="a12", source="a_notify", target="a_jr"),
            SequenceFlow(id="a13", source="a_jr", target="a_end"),
            SequenceFlow(id="a14", source="a_jr_window", target="a_time_barred"),
        ],
    )
    owner_roles = '"applicant","permitted_operator","general_permit_subject"'
    standing = Decision(
        id="d_review_standing", name="Reviewability, standing and filing window",
        question="Can this person get County review of this administrator action, and from when does the 30-day window run?",
        hit_policy="FIRST",
        inputs=[InputClause(id="in_action", label="Administrator action (§ 17-211(A))", expression="action_type",
                            values=['"disapproval"', '"conditional_approval"', '"variance_disapproval"', '"status_determination"',
                                    '"general_permit_decision"', '"enforcement_decision"', '"failure_to_act"',
                                    '"approval_downstream_issue"', '"other"']),
                InputClause(id="in_role", label="Person's role", expression="person_role",
                            values=['"applicant"', '"permitted_operator"', '"general_permit_subject"', '"downstream_owner"', '"other"']),
                InputClause(id="in_aggrieved", label="Aggrieved?", expression="aggrieved", type_ref="boolean")],
        outputs=[OutputClause(id="out_rev", label="Reviewable", name="reviewable", type_ref="boolean"),
                 OutputClause(id="out_std", label="Has standing", name="has_standing", type_ref="boolean"),
                 OutputClause(id="out_basis", label="30-day window runs from", name="window_basis"),
                 OutputClause(id="out_days", label="Window (days)", name="window_days", type_ref="number")],
        rules=[
            Rule(id="r1", inputs=['"disapproval","conditional_approval","variance_disapproval","status_determination","general_permit_decision","enforcement_decision"', owner_roles, "true"],
                 outputs=["true", "true", '"date of notice of the action"', "30"],
                 sources=[S("17-211", "A", None), S("17-211", "B", "who is aggrieved by any action or inaction under subsections (A)(i) through (vii) has standing to seek review"), win1]),
            Rule(id="r2", inputs=['"failure_to_act"', owner_roles, "true"],
                 outputs=["true", "true", '"date by which the administrator was required to act"', "30"],
                 sources=[S("17-211", "A", "(vii) the failure of the administrator to act within the time periods required by this chapter"), win2]),
            Rule(id="r3", inputs=['"approval_downstream_issue"', '"downstream_owner"', "true"],
                 outputs=["true", "true", '"date of the administrator\'s approval"', "30"],
                 sources=[S("17-211", "B", "Any downstream owner who is aggrieved by an action under subsection (A)(viii) has standing to seek review under this section."), win3]),
            Rule(id="r4", inputs=['not("other")', "-", "-"],
                 outputs=["true", "false", "null", "null"], annotation="Reviewable action, but this person lacks standing",
                 sources=[S("17-211", "B", None)]),
            Rule(id="r5", inputs=["-", "-", "-"], outputs=["false", "false", "null", "null"],
                 annotation="Not one of the eight reviewable actions", sources=[S("17-211", "A", None)]),
        ],
        sources=[S("17-211", "A", None), S("17-211", "B", None), S("17-211", "C", None)],
    )
    return LegalProcessModel(
        id="va-albemarle-17-211", title="Review of administrator's action; judicial review (VESMP)",
        jurisdiction=juris, jurisdiction_name="Albemarle County, Virginia", jurisdiction_qid="Q488653",
        summary=("How a person aggrieved by a VESMP administrator decision gets a County hearing and then judicial "
                 "review: 30-day filing windows, a soft 30-day hearing target, and appeal to circuit court."),
        actors=actors,
        participants=[Participant(id="p_appellant", name="Appellant (aggrieved person)", actor="appellant", process=appellant),
                      Participant(id="p_county", name="Albemarle County (VESMP authority)", actor="county", process=county),
                      Participant(id="p_court", name="Circuit court", actor="circuit_court")],
        message_flows=[
            MessageFlow(id="m1", source="c_notify", target="p_appellant", name="Notice of action", message="Notice of action"),
            MessageFlow(id="m2", source="a_file", target="c_request", name="Request for hearing", message="Request for hearing"),
            MessageFlow(id="m3", source="p_appellant", target="c_await_grounds", name="Grounds", message="Grounds for appeal"),
            MessageFlow(id="m4", source="p_appellant", target="ph_ext", name="Extension request", message="Extension request"),
            MessageFlow(id="m5", source="c_decide", target="a_wait", name="Written decision", message="Written decision"),
            MessageFlow(id="m6", source="a_appeal", target="p_court", name="Petition for appeal", message="Petition for appeal"),
            MessageFlow(id="m7", source="a_notify", target="c_jr_notice", name="Notice of appeal", message="Notice of appeal"),
            MessageFlow(id="m8", source="c_transmit", target="p_court", name="Hearing record", message="Hearing record"),
        ],
        decisions=[standing],
        texts=[SectionText(section="17-211", title=sec.title, code=code, jurisdiction=juris, text=sec.text,
                           history=sec.history, url="https://library.municode.com/va/albemarle_county/codes/code_of_ordinances",
                           retrieved_from="LOCUS-v1 rows " + ", ".join(str(r) for r in sec.rows), license_note=LOCUS_NOTE),
               SectionText(section="62.1-44.15:46", title="Appeals", code="Code of Virginia", jurisdiction="va",
                           text=VA_62_1_44_15_46, url="https://law.lis.virginia.gov/vacode/62.1-44.15:46/",
                           retrieved_from="law.lis.virginia.gov (second paragraph)")],
        provenance=Provenance(method="gold-manual", dataset_rows=[str(r) for r in sec.rows], created="2026-10-06",
                              notes=["Section rebuilt from 7 LOCUS chunks; flags: " + ", ".join(sec.flags)]),
        review=Review(status="machine-checked", gaps=[gap_e,
                      "Who determines standing is not stated (assigned to the hearing officer).",
                      "Consequence of an untimely request is not stated."]),
    )


def va_judicial_review_stub() -> LegalProcessModel:
    S = va_code
    proc = Process(id="va_62_1_44_15_46_judicial_review", name="Judicial review of a locality's VESMP decision", nodes=[
        Node(id="jr_start", type="startEvent", name="Appeal filed"),
        Node(id="jr_review", type="userTask", name="Court reviews the locality's final decision",
             sources=[S("62.1-44.15:46", "A final decision by a locality, when serving as a VESMP authority, shall be subject to judicial review")]),
        Node(id="jr_end", type="endEvent", name="Judgment"),
    ], flows=[SequenceFlow(id="jr1", source="jr_start", target="jr_review"),
              SequenceFlow(id="jr2", source="jr_review", target="jr_end")])
    return LegalProcessModel(
        id="va-62.1-44.15-46", title="Judicial review of a locality's VESMP decision (stub)", jurisdiction="va",
        jurisdiction_name="Virginia", jurisdiction_qid="Q1370",
        actors=[Actor(id="court", name="Circuit court", kind="court")],
        participants=[Participant(id="p_va_court", name="Circuit court", actor="court", process=proc)],
        texts=[SectionText(section="62.1-44.15:46", title="Appeals", code="Code of Virginia", jurisdiction="va",
                           text=VA_62_1_44_15_46, url="https://law.lis.virginia.gov/vacode/62.1-44.15:46/",
                           retrieved_from="law.lis.virginia.gov")],
        review=Review(status="draft", gaps=["Stub: only the step called from local processes is modeled."]))


# ============================================================ Charlottesville Ch. 16
def charlottesville_noise() -> LegalProcessModel:
    code, juris = "Charlottesville City Code", "va/charlottesville"
    secs = _sections(juris, code, "city", "charlottesville")
    S = _src_factory(code, juris, "https://library.municode.com/va/charlottesville/codes/code_of_ordinances")
    actors = [
        Actor(id="city", name="City of Charlottesville", kind="public-body", wikidata="Q123766"),
        Actor(id="police", name="Charlottesville Police Department", kind="public-body"),
        Actor(id="officer", name="Officer operating the sound level meter", kind="official"),
        Actor(id="complainant", name="Complainant (owner, tenant or resident)", kind="private-party"),
        Actor(id="accused", name="Responsible person (accused)", kind="private-party"),
        Actor(id="court", name="Court", kind="court"),
    ]
    copy_esp = Node(
        id="n_copy", type="subProcess", name="Certificate copy on request", triggered_by_event=True,
        sources=[S("16-12", "c", "A copy of the certificate shall be delivered to the accused upon request.")],
        nodes=[Node(id="nc_start", type="startEvent", name="Accused requests a copy", event="message", interrupting=False,
                    ref="Certificate copy request",
                    sources=[S("16-12", "c", "A copy of the certificate shall be delivered to the accused upon request.")]),
               Node(id="nc_send", type="sendTask", name="Deliver copy of certificate", ref="Certificate copy",
                    data_inputs=["certificate"], deontic="obligation", bearer="police",
                    sources=[S("16-12", "c", "A copy of the certificate shall be delivered to the accused upon request.")]),
               Node(id="nc_end", type="endEvent", name="Copy delivered")],
        flows=[SequenceFlow(id="nc1", source="nc_start", target="nc_send"),
               SequenceFlow(id="nc2", source="nc_send", target="nc_end")])
    cpd = Process(
        id="proc_cpd", name="Noise enforcement (Charlottesville Police Department)",
        documentation="Charlottesville City Code ch. 16 (Noise Control Ordinance).",
        data=[DataRef(id="meter_reports", name="Sworn meter test reports (12 months)", kind="store",
                      sources=[S("16-12", "b", "Any sworn report of the results of any test of the calibrator for the accuracy of a sound level meter shall be admissible in court"),
                               S("16-7", None, "the chief of police shall develop and promulgate standards and procedures for testing and validating sound level meters")]),
              DataRef(id="certificate", name="Sound-level certificate",
                      sources=[S("16-12", "c", "shall issue a certificate to indicate:")])],
        nodes=[
            Node(id="n_start", type="startEvent", name="Noise complaint or measurement request", event="message", ref="Noise complaint",
                 sources=[S("16-8", "c", "when requested to do so by the owner or tenant in possession and control thereof", "implied",
                            "Only multifamily measurements are tied to a request in the text; complaints and officer observation are operational triggers.")]),
            Node(id="n_identify", type="userTask", name="Identify source, location and time",
                 sources=[S("16-4", None, "The noise control program established by this chapter shall be enforced and administered by the police department", "assumed",
                            "Operational step that gathers the inputs for the limit decision.")]),
            Node(id="n_limit", type="businessRuleTask", name="Determine applicable sound limit", decision_ref="d_noise_limit",
                 sources=[S("16-6", None, "No provisions of this chapter shall apply to the emission of sound for the purpose of alerting persons to the existence of an emergency"),
                          S("16-8", "a", "in excess of fifty-five (55) dB(A) when measured at or outside the property boundary"),
                          S("16-8", "b", "in excess of sixty-five (65) dB(A) when measured at or outside the property boundary"),
                          S("16-10", "b", "seventy-five (75) dB(A) or more at a distance of ten (10) feet or more from the source of the sound generation"),
                          S("16-11", None, "in excess of seventy-five (75) dB(A) (fifty-five (55) dB(A) in the Neighborhood Commercial Corridor district")]),
            Node(id="n_applies_gw", type="exclusiveGateway", name="Numeric limit applies?", default="n5"),
            Node(id="n_no_limit", type="endEvent", name="No numeric limit applies",
                 sources=[S("16-8", "d", "shall be exempt from the daytime prohibition set forth in subsection (b) of this section", "implied")]),
            Node(id="n_mf_gw", type="exclusiveGateway", name="Multifamily measurement requested?", default="n7"),
            Node(id="n_measure_mf", type="userTask", name="Measure inside the multifamily building", data_inputs=["meter_reports"],
                 sources=[S("16-8", "c", "Such measurement shall be taken at a point at least four (4) feet from the wall, ceiling or floor nearest the noise source, with doors to the receiving area closed and windows in the normal position for the season.")]),
            Node(id="n_measure", type="userTask", name="Measure at the required point", data_inputs=["meter_reports"],
                 sources=[S("16-8", "a", "when measured at or outside the property boundary"),
                          S("16-10", "b", "at a distance of ten (10) feet or more from the source of the sound generation"),
                          S("16-11", None, "when measured at a residential property boundary"),
                          S("16-12", "a", "may be measured by the use of a sound level meter which measures sound pressure levels")]),
            Node(id="n_mjoin", type="exclusiveGateway", name=""),
            Node(id="n_exceeds_gw", type="exclusiveGateway", name="Reading over the limit?", default="n12"),
            Node(id="n_ok", type="endEvent", name="No violation shown"),
            Node(id="n_responsible", type="userTask", name="Identify the responsible person",
                 sources=[S("16-5", "b", "The person operating or controlling a noise source shall be guilty of any violation caused by that source."),
                          S("16-5", "b", "is rebuttably presumed to be guilty of the violation")]),
            Node(id="n_certificate", type="userTask", name="Issue sound-level certificate",
                 data_inputs=["meter_reports"], data_outputs=["certificate"], deontic="obligation", bearer="officer",
                 sources=[S("16-12", "c", "An individual operating a sound level meter pursuant to the provisions of this chapter shall issue a certificate to indicate:"),
                          S("16-12", "c.2", "has been tested within the past twelve (12) months and has been found to be accurate")]),
            Node(id="n_summons", type="sendTask", name="Charge Class 4 misdemeanor", ref="Summons",
                 documentation="Charging and summons mechanics follow state criminal procedure (assumption).",
                 sources=[S("16-5", "a", "shall be deemed to be guilty of a Class 4 misdemeanor")]),
            Node(id="n_court", type="sendTask", name="Present certificate in court", ref="Certificate as evidence",
                 data_inputs=["certificate"],
                 sources=[S("16-12", "a", "Such measurements shall be accepted as prima facie evidence of the level of noise at issue in any court or legal proceeding to enforce the provisions of this chapter."),
                          S("16-12", "c", "shall be admissible in court in any criminal or civil proceeding as evidence of the facts therein stated and of the decibel level reading")]),
            Node(id="n_end", type="endEvent", name="Case before the court"),
            copy_esp,
        ],
        flows=[
            SequenceFlow(id="n1", source="n_start", target="n_identify"),
            SequenceFlow(id="n2", source="n_identify", target="n_limit"),
            SequenceFlow(id="n3", source="n_limit", target="n_applies_gw"),
            SequenceFlow(id="n4", source="n_applies_gw", target="n_mf_gw", name="Yes", condition="limit_applies"),
            SequenceFlow(id="n5", source="n_applies_gw", target="n_no_limit", name="No"),
            SequenceFlow(id="n6", source="n_mf_gw", target="n_measure_mf", name="Multifamily request", condition="multifamily_request"),
            SequenceFlow(id="n7", source="n_mf_gw", target="n_measure", name="Otherwise"),
            SequenceFlow(id="n8", source="n_measure_mf", target="n_mjoin"),
            SequenceFlow(id="n9", source="n_measure", target="n_mjoin"),
            SequenceFlow(id="n10", source="n_mjoin", target="n_exceeds_gw"),
            SequenceFlow(id="n11", source="n_exceeds_gw", target="n_responsible", name="Over limit", condition="measured_dba > limit_dba"),
            SequenceFlow(id="n12", source="n_exceeds_gw", target="n_ok", name="Within limit"),
            SequenceFlow(id="n13", source="n_responsible", target="n_certificate"),
            SequenceFlow(id="n14", source="n_certificate", target="n_summons"),
            SequenceFlow(id="n15", source="n_summons", target="n_court"),
            SequenceFlow(id="n16", source="n_court", target="n_end"),
        ],
        annotations=[Annotation(id="note_meter", text="Meter must have a sworn accuracy test within 12 months (§ 16-12(c)(2)).",
                                attached_to=["n_certificate"])],
    )
    daytime_exempt = '"school","park","construction","landscaping","church_bells","first_amendment","federally_preempted","transportation_sanitation"'
    noise = Decision(
        id="d_noise_limit", name="Applicable sound limit", hit_policy="FIRST",
        question="Which Chapter 16 numeric limit applies to this sound, where is it measured, and under which section?",
        inputs=[InputClause(id="ni_ctx", label="Location context", expression="context",
                            values=['"residential_zone"', '"downtown_business_district"', '"restaurant_music_hall"', '"other"']),
                InputClause(id="ni_hour", label="Hour (0-23)", expression="hour", type_ref="number"),
                InputClause(id="ni_act", label="Activity / source", expression="activity"),
                InputClause(id="ni_ncc", label="Neighborhood Commercial Corridor?", expression="ncc_district", type_ref="boolean")],
        outputs=[OutputClause(id="no_applies", label="Limit applies", name="limit_applies", type_ref="boolean"),
                 OutputClause(id="no_dba", label="Limit dB(A)", name="limit_dba", type_ref="number"),
                 OutputClause(id="no_where", label="Measured at", name="measured_at"),
                 OutputClause(id="no_basis", label="Basis", name="basis")],
        rules=[
            Rule(id="nr1", inputs=["-", "-", '"emergency"', "-"], outputs=["false", "null", '"-"', '"§ 16-6 emergency exception"'],
                 sources=[S("16-6", None, "No provisions of this chapter shall apply to the emission of sound for the purpose of alerting persons to the existence of an emergency")]),
            Rule(id="nr2", inputs=['"residential_zone"', "[22..23],[0..5]", "-", "-"],
                 outputs=["true", "55", '"at or outside the property boundary"', '"§ 16-8(a) nighttime"'],
                 sources=[S("16-8", "a", "during the hours between 10:00 p.m. and 6:00 a.m. in excess of fifty-five (55) dB(A)")]),
            Rule(id="nr3", inputs=['"residential_zone"', "[6..21]", daytime_exempt, "-"],
                 outputs=["false", "null", '"-"', '"§ 16-8(d) daytime exemption"'],
                 sources=[S("16-8", "d", "The following activities or sources of noise shall be exempt from the daytime prohibition set forth in subsection (b) of this section:")]),
            Rule(id="nr4", inputs=['"residential_zone"', "[6..21]", "-", "-"],
                 outputs=["true", "65", '"at or outside the property boundary"', '"§ 16-8(b) daytime"'],
                 sources=[S("16-8", "b", "during the hours between 6:00 a.m. and 10:00 p.m. in excess of sixty-five (65) dB(A)")]),
            Rule(id="nr5", inputs=['"downtown_business_district"', "-", '"community_event","transportation_sanitation"', "-"],
                 outputs=["false", "null", '"-"', '"§ 16-10(c) exception"'],
                 sources=[S("16-10", "c", "The prohibitions set forth within this section shall not apply to any sound generation which occurs:")]),
            Rule(id="nr6", inputs=['"downtown_business_district"', "-", '"special_event_permit"', "-"],
                 outputs=["false", "null", '"per special event permit"', '"§ 16-10(d) permit terms govern"'],
                 sources=[S("16-10", "d", "shall be in compliance with the noise level and sound amplification requirements set forth in the permit for that special event")]),
            Rule(id="nr7", inputs=['"downtown_business_district"', "-", "-", "-"],
                 outputs=["true", "75", '"10 feet or more from the source"', '"§ 16-10(b) prima facie threshold"'],
                 sources=[S("16-10", "b", "seventy-five (75) dB(A) or more at a distance of ten (10) feet or more from the source of the sound generation shall constitute prima facie evidence of a violation")]),
            Rule(id="nr8", inputs=['"restaurant_music_hall"', "23,[0..5]", "-", "true"],
                 outputs=["true", "55", '"at a residential property boundary"', '"§ 16-11 (Neighborhood Commercial Corridor)"'],
                 sources=[S("16-11", None, "fifty-five (55) dB(A) in the Neighborhood Commercial Corridor district")]),
            Rule(id="nr9", inputs=['"restaurant_music_hall"', "23,[0..5]", "-", "-"],
                 outputs=["true", "75", '"at a residential property boundary"', '"§ 16-11"'],
                 sources=[S("16-11", None, "during the hours between 11:00 p.m. and 6:00 a.m. in excess of seventy-five (75) dB(A)")]),
            Rule(id="nr10", inputs=["-", "-", "-", "-"], outputs=["false", "null", '"-"', '"No numeric limit in ch. 16 for this context (review)"'],
                 annotation="Coverage gap surfaced by the table: flag for legal review"),
        ],
        sources=[S("16-6", None, None), S("16-8", None, None), S("16-10", None, None), S("16-11", None, None)],
    )
    vehicle = Decision(
        id="d_vehicle_limit", name="Motor vehicle sound limit", hit_policy="UNIQUE",
        question="What is the maximum sound level for this vehicle on this road (measured at 50 feet or more)?",
        inputs=[InputClause(id="vi_class", label="Vehicle class", expression="vehicle_class",
                            values=['"heavy_6000_plus"', '"motorcycle"', '"other"']),
                InputClause(id="vi_speed", label="Speed limit (mph)", expression="speed_limit_mph", type_ref="number"),
                InputClause(id="vi_interstate", label="Interstate motor carrier?", expression="interstate_carrier", type_ref="boolean")],
        outputs=[OutputClause(id="vo_applies", label="Limit applies", name="limit_applies", type_ref="boolean"),
                 OutputClause(id="vo_dba", label="Limit dB(A)", name="limit_dba", type_ref="number")],
        rules=[
            Rule(id="vr1", inputs=["-", "-", "true"], outputs=["false", "null"],
                 sources=[S("16-9", "b", "This section shall not apply to any motor carrier vehicle engaged in interstate commerce.")]),
            Rule(id="vr2", inputs=['"heavy_6000_plus"', "<= 35", "false"], outputs=["true", "86"], sources=[S("16-9", "a", None)]),
            Rule(id="vr3", inputs=['"heavy_6000_plus"', "> 35", "false"], outputs=["true", "90"], sources=[S("16-9", "a", None)]),
            Rule(id="vr4", inputs=['"motorcycle"', "<= 35", "false"], outputs=["true", "82"], sources=[S("16-9", "a", None)]),
            Rule(id="vr5", inputs=['"motorcycle"', "> 35", "false"], outputs=["true", "86"], sources=[S("16-9", "a", None)]),
            Rule(id="vr6", inputs=['"other"', "<= 35", "false"], outputs=["true", "76"], sources=[S("16-9", "a", None)]),
            Rule(id="vr7", inputs=['"other"', "> 35", "false"], outputs=["true", "82"], sources=[S("16-9", "a", None)]),
        ],
        sources=[S("16-9", "a", "when measured at a distance of fifty (50) feet or more, exceeds the level set forth in the following table:")],
    )
    texts = [SectionText(section=n, title=secs[n].title, code=code, jurisdiction=juris, text=secs[n].text,
                         history=secs[n].history, url="https://library.municode.com/va/charlottesville/codes/code_of_ordinances",
                         retrieved_from="LOCUS-v1 row " + ", ".join(str(r) for r in secs[n].rows), license_note=LOCUS_NOTE)
             for n in ["16-4", "16-5", "16-6", "16-7", "16-8", "16-9", "16-10", "16-11", "16-12"]]
    return LegalProcessModel(
        id="va-charlottesville-ch16-noise", title="Noise enforcement and sound limits (Noise Control Ordinance)",
        jurisdiction=juris, jurisdiction_name="Charlottesville, Virginia", jurisdiction_qid="Q123766",
        summary=("How Charlottesville police apply Chapter 16: pick the limit (DMN), measure with a tested meter, "
                 "identify who is responsible, certify the reading and charge a Class 4 misdemeanor."),
        actors=actors,
        participants=[Participant(id="p_complainant", name="Complainant", actor="complainant"),
                      Participant(id="p_cpd", name="Charlottesville Police Department", actor="police", process=cpd),
                      Participant(id="p_accused", name="Responsible person (accused)", actor="accused"),
                      Participant(id="p_court", name="Court", actor="court")],
        message_flows=[
            MessageFlow(id="k1", source="p_complainant", target="n_start", name="Noise complaint", message="Noise complaint"),
            MessageFlow(id="k2", source="n_summons", target="p_accused", name="Summons", message="Summons"),
            MessageFlow(id="k3", source="n_court", target="p_court", name="Certificate and charge", message="Certificate as evidence"),
            MessageFlow(id="k4", source="p_accused", target="nc_start", name="Copy request", message="Certificate copy request"),
            MessageFlow(id="k5", source="nc_send", target="p_accused", name="Certificate copy", message="Certificate copy"),
        ],
        decisions=[noise, vehicle],
        texts=texts,
        provenance=Provenance(method="gold-manual", created="2026-10-06",
                              dataset_rows=[str(r) for n in ["16-4", "16-5", "16-6", "16-7", "16-8", "16-9", "16-10", "16-11", "16-12"] for r in secs[n].rows]),
        review=Review(status="machine-checked", gaps=[
            "Daytime limits for restaurants/music halls outside residential zones are not set in ch. 16 (rule nr10).",
            "Complaint intake and charging mechanics are operational assumptions."]),
    )


ALL = {"albemarle_17_211": albemarle_17_211, "charlottesville_noise": charlottesville_noise,
       "va_judicial_review_stub": va_judicial_review_stub}
