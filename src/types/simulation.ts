// Mirror of `backend/schemas.py`. The two files change together.
// snake_case like the JSON, with units in every dimensional key.

export type ZoneId = "A" | "B" | "C";
export type FeedMode = "GRAVITY" | "PUMPED";
export type ControlMode = "AUTO" | "MANUAL_OPEN" | "MANUAL_CLOSED";
export type ControlPolicy =
  "SMART_HYSTERESIS" | "FIXED_TIMER" | "SMART_RESOURCE_AWARE";
export type RequestedAction = "START" | "KEEP_OPEN" | "STOP" | "KEEP_CLOSED";
export type WaterQuality = "OK" | "HOLD" | "UNKNOWN";
export type ScenarioId =
  "baseline" | "clogged_filter" | "low_solar" | "tse_interrupt";
export type EventCategory =
  "DENIAL" | "FILTER" | "WATER" | "ENERGY" | "SCENARIO" | "COMMAND";

export type ReasonCode =
  | "SOIL_BELOW_THRESHOLD"
  | "KEEP_OPEN"
  | "KEEP_CLOSED"
  | "MANUAL_OVERRIDE_OK"
  | "MANUAL_STOP_OK"
  | "WATER_QUALITY_HOLD"
  | "FLUSH_IN_PROGRESS"
  | "FILTER_FLUSH_REQUIRED"
  | "RESERVOIR_LOW"
  | "INSUFFICIENT_HEAD"
  | "CONCURRENT_FLOW_LIMIT"
  | "POWER_DEFICIT"
  | "BATTERY_BELOW_RESERVE"
  | "AUX_POWER_OUTAGE"
  | "FILTER_FLUSH_STARTED"
  | "FILTER_FLUSH_COMPLETE"
  | "OVERFLOW_OCCURRING"
  | "SCENARIO_LOADED"
  | "MOISTURE_TARGET_REACHED"
  | "SCHEDULE_WINDOW_OPEN"
  | "SCHEDULE_WINDOW_CLOSED"
  | "OPERATOR_COMMAND"
  | "SCHEDULER_WATER_HOLD"
  | "SCHEDULER_ENERGY_HOLD"
  | "SCHEDULER_QUEUE"
  | "SCHEDULER_REST";

export interface Reservoir {
  volume_m3: number;
  capacity_m3: number;
  dead_volume_m3: number;
  surface_elevation_m: number;
  floor_elevation_m: number;
  depth_at_capacity_m: number;
  inflow_m3_s: number;
  overflow_flow_m3_s: number;
}

export interface ZoneService {
  zone_id: ZoneId;
  irrigation_requested_m3: number;
  irrigation_delivered_m3: number;
  potential_et_m3: number;
  actual_et_m3: number;
  et_deficit_m3: number;
  et_deficit_mm: number;
  et_service_ratio_0_1: number | null;
  below_trigger_min: number;
  denied_by_reason_min: Record<string, number>;
  deferred_by_reason_min: Record<string, number>;
  initial_root_zone_storage_m3: number;
  final_root_zone_storage_m3: number;
  soil_stock_adjusted_delivery_m3: number;
  minimum_moisture_m3_m3: number;
  minimum_head_margin_m: number | null;
  session_count: number;
  pause_count: number;
  resume_count: number;
}

export interface SiteDiagnostics {
  electrical_autonomy_0_1: number | null;
  overflow_fraction_0_1: number | null;
  minimum_reservoir_volume_m3: number;
  minimum_battery_soc_0_1: number;
  battery_equivalent_full_cycles: number;
  initial_reservoir_volume_m3: number;
  final_reservoir_volume_m3: number;
  initial_battery_energy_j: number;
  final_battery_energy_j: number;
  soil_stock_adjusted_delivery_m3: number;
}

export interface Zone {
  id: ZoneId;
  feed_mode: FeedMode;
  control_mode: ControlMode;
  area_m2: number;
  elevation_m: number;
  soil_moisture_m3_m3: number;
  moisture_trigger_m3_m3: number;
  moisture_target_m3_m3: number;
  irrigation_latched: boolean;
  valve_open: boolean;
  requested_flow_m3_s: number;
  delivered_flow_m3_s: number;
  water_stress_0_1: number;
  head_available_m: number;
  head_required_m: number;
  service: ZoneService;
}

export interface Pump {
  zone_id: ZoneId;
  total_dynamic_head_m: number;
  required_power_w: number;
  power_limit_w: number;
  running: boolean;
}

export interface Energy {
  hydro_power_w: number;
  solar_power_w: number;
  pump_power_w: number;
  aux_power_w: number;
  flush_power_w: number;
  battery_energy_j: number;
  battery_capacity_j: number;
  battery_soc_0_1: number;
  charge_power_w: number;
  discharge_power_w: number;
  curtail_power_w: number;
  unserved_power_w: number;
}

export interface Filtration {
  clog_index_0_1: number;
  pressure_drop_pa: number;
  head_loss_m: number;
  flushing: boolean;
  flush_steps_remaining: number;
  flush_required: boolean;
}

export interface Environment {
  control_policy: ControlPolicy;
  water_quality: WaterQuality;
  cloud_factor: number;
  solids_loading_multiplier: number;
  inflow_available: boolean;
  et0_mm_day: number;
}

export interface Decision {
  zone_id: ZoneId;
  requested_action: RequestedAction;
  accepted: boolean;
  reason_code: ReasonCode;
  explanation: string;
}

export interface Metrics {
  tse_inflow_m3: number;
  irrigation_delivered_m3: number;
  requested_undelivered_m3: number;
  overflow_m3: number;
  other_diversion_m3: number;
  flush_water_m3: number;
  application_loss_m3: number;
  deep_percolation_m3: number;
  potential_et_m3: number;
  actual_et_m3: number;
  et_deficit_m3: number;
  hydro_energy_j: number;
  solar_energy_j: number;
  pump_energy_j: number;
  aux_energy_j: number;
  flush_energy_j: number;
  battery_charge_energy_j: number;
  battery_discharge_energy_j: number;
  battery_losses_j: number;
  curtailed_energy_j: number;
  unserved_energy_j: number;
  required_electrical_energy_j: number;
  flush_count: number;
}

export interface SimulationSnapshot {
  schema_version: "1.2";
  data_mode: "SIMULATED";
  step: number;
  sim_time_s: number;
  dt_s: number;
  start_hour: number;
  scenario_id: ScenarioId;
  seed: number;
  run_generation: number;
  reservoir: Reservoir;
  zones: Zone[];
  pump: Pump;
  energy: Energy;
  filtration: Filtration;
  environment: Environment;
  decisions: Decision[];
  metrics: Metrics;
  diagnostics: SiteDiagnostics;
  latest_event_id: number;
}

export interface SimulationEvent {
  id: number;
  step: number;
  category: EventCategory;
  zone_id: ZoneId | null;
  reason_code: ReasonCode;
  message: string;
}

export interface AdvanceRequest {
  run_generation: number;
  expected_step: number;
  steps: number;
  request_id: string;
}

export interface AdvanceResponse {
  snapshot: SimulationSnapshot;
  events: SimulationEvent[];
  events_truncated: boolean;
  latest_event_id: number;
}

export type Command =
  | { type: "set_zone_mode"; zone_id: ZoneId; mode: ControlMode }
  | { type: "set_water_quality"; status: WaterQuality }
  | { type: "set_cloud_factor"; cloud_factor: number }
  | { type: "set_solids_multiplier"; multiplier: number }
  | { type: "set_inflow_available"; available: boolean };

export interface CommandRequest {
  run_generation: number;
  expected_step: number;
  command: Command;
}

export interface ResetRequest {
  scenario_id: ScenarioId;
  seed: number;
  control_policy: ControlPolicy;
}

export interface EventsPage {
  events: SimulationEvent[];
  latest_event_id: number;
  history_truncated: boolean;
}

export interface ConflictDetail {
  error_code: "STEP_CONFLICT" | "IDEMPOTENCY_CONFLICT";
  message: string;
  current_step: number;
  run_generation: number;
}

export interface AssumptionRow {
  name: string;
  value: string;
  unit: string;
  status: "assumed" | "derived" | "measured";
  source: string;
}

export interface ScenarioInfo {
  id: ScenarioId;
  title: string;
  description: string;
  demo_initial_conditions: string;
}

export interface ScenariosResponse {
  scenarios: ScenarioInfo[];
  assumptions: AssumptionRow[];
}

export interface CompareRequest {
  scenario_id: ScenarioId;
  seed: number;
  horizon_days: number;
  evaluation_mode: "STARTUP_FAULT" | "MATCHED_OPERATION";
  warmup_days: 5 | 10 | 20;
  include_resource_aware: boolean;
}

export interface PolicyReport {
  policy: ControlPolicy;
  input_digest: string;
  initial_state_digest: string;
  tse_inflow_m3: number;
  irrigation_delivered_m3: number;
  requested_undelivered_m3: number;
  potential_et_m3: number;
  actual_et_m3: number;
  et_deficit_m3: number;
  et_deficit_mm: number;
  deep_percolation_m3: number;
  overflow_m3: number;
  flush_water_m3: number;
  flush_count: number;
  battery_losses_kwh: number;
  pump_energy_kwh: number;
  pump_kwh_per_delivered_m3: number;
  required_electrical_kwh: number;
  unserved_kwh: number;
  electrical_autonomy_0_1: number;
  final_battery_soc_0_1: number;
  final_mean_moisture_m3_m3: number;
  denied_request_steps: number;
  zones: ZoneService[];
  diagnostics: SiteDiagnostics;
}

export interface CompareResponse {
  data_mode: "SIMULATED";
  scenario_id: ScenarioId;
  seed: number;
  horizon_days: number;
  steps: number;
  fixed_timer: PolicyReport;
  smart_hysteresis: PolicyReport;
  water_savings_fraction: number;
  elapsed_s: number;
  resource_aware: PolicyReport | null;
  evaluation_mode: "STARTUP_FAULT" | "MATCHED_OPERATION";
  warmup_days: number;
  measurement_start_step: number;
  measurement_end_step: number;
}
