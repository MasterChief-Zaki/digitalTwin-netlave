"""API tests: the deterministic clock and the step and generation guards."""

import threading

import pytest
from fastapi.testclient import TestClient

import schemas
from main import StepConflict, TwinService, create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def advance(client: TestClient, expected_step: int, steps: int, request_id: str, run_generation: int = 1):
    return client.post(
        "/advance",
        json={
            "run_generation": run_generation,
            "expected_step": expected_step,
            "steps": steps,
            "request_id": request_id,
        },
    )


def test_state_returns_a_versioned_simulated_snapshot(client: TestClient):
    response = client.get("/state")

    assert response.status_code == 200
    snapshot = response.json()
    assert snapshot["schema_version"] == "1.0"
    assert snapshot["data_mode"] == "SIMULATED"
    assert snapshot["step"] == 0
    assert snapshot["run_generation"] == 1


def test_advance_moves_exactly_n_sixty_second_steps(client: TestClient):
    response = advance(client, expected_step=0, steps=12, request_id="r-1")

    assert response.status_code == 200
    snapshot = response.json()["snapshot"]
    assert snapshot["step"] == 12
    assert snapshot["sim_time_s"] == 12 * 60
    assert client.get("/state").json()["step"] == 12


def test_advance_with_a_stale_step_is_a_structured_conflict(client: TestClient):
    advance(client, expected_step=0, steps=3, request_id="r-1")

    response = advance(client, expected_step=0, steps=3, request_id="r-2")

    assert response.status_code == 409
    assert response.json() == {
        "error_code": "STEP_CONFLICT",
        "message": response.json()["message"],
        "current_step": 3,
        "run_generation": 1,
    }
    assert client.get("/state").json()["step"] == 3


def test_advance_with_a_stale_generation_is_rejected(client: TestClient):
    response = advance(client, expected_step=0, steps=1, request_id="r-1", run_generation=0)

    assert response.status_code == 409
    assert response.json()["error_code"] == "STEP_CONFLICT"
    assert client.get("/state").json()["step"] == 0


def test_invalid_advance_payload_is_a_validation_error(client: TestClient):
    response = advance(client, expected_step=0, steps=0, request_id="r-1")

    assert response.status_code == 422


# Idempotency, concurrency, commands, reset, events and scenarios (A1-A3).

def test_a1_retried_advance_returns_the_cached_reply_without_stepping(client: TestClient):
    first = advance(client, expected_step=0, steps=5, request_id="retry-me")
    retry = advance(client, expected_step=0, steps=5, request_id="retry-me")

    assert retry.status_code == 200
    assert retry.json() == first.json()
    assert client.get("/state").json()["step"] == 5


def test_reusing_a_request_id_with_other_arguments_is_a_conflict(client: TestClient):
    advance(client, expected_step=0, steps=5, request_id="once")

    response = advance(client, expected_step=0, steps=6, request_id="once")

    assert response.status_code == 409
    assert response.json()["error_code"] == "IDEMPOTENCY_CONFLICT"
    assert client.get("/state").json()["step"] == 5


def test_a2_two_clients_on_the_same_step_advance_once():
    service = TwinService()
    barrier = threading.Barrier(2)
    outcomes: list[str] = []

    def client_advance(request_id: str) -> None:
        barrier.wait()
        try:
            service.advance(schemas.AdvanceRequest(run_generation=1, expected_step=0, steps=10, request_id=request_id))
            outcomes.append("advanced")
        except StepConflict:
            outcomes.append("conflict")

    threads = [threading.Thread(target=client_advance, args=(name,)) for name in ("tab-1", "tab-2")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(outcomes) == ["advanced", "conflict"]
    assert service.state.step == 10


def test_a3_requests_from_an_old_generation_cannot_touch_the_new_run(client: TestClient):
    advance(client, expected_step=0, steps=4, request_id="old-run")
    reset = client.post("/reset", json={"scenario_id": "low_solar", "seed": 3})
    assert reset.status_code == 200
    assert reset.json()["run_generation"] == 2
    assert reset.json()["step"] == 0

    late = advance(client, expected_step=4, steps=1, request_id="old-run-2", run_generation=1)
    replayed = advance(client, expected_step=0, steps=4, request_id="old-run", run_generation=1)

    assert late.status_code == 409
    assert replayed.status_code == 409
    state = client.get("/state").json()
    assert state["step"] == 0
    assert state["scenario_id"] == "low_solar"


def test_reset_emits_scenario_loaded(client: TestClient):
    client.post("/reset", json={"scenario_id": "clogged_filter", "seed": 7})

    page = client.get("/events", params={"since_id": 0}).json()

    assert [event["reason_code"] for event in page["events"]][-1] == "SCENARIO_LOADED"
    assert page["latest_event_id"] == page["events"][-1]["id"]
    assert page["history_truncated"] is False


def test_events_since_id_returns_only_newer_events(client: TestClient):
    client.post("/reset", json={"scenario_id": "clogged_filter", "seed": 7})
    latest = client.get("/state").json()["latest_event_id"]
    advance(client, expected_step=0, steps=20, request_id="r-1", run_generation=2)

    page = client.get("/events", params={"since_id": latest}).json()

    assert page["events"]
    assert all(event["id"] > latest for event in page["events"])
    assert "FILTER_FLUSH_STARTED" in {event["reason_code"] for event in page["events"]}


def test_command_sets_a_manual_mode_and_logs_it(client: TestClient):
    response = client.post(
        "/command",
        json={
            "run_generation": 1,
            "expected_step": 0,
            "command": {"type": "set_zone_mode", "zone_id": "C", "mode": "MANUAL_OPEN"},
        },
    )

    assert response.status_code == 200
    snapshot = response.json()
    assert snapshot["zones"][2]["control_mode"] == "MANUAL_OPEN"
    assert snapshot["step"] == 0
    events = client.get("/events", params={"since_id": 0}).json()["events"]
    assert events[-1]["reason_code"] == "OPERATOR_COMMAND"


def test_environment_commands_change_the_inputs(client: TestClient):
    commands = [
        {"type": "set_water_quality", "status": "HOLD"},
        {"type": "set_cloud_factor", "cloud_factor": 0.25},
        {"type": "set_solids_multiplier", "multiplier": 8},
        {"type": "set_inflow_available", "available": False},
    ]
    for command in commands:
        response = client.post("/command", json={"run_generation": 1, "expected_step": 0, "command": command})
        assert response.status_code == 200

    environment = client.get("/state").json()["environment"]
    assert environment["water_quality"] == "HOLD"
    assert environment["cloud_factor"] == 0.25
    assert environment["solids_loading_multiplier"] == 8
    assert environment["inflow_available"] is False


def test_stale_command_is_rejected(client: TestClient):
    advance(client, expected_step=0, steps=2, request_id="r-1")

    response = client.post(
        "/command",
        json={"run_generation": 1, "expected_step": 0, "command": {"type": "set_water_quality", "status": "HOLD"}},
    )

    assert response.status_code == 409
    assert client.get("/state").json()["environment"]["water_quality"] == "OK"


def test_invalid_command_is_a_validation_error(client: TestClient):
    response = client.post(
        "/command",
        json={"run_generation": 1, "expected_step": 0, "command": {"type": "open_everything"}},
    )

    assert response.status_code == 422


def test_scenarios_lists_presets_and_assumptions(client: TestClient):
    body = client.get("/scenarios").json()

    assert {scenario["id"] for scenario in body["scenarios"]} == {
        "baseline",
        "clogged_filter",
        "low_solar",
        "tse_interrupt",
    }
    assert all(row["status"] in ("assumed", "derived", "measured") for row in body["assumptions"])
    assert len(body["assumptions"]) >= 25


def test_compare_reports_both_policies_without_touching_the_live_run(client: TestClient):
    advance(client, expected_step=0, steps=3, request_id="before-compare")

    response = client.post("/compare", json={"scenario_id": "baseline", "seed": 7, "horizon_days": 2})

    assert response.status_code == 200
    report = response.json()
    assert report["data_mode"] == "SIMULATED"
    assert report["steps"] == 2 * 1440
    assert report["fixed_timer"]["policy"] == "FIXED_TIMER"
    assert report["smart_hysteresis"]["policy"] == "SMART_HYSTERESIS"
    assert report["fixed_timer"]["input_digest"] == report["smart_hysteresis"]["input_digest"]
    state = client.get("/state").json()
    assert state["step"] == 3
    assert state["environment"]["control_policy"] == "SMART_HYSTERESIS"


def test_compare_limits_the_horizon(client: TestClient):
    for horizon_days in (0, 31):
        response = client.post("/compare", json={"scenario_id": "baseline", "seed": 7, "horizon_days": horizon_days})
        assert response.status_code == 422
