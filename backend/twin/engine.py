"""One 60-second step of the twin, in the causal order of the execution plan (section 6).

The engine owns time, decisions and accounting. Every step asserts finite state
and closes the reservoir, soil, bus and battery-cell balances; a failure raises
with the step, the account, both sides and the input context.
"""

import math
from dataclasses import dataclass

import schemas
from config import DT_S, SiteConfig, ZoneConfig
from control.policy import ZoneRequest, propose
from control.safety import Grant, SafetyContext, ZoneHydraulics, resolve
from models.energy import Dispatch, dispatch
from models.solar_profiles import profile_solar_power_w
from models.filtration import FlushPlan, filter_head_loss_m, load_filter, plan_flush
from models.hydraulics import gravity_head, hydro_power_w, pump_requirement
from models.water_soil import (
    SoilStepResult,
    soil_storage_m3,
    surface_elevation_m,
    update_reservoir,
    update_soil,
    usable_volume_m3,
    water_stress,
)
from twin.inputs import StepInputs, clock, inputs_at
from twin.state import DecisionRecord, SimState, ZoneState


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
    inputs: StepInputs


@dataclass(frozen=True)
class PowerBudget:
    hydro_w: float
    solar_w: float
    aux_w: float
    flush_w: float
    pump_w: float

    @property
    def generation_w(self) -> float:
        return self.hydro_w + self.solar_w

    @property
    def load_w(self) -> float:
        return self.aux_w + self.flush_w + self.pump_w


def step(previous: SimState, cfg: SiteConfig) -> StepResult:
    state = previous.clone()
    environment = state.environment
    events: list[EventDraft] = []

    # 1. Step-indexed inflow, ET and generation.
    step_inputs = inputs_at(previous.step, previous.seed, _inflow_available(previous), cfg)
    _, minute_of_day = clock(previous.step, cfg)
    hydro_w = hydro_power_w(
        step_inputs.tse_inflow_m3_s, cfg.supply.hydro_recoverable_head_m, cfg.supply.hydro_turbine_efficiency
    )
    solar_w = profile_solar_power_w(
        step_inputs.hour_of_day, environment.cloud_factor, cfg.energy,
        environment.solar_profile_id, previous.step - environment.profile_start_step,
    )

    # 2. Controller requests (smart hysteresis, fixed timer or manual).
    requests = [
        propose(
            zone,
            zone_config,
            water_stress(zone.theta_m3_m3, cfg.soil),
            environment.control_policy,
            minute_of_day,
            cfg,
        )
        for zone, zone_config in zip(state.zones, cfg.zones, strict=True)
    ]

    # 3. Is a filter flush in progress or mandatory? A flush is exclusive.
    usable_m3 = usable_volume_m3(previous.reservoir_volume_m3, cfg.reservoir)
    aux_w = cfg.energy.aux_power_w
    floor_j = cfg.energy.battery_floor_soc * cfg.energy.battery_capacity_j
    flush = plan_flush(
        previous.filter.flushing,
        previous.filter.clog_index,
        usable_m3,
        hydro_w + solar_w,
        aux_w,
        max(0.0, previous.battery_energy_j - floor_j),
        cfg.filtration,
        cfg.energy,
        DT_S,
    )

    # 4. Deterministic ranking: open valves keep their supply (no preemption), then water
    #    stress descending, then zone ID.
    ranked = sorted(
        requests,
        key=lambda request: (request.action != "KEEP_OPEN", -request.water_stress, request.zone_id),
    )

    # 5. Quality, reservoir, head, manifold, pump and electrical gates.
    surface_m = surface_elevation_m(previous.reservoir_volume_m3, cfg.reservoir)
    filter_head_m = filter_head_loss_m(previous.filter.clog_index, cfg.filtration)
    hydraulics = {
        zone_config.zone_id: _zone_hydraulics(zone_config, surface_m, filter_head_m, cfg) for zone_config in cfg.zones
    }
    context = SafetyContext(
        dt_s=DT_S,
        usable_volume_m3=usable_m3,
        hydraulics=hydraulics,
        generation_w=hydro_w + solar_w,
        battery_energy_j=previous.battery_energy_j,
        water_quality=environment.water_quality,
        filter_blocks_irrigation=flush.blocks_irrigation,
        committed_withdrawal_m3=flush.water_m3,
        committed_load_w=aux_w + flush.power_w,
    )
    grants = resolve(ranked, context, cfg)

    # 6. Deliver accepted flow and dispatch the electrical bus.
    budget = PowerBudget(
        hydro_w=hydro_w, solar_w=solar_w, aux_w=aux_w, flush_w=flush.power_w, pump_w=context.granted_pump_w
    )
    power = dispatch(budget.generation_w, budget.load_w, previous.battery_energy_j, cfg.energy, DT_S)
    delivered_m3 = sum(grant.flow_m3_s for grant in grants.values()) * DT_S
    inflow_m3 = step_inputs.tse_inflow_m3_s * DT_S

    # 7. Reservoir, soil buckets, events and metrics.
    reservoir = update_reservoir(previous.reservoir_volume_m3, inflow_m3, delivered_m3 + flush.water_m3, cfg.reservoir)
    soil_results = []
    decisions = []
    for zone, zone_config, request in zip(state.zones, cfg.zones, requests, strict=True):
        grant = grants[zone.zone_id]
        soil = update_soil(zone.theta_m3_m3, grant.flow_m3_s * DT_S, step_inputs.et0_step_mm, zone_config, cfg.soil)
        soil_results.append(soil)
        decisions.append(_apply_grant(state, zone, request, grant, soil, hydraulics[zone.zone_id], events, cfg))

    _book_water(state, inflow_m3, delivered_m3, flush.water_m3, reservoir.overflow_m3, soil_results)
    _update_filter(state, flush, delivered_m3, cfg, events)
    _book_energy(state, budget, power)
    _apply_pump(state, hydraulics["C"], grants["C"])
    if reservoir.overflow_m3 > 0 and not previous.overflow_active:
        events.append(
            EventDraft("WATER", None, "OVERFLOW_OCCURRING", "Reservoir is full; arriving TSE is spilling to overflow.")
        )
    if power.unserved_power_w > 0 and not previous.aux_outage_active:
        events.append(
            EventDraft(
                "ENERGY",
                None,
                "AUX_POWER_OUTAGE",
                f"Battery is at its floor and generation is {budget.generation_w:,.0f} W; "
                f"{power.unserved_power_w:,.0f} W of auxiliary load (controller, sensors) is unserved.",
            )
        )
    state.overflow_active = reservoir.overflow_m3 > 0
    state.aux_outage_active = power.unserved_power_w > 0
    state.reservoir_volume_m3 = reservoir.volume_m3
    state.battery_energy_j = power.battery_energy_j
    state.minimum_reservoir_volume_m3 = min(state.minimum_reservoir_volume_m3, reservoir.volume_m3)
    state.minimum_battery_soc_0_1 = min(
        state.minimum_battery_soc_0_1, power.battery_energy_j / cfg.energy.battery_capacity_j
    )
    state.inflow_m3_s = step_inputs.tse_inflow_m3_s
    state.overflow_flow_m3_s = reservoir.overflow_m3 / DT_S
    state.et0_mm_day = step_inputs.et0_mm_day
    state.decisions = decisions

    # 8. Accounts and bounds.
    _check_water_balances(
        previous, state, inflow_m3, delivered_m3 + flush.water_m3, reservoir.overflow_m3, soil_results, cfg, step_inputs
    )
    _check_energy_balances(previous, state, budget, power, step_inputs)
    _check_bounds(state, cfg, step_inputs)

    # 9. Advance the clock once.
    state.step = previous.step + 1
    return StepResult(state, tuple(decisions), tuple(events), tuple(soil_results), step_inputs)


def _inflow_available(state: SimState) -> bool:
    outage = state.environment.inflow_outage_steps
    in_outage = outage is not None and outage[0] <= state.step < outage[1]
    return state.environment.inflow_available and not in_outage


def _zone_hydraulics(zone: ZoneConfig, surface_m: float, filter_head_m: float, cfg: SiteConfig) -> ZoneHydraulics:
    """Head at the zone's rated flow, computed every step so the margin is visible even when idle."""
    if zone.feed_mode == "PUMPED":
        return ZoneHydraulics(pump=pump_requirement(zone, surface_m, filter_head_m, zone.max_flow_m3_s, cfg.hydraulics))
    return ZoneHydraulics(gravity=gravity_head(zone, surface_m, filter_head_m, zone.max_flow_m3_s, cfg.hydraulics))


def _apply_grant(
    state: SimState,
    zone: ZoneState,
    request: ZoneRequest,
    grant: Grant,
    soil: SoilStepResult,
    hydraulics: ZoneHydraulics,
    events: list[EventDraft],
    cfg: SiteConfig,
) -> DecisionRecord:
    if request.wants_water and not grant.accepted:
        state.metrics.requested_undelivered_m3 += grant.requested_flow_m3_s * DT_S
        if zone.active_denial != grant.reason_code:
            events.append(EventDraft("DENIAL", zone.zone_id, grant.reason_code, grant.explanation))
        zone.active_denial = grant.reason_code
    else:
        zone.active_denial = None

    if hydraulics.gravity is not None:
        zone.head_available_m = hydraulics.gravity.available_m
        zone.head_required_m = hydraulics.gravity.required_m
    elif hydraulics.pump is not None:
        zone.head_available_m = hydraulics.pump.head_within_limit_m
        zone.head_required_m = hydraulics.pump.total_dynamic_head_m

    accounts = zone.accounts
    accounts.irrigation_requested_m3 += grant.requested_flow_m3_s * DT_S
    accounts.irrigation_delivered_m3 += grant.flow_m3_s * DT_S
    accounts.potential_et_m3 += soil.potential_et_m3
    accounts.actual_et_m3 += soil.actual_et_m3
    if zone.theta_m3_m3 < cfg.soil.theta_on_m3_m3:
        accounts.below_trigger_min += DT_S / 60.0
    if request.wants_water and not grant.accepted:
        accounts.denied_by_reason_min[grant.reason_code] = accounts.denied_by_reason_min.get(grant.reason_code, 0.0) + DT_S / 60.0
    accounts.minimum_moisture_m3_m3 = min(accounts.minimum_moisture_m3_m3, soil.theta_m3_m3)
    margin_m = zone.head_available_m - zone.head_required_m
    accounts.minimum_head_margin_m = margin_m if accounts.minimum_head_margin_m is None else min(accounts.minimum_head_margin_m, margin_m)
    if grant.flow_m3_s > 0 and not zone.valve_open:
        accounts.session_count += 1
    zone.irrigation_latched = request.irrigation_latched
    zone.valve_open = grant.flow_m3_s > 0
    zone.requested_flow_m3_s = grant.requested_flow_m3_s
    zone.delivered_flow_m3_s = grant.flow_m3_s
    zone.theta_m3_m3 = soil.theta_m3_m3
    return DecisionRecord(zone.zone_id, request.action, grant.accepted, grant.reason_code, grant.explanation)


def _apply_pump(state: SimState, hydraulics: ZoneHydraulics, grant: Grant) -> None:
    if hydraulics.pump is None:
        return
    state.pump.total_dynamic_head_m = hydraulics.pump.total_dynamic_head_m
    state.pump.required_power_w = hydraulics.pump.power_w
    state.pump.running = grant.flow_m3_s > 0


def _book_water(
    state: SimState,
    inflow_m3: float,
    delivered_m3: float,
    flush_water_m3: float,
    overflow_m3: float,
    soil_results: list[SoilStepResult],
) -> None:
    metrics = state.metrics
    metrics.tse_inflow_m3 += inflow_m3
    metrics.irrigation_delivered_m3 += delivered_m3
    metrics.flush_water_m3 += flush_water_m3
    metrics.overflow_m3 += overflow_m3
    for soil in soil_results:
        metrics.application_loss_m3 += soil.application_loss_m3
        metrics.deep_percolation_m3 += soil.drainage_m3
        metrics.potential_et_m3 += soil.potential_et_m3
        metrics.actual_et_m3 += soil.actual_et_m3
        metrics.et_deficit_m3 += soil.potential_et_m3 - soil.actual_et_m3


def _update_filter(
    state: SimState, flush: FlushPlan, filtered_m3: float, cfg: SiteConfig, events: list[EventDraft]
) -> None:
    filtration = cfg.filtration
    filter_state = state.filter
    if flush.started:
        events.append(
            EventDraft(
                "FILTER",
                None,
                "FILTER_FLUSH_STARTED",
                f"Filter clog index {filter_state.clog_index:.2f} reached {filtration.flush_threshold:.2f}; "
                f"backflushing for {filtration.flush_steps} minutes ({filtration.flush_water_m3:.1f} m3, "
                f"{filtration.flush_power_w * filtration.flush_steps * 60 / 3.6e6:.2f} kWh). Irrigation is suspended.",
            )
        )
        filter_state.flush_steps_remaining = filtration.flush_steps
    if flush.flushing:
        filter_state.flushing = True
        filter_state.flush_steps_remaining -= 1
        if filter_state.flush_steps_remaining == 0:
            filter_state.flushing = False
            filter_state.clog_index = filtration.clog_after_flush
            state.metrics.flush_count += 1
            events.append(
                EventDraft(
                    "FILTER",
                    None,
                    "FILTER_FLUSH_COMPLETE",
                    f"Flush complete; clog index back to {filtration.clog_after_flush:.2f} and head restored.",
                )
            )
    else:
        filter_state.clog_index = load_filter(
            filter_state.clog_index, filtered_m3, state.environment.solids_loading_multiplier, filtration
        )
    filter_state.flush_required = not filter_state.flushing and filter_state.clog_index >= filtration.flush_threshold


def _book_energy(state: SimState, budget: PowerBudget, power: Dispatch) -> None:
    flows = state.power
    flows.hydro_power_w = budget.hydro_w
    flows.solar_power_w = budget.solar_w
    flows.pump_power_w = budget.pump_w
    flows.aux_power_w = budget.aux_w
    flows.flush_power_w = budget.flush_w
    flows.charge_power_w = power.charge_power_w
    flows.discharge_power_w = power.discharge_power_w
    flows.curtail_power_w = power.curtail_power_w
    flows.unserved_power_w = power.unserved_power_w

    metrics = state.metrics
    metrics.hydro_energy_j += budget.hydro_w * DT_S
    metrics.solar_energy_j += budget.solar_w * DT_S
    metrics.pump_energy_j += budget.pump_w * DT_S
    metrics.aux_energy_j += budget.aux_w * DT_S
    metrics.flush_energy_j += budget.flush_w * DT_S
    metrics.required_electrical_energy_j += budget.load_w * DT_S
    metrics.battery_charge_energy_j += power.charge_power_w * DT_S
    metrics.battery_discharge_energy_j += power.discharge_power_w * DT_S
    metrics.battery_losses_j += power.losses_j
    metrics.curtailed_energy_j += power.curtail_power_w * DT_S
    metrics.unserved_energy_j += power.unserved_power_w * DT_S


def check_balance(step_index: int, account: str, lhs: float, rhs: float, context: object) -> None:
    tolerance = 1e-9 + 1e-6 * max(abs(lhs), abs(rhs))
    if not (math.isfinite(lhs) and math.isfinite(rhs)) or abs(lhs - rhs) > tolerance:
        raise PhysicsInvariantError(f"step {step_index}: {account} does not close: lhs={lhs!r} rhs={rhs!r}; {context}")


def _check_water_balances(
    previous: SimState,
    state: SimState,
    inflow_m3: float,
    withdrawn_m3: float,
    overflow_m3: float,
    soil_results: list[SoilStepResult],
    cfg: SiteConfig,
    step_inputs: StepInputs,
) -> None:
    check_balance(
        previous.step,
        "reservoir",
        state.reservoir_volume_m3 - previous.reservoir_volume_m3,
        inflow_m3 - withdrawn_m3 - overflow_m3,
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


def _check_energy_balances(
    previous: SimState, state: SimState, budget: PowerBudget, power: Dispatch, step_inputs: StepInputs
) -> None:
    check_balance(
        previous.step,
        "electrical bus",
        budget.generation_w + power.discharge_power_w + power.unserved_power_w,
        budget.load_w + power.charge_power_w + power.curtail_power_w,
        step_inputs,
    )
    check_balance(
        previous.step,
        "battery cells",
        state.battery_energy_j - previous.battery_energy_j,
        (power.charge_power_w - power.discharge_power_w) * DT_S - power.losses_j,
        step_inputs,
    )
    if budget.pump_w > 0 and power.unserved_power_w > 0:
        raise PhysicsInvariantError(
            f"step {previous.step}: pump granted {budget.pump_w} W while {power.unserved_power_w} W is unserved"
        )


def _check_bounds(state: SimState, cfg: SiteConfig, step_inputs: StepInputs) -> None:
    tolerance = 1e-9
    problems = []
    if not 0.0 <= state.reservoir_volume_m3 <= cfg.reservoir.capacity_m3 + 1e-6:
        problems.append(f"reservoir volume {state.reservoir_volume_m3}")
    for zone in state.zones:
        if not (cfg.soil.theta_wp_m3_m3 - tolerance <= zone.theta_m3_m3 <= cfg.soil.theta_sat_m3_m3 + tolerance):
            problems.append(f"zone {zone.zone_id} moisture {zone.theta_m3_m3}")
    soc = state.battery_energy_j / cfg.energy.battery_capacity_j
    if not -tolerance <= soc <= 1.0 + tolerance:
        problems.append(f"battery state of charge {soc}")
    if state.power.discharge_power_w > 0 and soc < cfg.energy.battery_floor_soc - tolerance:
        problems.append(f"battery discharged below its floor to {soc}")
    if problems:
        raise PhysicsInvariantError(f"step {state.step}: out of bounds: {', '.join(problems)}; {step_inputs}")
