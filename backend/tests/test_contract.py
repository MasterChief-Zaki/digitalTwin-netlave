"""Contract tests: the shared fixture, the frozen reason codes and the derived soil thresholds."""

import json
import typing
from pathlib import Path

import pytest
from pydantic import ValidationError

import schemas
from config import SITE

FIXTURE_PATH = Path(__file__).resolve().parents[2] / "src" / "fixtures" / "initial-snapshot.json"

FROZEN_REASON_CODES = {
    "SOIL_BELOW_THRESHOLD",
    "KEEP_OPEN",
    "KEEP_CLOSED",
    "MANUAL_OVERRIDE_OK",
    "MANUAL_STOP_OK",
    "WATER_QUALITY_HOLD",
    "FLUSH_IN_PROGRESS",
    "FILTER_FLUSH_REQUIRED",
    "RESERVOIR_LOW",
    "INSUFFICIENT_HEAD",
    "CONCURRENT_FLOW_LIMIT",
    "POWER_DEFICIT",
    "BATTERY_BELOW_RESERVE",
    "AUX_POWER_OUTAGE",
    "FILTER_FLUSH_STARTED",
    "FILTER_FLUSH_COMPLETE",
    "OVERFLOW_OCCURRING",
    "SCENARIO_LOADED",
    # Added by ruling 3 of the plan.
    "MOISTURE_TARGET_REACHED",
    "SCHEDULE_WINDOW_OPEN",
    "SCHEDULE_WINDOW_CLOSED",
    "OPERATOR_COMMAND",
    "SCHEDULER_WATER_HOLD",
    "SCHEDULER_ENERGY_HOLD",
    "SCHEDULER_QUEUE",
    "SCHEDULER_REST",
}


def load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_fixture_validates_as_a_snapshot():
    snapshot = schemas.SimulationSnapshot.model_validate(load_fixture())

    assert snapshot.schema_version == "1.1"
    assert snapshot.data_mode == "SIMULATED"
    assert snapshot.step == 0
    assert snapshot.sim_time_s == 0
    assert snapshot.latest_event_id == 0


def test_fixture_matches_the_initial_conditions():
    snapshot = schemas.SimulationSnapshot.model_validate(load_fixture())

    assert snapshot.reservoir.volume_m3 == 900
    assert snapshot.reservoir.capacity_m3 == 1500
    assert snapshot.energy.battery_soc_0_1 == pytest.approx(0.80)
    assert [zone.id for zone in snapshot.zones] == ["A", "B", "C"]
    assert all(zone.soil_moisture_m3_m3 == pytest.approx(0.165) for zone in snapshot.zones)
    assert all(zone.delivered_flow_m3_s == 0 for zone in snapshot.zones)
    assert snapshot.environment.water_quality == "OK"
    assert len(snapshot.decisions) == 3


def test_snapshot_rejects_unknown_fields():
    fixture = load_fixture()
    fixture["reservoir"]["volume_litres"] = 1

    with pytest.raises(ValidationError):
        schemas.SimulationSnapshot.model_validate(fixture)


def test_snapshot_requires_exactly_three_zones():
    fixture = load_fixture()
    fixture["zones"] = fixture["zones"][:2]

    with pytest.raises(ValidationError):
        schemas.SimulationSnapshot.model_validate(fixture)


def test_reason_codes_are_frozen():
    assert set(typing.get_args(schemas.ReasonCode)) == FROZEN_REASON_CODES


def test_advance_request_limits_steps_to_sixty():
    valid = {"run_generation": 1, "expected_step": 0, "steps": 60, "request_id": "demo-1-1"}
    schemas.AdvanceRequest.model_validate(valid)

    for steps in (0, 61):
        with pytest.raises(ValidationError):
            schemas.AdvanceRequest.model_validate({**valid, "steps": steps})


def test_command_payload_is_discriminated_by_type():
    request = schemas.CommandRequest.model_validate(
        {
            "run_generation": 1,
            "expected_step": 0,
            "command": {"type": "set_zone_mode", "zone_id": "C", "mode": "MANUAL_OPEN"},
        }
    )
    assert isinstance(request.command, schemas.SetZoneModeCommand)

    with pytest.raises(ValidationError):
        schemas.CommandRequest.model_validate(
            {"run_generation": 1, "expected_step": 0, "command": {"type": "set_cloud_factor", "cloud_factor": 2}}
        )


def test_moisture_thresholds_are_derived_from_depletion():
    # 45% management-allowed depletion from field capacity, not 45% above wilting point.
    assert SITE.soil.theta_on_m3_m3 == pytest.approx(0.166)
    assert SITE.soil.theta_off_m3_m3 == pytest.approx(0.198)


def test_site_has_fifteen_hectares_in_three_zones():
    assert [zone.zone_id for zone in SITE.zones] == ["A", "B", "C"]
    assert sum(zone.area_m2 for zone in SITE.zones) == 150_000
