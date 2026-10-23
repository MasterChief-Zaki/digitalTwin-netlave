"""Matched warm-up, fault placement, held-out inputs and paired bounds."""

from dataclasses import replace

import pytest

from config import SITE, STEPS_PER_DAY
from scenarios.paired_evaluation import matched_initial_state, paired_interval, run_paired_trial, summarize
from models.solar_profiles import profile_solar_power_w


def test_common_warmup_resets_counters_not_clock_and_moves_fault() -> None:
    state = matched_initial_state(SITE, "tse_interrupt", 7, 5)
    assert state.step == 5 * STEPS_PER_DAY
    assert state.environment.inflow_outage_steps == (state.step + 30, state.step + 390)
    assert state.metrics.irrigation_delivered_m3 == 0
    assert all(not zone.valve_open and not zone.irrigation_latched for zone in state.zones)
    assert state.initial_reservoir_volume_m3 == state.reservoir_volume_m3


def test_identical_policies_have_exact_zero_paired_effect_after_warmup() -> None:
    trial = run_paired_trial(SITE, "baseline", 100, horizon_days=1, warmup_days=5)
    assert trial.reference == trial.candidate
    assert trial.measurement_start_step == 5 * STEPS_PER_DAY
    assert trial.measurement_end_step == 6 * STEPS_PER_DAY


def test_profile_changes_inputs_but_keeps_pair_matched() -> None:
    nominal = run_paired_trial(SITE, "baseline", 100, 1, 0, "nominal")
    heldout = run_paired_trial(SITE, "baseline", 100, 1, 0, "cloud_pulses")
    assert nominal.reference.input_digest != heldout.reference.input_digest
    assert heldout.reference.input_digest == heldout.candidate.input_digest


def test_bootstrap_bounds_are_deterministic_and_report_effects() -> None:
    interval = paired_interval([-1.0, -2.0, -3.0], 24, 1000)
    assert interval == paired_interval([-1.0, -2.0, -3.0], 24, 1000)
    assert interval["mean"] == -2.0
    assert interval["negative_count"] == 3
    assert interval["upper_bound"] <= -1.0
    with pytest.raises(ValueError):
        paired_interval([1.0], 1)


def test_short_diagnostics_cannot_pass_release_seed_gate() -> None:
    trials = [run_paired_trial(SITE, "baseline", seed, 1, 0) for seed in (100, 101)]
    summaries = summarize(trials)
    assert len(summaries) == 3
    assert all(item["service_noninferiority"] == "INCONCLUSIVE" for item in summaries)
    assert all(item["additional_et_deficit_mm"]["mean"] == 0 for item in summaries)


def test_repeated_seeds_and_short_horizons_cannot_manufacture_acceptance() -> None:
    trial = run_paired_trial(SITE, "baseline", 100, 1, 0)
    repeated = summarize([trial] * 20)
    assert all(item["service_noninferiority"] == "INCONCLUSIVE" for item in repeated)
    distinct_short = summarize([replace(trial, seed=seed) for seed in range(100, 120)])
    assert all(item["service_noninferiority"] == "INCONCLUSIVE" for item in distinct_short)


def test_dark_profile_is_a_sustained_input_change() -> None:
    nominal = profile_solar_power_w(12, 1, SITE.energy, "nominal", 2 * STEPS_PER_DAY)
    dark = profile_solar_power_w(12, 1, SITE.energy, "three_day_dark", 2 * STEPS_PER_DAY)
    assert dark == nominal * 0.05
