"""Candidate sizing never overwrites the reference hardware."""

from config import SITE
from scenarios.design_study import candidates, hydraulic_margins
from scenarios.comparison import run_comparison


def test_design_candidates_are_explicit_and_do_not_modify_defaults() -> None:
    study = candidates()
    assert SITE.zones[2].max_flow_m3_h == 24
    assert study["pump_derated_18_m3_h"].zones[2].max_flow_m3_h == 18
    assert hydraulic_margins(study["pump_derated_18_m3_h"])["worst_case_pump_power_w"] < hydraulic_margins(SITE)["worst_case_pump_power_w"]
    assert hydraulic_margins(study["zone_b_pipe_025_m"])["zone_b_full_clogged_head_margin_m"] > hydraulic_margins(SITE)["zone_b_full_clogged_head_margin_m"]


def test_api_comparison_can_measure_matched_candidate_without_default_promotion() -> None:
    report = run_comparison(SITE, "tse_interrupt", 7, 1, "MATCHED_OPERATION", 5, True)
    assert report.measurement_start_step == 5 * 1440
    assert report.measurement_end_step == 6 * 1440
    assert report.resource_aware is not None
    assert report.resource_aware.policy == "SMART_RESOURCE_AWARE"
    assert report.resource_aware.input_digest == report.smart_hysteresis.input_digest
    assert report.resource_aware.initial_state_digest == report.smart_hysteresis.initial_state_digest
