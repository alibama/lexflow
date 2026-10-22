"""The Virginia Retirement System pilot as a question family (``fixtures/families/retirement_va.json``).

The family is generated here, deterministically, from the provisions in
``fixtures/benefits/va_retirement_backbone.json`` (each a verbatim quote of Va. Code Title 51.1, the Administrative
Process Act or VRS's own pages), then grounded like any family (``python -m lexflow.scenarios.family --fill
retirement_va``: every rule's quote is copied from its pointer and matched by lexflow's software).

Dimensions: the employer type (state, teacher, political subdivision, hazardous duty), the membership date (with
the vesting test of 1 January 2013), age and years of creditable service; the plan (Plan 1, Plan 2, Hybrid) is a
derived input, determined by the membership date as the Code defines it, so a hazardous-duty member hired in 2014
or later is in Plan 2 (§ 51.1-169 keeps him out of the hybrid program).

Service retirement eligibility is computed by ``eligibility`` for every whole age and year of service and written
as decision-table rules (one rule per run of ages and years that share an outcome and the provision that gives
it), so the Rule of 90 (§ 51.1-153(B)(3): age plus service equals 90) is exact for whole years even though FEEL
unary tests cannot add two inputs.

In this family a row's status reads: ``required`` = applies to you now (you are eligible, or the Code requires it of
you); ``recommended`` = an option worth checking; ``ask first`` = depends on your employer's election; ``not
required`` = not (yet) eligible.

    python -m lexflow.benefits family-va [--write]
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import config

BACKBONE = "fixtures/benefits/va_retirement_backbone.json"
PATH = config.ROOT / "fixtures" / "families" / "retirement_va.json"
SS_AGE = 67                 # ASM-01: the Social Security retirement age taken as 67 (born 1960 or later)
AGES = range(0, 101)
YEARS = range(0, 61)


def _sections() -> list[dict]:
    return json.loads((config.ROOT / BACKBONE).read_text(encoding="utf-8"))["sections"]


def ptr(sid: str) -> dict:
    """A source pointer into the backbone by the section's id."""
    for i, s in enumerate(_sections()):
        if s["id"] == sid:
            return {"from": f"{BACKBONE}#sections[{i}]"}
    raise KeyError(sid)


# --------------------------------------------------------------------------------------------- eligibility
def eligibility(klass: str, age: int, svc: int) -> tuple[str, str, str]:
    """(category, provision id, why) for a plan class ('plan1', 'plan2' for Plan 2 and Hybrid, 'hazardous'),
    whole age and years of creditable service.  Categories: unreduced, reduced, not_yet."""
    if klass == "plan1":
        if age >= 65 and svc >= 5:
            return "unreduced", "normal", "Plan 1: age 65 with 5 or more years"
        if age >= 50 and svc >= 30:
            return "unreduced", "plan1_50_30", "Plan 1: age 50 with 30 or more years"
        if age >= 55 and svc >= 5:
            return "reduced", "early_55_5", "Plan 1: age 55 with 5 or more years, reduced unless 30 years"
        if age >= 50 and svc >= 10:
            return "reduced", "plan1_50_10", "Plan 1: age 50 with 10 or more years (the 50/10 allowance)"
        return "not_yet", "early_55_5", "Plan 1 needs age 55 with 5 years (reduced), age 50 with 10 years " \
                                        "(50/10), age 50 with 30 years or age 65 with 5 years (unreduced)"
    if klass == "plan2":
        if age >= SS_AGE and svc >= 5:
            return "unreduced", "normal", f"Plan 2 and Hybrid: Social Security retirement age ({SS_AGE}) with 5 or " \
                                          f"more years"
        if age + svc >= 90:
            return "unreduced", "rule_of_90", "Plan 2 and Hybrid: age plus service equals 90 (the Rule of 90)"
        if age >= 60 and svc >= 5:
            return "reduced", "early_60_5", "Plan 2 and Hybrid: age 60 with 5 or more years, reduced"
        return "not_yet", "early_60_5", f"Plan 2 and Hybrid need age 60 with 5 years (reduced), or age plus " \
                                        f"service of 90 or Social Security retirement age ({SS_AGE}) with 5 years " \
                                        f"(unreduced)"
    if klass == "hazardous":
        if age >= 60 and svc >= 5:
            return "unreduced", "sp_normal", "hazardous duty: age 60 with 5 or more years"
        if age >= 50 and svc >= 25:
            return "unreduced", "sp_reduction_25", "hazardous duty: age 50 with 25 or more years"
        if age >= 50 and svc >= 5:
            return "reduced", "sp_early", "hazardous duty: age 50 with 5 or more years, reduced unless 25 years"
        return "not_yet", "sp_early", "hazardous duty needs age 50 with 5 years (reduced), age 50 with 25 years " \
                                      "or age 60 with 5 years (unreduced)"
    raise ValueError(klass)


def _cell(lo: int, hi: int | None, top: int) -> str:
    """A FEEL test for whole numbers lo..hi-1 (hi None: and above)."""
    if hi is None or hi > top:
        return f">= {lo}" if lo > 0 else "-"
    if lo <= 0:
        return f"< {hi}"
    return f"[{lo}..{hi})"


def runs(klass: str) -> list[dict]:
    """The rule runs: ages a0..a1 and years s0..s1 that share (category, provision)."""
    per_age = []
    for a in AGES:
        segs, start = [], 0
        cur = eligibility(klass, a, 0)
        for s in list(YEARS)[1:] + [None]:
            nxt = eligibility(klass, a, s) if s is not None else None
            if nxt is None or nxt[:2] != cur[:2]:
                segs.append((start, s, cur))
                if s is not None:
                    start, cur = s, nxt
        per_age.append(segs)
    out, a0 = [], 0
    for a in list(AGES)[1:] + [None]:
        same = a is not None and [(x[0], x[1], x[2][:2]) for x in per_age[a]] == \
            [(x[0], x[1], x[2][:2]) for x in per_age[a0]]
        if not same:
            for s0, s1, (cat, prov, why) in per_age[a0]:
                out.append({"age": (a0, a), "svc": (s0, s1), "category": cat, "provision": prov, "why": why})
            if a is not None:
                a0 = a
    return out


CLASS_WHEN = {"plan1": ['"plan1"', 'not("hazardous")'], "plan2": ['"plan2","hybrid"', 'not("hazardous")'],
              "hazardous": ["-", '"hazardous"']}
CATEGORY = {
    "unreduced": ("retire_unreduced", "required",
                  "Tell the Board in writing when your unreduced (full) service retirement is to start: you are "
                  "eligible now; apply to VRS 60 to 120 days ahead"),
    "reduced": ("retire_reduced", "recommended",
                "Check reduced early retirement: you may retire now with an allowance reduced for each year before "
                "your unreduced date"),
    "not_yet": ("retire_not_yet", "not required", "Service retirement: not yet eligible"),
}


def retirement_rules() -> list[dict]:
    rules = []
    for klass in ("plan1", "plan2", "hazardous"):
        for n, r in enumerate(runs(klass), 1):
            rid, status, title = CATEGORY[r["category"]]
            when = CLASS_WHEN[klass] + [_cell(r["age"][0], r["age"][1], 100), _cell(r["svc"][0], r["svc"][1], 60)]
            rule = {"id": f"{klass}_{n:02d}", "when": when, "then": [f'"{rid}"', f'"{status}"'],
                    "title": f"{title} ({r['why']})", "office": "vrs", "fee": {"none": True},
                    "tags": ["retire"], "stage": 3, "tag": "SRC",
                    "assumptions": ["ASM-02"] + (["ASM-01"] if klass == "plan2" and r["provision"] in ("normal", "early_60_5") else [])
                    + (["ASM-03"] if klass == "plan2" else []) + (["ASM-04"] if klass == "hazardous" else []),
                    "source": ptr(r["provision"]), "level": "state"}
            if r["category"] != "not_yet":
                rule["deadline"] = ("the retirement date may be no more than 90 days before the written notice is "
                                    "filed; VRS asks for the application 60 to 120 days before the date")
                rule["deadline_source"] = ptr("effective_date")
            if r["category"] == "reduced" and klass in ("plan1", "hazardous"):
                rule["note"] = "reduction: " + ("§ 51.1-155(A)(2), unless 30 years of service" if klass == "plan1"
                                                else "§ 51.1-206(A)(2), unless 25 years of service")
            rules.append(rule)
    return rules


# --------------------------------------------------------------------------------------------- the family
def spec() -> dict:
    sid = {s["id"] for s in _sections()}
    assert {"normal", "rule_of_90", "effective_date"} <= sid
    dims = [
        {"name": "locality", "label": "State", "type": "string", "slot": "LOC", "default": "virginia",
         "values": [{"value": "virginia", "code": "VA", "label": "Virginia (statewide)", "tag": "SRC",
                     "defined_in": "Va. Code § 51.1-124.1"}]},
        {"name": "employer", "label": "Employer type", "type": "string", "slot": "EMP", "default": "state",
         "values": [
             {"value": "state", "code": "STE", "label": "State employee", "tag": "SRC", "source": ptr("state_employee"),
              "defined_in": "Va. Code § 51.1-124.3"},
             {"value": "teacher", "code": "TCH", "label": "Teacher (local public school board)", "tag": "SRC",
              "source": ptr("teacher"), "defined_in": "Va. Code § 51.1-124.3"},
             {"value": "political_subdivision", "code": "PSD", "label": "Political subdivision (county, city, town) "
              "general employee", "tag": "SRC", "source": ptr("political_subdivision"), "defined_in": "Va. Code § 51.1-130"},
             {"value": "hazardous", "code": "HAZ", "label": "Hazardous duty: state police, VaLORS, or a political "
              "subdivision's law-enforcement officer, firefighter or EMT with enhanced benefits", "tag": "ASM",
              "assumptions": ["ASM-04"], "source": ptr("hazardous_election"), "defined_in": "Va. Code §§ 51.1-138, 51.1-205"}]},
        {"name": "membership", "label": "When you first became a VRS member", "type": "string", "slot": "MEM",
         "default": "before_2010_vested",
         "values": [
             {"value": "before_2010_vested", "code": "M1", "label": "Before 1 July 2010, with 5 years of service by "
              "1 January 2013", "plan": "plan1", "tag": "SRC", "source": ptr("page_plan1"),
              "defined_in": "Va. Code § 51.1-124.3 (normal retirement date)"},
             {"value": "before_2010_not_vested", "code": "M2", "label": "Before 1 July 2010, without 5 years of "
              "service by 1 January 2013", "plan": "plan2", "tag": "SRC", "source": ptr("nrd_plan2"),
              "defined_in": "Va. Code § 51.1-124.3"},
             {"value": "2010_to_2013", "code": "M3", "label": "1 July 2010 to 31 December 2013", "plan": "plan2",
              "tag": "SRC", "source": ptr("page_plan2"), "defined_in": "Va. Code § 51.1-124.3"},
             {"value": "2014_on", "code": "M4", "label": "On or after 1 January 2014", "plan": "hybrid", "tag": "SRC",
              "source": ptr("hybrid"), "defined_in": "Va. Code § 51.1-169",
              "scope": {"employer": ["state", "teacher", "political_subdivision"]}},
             {"value": "2014_on_hazardous", "code": "M4H", "label": "On or after 1 January 2014 (hazardous duty: not "
              "in the hybrid program)", "plan": "plan2", "tag": "SRC", "source": ptr("hybrid_excludes_hazardous"),
              "defined_in": "Va. Code § 51.1-169", "scope": {"employer": ["hazardous"]}}]},
        {"name": "age", "label": "Age (whole years)", "type": "number", "slot": "AGE", "default": 60,
         "bins": [{"code": "A40", "label": "Under 50", "min": 0, "max": 49, "value": 45, "tag": "SCN"},
                  {"code": "A50", "label": "50 to 54", "min": 50, "max": 54, "value": 52, "tag": "SCN"},
                  {"code": "A55", "label": "55 to 59", "min": 55, "max": 59, "value": 57, "tag": "SCN"},
                  {"code": "A60", "label": "60 to 64", "min": 60, "max": 64, "value": 62, "tag": "SCN"},
                  {"code": "A65", "label": "65 to 66", "min": 65, "max": 66, "value": 65, "tag": "SCN"},
                  {"code": "A67", "label": "67 or older", "min": 67, "value": 68, "tag": "SCN"}]},
        {"name": "service", "label": "Years of creditable service (whole years)", "type": "number", "slot": "SVC",
         "default": 10,
         "bins": [{"code": "S0", "label": "Under 5", "min": 0, "max": 4, "value": 2, "tag": "SCN"},
                  {"code": "S5", "label": "5 to 9", "min": 5, "max": 9, "value": 7, "tag": "SCN"},
                  {"code": "S10", "label": "10 to 14", "min": 10, "max": 14, "value": 12, "tag": "SCN"},
                  {"code": "S15", "label": "15 to 19", "min": 15, "max": 19, "value": 17, "tag": "SCN"},
                  {"code": "S20", "label": "20 to 24", "min": 20, "max": 24, "value": 22, "tag": "SCN"},
                  {"code": "S25", "label": "25 to 29", "min": 25, "max": 29, "value": 27, "tag": "SCN"},
                  {"code": "S30", "label": "30 or more", "min": 30, "value": 32, "tag": "SCN"}]},
    ]
    plan_rules = [
        {"id": "plan1", "when": ['"plan1"', 'not("hazardous")'], "then": ['"plan_1"', '"required"'],
         "title": "Check your plan: VRS Plan 1. Your normal retirement date is your 65th birthday", "office": "vrs",
         "fee": {"none": True}, "tags": ["plan"], "stage": 1, "tag": "SRC", "assumptions": [],
         "source": ptr("nrd_plan1"), "level": "state"},
        {"id": "plan2", "when": ['"plan2"', 'not("hazardous")'], "then": ['"plan_2"', '"required"'],
         "title": "Check your plan: VRS Plan 2. Your normal retirement date is your Social Security retirement age",
         "office": "vrs", "fee": {"none": True}, "tags": ["plan"], "stage": 1, "tag": "SRC", "assumptions": ["ASM-01"],
         "source": ptr("nrd_plan2"), "level": "state"},
        {"id": "hybrid", "when": ['"hybrid"', "-"], "then": ['"plan_hybrid"', '"required"'],
         "title": "Check your plan: the VRS Hybrid Retirement Plan (a Plan 2 style defined benefit and a defined "
                  "contribution part)", "office": "vrs", "fee": {"none": True}, "tags": ["plan"], "stage": 1,
         "tag": "SRC", "assumptions": ["ASM-03"], "source": ptr("hybrid"), "level": "state"},
        {"id": "hazardous", "when": ["-", '"hazardous"'], "then": ['"plan_hazardous"', '"required"'],
         "title": "Check your plan: hazardous duty benefits equal to the State Police Officers' Retirement System's. "
                  "Your normal retirement date is your 60th birthday", "office": "vrs", "fee": {"none": True},
         "tags": ["plan"], "stage": 1, "tag": "SRC", "assumptions": ["ASM-04"], "source": ptr("sp_nrd"),
         "level": "state"},
        {"id": "hazardous_election", "when": ["-", '"hazardous"'], "then": ['"ask_hazardous_election"', '"ask first"'],
         "title": "Ask your employer whether it provides the enhanced hazardous duty benefits (a political "
                  "subdivision elects them by resolution approved by the Board)", "office": "employer",
         "fee": {"none": True}, "tags": ["plan"], "stage": 1, "tag": "SRC", "assumptions": ["ASM-04"],
         "source": ptr("hazardous_election"), "level": "state"},
    ]
    steps_rules = [
        {"id": "purchase", "when": ["-", "-", "-"], "then": ['"buy_service_credit"', '"recommended"'],
         "title": "Check whether to buy service credit for prior public service, certain leaves, or up to four "
                  "years of active duty military service", "office": "vrs", "fee": {"rule": "the approximate normal "
                  "cost within 24 months of hire or of the leave's end; the actuarial equivalent cost after that",
                  "kind": "charge"}, "tags": ["purchase"], "stage": 2, "tag": "SRC", "assumptions": [],
         "source": ptr("purchase_military"), "level": "state",
         "deadline": "within the first 24 months of active service after hire (or after the leave ends) to pay the "
                     "approximate normal cost; later purchases cost the actuarial equivalent",
         "deadline_source": ptr("purchase_cost")},
        {"id": "deferred", "when": ["-", "-", ">= 5"], "then": ['"keep_contributions"', '"recommended"'],
         "title": "Keep your contributions in VRS if you leave: with five or more years of service you can retire "
                  "later (deferred retirement)", "office": "vrs", "fee": {"none": True}, "tags": ["deferred"],
         "stage": 4, "tag": "SRC", "assumptions": [], "source": ptr("deferred"), "level": "state"},
        {"id": "hybrid_dc", "when": ['"hybrid"', "-", "-"], "then": ['"hybrid_contributions"', '"recommended"'],
         "title": "Plan the hybrid plan's defined contribution part: your employer contributes 1% of pay and matches "
                  "your voluntary contributions", "office": "vrs", "fee": {"none": True}, "tags": ["hybrid"],
         "stage": 2, "tag": "SRC", "assumptions": [], "source": ptr("hybrid_dc"), "level": "state"},
        {"id": "beneficiary", "when": ["-", "-", "-"], "then": ['"designate_beneficiary"', '"required"'],
         "title": "Tell VRS whom you designate as your beneficiary if you die before retirement", "office": "vrs",
         "fee": {"none": True}, "tags": ["beneficiary"], "stage": 1, "tag": "SRC", "assumptions": [],
         "source": ptr("beneficiary"), "level": "state"},
    ]
    protection_rules = [
        {"id": "disability", "when": ["-"], "then": ['"disability_retirement"', '"recommended"'],
         "title": "Check disability retirement if a disability stops you working (in service, or within 90 days "
                  "after leaving, with your contributions still in VRS)", "office": "vrs", "fee": {"none": True},
         "tags": ["protection"], "stage": 5, "tag": "SRC", "assumptions": [], "source": ptr("disability"),
         "level": "state"},
        {"id": "survivor", "when": ["-"], "then": ['"survivor_allowance"', '"recommended"'],
         "title": "Tell your family: if you die in service, a retirement allowance is paid to a designated surviving "
                  "spouse, minor child or parent", "office": "vrs", "fee": {"none": True}, "tags": ["protection"],
         "stage": 5, "tag": "SRC", "assumptions": [], "source": ptr("death_in_service"), "level": "state"},
    ]
    tables = [
        {"id": "plan", "question": "Which VRS plan covers me?", "hit_policy": "COLLECT",
         "inputs": [{"name": "plan", "label": "Plan", "type": "string"},
                    {"name": "employer", "label": "Employer type", "type": "string"}],
         "outputs": [{"name": "requirement", "label": "Requirement", "type": "string"},
                     {"name": "status", "label": "Status", "type": "string"}], "rules": plan_rules},
        {"id": "retirement", "question": "When can I retire, with an unreduced or a reduced benefit?",
         "hit_policy": "COLLECT",
         "inputs": [{"name": "plan", "label": "Plan", "type": "string"},
                    {"name": "employer", "label": "Employer type", "type": "string"},
                    {"name": "age", "label": "Age", "type": "number"},
                    {"name": "service", "label": "Years of creditable service", "type": "number"}],
         "outputs": [{"name": "requirement", "label": "Requirement", "type": "string"},
                     {"name": "status", "label": "Status", "type": "string"}], "rules": retirement_rules()},
        {"id": "steps", "question": "What should I do about service credit, contributions and beneficiaries?",
         "hit_policy": "COLLECT",
         "inputs": [{"name": "plan", "label": "Plan", "type": "string"},
                    {"name": "employer", "label": "Employer type", "type": "string"},
                    {"name": "service", "label": "Years of creditable service", "type": "number"}],
         "outputs": [{"name": "requirement", "label": "Requirement", "type": "string"},
                     {"name": "status", "label": "Status", "type": "string"}], "rules": steps_rules},
        {"id": "protection", "question": "What if I become disabled or die before I retire?", "hit_policy": "COLLECT",
         "inputs": [{"name": "plan", "label": "Plan", "type": "string"}],
         "outputs": [{"name": "requirement", "label": "Requirement", "type": "string"},
                     {"name": "status", "label": "Status", "type": "string"}], "rules": protection_rules},
    ]
    return {
        "family": "retirement_va",
        "title": "Retiring from the Virginia Retirement System: plan, eligibility, service credit and survivors",
        "version": "2026-10-22.1",
        "state": "va",
        "about": __doc__.split("\n\n")[0].replace("\n", " ") + " Statuses: required = applies to you now; "
                 "recommended = an option worth checking; ask first = depends on your employer's election; not "
                 "required = not (yet) eligible.",
        "inspiration": "The idea of tagging inputs as published facts, assumptions or scenario values, personas and "
                       "one-at-a-time sensitivity comes from github.com/dam8u/VRSLite (no licence: nothing copied).",
        "status": "Computed from grounded decision tables, not reviewed by a person; not legal or financial advice. "
                  "VRS decides every benefit; its handbooks and the member's own record govern.",
        "default_persona": "teacher_55_25",
        "grammar": {"separator": "-", "locality": "locality",
                    "slots": ["locality", "employer", "membership", "age", "service"]},
        "dimensions": dims,
        "derived": [{"name": "plan", "from": "membership", "attribute": "plan",
                     "values": ["plan1", "plan2", "hybrid"], "label": "VRS plan, determined by the membership date"}],
        "constraints": [
            {"id": "C1", "text": "Service cannot exceed working years: under 50 means fewer than 30 years",
             "when": {"age": ["A40"]}, "require_any": [{"service": ["S0", "S5", "S10", "S15", "S20", "S25"]}]},
            {"id": "C2", "text": "Members since 2014 have at most about 13 years of membership service, plus up to "
                                 "four purchased years (as of 2026)",
             "when": {"membership": ["M4", "M4H"]}, "require_any": [{"service": ["S0", "S5", "S10", "S15"]}]},
            {"id": "C3", "text": "A member vested by 1 January 2013 has at least 5 years of service",
             "when": {"membership": ["M1"]}, "require_any": [{"service": ["S5", "S10", "S15", "S20", "S25", "S30"]}]},
        ],
        "offices": {"vrs": {"label": "Virginia Retirement System (Board of Trustees)", "url": "https://www.varetire.org/"},
                    "employer": {"label": "Your employer's human resources office (the VRS employer)", "url": None}},
        "milestones": [],
        "tables": tables,
        "order": [{"id": "O1", "first": "purchase", "then": "retire", "tag": "SRC",
                   "why": "service credit is bought by a member in service, so before retirement",
                   "source": ptr("purchase")},
                  {"id": "O2", "first": "plan", "then": "retire", "tag": "SRC",
                   "why": "the plan sets the normal retirement date the eligibility tests use",
                   "source": ptr("nrd_plan2")}],
        "appeals": [{"id": "AP1", "table": "retirement", "to": "the Virginia Retirement System, by informal "
                     "fact-finding under the Administrative Process Act, then a court action",
                     "deadline": "a timely court action under the Rules of the Supreme Court of Virginia",
                     "source": ptr("appeal_court")},
                    {"id": "AP2", "table": "plan", "to": "the Virginia Retirement System's informal fact-finding "
                     "proceeding (Administrative Process Act)", "deadline": "as the Board's notice states",
                     "source": ptr("appeal_iffp")}],
        "assumptions": [
            {"id": "ASM-01", "text": f"The Social Security retirement age (Plan 2 and Hybrid normal retirement date) is "
                                     f"taken as {SS_AGE}, the age for people born in 1960 or later.",
             "direction": "overstates the age for members born before 1960 (66 to 66 and 10 months), who reach the "
                          "unreduced date earlier", "range": "66 to 67"},
            {"id": "ASM-02", "text": "Age and creditable service are whole years; creditable service includes "
                                     "purchased service and excludes refunded service.",
             "direction": "a member a few months short of a threshold is shown as not yet eligible",
             "range": "up to 11 months"},
            {"id": "ASM-03", "text": "Hybrid plan members are 'persons who become members on or after July 1, 2010' "
                                     "for § 51.1-153, so the Plan 2 eligibility rules apply to their defined benefit.",
             "direction": "none expected: the hybrid program's defined benefit follows Plan 2", "range": "-"},
            {"id": "ASM-04", "text": "Hazardous duty means benefits equal to the State Police Officers' Retirement "
                                     "System's: a state police officer, a VaLORS member under § 51.1-216, or a "
                                     "political subdivision employee whose employer elected § 51.1-138 benefits.",
             "direction": "VaLORS members hired before 1 July 2001 who did not elect, and employers that did not "
                          "elect, follow the general Plan 1 or Plan 2 rules instead", "range": "employer by employer"},
            {"id": "ASM-05", "text": "The 2014 window in which Plan 1 and Plan 2 members could elect the hybrid "
                                     "program (§ 51.1-169(A)), and § 51.1-153(B)(4) resolutions treating a "
                                     "subdivision's firefighters, EMS personnel and law-enforcement officers as Plan 1, "
                                     "are not modelled.",
             "direction": "a member who elected the hybrid plan, or is covered by such a resolution, gets the wrong "
                          "plan here", "range": "-"},
        ],
        "personas": [
            {"id": "teacher_55_25", "label": "Teacher, 55, 25 years, Plan 1",
             "note": "A teacher who joined VRS in 2001 and kept working.",
             "inputs": {"employer": "teacher", "membership": "before_2010_vested", "age": 55, "service": 25}},
            {"id": "state_60_10", "label": "State employee, 60, 10 years, Plan 2",
             "note": "Hired by a state agency in 2011.",
             "inputs": {"employer": "state", "membership": "2010_to_2013", "age": 60, "service": 10}},
            {"id": "firefighter_50_25", "label": "Firefighter, 50, 25 years, hazardous duty",
             "note": "A county firefighter whose county provides the enhanced hazardous duty benefits.",
             "inputs": {"employer": "hazardous", "membership": "before_2010_vested", "age": 50, "service": 25}},
            {"id": "hybrid_45_8", "label": "Political subdivision employee, 45, 8 years, Hybrid",
             "note": "A city employee hired in 2018.",
             "inputs": {"employer": "political_subdivision", "membership": "2014_on", "age": 45, "service": 8}},
        ],
        "variants": [],
        "serves": {
            "retirement_which_system": {"tables": ["plan"]},
            "retirement_unreduced": {"tables": ["retirement", "plan"]},
            "retirement_buy_service": {"tables": ["steps"]},
            "retirement_apply": {"tables": ["retirement"]},
            "retirement_appeal": {"tables": ["retirement", "plan"]},
            "retirement_survivor": {"tables": ["steps", "protection"]},
        },
    }


def write(path: Path | None = None) -> dict:
    """Write the family (ungrounded: run ``python -m lexflow.scenarios.family --fill retirement_va`` next)."""
    s = spec()
    (path or PATH).write_text(json.dumps(s, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"tables": len(s["tables"]), "rules": sum(len(t["rules"]) for t in s["tables"])}
