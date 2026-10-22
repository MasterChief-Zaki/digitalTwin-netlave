"""A/B comparison and long-run tests (X1, X2) plus the comparison benchmark."""

import math
import time
from dataclasses import fields

from config import SITE, STEPS_PER_DAY
from scenarios.comparison import run_comparison
from scenarios.presets import build_scenario
from twin.engine import step


def test_x1_both_policies_see_identical_inputs_hardware_and_safety():
    report = run_comparison(SITE, "baseline", seed=7, horizon_days=14)

    fixed, smart = report.fixed_timer, report.smart_hysteresis
    assert fixed.policy == "FIXED_TIMER"
    assert smart.policy == "SMART_HYSTERESIS"
    assert fixed.input_digest == smart.input_digest
    assert fixed.initial_state_digest == smart.initial_state_digest
    assert report.horizon_days == 14
    assert report.steps == 14 * STEPS_PER_DAY


def test_x1_reports_finite_coherent_metrics():
    report = run_comparison(SITE, "baseline", seed=7, horizon_days=14)

    for policy in (report.fixed_timer, report.smart_hysteresis):
        values = [getattr(policy, field.name) for field in fields(policy) if isinstance(getattr(policy, field.name), float)]
        assert all(math.isfinite(value) for value in values)
        assert policy.irrigation_delivered_m3 > 0
        assert 0.0 <= policy.electrical_autonomy_0_1 <= 1.0
        assert 0.0 <= policy.final_battery_soc_0_1 <= 1.0
        assert policy.actual_et_m3 <= policy.potential_et_m3 + 1e-9
        assert math.isclose(policy.et_deficit_m3, policy.potential_et_m3 - policy.actual_et_m3, rel_tol=1e-9)
        assert policy.irrigation_delivered_m3 <= policy.tse_inflow_m3 + SITE.reservoir.initial_volume_m3
    assert report.fixed_timer.irrigation_delivered_m3 != report.smart_hysteresis.irrigation_delivered_m3


def test_x1_water_savings_are_computed_not_asserted():
    report = run_comparison(SITE, "baseline", seed=7, horizon_days=14)

    fixed = report.fixed_timer.irrigation_delivered_m3
    smart = report.smart_hysteresis.irrigation_delivered_m3
    assert math.isclose(report.water_savings_fraction, (fixed - smart) / fixed)


def test_comparison_is_reproducible():
    first = run_comparison(SITE, "baseline", seed=11, horizon_days=2)
    second = run_comparison(SITE, "baseline", seed=11, horizon_days=2)

    assert first.fixed_timer == second.fixed_timer
    assert first.smart_hysteresis == second.smart_hysteresis


def test_x2_thirty_day_soak_keeps_valid_state_and_monotonic_counters():
    state = build_scenario(SITE, "baseline", seed=7)
    counter_names = [field.name for field in fields(state.metrics)]
    previous_counters = [getattr(state.metrics, name) for name in counter_names]

    for _ in range(30 * STEPS_PER_DAY):
        state = step(state, SITE).state
        counters = [getattr(state.metrics, name) for name in counter_names]
        assert all(after >= before for before, after in zip(previous_counters, counters, strict=True))
        previous_counters = counters

    assert state.step == 43_200
    assert all(math.isfinite(value) for value in previous_counters)
    assert SITE.reservoir.dead_volume_m3 <= state.reservoir_volume_m3 <= SITE.reservoir.capacity_m3
    assert state.metrics.overflow_m3 > 0
    assert state.metrics.flush_count > 0


def test_fourteen_day_comparison_runs_in_under_five_seconds():
    started = time.perf_counter()
    run_comparison(SITE, "baseline", seed=7, horizon_days=14)
    elapsed_s = time.perf_counter() - started

    assert elapsed_s < 5.0, f"14-day A/B took {elapsed_s:.2f} s"
