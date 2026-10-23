"""Headless A/B experiment: fixed timer versus smart hysteresis.

Both runs share the site, hardware, initial state, seed, weather and inflow
series, water quality and safety gates; only the controller's request policy
differs. The live run is never touched. Results can favour either controller,
and lower water use that raises the ET deficit is not a success: the report
always carries the deficit, drainage, energy and unserved load beside any
water saving.
"""

import hashlib
import json
import struct
import time
from dataclasses import dataclass

import schemas
from config import STEPS_PER_DAY, SiteConfig
from scenarios.presets import build_scenario
from twin.engine import step
from twin.state import SimState, to_snapshot, zone_service, site_diagnostics, reset_accounts


@dataclass(frozen=True)
class PolicyResult:
    policy: schemas.ControlPolicy
    input_digest: str
    initial_state_digest: str
    tse_inflow_m3: float
    irrigation_delivered_m3: float
    requested_undelivered_m3: float
    potential_et_m3: float
    actual_et_m3: float
    et_deficit_m3: float
    et_deficit_mm: float
    deep_percolation_m3: float
    overflow_m3: float
    flush_water_m3: float
    flush_count: int
    battery_losses_kwh: float
    pump_energy_kwh: float
    pump_kwh_per_delivered_m3: float
    required_electrical_kwh: float
    unserved_kwh: float
    electrical_autonomy_0_1: float
    final_battery_soc_0_1: float
    final_mean_moisture_m3_m3: float
    denied_request_steps: int
    zones: list[schemas.ZoneService]
    diagnostics: schemas.SiteDiagnostics


@dataclass(frozen=True)
class ComparisonReport:
    scenario_id: schemas.ScenarioId
    seed: int
    horizon_days: int
    steps: int
    fixed_timer: PolicyResult
    smart_hysteresis: PolicyResult
    # (V_fixed - V_smart) / V_fixed; positive means the smart controller applied less water.
    water_savings_fraction: float
    elapsed_s: float
    resource_aware: PolicyResult | None = None
    evaluation_mode: str = "STARTUP_FAULT"
    warmup_days: int = 0
    measurement_start_step: int = 0
    measurement_end_step: int = 0


def run_comparison(
    cfg: SiteConfig, scenario_id: schemas.ScenarioId, seed: int, horizon_days: int,
    evaluation_mode: str = "STARTUP_FAULT", warmup_days: int = 10, include_resource_aware: bool = False,
) -> ComparisonReport:
    started = time.perf_counter()
    steps = horizon_days * STEPS_PER_DAY
    initial = None
    if evaluation_mode == "MATCHED_OPERATION":
        from scenarios.paired_evaluation import matched_initial_state
        initial = matched_initial_state(cfg, scenario_id, seed, warmup_days)
    elif evaluation_mode != "STARTUP_FAULT":
        raise ValueError("Unknown evaluation mode.")
    fixed = _run_policy(cfg, scenario_id, seed, "FIXED_TIMER", steps, initial)
    smart = _run_policy(cfg, scenario_id, seed, "SMART_HYSTERESIS", steps, initial)
    candidate = _run_policy(cfg, scenario_id, seed, "SMART_RESOURCE_AWARE", steps, initial) if include_resource_aware else None
    fixed_m3 = fixed.irrigation_delivered_m3
    return ComparisonReport(
        scenario_id=scenario_id,
        seed=seed,
        horizon_days=horizon_days,
        steps=steps,
        fixed_timer=fixed,
        smart_hysteresis=smart,
        water_savings_fraction=(fixed_m3 - smart.irrigation_delivered_m3) / fixed_m3 if fixed_m3 > 0 else 0.0,
        elapsed_s=time.perf_counter() - started,
        resource_aware=candidate, evaluation_mode=evaluation_mode,
        warmup_days=warmup_days if initial is not None else 0,
        measurement_start_step=initial.step if initial is not None else 0,
        measurement_end_step=(initial.step if initial is not None else 0) + steps,
    )


def _run_policy(
    cfg: SiteConfig, scenario_id: schemas.ScenarioId, seed: int, policy: schemas.ControlPolicy, steps: int,
    initial_state: SimState | None = None,
) -> PolicyResult:
    """A tight scalar loop: no Pydantic and no event IDs per step."""
    state = build_scenario(cfg, scenario_id, seed=seed, control_policy=policy) if initial_state is None else initial_state.clone()
    state.environment.control_policy = policy
    reset_accounts(state, cfg)
    initial_state_digest = _policy_neutral_digest(state, cfg)
    input_hash = hashlib.sha256()
    denied_request_steps = 0
    for _ in range(steps):
        result = step(state, cfg)
        state = result.state
        inputs = result.inputs
        input_hash.update(
            struct.pack(
                "<4d",
                inputs.tse_inflow_m3_s,
                inputs.et0_step_mm,
                state.power.solar_power_w,
                state.power.hydro_power_w,
            )
        )
        denied_request_steps += sum(
            1 for decision in result.decisions if not decision.accepted
        )

    metrics = state.metrics
    delivered_m3 = metrics.irrigation_delivered_m3
    pump_kwh = metrics.pump_energy_j / 3.6e6
    total_area_m2 = sum(zone.area_m2 for zone in cfg.zones)
    required_j = metrics.required_electrical_energy_j
    return PolicyResult(
        policy=policy,
        input_digest=input_hash.hexdigest(),
        initial_state_digest=initial_state_digest,
        tse_inflow_m3=metrics.tse_inflow_m3,
        irrigation_delivered_m3=delivered_m3,
        requested_undelivered_m3=metrics.requested_undelivered_m3,
        potential_et_m3=metrics.potential_et_m3,
        actual_et_m3=metrics.actual_et_m3,
        et_deficit_m3=metrics.et_deficit_m3,
        et_deficit_mm=metrics.et_deficit_m3 / total_area_m2 * 1000.0,
        deep_percolation_m3=metrics.deep_percolation_m3,
        overflow_m3=metrics.overflow_m3,
        flush_water_m3=metrics.flush_water_m3,
        flush_count=metrics.flush_count,
        battery_losses_kwh=metrics.battery_losses_j / 3.6e6,
        pump_energy_kwh=pump_kwh,
        pump_kwh_per_delivered_m3=pump_kwh / delivered_m3 if delivered_m3 > 0 else 0.0,
        required_electrical_kwh=required_j / 3.6e6,
        unserved_kwh=metrics.unserved_energy_j / 3.6e6,
        electrical_autonomy_0_1=1.0 - metrics.unserved_energy_j / required_j if required_j > 0 else 1.0,
        final_battery_soc_0_1=state.battery_energy_j / cfg.energy.battery_capacity_j,
        final_mean_moisture_m3_m3=sum(zone.theta_m3_m3 for zone in state.zones) / len(state.zones),
        denied_request_steps=denied_request_steps,
        zones=[zone_service(zone, cfg) for zone in state.zones],
        diagnostics=site_diagnostics(state, cfg),
    )


def _policy_neutral_digest(state: SimState, cfg: SiteConfig) -> str:
    """Digest of the physical starting point with the policy itself left out."""
    physical = to_snapshot(state, cfg, run_generation=0, latest_event_id=0).model_dump(
        mode="json", exclude={"run_generation", "latest_event_id"}
    )
    del physical["environment"]["control_policy"]
    # Preserve the historical physical digest across additive reporting fields.
    physical.pop("diagnostics", None)
    physical["schema_version"] = "1.0"
    for zone in physical["zones"]:
        zone.pop("service", None)
    return hashlib.sha256(json.dumps(physical, sort_keys=True).encode("utf-8")).hexdigest()
