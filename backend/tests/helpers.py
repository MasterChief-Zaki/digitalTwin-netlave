"""Shared helpers for the backend tests."""

import math

from config import SITE
from twin.engine import StepResult, step
from twin.state import SimState


def run_steps(state: SimState, steps: int) -> tuple[SimState, list[StepResult]]:
    results: list[StepResult] = []
    for _ in range(steps):
        result = step(state, SITE)
        results.append(result)
        state = result.state
    return state, results


def assert_close(actual: float, expected: float, label: str) -> None:
    tolerance = 1e-9 + 1e-6 * max(abs(actual), abs(expected))
    assert math.isfinite(actual) and math.isfinite(expected), label
    assert abs(actual - expected) <= tolerance, f"{label}: {actual} != {expected}"


def set_all_moisture(state: SimState, theta_m3_m3: float) -> None:
    for zone in state.zones:
        zone.theta_m3_m3 = theta_m3_m3
