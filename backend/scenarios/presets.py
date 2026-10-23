"""Scenario presets: controlled variations and fast demo initial conditions.

A preset only sets the starting state and the environment. The denials,
flushes, recoveries and counters that follow are produced by the engine.
Near-threshold starting values are explicitly demo initial conditions, not
plausible steady-state measurements.
"""

from dataclasses import dataclass

import schemas
from config import SiteConfig
from twin.state import SimState, new_run_state, reset_accounts


@dataclass(frozen=True)
class Scenario:
    id: schemas.ScenarioId
    title: str
    description: str
    demo_initial_conditions: str


SCENARIOS: tuple[Scenario, ...] = (
    Scenario(
        "baseline",
        "Baseline",
        "Documented site defaults: 60 m3/h of TSE, clear sky, clean filter, synthetic quality OK.",
        "All three zones start at 0.165 m3/m3, just below the 0.166 irrigation trigger.",
    ),
    Scenario(
        "clogged_filter",
        "Clogged filter",
        "Eight times the solids loading. Filter head loss takes zone B's gravity margin until the filter flushes "
        "(1.5 m3 and 0.10 kWh).",
        "Filter clog index 0.56 (flush at 0.60); zone B at 0.150 m3/m3 demanding water, zone A at 0.165.",
    ),
    Scenario(
        "low_solar",
        "Low solar (sandstorm)",
        "Cloud factor 0.25 cuts solar to a quarter. The uphill zone C pump competes with the battery reserve.",
        "Battery at 24% (pump reserve 20%); zone C at 0.150 m3/m3 requesting the pump; A and B wet.",
    ),
    Scenario(
        "tse_interrupt",
        "TSE interruption",
        "No effluent arrives from 06:30 to 12:30: the turbine stops and the reservoir draws down.",
        "Baseline initial state; inflow is zero for steps 30 to 389.",
    ),
)


def build_scenario(
    cfg: SiteConfig,
    scenario_id: schemas.ScenarioId,
    seed: int,
    control_policy: schemas.ControlPolicy = "SMART_HYSTERESIS",
) -> SimState:
    state = new_run_state(cfg, seed=seed, scenario_id=scenario_id, control_policy=control_policy)
    zone_a, zone_b, zone_c = state.zones
    if scenario_id == "clogged_filter":
        state.filter.clog_index = 0.56
        state.environment.solids_loading_multiplier = 8.0
        zone_b.theta_m3_m3 = 0.150
        zone_c.theta_m3_m3 = 0.21
    elif scenario_id == "low_solar":
        state.environment.cloud_factor = 0.25
        state.battery_energy_j = 0.24 * cfg.energy.battery_capacity_j
        zone_a.theta_m3_m3 = 0.21
        zone_b.theta_m3_m3 = 0.21
        zone_c.theta_m3_m3 = 0.150
    elif scenario_id == "tse_interrupt":
        state.environment.inflow_outage_steps = (30, 390)
    reset_accounts(state, cfg)
    return state
