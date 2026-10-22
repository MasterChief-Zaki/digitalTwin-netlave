"""One 60-second step of the twin, in the causal order of the execution plan (section 6).

The engine owns time, decisions and accounting. Every step asserts finite state
and closes the reservoir and soil balances; a failure raises with the step, the
account, both sides and the input context.
"""

import math
from dataclasses import dataclass

import schemas
from config import DT_S, SiteConfig
from control.policy import ZoneRequest, propose
from control.safety import Grant, SafetyContext, resolve
from models.water_soil import (
    SoilStepResult,
    soil_storage_m3,
    update_reservoir,
    update_soil,
    usable_volume_m3,
    water_stress,
)
from twin.inputs import StepInputs, clock, inputs_at
from twin.state import DecisionRecord, SimState


class PhysicsInvariantError(RuntimeError):
    pass


@dataclass(frozen=True)
class EventDraft:
    """An event before the API ledger gives it an ID."""

    category: schemas.EventCategory
    zone_id: str | None
    reason_code: schemas.ReasonCode
    message: str


@dataclass(frozen=True)
class StepResult:
    state: SimState
    decisions: tuple[DecisionRecord, ...]
    events: tuple[EventDraft, ...]
    soil: tuple[SoilStepResult, ...]


def step(previous: SimState, cfg: SiteConfig) -> StepResult:
    state = previous.clone()
    events: list[EventDraft] = []

    # 1. Step-indexed inflow and ET.
    step_inputs = inputs_at(previous.step, previous.seed, _inflow_available(previous), cfg)
    _, minute_of_day = clock(previous.step, cfg)

    # 2. Controller requests (smart hysteresis, fixed timer or manual).
    requests = [
        propose(
            zone,
            zone_config,
            water_stress(zone.theta_m3_m3, cfg.soil),
            state.environment.control_policy,
            minute_of_day,
            cfg,
        )
        for zone, zone_config in zip(state.zones, cfg.zones, strict=True)
    ]

    # 4. Deterministic ranking: water stress descending, then zone ID.
    ranked = sorted(requests, key=lambda request: (-request.water_stress, request.zone_id))

    # 5. Safety gates.
    context = SafetyContext(dt_s=DT_S, usable_volume_m3=usable_volume_m3(previous.reservoir_volume_m3, cfg.reservoir))
    grants = resolve(ranked, context, cfg)

    # 6-7. Deliver accepted flow, then update reservoir, soil, events and metrics.
    delivered_m3 = sum(grant.flow_m3_s for grant in grants.values()) * DT_S
    inflow_m3 = step_inputs.tse_inflow_m3_s * DT_S
    reservoir = update_reservoir(previous.reservoir_volume_m3, inflow_m3, delivered_m3, cfg.reservoir)

    soil_results = []
    decisions = []
    for zone, zone_config, request in zip(state.zones, cfg.zones, requests, strict=True):
        grant = grants[zone.zone_id]
        soil = update_soil(zone.theta_m3_m3, grant.flow_m3_s * DT_S, step_inputs.et0_step_mm, zone_config, cfg.soil)
        soil_results.append(soil)
        decisions.append(_apply_grant(state, zone, request, grant, soil, events))

    _book_water(state, inflow_m3, delivered_m3, reservoir.overflow_m3, soil_results, decisions)
    if reservoir.overflow_m3 > 0 and not previous.overflow_active:
        events.append(
            EventDraft("WATER", None, "OVERFLOW_OCCURRING", "Reservoir is full; arriving TSE is spilling to overflow.")
        )
    state.overflow_active = reservoir.overflow_m3 > 0
    state.reservoir_volume_m3 = reservoir.volume_m3
    state.inflow_m3_s = step_inputs.tse_inflow_m3_s
    state.overflow_flow_m3_s = reservoir.overflow_m3 / DT_S
    state.et0_mm_day = step_inputs.et0_mm_day
    state.decisions = decisions

    # 8. Accounts and bounds.
    _check_water_balances(previous, state, inflow_m3, delivered_m3, reservoir.overflow_m3, soil_results, cfg, step_inputs)
    _check_bounds(state, cfg, step_inputs)

    # 9. Advance the clock once.
    state.step = previous.step + 1
    return StepResult(state, tuple(decisions), tuple(events), tuple(soil_results))


def _inflow_available(state: SimState) -> bool:
    outage = state.environment.inflow_outage_steps
    in_outage = outage is not None and outage[0] <= state.step < outage[1]
    return state.environment.inflow_available and not in_outage


def _apply_grant(
    state: SimState,
    zone,
    request: ZoneRequest,
    grant: Grant,
    soil: SoilStepResult,
    events: list[EventDraft],
) -> DecisionRecord:
    if request.wants_water and not grant.accepted:
        state.metrics.requested_undelivered_m3 += grant.requested_flow_m3_s * DT_S
        if zone.active_denial != grant.reason_code:
            events.append(EventDraft("DENIAL", zone.zone_id, grant.reason_code, grant.explanation))
        zone.active_denial = grant.reason_code
    else:
        zone.active_denial = None

    zone.irrigation_latched = request.irrigation_latched
    zone.valve_open = grant.flow_m3_s > 0
    zone.requested_flow_m3_s = grant.requested_flow_m3_s
    zone.delivered_flow_m3_s = grant.flow_m3_s
    zone.theta_m3_m3 = soil.theta_m3_m3
    return DecisionRecord(zone.zone_id, request.action, grant.accepted, grant.reason_code, grant.explanation)


def _book_water(
    state: SimState,
    inflow_m3: float,
    delivered_m3: float,
    overflow_m3: float,
    soil_results: list[SoilStepResult],
    decisions: list[DecisionRecord],
) -> None:
    metrics = state.metrics
    metrics.tse_inflow_m3 += inflow_m3
    metrics.irrigation_delivered_m3 += delivered_m3
    metrics.overflow_m3 += overflow_m3
    for soil in soil_results:
        metrics.application_loss_m3 += soil.application_loss_m3
        metrics.deep_percolation_m3 += soil.drainage_m3
        metrics.potential_et_m3 += soil.potential_et_m3
        metrics.actual_et_m3 += soil.actual_et_m3
        metrics.et_deficit_m3 += soil.potential_et_m3 - soil.actual_et_m3


def check_balance(step_index: int, account: str, lhs: float, rhs: float, context: object) -> None:
    tolerance = 1e-9 + 1e-6 * max(abs(lhs), abs(rhs))
    if not (math.isfinite(lhs) and math.isfinite(rhs)) or abs(lhs - rhs) > tolerance:
        raise PhysicsInvariantError(f"step {step_index}: {account} does not close: lhs={lhs!r} rhs={rhs!r}; {context}")


def _check_water_balances(
    previous: SimState,
    state: SimState,
    inflow_m3: float,
    delivered_m3: float,
    overflow_m3: float,
    soil_results: list[SoilStepResult],
    cfg: SiteConfig,
    step_inputs: StepInputs,
) -> None:
    check_balance(
        previous.step,
        "reservoir",
        state.reservoir_volume_m3 - previous.reservoir_volume_m3,
        inflow_m3 - delivered_m3 - overflow_m3,
        step_inputs,
    )
    for before, after, zone_config, soil in zip(previous.zones, state.zones, cfg.zones, soil_results, strict=True):
        check_balance(
            previous.step,
            f"soil zone {zone_config.zone_id}",
            soil_storage_m3(after.theta_m3_m3, zone_config, cfg.soil)
            - soil_storage_m3(before.theta_m3_m3, zone_config, cfg.soil),
            soil.infiltrated_m3 - soil.actual_et_m3 - soil.drainage_m3,
            step_inputs,
        )


def _check_bounds(state: SimState, cfg: SiteConfig, step_inputs: StepInputs) -> None:
    tolerance = 1e-9
    problems = []
    if not 0.0 <= state.reservoir_volume_m3 <= cfg.reservoir.capacity_m3 + 1e-6:
        problems.append(f"reservoir volume {state.reservoir_volume_m3}")
    for zone in state.zones:
        if not (cfg.soil.theta_wp_m3_m3 - tolerance <= zone.theta_m3_m3 <= cfg.soil.theta_sat_m3_m3 + tolerance):
            problems.append(f"zone {zone.zone_id} moisture {zone.theta_m3_m3}")
    if problems:
        raise PhysicsInvariantError(f"step {state.step}: out of bounds: {', '.join(problems)}; {step_inputs}")
