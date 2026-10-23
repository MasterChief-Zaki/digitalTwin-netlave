"""Resource scheduler bounds sessions without changing safety resolution."""

from dataclasses import replace

from config import SITE
from control.scheduler import operating_floor_m3
from scenarios.presets import build_scenario
from twin.engine import step
from twin.state import to_snapshot


def test_floor_recomputes_with_actual_filter_above_design_state() -> None:
    state = build_scenario(SITE, "baseline", 7, "SMART_RESOURCE_AWARE")
    clean_floor = operating_floor_m3(state, SITE)
    state.filter.clog_index = 0.56
    assert operating_floor_m3(state, SITE) > clean_floor
    assert operating_floor_m3(state, SITE) > 850


def test_joint_water_and_energy_constraints_preserve_latch_and_account_deferral() -> None:
    state = build_scenario(SITE, "low_solar", 7, "SMART_RESOURCE_AWARE")
    state.reservoir_volume_m3 = 850
    result = step(state, SITE).state
    pumped = result.zones[2]
    assert not pumped.valve_open
    assert pumped.irrigation_latched
    assert sum(pumped.accounts.deferred_by_reason_min.values()) == 1
    assert not pumped.accounts.denied_by_reason_min
    state.reservoir_volume_m3 = 1500
    result = step(state, SITE).state
    assert result.zones[2].accounts.deferred_by_reason_min["SCHEDULER_ENERGY_HOLD"] == 1


def test_bounded_sessions_stagger_and_rest_without_starvation() -> None:
    state = build_scenario(SITE, "baseline", 7, "SMART_RESOURCE_AWARE")
    for _ in range(1440):
        state = step(state, SITE).state
        assert sum(zone.valve_open for zone in state.zones) <= 1
        assert state.reservoir_volume_m3 >= SITE.scheduler.operating_inventory_m3
    assert all(zone.accounts.irrigation_delivered_m3 > 0 for zone in state.zones)
    assert all(zone.accounts.session_count > 0 for zone in state.zones)


def test_paused_session_resumes_same_identity_and_volume() -> None:
    cfg = replace(SITE, scheduler=replace(SITE.scheduler, energy_aware=False))
    state = build_scenario(cfg, "baseline", 7, "SMART_RESOURCE_AWARE")
    state.reservoir_volume_m3 = 1500
    state = step(state, cfg).state
    active = next(zone for zone in state.zones if zone.valve_open)
    count, remaining = active.accounts.session_count, active.session.remaining_volume_m3
    state.reservoir_volume_m3 = 850
    paused = step(state, cfg).state
    zone = paused.zones_by_id[active.zone_id]
    assert zone.session.paused
    assert zone.accounts.pause_count == 1
    assert zone.session.remaining_volume_m3 == remaining
    paused.reservoir_volume_m3 = 1500
    # Other waiting zones may run first; fairness must eventually resume this session.
    resumed_state = paused
    for _ in range(100):
        resumed_state = step(resumed_state, cfg).state
        if resumed_state.zones_by_id[active.zone_id].accounts.resume_count > 0:
            break
    resumed = resumed_state.zones_by_id[active.zone_id]
    assert resumed.accounts.session_count == count
    assert resumed.accounts.resume_count == 1
    assert resumed.session.remaining_volume_m3 < remaining


def test_manual_open_still_fails_quality_safety_gate() -> None:
    state = build_scenario(SITE, "baseline", 7, "SMART_RESOURCE_AWARE")
    state.zones[2].control_mode = "MANUAL_OPEN"
    state.environment.water_quality = "HOLD"
    result = step(state, SITE).state
    assert result.decisions[2].reason_code == "WATER_QUALITY_HOLD"
    assert not result.zones[2].valve_open


def test_default_policy_is_not_promoted() -> None:
    snapshot = to_snapshot(build_scenario(SITE, "baseline", 7), SITE, 0, 0)
    assert snapshot.environment.control_policy == "SMART_HYSTERESIS"
