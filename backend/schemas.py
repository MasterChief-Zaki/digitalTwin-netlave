"""The JSON contract between the simulation and the browser.

snake_case everywhere, units in every dimensional key. `src/types/simulation.ts`
mirrors these models and changes with them. Physical and business constraints
are enforced by the engine and the safety resolver, not by validators here.
"""

from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field

from config import FeedMode, ZoneId

SCHEMA_VERSION = "1.1"

ControlMode = Literal["AUTO", "MANUAL_OPEN", "MANUAL_CLOSED"]
ControlPolicy = Literal["SMART_HYSTERESIS", "FIXED_TIMER", "SMART_RESOURCE_AWARE"]
RequestedAction = Literal["START", "KEEP_OPEN", "STOP", "KEEP_CLOSED"]
WaterQuality = Literal["OK", "HOLD", "UNKNOWN"]
ScenarioId = Literal["baseline", "clogged_filter", "low_solar", "tse_interrupt"]
EventCategory = Literal["DENIAL", "FILTER", "WATER", "ENERGY", "SCENARIO", "COMMAND"]

ReasonCode = Literal[
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
    "MOISTURE_TARGET_REACHED",
    "SCHEDULE_WINDOW_OPEN",
    "SCHEDULE_WINDOW_CLOSED",
    "OPERATOR_COMMAND",
    "SCHEDULER_WATER_HOLD",
    "SCHEDULER_ENERGY_HOLD",
    "SCHEDULER_QUEUE",
    "SCHEDULER_REST",
]


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Reservoir(ContractModel):
    volume_m3: float
    capacity_m3: float
    dead_volume_m3: float
    surface_elevation_m: float
    inflow_m3_s: float
    overflow_flow_m3_s: float


class ZoneService(ContractModel):
    zone_id: ZoneId
    irrigation_requested_m3: float
    irrigation_delivered_m3: float
    potential_et_m3: float
    actual_et_m3: float
    et_deficit_m3: float
    et_deficit_mm: float
    et_service_ratio_0_1: float | None
    below_trigger_min: float
    denied_by_reason_min: dict[str, float]
    deferred_by_reason_min: dict[str, float]
    initial_root_zone_storage_m3: float
    final_root_zone_storage_m3: float
    soil_stock_adjusted_delivery_m3: float
    minimum_moisture_m3_m3: float
    minimum_head_margin_m: float | None
    session_count: int
    pause_count: int
    resume_count: int


class SiteDiagnostics(ContractModel):
    electrical_autonomy_0_1: float | None
    overflow_fraction_0_1: float | None
    minimum_reservoir_volume_m3: float
    minimum_battery_soc_0_1: float
    battery_equivalent_full_cycles: float
    initial_reservoir_volume_m3: float
    final_reservoir_volume_m3: float
    initial_battery_energy_j: float
    final_battery_energy_j: float
    soil_stock_adjusted_delivery_m3: float


class Zone(ContractModel):
    id: ZoneId
    feed_mode: FeedMode
    control_mode: ControlMode
    area_m2: float
    elevation_m: float
    soil_moisture_m3_m3: float
    moisture_trigger_m3_m3: float
    moisture_target_m3_m3: float
    irrigation_latched: bool
    valve_open: bool
    requested_flow_m3_s: float
    delivered_flow_m3_s: float
    water_stress_0_1: float
    head_available_m: float
    head_required_m: float
    service: ZoneService


class Pump(ContractModel):
    zone_id: ZoneId
    total_dynamic_head_m: float
    required_power_w: float
    power_limit_w: float
    running: bool


class Energy(ContractModel):
    hydro_power_w: float
    solar_power_w: float
    pump_power_w: float
    aux_power_w: float
    flush_power_w: float
    battery_energy_j: float
    battery_capacity_j: float
    battery_soc_0_1: float
    charge_power_w: float
    discharge_power_w: float
    curtail_power_w: float
    unserved_power_w: float


class Filtration(ContractModel):
    clog_index_0_1: float
    pressure_drop_pa: float
    head_loss_m: float
    flushing: bool
    flush_steps_remaining: int
    flush_required: bool


class Environment(ContractModel):
    control_policy: ControlPolicy
    water_quality: WaterQuality
    cloud_factor: float
    solids_loading_multiplier: float
    inflow_available: bool
    et0_mm_day: float


class Decision(ContractModel):
    zone_id: ZoneId
    requested_action: RequestedAction
    accepted: bool
    reason_code: ReasonCode
    explanation: str


class Metrics(ContractModel):
    tse_inflow_m3: float
    irrigation_delivered_m3: float
    requested_undelivered_m3: float
    overflow_m3: float
    other_diversion_m3: float
    flush_water_m3: float
    application_loss_m3: float
    deep_percolation_m3: float
    potential_et_m3: float
    actual_et_m3: float
    et_deficit_m3: float
    hydro_energy_j: float
    solar_energy_j: float
    pump_energy_j: float
    aux_energy_j: float
    flush_energy_j: float
    battery_charge_energy_j: float
    battery_discharge_energy_j: float
    battery_losses_j: float
    curtailed_energy_j: float
    unserved_energy_j: float
    required_electrical_energy_j: float
    flush_count: int


class SimulationSnapshot(ContractModel):
    schema_version: Literal["1.1"]
    data_mode: Literal["SIMULATED"]
    step: int = Field(ge=0)
    sim_time_s: int = Field(ge=0)
    dt_s: int
    start_hour: int
    scenario_id: ScenarioId
    seed: int
    run_generation: int
    reservoir: Reservoir
    zones: list[Zone] = Field(min_length=3, max_length=3)
    pump: Pump
    energy: Energy
    filtration: Filtration
    environment: Environment
    decisions: list[Decision] = Field(min_length=3, max_length=3)
    metrics: Metrics
    diagnostics: SiteDiagnostics
    latest_event_id: int = Field(ge=0)


class Event(ContractModel):
    id: int
    step: int
    category: EventCategory
    zone_id: ZoneId | None
    reason_code: ReasonCode
    message: str


class AdvanceRequest(ContractModel):
    run_generation: int
    expected_step: int = Field(ge=0)
    steps: int = Field(ge=1, le=60)
    request_id: str = Field(min_length=1, max_length=64)


class AdvanceResponse(ContractModel):
    snapshot: SimulationSnapshot
    events: list[Event]
    events_truncated: bool
    latest_event_id: int


class SetZoneModeCommand(ContractModel):
    type: Literal["set_zone_mode"]
    zone_id: ZoneId
    mode: ControlMode


class SetWaterQualityCommand(ContractModel):
    type: Literal["set_water_quality"]
    status: WaterQuality


class SetCloudFactorCommand(ContractModel):
    type: Literal["set_cloud_factor"]
    cloud_factor: float = Field(ge=0, le=1)


class SetSolidsMultiplierCommand(ContractModel):
    type: Literal["set_solids_multiplier"]
    multiplier: float = Field(ge=0, le=20)


class SetInflowAvailableCommand(ContractModel):
    type: Literal["set_inflow_available"]
    available: bool


Command = Annotated[
    Union[
        SetZoneModeCommand,
        SetWaterQualityCommand,
        SetCloudFactorCommand,
        SetSolidsMultiplierCommand,
        SetInflowAvailableCommand,
    ],
    Field(discriminator="type"),
]


class CommandRequest(ContractModel):
    run_generation: int
    expected_step: int = Field(ge=0)
    command: Command


class ResetRequest(ContractModel):
    scenario_id: ScenarioId = "baseline"
    seed: int = Field(default=7, ge=0)
    control_policy: ControlPolicy = "SMART_HYSTERESIS"


class EventsPage(ContractModel):
    events: list[Event]
    latest_event_id: int
    history_truncated: bool


class ConflictDetail(ContractModel):
    error_code: Literal["STEP_CONFLICT", "IDEMPOTENCY_CONFLICT"]
    message: str
    current_step: int
    run_generation: int


class AssumptionRow(ContractModel):
    name: str
    value: str
    unit: str
    status: Literal["assumed", "derived", "measured"]
    source: str


class ScenarioInfo(ContractModel):
    id: ScenarioId
    title: str
    description: str
    demo_initial_conditions: str


class ScenariosResponse(ContractModel):
    scenarios: list[ScenarioInfo]
    assumptions: list[AssumptionRow]


class CompareRequest(ContractModel):
    scenario_id: ScenarioId = "baseline"
    seed: int = Field(default=7, ge=0)
    horizon_days: int = Field(default=14, ge=1, le=30)
    evaluation_mode: Literal["STARTUP_FAULT", "MATCHED_OPERATION"] = "STARTUP_FAULT"
    warmup_days: Literal[5, 10, 20] = 10
    include_resource_aware: bool = False


class PolicyReport(ContractModel):
    policy: ControlPolicy
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
    zones: list[ZoneService]
    diagnostics: SiteDiagnostics


class CompareResponse(ContractModel):
    data_mode: Literal["SIMULATED"]
    scenario_id: ScenarioId
    seed: int
    horizon_days: int
    steps: int
    fixed_timer: PolicyReport
    smart_hysteresis: PolicyReport
    water_savings_fraction: float
    elapsed_s: float
    resource_aware: PolicyReport | None
    evaluation_mode: Literal["STARTUP_FAULT", "MATCHED_OPERATION"]
    warmup_days: int
    measurement_start_step: int
    measurement_end_step: int
