"""Physics tests: conservation, bounds, determinism and the section 5 sanity checks (C1-C3, S1, D1, P4)."""

import json
import math
from dataclasses import replace as replace_config
from pathlib import Path

import pytest

from config import SITE
from models.energy import solar_power_w
from models.filtration import filter_head_loss_m
from models.hydraulics import hydro_power_w, pump_requirement
from models.water_soil import surface_elevation_m, update_soil
from tests.helpers import assert_close, run_steps, set_all_moisture
from twin.engine import step
from twin.inputs import daylight_weight
from twin.state import new_run_state, physical_digest, to_snapshot

FIXTURE_PATH = Path(__file__).resolve().parents[2] / "src" / "fixtures" / "initial-snapshot.json"


def test_initial_snapshot_matches_the_shared_fixture():
    snapshot = to_snapshot(new_run_state(SITE, seed=7), SITE, run_generation=0, latest_event_id=0)
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    assert snapshot.model_dump(mode="json") == fixture


def test_c1_reservoir_water_is_conserved_with_overflow():
    state = new_run_state(SITE, seed=7)
    state.reservoir_volume_m3 = SITE.reservoir.capacity_m3 - 5.0
    # Only zone C irrigates, at 24 m3/h, so the 60 m3/h inflow fills the reservoir and spills.
    state.zones[0].theta_m3_m3 = 0.21
    state.zones[1].theta_m3_m3 = 0.21
    initial_volume_m3 = state.reservoir_volume_m3

    state, results = run_steps(state, 1000)

    metrics = state.metrics
    assert metrics.overflow_m3 > 0
    assert metrics.irrigation_delivered_m3 > 0
    assert_close(
        state.reservoir_volume_m3 - initial_volume_m3,
        metrics.tse_inflow_m3 - metrics.irrigation_delivered_m3 - metrics.flush_water_m3 - metrics.overflow_m3,
        "reservoir balance",
    )
    assert all(result.state.reservoir_volume_m3 <= SITE.reservoir.capacity_m3 for result in results)


def test_c2_soil_water_is_conserved_in_wet_and_dry_cycles():
    for initial_theta in (0.30, 0.165, 0.11):
        state = new_run_state(SITE, seed=7)
        set_all_moisture(state, initial_theta)
        initial_storage = [zone_storage(state, index) for index in range(3)]

        state, results = run_steps(state, 1000)

        for index in range(3):
            soil_results = [result.soil[index] for result in results]
            infiltrated = sum(soil.infiltrated_m3 for soil in soil_results)
            evapotranspired = sum(soil.actual_et_m3 for soil in soil_results)
            drained = sum(soil.drainage_m3 for soil in soil_results)
            assert_close(
                zone_storage(state, index) - initial_storage[index],
                infiltrated - evapotranspired - drained,
                f"soil balance zone {index} from theta {initial_theta}",
            )
            assert all(soil.drainage_m3 >= 0 and soil.actual_et_m3 >= 0 for soil in soil_results)


def test_c2_wet_soil_drains_to_field_capacity():
    state = new_run_state(SITE, seed=7)
    set_all_moisture(state, 0.30)

    state, results = run_steps(state, 1)

    assert results[0].soil[0].drainage_m3 > 0
    assert all(zone.theta_m3_m3 <= SITE.soil.theta_fc_m3_m3 + 1e-12 for zone in state.zones)


def test_p4_full_reservoir_spills_and_stays_at_capacity():
    state = new_run_state(SITE, seed=7)
    state.reservoir_volume_m3 = SITE.reservoir.capacity_m3
    set_all_moisture(state, 0.21)

    state, results = run_steps(state, 30)

    assert state.metrics.overflow_m3 > 0
    assert state.metrics.irrigation_delivered_m3 == 0
    assert_close(state.reservoir_volume_m3, SITE.reservoir.capacity_m3, "volume at capacity")
    assert any(event.reason_code == "OVERFLOW_OCCURRING" for result in results for event in result.events)


def test_s1_empty_reservoir_without_inflow_stays_in_bounds():
    state = new_run_state(SITE, seed=7)
    state.reservoir_volume_m3 = SITE.reservoir.dead_volume_m3
    state.environment.inflow_available = False

    state, results = run_steps(state, 120)

    assert state.metrics.irrigation_delivered_m3 == 0
    assert state.metrics.requested_undelivered_m3 > 0
    assert state.reservoir_volume_m3 >= SITE.reservoir.dead_volume_m3
    assert {decision.reason_code for decision in results[-1].decisions} == {"RESERVOIR_LOW"}
    snapshot = to_snapshot(state, SITE, run_generation=1, latest_event_id=0)
    assert all_finite(snapshot.model_dump())
    for zone in snapshot.zones:
        assert SITE.soil.theta_wp_m3_m3 <= zone.soil_moisture_m3_m3 <= SITE.soil.theta_sat_m3_m3
        assert 0 <= zone.water_stress_0_1 <= 1


def test_d1_replay_is_deterministic():
    digests = []
    for _ in range(2):
        state = new_run_state(SITE, seed=11)
        series = []
        for _ in range(10):
            state, _ = run_steps(state, 100)
            series.append(physical_digest(to_snapshot(state, SITE, run_generation=1, latest_event_id=0)))
        digests.append(series)

    assert digests[0] == digests[1]


def test_physical_digest_ignores_transport_metadata():
    state = new_run_state(SITE, seed=7)
    first = physical_digest(to_snapshot(state, SITE, run_generation=1, latest_event_id=3))
    second = physical_digest(to_snapshot(state, SITE, run_generation=9, latest_event_id=40))

    assert first == second


def test_different_seeds_change_the_weather():
    first = new_run_state(SITE, seed=1)
    second = new_run_state(SITE, seed=2)

    first, _ = run_steps(first, 1)
    second, _ = run_steps(second, 1)

    assert first.metrics.potential_et_m3 != second.metrics.potential_et_m3


def zone_storage(state, index: int) -> float:
    zone_config = SITE.zones[index]
    return state.zones[index].theta_m3_m3 * zone_config.area_m2 * SITE.soil.root_depth_m


def all_finite(value) -> bool:
    if isinstance(value, dict):
        return all(all_finite(item) for item in value.values())
    if isinstance(value, list):
        return all(all_finite(item) for item in value)
    if isinstance(value, float):
        return math.isfinite(value)
    return True


# Section 5 sanity checks and C3 electrical conservation.


def test_sanity_hydro_at_three_metres_is_about_294_watts():
    assert hydro_power_w(60 / 3600, 3.0, 0.60) == pytest.approx(294.3, abs=0.5)
    assert hydro_power_w(60 / 3600, 18.0, 0.60) == pytest.approx(1766, abs=2)


def test_sanity_zone_c_pump_needs_about_2_8_kilowatts():
    zone_c = SITE.zones[2]
    clean_filter_head_m = filter_head_loss_m(0.0, SITE.filtration)
    surface_m = surface_elevation_m(SITE.reservoir.initial_volume_m3, SITE.reservoir)

    requirement = pump_requirement(zone_c, surface_m, clean_filter_head_m, zone_c.max_flow_m3_s, SITE.hydraulics)

    assert requirement.total_dynamic_head_m == pytest.approx(23.4, abs=0.1)
    assert requirement.power_w == pytest.approx(2780, abs=15)
    assert requirement.within_envelope


def test_sanity_24_m3_h_at_28_metres_exceeds_the_3_kw_pump():
    flow_m3_s = 24 / 3600
    power_w = 1000 * 9.81 * flow_m3_s * 28 / 0.55

    assert power_w == pytest.approx(3330, abs=5)
    assert power_w > SITE.hydraulics.pump_power_limit_w


def test_sanity_site_net_et_is_about_625_m3_per_day():
    daily_et_m3 = 0.0
    for minute in range(24 * 60):
        et0_step_mm = SITE.climate.et0_nominal_mm_day * daylight_weight(minute, SITE)
        for zone in SITE.zones:
            daily_et_m3 += update_soil(0.2, 0.0, et0_step_mm, zone, SITE.soil).potential_et_m3

    assert daily_et_m3 == pytest.approx(624.75, rel=1e-9)


def test_solar_profile_is_zero_at_night_and_peaks_at_noon():
    assert solar_power_w(3.0, 1.0, SITE.energy) == 0
    assert solar_power_w(12.0, 1.0, SITE.energy) == pytest.approx(6000)
    assert solar_power_w(12.0, 0.25, SITE.energy) == pytest.approx(1500)


@pytest.mark.parametrize(
    "case",
    ["charging", "pump_on_battery", "full_battery", "shortage"],
)
def test_c3_bus_and_cell_balances_close(case: str):
    state = new_run_state(SITE, seed=7)
    set_all_moisture(state, 0.21)
    if case == "charging":
        state.battery_energy_j = 0.3 * SITE.energy.battery_capacity_j
    elif case == "pump_on_battery":
        state.zones[2].theta_m3_m3 = 0.15
        state.environment.cloud_factor = 0.0
    elif case == "full_battery":
        state.battery_energy_j = SITE.energy.battery_capacity_j
    elif case == "shortage":
        state.battery_energy_j = SITE.energy.battery_floor_soc * SITE.energy.battery_capacity_j
        state.environment.cloud_factor = 0.0
        state.environment.inflow_available = False
    initial_energy_j = state.battery_energy_j

    state, _ = run_steps(state, 600)

    metrics = state.metrics
    supplied_j = metrics.hydro_energy_j + metrics.solar_energy_j + metrics.battery_discharge_energy_j + metrics.unserved_energy_j
    consumed_j = (
        metrics.pump_energy_j + metrics.aux_energy_j + metrics.flush_energy_j
        + metrics.battery_charge_energy_j + metrics.curtailed_energy_j
    )
    assert_close(supplied_j, consumed_j, "bus energy")
    assert_close(
        state.battery_energy_j - initial_energy_j,
        metrics.battery_charge_energy_j - metrics.battery_discharge_energy_j - metrics.battery_losses_j,
        "cell energy",
    )
    assert_close(
        metrics.required_electrical_energy_j,
        metrics.pump_energy_j + metrics.aux_energy_j + metrics.flush_energy_j,
        "required energy",
    )
    soc = state.battery_energy_j / SITE.energy.battery_capacity_j
    assert SITE.energy.battery_floor_soc - 1e-9 <= soc <= 1 + 1e-9
    expected_flag = {
        "charging": metrics.battery_charge_energy_j > 0,
        "pump_on_battery": metrics.battery_discharge_energy_j > 0 and metrics.pump_energy_j > 0,
        "full_battery": metrics.curtailed_energy_j > 0,
        "shortage": metrics.unserved_energy_j > 0,
    }[case]
    assert expected_flag


def test_shortage_records_an_aux_power_outage_event():
    state = new_run_state(SITE, seed=7)
    set_all_moisture(state, 0.21)
    state.battery_energy_j = SITE.energy.battery_floor_soc * SITE.energy.battery_capacity_j
    state.environment.cloud_factor = 0.0
    state.environment.inflow_available = False

    state, results = run_steps(state, 5)

    outage_events = [event for result in results for event in result.events if event.reason_code == "AUX_POWER_OUTAGE"]
    assert len(outage_events) == 1
    assert state.power.unserved_power_w == pytest.approx(SITE.energy.aux_power_w)



def test_battery_respects_its_charge_limit():
    cfg = replace_config(SITE, energy=replace_config(SITE.energy, battery_max_charge_w=2000.0))
    state = new_run_state(cfg, seed=7)
    state.battery_energy_j = 0.3 * cfg.energy.battery_capacity_j
    set_all_moisture(state, 0.21)
    state.step = 6 * 60  # noon: solar exceeds the charge limit

    result = step(state, cfg)

    assert result.state.power.charge_power_w == pytest.approx(2000.0)
    assert result.state.power.curtail_power_w > 0
