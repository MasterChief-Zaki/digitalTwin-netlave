"""API tests: the deterministic clock and the step and generation guards."""

import pytest
from fastapi.testclient import TestClient

from main import create_app


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
