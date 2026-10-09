"""The gold models execute in SpiffWorkflow along every legally distinct path."""
import itertools

import pytest
from SpiffWorkflow.dmn.engine.DMNEngine import DMNEngine
from SpiffWorkflow.bpmn.script_engine import PythonScriptEngine

from lexflow.dmn_eval import decide, completeness_gaps, overlaps
from lexflow.simulate import Sim, prepare
from lexflow.validate import spiff_parser


def county_sim(built, tmp_path, overrides=None):
    county = prepare(built["albemarle_17_211"]["bpmn"], tmp_path, overrides)
    stub = prepare(built["va_judicial_review_stub"]["bpmn"], tmp_path)
    return Sim([county, stub], built["albemarle_17_211"]["spiff_dmn"], "proc_county")


REQUEST = dict(grounds_stated=True, action_type="disapproval", person_role="applicant", aggrieved=True)


def run_hearing(s):
    s.complete("ph_schedule")
    s.complete("h_evidence")
    s.complete("h_consider")
    s.complete("h_record")
    s.complete("c_decide") if "c_decide" in s.ready() else None


def test_county_hearing_then_final(built, tmp_path):
    s = county_sim(built, tmp_path, {"c_jr_window": "PT0S"})
    assert s.waiting() == ["c_await_request"]
    s.message("Request for hearing", at="c_await_request", **REQUEST)
    assert s.data()["window_basis"] == "date of notice of the action"
    run_hearing(s)
    assert "c_final" in s.completed()
    assert "c_transcribe" not in s.completed()       # transcription only if judicial review sought


def test_county_judicial_review_transcribes(built, tmp_path):
    s = county_sim(built, tmp_path)
    s.message("Request for hearing", at="c_await_request", **REQUEST)
    run_hearing(s)
    assert "c_after_gw" in s.waiting()
    s.message("Notice of appeal", at="c_after_gw")
    s.complete("c_transcribe")
    assert "c_jr_end" in s.completed() and "c_final" not in s.completed()


def test_county_no_standing_dismissed(built, tmp_path):
    s = county_sim(built, tmp_path)
    s.message("Request for hearing", at="c_await_request", **{**REQUEST, "person_role": "other"})
    assert "c_dismiss" in s.completed()
    assert s.data()["reviewable"] is True and s.data()["has_standing"] is False


def test_county_untimely_request_lapses(built, tmp_path):
    s = county_sim(built, tmp_path, {"c_window": "PT0S"})
    assert "c_lapsed" in s.completed()


def test_county_waits_for_grounds(built, tmp_path):
    s = county_sim(built, tmp_path)
    s.message("Request for hearing", at="c_await_request", **{**REQUEST, "grounds_stated": False})
    assert "c_await_grounds" in s.waiting()
    s.message("Grounds for appeal", at="c_await_grounds")
    assert "ph_schedule" in s.ready()


def test_county_extension_is_non_interrupting(built, tmp_path):
    s = county_sim(built, tmp_path)
    s.message("Request for hearing", at="c_await_request", **REQUEST)
    s.message("Extension request", at="ph_ext")
    assert set(s.ready()) >= {"ph_schedule", "ph_extend"}


def test_appellant_calls_state_judicial_review(built, tmp_path):
    a = prepare(built["albemarle_17_211"]["bpmn"], tmp_path)
    stub = prepare(built["va_judicial_review_stub"]["bpmn"], tmp_path)
    s = Sim([a, stub], built["albemarle_17_211"]["spiff_dmn"], "proc_appellant")
    s.complete("a_decide", request_review=True)
    assert "a_wait" in s.waiting()
    s.message("Written decision", at="a_wait")
    s.complete("a_decide_jr", seek_judicial_review=True)
    assert "jr_review" in s.ready()                    # inside the called Va. Code process
    s.complete("jr_review")
    assert s.done and "a_end" in s.completed()


def test_appellant_window_lapses(built, tmp_path):
    a = prepare(built["albemarle_17_211"]["bpmn"], tmp_path, {"a_window": "PT0S"})
    stub = prepare(built["va_judicial_review_stub"]["bpmn"], tmp_path)
    s = Sim([a, stub], built["albemarle_17_211"]["spiff_dmn"], "proc_appellant")
    assert "a_lapsed" in s.completed()


def noise_sim(built, tmp_path):
    b = prepare(built["charlottesville_noise"]["bpmn"], tmp_path)
    return Sim([b], built["charlottesville_noise"]["spiff_dmn"], "proc_cpd")


def test_noise_violation_path_with_copy_request(built, tmp_path):
    s = noise_sim(built, tmp_path)
    s.message("Noise complaint")
    s.complete("n_identify", context="residential_zone", hour=23, activity="none", ncc_district=False,
               multifamily_request=False)
    assert s.data()["limit_dba"] == 55
    s.complete("n_measure", measured_dba=61)
    s.complete("n_responsible")
    s.message("Certificate copy request")               # event sub-process, non-interrupting
    s.complete("n_certificate")
    assert "n_end" in s.completed()
    assert "nc_end" in s.completed()


def test_noise_daytime_construction_exempt(built, tmp_path):
    s = noise_sim(built, tmp_path)
    s.message("Noise complaint")
    s.complete("n_identify", context="residential_zone", hour=10, activity="construction", ncc_district=False,
               multifamily_request=False)
    assert "n_no_limit" in s.completed()


def test_noise_downtown_within_limit(built, tmp_path):
    s = noise_sim(built, tmp_path)
    s.message("Noise complaint")
    s.complete("n_identify", context="downtown_business_district", hour=20, activity="none", ncc_district=False,
               multifamily_request=False)
    s.complete("n_measure", measured_dba=70)
    assert "n_ok" in s.completed()


def test_noise_multifamily_measurement(built, tmp_path):
    s = noise_sim(built, tmp_path)
    s.message("Noise complaint")
    s.complete("n_identify", context="residential_zone", hour=2, activity="none", ncc_district=False,
               multifamily_request=True)
    assert s.ready() == ["n_measure_mf"]
    s.complete("n_measure_mf", measured_dba=50)
    assert "n_ok" in s.completed()


# ----------------------------------------------------------- DMN cross-checks
class _FakeWorkflow:
    script_engine = PythonScriptEngine()


class _FakeTask:
    def __init__(self, data):
        self.data = dict(data)
        self.workflow = _FakeWorkflow()


def spiff_decide(built, model_name, decision_id, data):
    parser = spiff_parser([], [p for p in built[model_name]["spiff_dmn"] if decision_id in p.name])
    dp = parser.dmn_parsers[decision_id]
    dp.parse()
    return DMNEngine(dp.decision.decisionTables[0]).result(_FakeTask(data))


NOISE_GRID = [dict(context=c, hour=h, activity=a, ncc_district=n)
              for c, h, a, n in itertools.product(
                  ["residential_zone", "downtown_business_district", "restaurant_music_hall", "other"],
                  [0, 5, 6, 10, 21, 22, 23],
                  ["none", "emergency", "construction", "community_event", "special_event_permit"],
                  [True, False])]
VEHICLE_GRID = [dict(vehicle_class=v, speed_limit_mph=s, interstate_carrier=i)
                for v, s, i in itertools.product(["heavy_6000_plus", "motorcycle", "other"], [25, 35, 36, 55], [True, False])]
STANDING_GRID = [dict(action_type=a, person_role=r, aggrieved=g)
                 for a, r, g in itertools.product(
                     ["disapproval", "failure_to_act", "approval_downstream_issue", "enforcement_decision", "other"],
                     ["applicant", "downstream_owner", "other"], [True, False])]


@pytest.mark.parametrize("model_name,decision_id,grid", [
    ("charlottesville_noise", "d_noise_limit", NOISE_GRID),
    ("charlottesville_noise", "d_vehicle_limit", VEHICLE_GRID),
    ("albemarle_17_211", "d_review_standing", STANDING_GRID),
])
def test_feel_and_spiff_agree(built, models, model_name, decision_id, grid):
    decision = next(d for d in models[model_name].decisions if d.id == decision_id)
    for point in grid:
        ours = {k: v for k, v in decide(decision, point).items() if k != "_rule"}
        theirs = dict(spiff_decide(built, model_name, decision_id, point))
        assert ours == theirs, (point, ours, theirs)


def test_tables_are_complete_and_unique(models):
    noise = next(d for d in models["charlottesville_noise"].decisions if d.id == "d_noise_limit")
    vehicle = next(d for d in models["charlottesville_noise"].decisions if d.id == "d_vehicle_limit")
    standing = models["albemarle_17_211"].decisions[0]
    assert completeness_gaps(noise, NOISE_GRID) == []          # catch-all rule nr10 closes the table
    assert completeness_gaps(standing, STANDING_GRID) == []
    assert overlaps(vehicle, VEHICLE_GRID) == []                 # UNIQUE table really is unique
    assert completeness_gaps(vehicle, VEHICLE_GRID) == []
