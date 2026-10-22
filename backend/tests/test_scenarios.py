"""Scenario tests: physically justified grants and denials."""

from dataclasses import replace

from config import SITE
from scenarios.presets import SCENARIOS, build_scenario
from tests.helpers import assert_close, run_steps, set_all_moisture
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


# Filtration, water quality and the scenario presets.


def test_p2_clogged_filter_denies_zone_b_on_head_while_zone_a_runs():
    state = build_scenario(SITE, "clogged_filter", seed=7)

    result = step(state, SITE)

    zone_b = decision_for(result, "B")
    assert zone_b.reason_code == "INSUFFICIENT_HEAD"
    assert result.state.zones[1].head_available_m < result.state.zones[1].head_required_m
    assert decision_for(result, "A").accepted
    assert result.state.zones[0].delivered_flow_m3_s > 0


def test_p3_flush_is_exclusive_for_five_steps_and_booked_once():
    state = build_scenario(SITE, "clogged_filter", seed=7)
    filtration = SITE.filtration

    state, results = run_steps(state, 40)

    flushing_steps = [result for result in results if result.state.power.flush_power_w > 0]
    assert len(flushing_steps) == filtration.flush_steps
    for result in flushing_steps:
        assert all(zone.delivered_flow_m3_s == 0 for zone in result.state.zones)
        assert {decision.reason_code for decision in result.decisions if decision.requested_action in ("START", "KEEP_OPEN")} <= {
            "FLUSH_IN_PROGRESS",
            "FILTER_FLUSH_REQUIRED",
        }
    assert state.metrics.flush_count == 1
    assert_close(state.metrics.flush_water_m3, filtration.flush_water_m3, "flush water")
    assert_close(state.metrics.flush_energy_j, filtration.flush_power_w * filtration.flush_steps * 60, "flush energy")
    assert_close(state.metrics.flush_energy_j / 3.6e6, 0.10, "flush kWh")
    codes = [event.reason_code for result in results for event in result.events]
    assert codes.count("FILTER_FLUSH_STARTED") == 1
    assert codes.count("FILTER_FLUSH_COMPLETE") == 1


def test_flush_recovers_head_so_zone_b_irrigates():
    state = build_scenario(SITE, "clogged_filter", seed=7)

    state, results = run_steps(state, 40)

    flush_end = max(index for index, result in enumerate(results) if result.state.power.flush_power_w > 0)
    after_flush = results[flush_end + 1]
    assert after_flush.state.filter.clog_index < 0.1
    assert decision_for(after_flush, "B").accepted
    assert after_flush.state.zones[1].delivered_flow_m3_s > 0


def test_filter_only_loads_with_filtered_water():
    state = new_run_state(SITE, seed=7)
    set_all_moisture(state, 0.21)
    initial_clog = state.filter.clog_index

    state, _ = run_steps(state, 60)

    assert state.metrics.irrigation_delivered_m3 == 0
    assert state.filter.clog_index == initial_clog


def test_water_quality_hold_fails_closed():
    for status in ("HOLD", "UNKNOWN"):
        state = new_run_state(SITE, seed=7)
        state.environment.water_quality = status

        result = step(state, SITE)

        assert {decision.reason_code for decision in result.decisions} == {"WATER_QUALITY_HOLD"}
        assert result.state.metrics.irrigation_delivered_m3 == 0


def test_low_solar_runs_the_pump_briefly_then_denies_it_at_the_reserve():
    state = build_scenario(SITE, "low_solar", seed=7)

    state, results = run_steps(state, 30)

    zone_c = [decision_for(result, "C") for result in results]
    assert zone_c[0].accepted
    assert any(decision.reason_code == "BATTERY_BELOW_RESERVE" for decision in zone_c)
    first_denial = next(index for index, decision in enumerate(zone_c) if not decision.accepted)
    assert all(not decision.accepted for decision in zone_c[first_denial:])


def test_starting_the_pump_needs_ten_minutes_of_battery_above_the_reserve():
    state = pump_only_state()
    state.environment.cloud_factor = 0.0
    reserve_j = SITE.energy.pump_reserve_soc * SITE.energy.battery_capacity_j
    state.battery_energy_j = reserve_j + 5 * 60 * 2600 / SITE.energy.battery_discharge_efficiency

    result = step(state, SITE)

    assert decision_for(result, "C").reason_code == "BATTERY_BELOW_RESERVE"


def test_tse_interrupt_stops_inflow_and_hydro_in_its_window():
    state = build_scenario(SITE, "tse_interrupt", seed=7)
    outage_start, outage_end = state.environment.inflow_outage_steps

    state, results = run_steps(state, outage_start + 10)

    assert results[outage_start - 1].state.power.hydro_power_w > 0
    assert results[outage_start + 5].state.inflow_m3_s == 0
    assert results[outage_start + 5].state.power.hydro_power_w == 0


def test_every_scenario_is_listed_and_buildable():
    assert {scenario.id for scenario in SCENARIOS} == {"baseline", "clogged_filter", "low_solar", "tse_interrupt"}
    for scenario in SCENARIOS:
        state = build_scenario(SITE, scenario.id, seed=3)
        state, _ = run_steps(state, 5)
        assert state.scenario_id == scenario.id
