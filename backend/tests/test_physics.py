"""Physics tests: conservation, bounds and determinism (C1, C2, S1, D1, P4)."""

import json
import math
from pathlib import Path

from config import SITE
from tests.helpers import assert_close, run_steps, set_all_moisture
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
