"""Scenario tests: physically justified grants and denials."""

from dataclasses import replace

from config import SITE
from tests.helpers import run_steps, set_all_moisture
from twin.engine import step
from twin.state import new_run_state


def decision_for(result, zone_id: str):
    return next(decision for decision in result.decisions if decision.zone_id == zone_id)


def pump_only_state():
    state = new_run_state(SITE, seed=7)
    set_all_moisture(state, 0.21)
    state.zones[2].theta_m3_m3 = 0.15
    return state


def test_pump_runs_on_the_battery_at_dawn():
    result = step(pump_only_state(), SITE)

    decision = decision_for(result, "C")
    assert decision.accepted
    assert decision.reason_code == "SOIL_BELOW_THRESHOLD"
    assert result.state.zones[2].delivered_flow_m3_s == SITE.zones[2].max_flow_m3_s
    assert 2700 < result.state.power.pump_power_w < 3000
    assert result.state.power.discharge_power_w > 0
    assert result.state.pump.running


def test_p1_pump_is_denied_at_the_battery_reserve():
    state = pump_only_state()
    state.battery_energy_j = SITE.energy.pump_reserve_soc * SITE.energy.battery_capacity_j
    state.environment.cloud_factor = 0.0

    result = step(state, SITE)

    decision = decision_for(result, "C")
    assert not decision.accepted
    assert decision.reason_code == "BATTERY_BELOW_RESERVE"
    assert "reserve" in decision.explanation
    assert result.state.zones[2].delivered_flow_m3_s == 0
    assert result.state.power.pump_power_w == 0
    assert result.state.metrics.requested_undelivered_m3 > 0
    assert [(event.zone_id, event.reason_code) for event in result.events] == [("C", "BATTERY_BELOW_RESERVE")]


def test_repeated_denials_emit_one_event_per_episode():
    state = pump_only_state()
    state.battery_energy_j = SITE.energy.pump_reserve_soc * SITE.energy.battery_capacity_j
    state.environment.cloud_factor = 0.0

    state, results = run_steps(state, 10)

    assert all(not decision_for(result, "C").accepted for result in results)
    denial_events = [event for result in results for event in result.events if event.category == "DENIAL"]
    assert len(denial_events) == 1


def test_pump_is_denied_when_instantaneous_power_is_short():
    cfg = replace(SITE, energy=replace(SITE.energy, battery_max_discharge_w=1000.0))
    state = pump_only_state()
    state.environment.cloud_factor = 0.0

    result = step(state, cfg)

    decision = decision_for(result, "C")
    assert decision.reason_code == "POWER_DEFICIT"
    assert result.state.zones[2].delivered_flow_m3_s == 0


def test_manual_open_never_bypasses_the_gates():
    state = pump_only_state()
    state.zones[2].theta_m3_m3 = 0.21
    state.zones[2].control_mode = "MANUAL_OPEN"
    state.battery_energy_j = SITE.energy.pump_reserve_soc * SITE.energy.battery_capacity_j
    state.environment.cloud_factor = 0.0

    result = step(state, SITE)

    assert decision_for(result, "C").reason_code == "BATTERY_BELOW_RESERVE"
    assert result.state.zones[2].delivered_flow_m3_s == 0


def test_manual_open_is_granted_when_supply_permits():
    state = pump_only_state()
    state.zones[2].theta_m3_m3 = 0.21
    state.zones[2].control_mode = "MANUAL_OPEN"

    result = step(state, SITE)

    assert decision_for(result, "C").reason_code == "MANUAL_OVERRIDE_OK"
    assert result.state.zones[2].delivered_flow_m3_s > 0


def test_gravity_manifold_grants_the_first_ranked_zone_only():
    state = new_run_state(SITE, seed=7)

    result = step(state, SITE)

    assert decision_for(result, "A").accepted
    assert decision_for(result, "B").reason_code == "CONCURRENT_FLOW_LIMIT"
    assert result.state.zones[1].delivered_flow_m3_s == 0


def test_the_more_stressed_zone_wins_the_manifold():
    state = new_run_state(SITE, seed=7)
    state.zones[1].theta_m3_m3 = 0.15

    result = step(state, SITE)

    assert decision_for(result, "B").accepted
    assert decision_for(result, "A").reason_code == "CONCURRENT_FLOW_LIMIT"


def test_gravity_zones_report_their_head_margin():
    result = step(new_run_state(SITE, seed=7), SITE)

    zone_b = result.state.zones[1]
    assert zone_b.head_available_m > zone_b.head_required_m > SITE.zones[1].emitter_head_m


def test_hysteresis_stops_at_the_target_and_reports_it():
    state = new_run_state(SITE, seed=7)
    set_all_moisture(state, 0.21)
    zone_a = state.zones[0]
    zone_a.theta_m3_m3 = 0.1979
    zone_a.irrigation_latched = True
    zone_a.valve_open = True

    state, results = run_steps(state, 30)

    stops = [decision_for(result, "A") for result in results if decision_for(result, "A").requested_action == "STOP"]
    assert len(stops) == 1
    assert stops[0].reason_code == "MOISTURE_TARGET_REACHED"
    assert not state.zones[0].irrigation_latched
    assert not state.zones[0].valve_open


def test_starting_a_zone_needs_ten_minutes_of_water_but_keeping_it_open_needs_one():
    zone_a_flow_m3_per_minute = SITE.zones[0].max_flow_m3_s * 60
    for valve_open, expected_accepted in ((False, False), (True, True)):
        state = new_run_state(SITE, seed=7)
        set_all_moisture(state, 0.21)
        state.zones[0].theta_m3_m3 = 0.15
        state.zones[0].irrigation_latched = valve_open
        state.zones[0].valve_open = valve_open
        state.reservoir_volume_m3 = SITE.reservoir.dead_volume_m3 + 5 * zone_a_flow_m3_per_minute

        result = step(state, SITE)

        decision = decision_for(result, "A")
        assert decision.accepted is expected_accepted
        if not expected_accepted:
            assert decision.reason_code == "RESERVOIR_LOW"
