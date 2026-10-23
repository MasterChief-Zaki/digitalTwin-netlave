"""The typed in-memory run state and its projection onto the JSON contract."""

import hashlib
import json
from dataclasses import dataclass, field

import schemas
from config import STEPS_PER_DAY, SiteConfig, ZoneId
from models.filtration import filter_head_loss_m, filter_pressure_drop_pa
from models.water_soil import surface_elevation_m, water_stress
from twin.inputs import daily_et0_mm


@dataclass
class ZoneAccounts:
    irrigation_requested_m3: float = 0.0
    irrigation_delivered_m3: float = 0.0
    potential_et_m3: float = 0.0
    actual_et_m3: float = 0.0
    below_trigger_min: float = 0.0
    denied_by_reason_min: dict[str, float] = field(default_factory=dict)
    deferred_by_reason_min: dict[str, float] = field(default_factory=dict)
    initial_root_zone_storage_m3: float = 0.0
    minimum_moisture_m3_m3: float = 0.0
    minimum_head_margin_m: float | None = None
    session_count: int = 0
    pause_count: int = 0
    resume_count: int = 0


@dataclass
class ZoneState:
    zone_id: ZoneId
    theta_m3_m3: float
    control_mode: schemas.ControlMode = "AUTO"
    irrigation_latched: bool = False
    valve_open: bool = False
    requested_flow_m3_s: float = 0.0
    delivered_flow_m3_s: float = 0.0
    head_available_m: float = 0.0
    head_required_m: float = 0.0
    # The denial reason of the zone's current denial episode, for event de-duplication.
    active_denial: schemas.ReasonCode | None = None
    accounts: ZoneAccounts = field(default_factory=ZoneAccounts)


@dataclass
class EnvironmentState:
    control_policy: schemas.ControlPolicy = "SMART_HYSTERESIS"
    water_quality: schemas.WaterQuality = "OK"
    cloud_factor: float = 1.0
    solids_loading_multiplier: float = 1.0
    inflow_available: bool = True
    # Scenario-defined [start, end) step interval with no TSE arriving.
    inflow_outage_steps: tuple[int, int] | None = None


@dataclass
class PowerFlows:
    hydro_power_w: float = 0.0
    solar_power_w: float = 0.0
    pump_power_w: float = 0.0
    aux_power_w: float = 0.0
    flush_power_w: float = 0.0
    charge_power_w: float = 0.0
    discharge_power_w: float = 0.0
    curtail_power_w: float = 0.0
    unserved_power_w: float = 0.0


@dataclass
class FilterState:
    clog_index: float
    flushing: bool = False
    flush_steps_remaining: int = 0
    flush_required: bool = False


@dataclass
class PumpState:
    total_dynamic_head_m: float = 0.0
    required_power_w: float = 0.0
    running: bool = False


@dataclass
class Metrics:
    tse_inflow_m3: float = 0.0
    irrigation_delivered_m3: float = 0.0
    requested_undelivered_m3: float = 0.0
    overflow_m3: float = 0.0
    other_diversion_m3: float = 0.0
    flush_water_m3: float = 0.0
    application_loss_m3: float = 0.0
    deep_percolation_m3: float = 0.0
    potential_et_m3: float = 0.0
    actual_et_m3: float = 0.0
    et_deficit_m3: float = 0.0
    hydro_energy_j: float = 0.0
    solar_energy_j: float = 0.0
    pump_energy_j: float = 0.0
    aux_energy_j: float = 0.0
    flush_energy_j: float = 0.0
    battery_charge_energy_j: float = 0.0
    battery_discharge_energy_j: float = 0.0
    battery_losses_j: float = 0.0
    curtailed_energy_j: float = 0.0
    unserved_energy_j: float = 0.0
    required_electrical_energy_j: float = 0.0
    flush_count: int = 0


@dataclass(frozen=True)
class DecisionRecord:
    zone_id: ZoneId
    requested_action: schemas.RequestedAction
    accepted: bool
    reason_code: schemas.ReasonCode
    explanation: str


@dataclass
class SimState:
    step: int
    seed: int
    scenario_id: schemas.ScenarioId
    reservoir_volume_m3: float
    zones: list[ZoneState]
    battery_energy_j: float
    filter: FilterState
    environment: EnvironmentState
    et0_mm_day: float
    decisions: list[DecisionRecord]
    inflow_m3_s: float = 0.0
    overflow_flow_m3_s: float = 0.0
    power: PowerFlows = field(default_factory=PowerFlows)
    pump: PumpState = field(default_factory=PumpState)
    metrics: Metrics = field(default_factory=Metrics)
    overflow_active: bool = False
    aux_outage_active: bool = False
    initial_reservoir_volume_m3: float = 0.0
    initial_battery_energy_j: float = 0.0
    minimum_reservoir_volume_m3: float = 0.0
    minimum_battery_soc_0_1: float = 0.0

    def clone(self) -> "SimState":
        """An owned copy for the next step; field copies are far cheaper than deepcopy or replace()."""
        copied = _shallow_copy(self)
        copied.zones = [_shallow_copy(zone) for zone in self.zones]
        for zone in copied.zones:
            zone.accounts = _shallow_copy(zone.accounts)
            zone.accounts.denied_by_reason_min = dict(zone.accounts.denied_by_reason_min)
            zone.accounts.deferred_by_reason_min = dict(zone.accounts.deferred_by_reason_min)
        copied.filter = _shallow_copy(self.filter)
        copied.environment = _shallow_copy(self.environment)
        copied.power = _shallow_copy(self.power)
        copied.pump = _shallow_copy(self.pump)
        copied.metrics = _shallow_copy(self.metrics)
        copied.decisions = list(self.decisions)
        return copied


def _shallow_copy[T](instance: T) -> T:
    """Copy a plain (non-frozen, non-slotted) dataclass by its field dictionary, skipping __init__."""
    copied = object.__new__(type(instance))
    copied.__dict__.update(instance.__dict__)
    return copied


def new_run_state(
    cfg: SiteConfig,
    seed: int,
    scenario_id: schemas.ScenarioId = "baseline",
    control_policy: schemas.ControlPolicy = "SMART_HYSTERESIS",
) -> SimState:
    """Documented site defaults at step 0, with near-threshold moisture for a quick demo."""
    state = SimState(
        step=0,
        seed=seed,
        scenario_id=scenario_id,
        reservoir_volume_m3=cfg.reservoir.initial_volume_m3,
        zones=[ZoneState(zone_id=zone.zone_id, theta_m3_m3=0.165) for zone in cfg.zones],
        battery_energy_j=cfg.energy.battery_initial_soc * cfg.energy.battery_capacity_j,
        filter=FilterState(clog_index=cfg.filtration.initial_clog_index),
        environment=EnvironmentState(control_policy=control_policy),
        et0_mm_day=daily_et0_mm(seed, (cfg.start_hour * 60) // STEPS_PER_DAY, cfg),
        decisions=[
            DecisionRecord(zone.zone_id, "KEEP_CLOSED", True, "KEEP_CLOSED", "No step has been simulated yet.")
            for zone in cfg.zones
        ],
    )
    reset_accounts(state, cfg)
    return state


def reset_accounts(state: SimState, cfg: SiteConfig) -> None:
    """Start a measured window without changing physical state or the clock."""
    from models.water_soil import soil_storage_m3

    state.metrics = Metrics()
    state.initial_reservoir_volume_m3 = state.reservoir_volume_m3
    state.initial_battery_energy_j = state.battery_energy_j
    state.minimum_reservoir_volume_m3 = state.reservoir_volume_m3
    state.minimum_battery_soc_0_1 = state.battery_energy_j / cfg.energy.battery_capacity_j
    for zone, zone_cfg in zip(state.zones, cfg.zones, strict=True):
        zone.accounts = ZoneAccounts(
            initial_root_zone_storage_m3=soil_storage_m3(zone.theta_m3_m3, zone_cfg, cfg.soil),
            minimum_moisture_m3_m3=zone.theta_m3_m3,
        )


def zone_service(zone: ZoneState, cfg: SiteConfig) -> schemas.ZoneService:
    from models.water_soil import soil_storage_m3
    from scenarios.evaluation import stock_adjusted_delivery_m3

    zone_cfg = next(item for item in cfg.zones if item.zone_id == zone.zone_id)
    accounts = zone.accounts
    final_storage = soil_storage_m3(zone.theta_m3_m3, zone_cfg, cfg.soil)
    deficit = accounts.potential_et_m3 - accounts.actual_et_m3
    return schemas.ZoneService(
        zone_id=zone.zone_id,
        irrigation_requested_m3=accounts.irrigation_requested_m3,
        irrigation_delivered_m3=accounts.irrigation_delivered_m3,
        potential_et_m3=accounts.potential_et_m3,
        actual_et_m3=accounts.actual_et_m3,
        et_deficit_m3=deficit,
        et_deficit_mm=deficit / zone_cfg.area_m2 * 1000.0,
        et_service_ratio_0_1=accounts.actual_et_m3 / accounts.potential_et_m3 if accounts.potential_et_m3 > 0 else None,
        below_trigger_min=accounts.below_trigger_min,
        denied_by_reason_min=accounts.denied_by_reason_min,
        deferred_by_reason_min=accounts.deferred_by_reason_min,
        initial_root_zone_storage_m3=accounts.initial_root_zone_storage_m3,
        final_root_zone_storage_m3=final_storage,
        soil_stock_adjusted_delivery_m3=stock_adjusted_delivery_m3(
            accounts.irrigation_delivered_m3, final_storage - accounts.initial_root_zone_storage_m3,
            cfg.soil.application_efficiency,
        ),
        minimum_moisture_m3_m3=accounts.minimum_moisture_m3_m3,
        minimum_head_margin_m=accounts.minimum_head_margin_m,
        session_count=accounts.session_count, pause_count=accounts.pause_count, resume_count=accounts.resume_count,
    )


def site_diagnostics(state: SimState, cfg: SiteConfig) -> schemas.SiteDiagnostics:
    from scenarios.evaluation import battery_equivalent_full_cycles

    metrics = state.metrics
    return schemas.SiteDiagnostics(
        electrical_autonomy_0_1=1.0 - metrics.unserved_energy_j / metrics.required_electrical_energy_j
        if metrics.required_electrical_energy_j > 0 else None,
        overflow_fraction_0_1=metrics.overflow_m3 / metrics.tse_inflow_m3 if metrics.tse_inflow_m3 > 0 else None,
        minimum_reservoir_volume_m3=state.minimum_reservoir_volume_m3,
        minimum_battery_soc_0_1=state.minimum_battery_soc_0_1,
        battery_equivalent_full_cycles=battery_equivalent_full_cycles(
            metrics.battery_discharge_energy_j, cfg.energy.battery_capacity_j, cfg.energy.battery_discharge_efficiency,
        ),
        initial_reservoir_volume_m3=state.initial_reservoir_volume_m3,
        final_reservoir_volume_m3=state.reservoir_volume_m3,
        initial_battery_energy_j=state.initial_battery_energy_j,
        final_battery_energy_j=state.battery_energy_j,
        soil_stock_adjusted_delivery_m3=sum(zone_service(zone, cfg).soil_stock_adjusted_delivery_m3 for zone in state.zones),
    )


def to_snapshot(
    state: SimState, cfg: SiteConfig, run_generation: int, latest_event_id: int
) -> schemas.SimulationSnapshot:
    pressure_drop_pa = filter_pressure_drop_pa(state.filter.clog_index, cfg.filtration)
    return schemas.SimulationSnapshot(
        schema_version=schemas.SCHEMA_VERSION,
        data_mode="SIMULATED",
        step=state.step,
        sim_time_s=state.step * 60,
        dt_s=60,
        start_hour=cfg.start_hour,
        scenario_id=state.scenario_id,
        seed=state.seed,
        run_generation=run_generation,
        reservoir=schemas.Reservoir(
            volume_m3=state.reservoir_volume_m3,
            capacity_m3=cfg.reservoir.capacity_m3,
            dead_volume_m3=cfg.reservoir.dead_volume_m3,
            surface_elevation_m=surface_elevation_m(state.reservoir_volume_m3, cfg.reservoir),
            inflow_m3_s=state.inflow_m3_s,
            overflow_flow_m3_s=state.overflow_flow_m3_s,
        ),
        zones=[
            schemas.Zone(
                id=zone.zone_id,
                feed_mode=zone_config.feed_mode,
                control_mode=zone.control_mode,
                area_m2=zone_config.area_m2,
                elevation_m=zone_config.elevation_m,
                soil_moisture_m3_m3=zone.theta_m3_m3,
                moisture_trigger_m3_m3=cfg.soil.theta_on_m3_m3,
                moisture_target_m3_m3=cfg.soil.theta_off_m3_m3,
                irrigation_latched=zone.irrigation_latched,
                valve_open=zone.valve_open,
                requested_flow_m3_s=zone.requested_flow_m3_s,
                delivered_flow_m3_s=zone.delivered_flow_m3_s,
                water_stress_0_1=water_stress(zone.theta_m3_m3, cfg.soil),
                head_available_m=zone.head_available_m,
                head_required_m=zone.head_required_m,
                service=zone_service(zone, cfg),
            )
            for zone, zone_config in zip(state.zones, cfg.zones, strict=True)
        ],
        pump=schemas.Pump(
            zone_id="C",
            total_dynamic_head_m=state.pump.total_dynamic_head_m,
            required_power_w=state.pump.required_power_w,
            power_limit_w=cfg.hydraulics.pump_power_limit_w,
            running=state.pump.running,
        ),
        energy=schemas.Energy(
            hydro_power_w=state.power.hydro_power_w,
            solar_power_w=state.power.solar_power_w,
            pump_power_w=state.power.pump_power_w,
            aux_power_w=state.power.aux_power_w,
            flush_power_w=state.power.flush_power_w,
            battery_energy_j=state.battery_energy_j,
            battery_capacity_j=cfg.energy.battery_capacity_j,
            battery_soc_0_1=state.battery_energy_j / cfg.energy.battery_capacity_j,
            charge_power_w=state.power.charge_power_w,
            discharge_power_w=state.power.discharge_power_w,
            curtail_power_w=state.power.curtail_power_w,
            unserved_power_w=state.power.unserved_power_w,
        ),
        filtration=schemas.Filtration(
            clog_index_0_1=state.filter.clog_index,
            pressure_drop_pa=pressure_drop_pa,
            head_loss_m=filter_head_loss_m(state.filter.clog_index, cfg.filtration),
            flushing=state.filter.flushing,
            flush_steps_remaining=state.filter.flush_steps_remaining,
            flush_required=state.filter.flush_required,
        ),
        environment=schemas.Environment(
            control_policy=state.environment.control_policy,
            water_quality=state.environment.water_quality,
            cloud_factor=state.environment.cloud_factor,
            solids_loading_multiplier=state.environment.solids_loading_multiplier,
            inflow_available=state.environment.inflow_available,
            et0_mm_day=state.et0_mm_day,
        ),
        decisions=[
            schemas.Decision(
                zone_id=decision.zone_id,
                requested_action=decision.requested_action,
                accepted=decision.accepted,
                reason_code=decision.reason_code,
                explanation=decision.explanation,
            )
            for decision in state.decisions
        ],
        metrics=schemas.Metrics(**vars(state.metrics)),
        diagnostics=site_diagnostics(state, cfg),
        latest_event_id=latest_event_id,
    )


TRANSPORT_FIELDS = {"run_generation", "latest_event_id"}


def physical_digest(snapshot: schemas.SimulationSnapshot) -> str:
    """SHA-256 of the physical snapshot, excluding API transport metadata."""
    physical = snapshot.model_dump(mode="json", exclude=TRANSPORT_FIELDS)
    return hashlib.sha256(json.dumps(physical, sort_keys=True).encode("utf-8")).hexdigest()
