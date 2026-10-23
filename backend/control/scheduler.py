"""Bounded joint water/head/energy arbitration upstream of unchanged safety gates.

At most one automatic session is delivered at a time. Denied/paused sessions
retain their volume and demand latch; actual grants alone consume their budget.
No forecast, future input or profile ID is visible to this scheduler.
"""

from dataclasses import dataclass, replace

import schemas
from config import DT_S, SiteConfig
from control.policy import ZoneRequest
from models.filtration import filter_head_loss_m
from models.hydraulics import gravity_head, pump_requirement
from models.water_soil import surface_elevation_m
from twin.state import SimState


@dataclass(frozen=True)
class Schedule:
    requests: list[ZoneRequest]
    deferred: dict[str, schemas.ReasonCode]
    operating_floor_m3: float


def operating_floor_m3(state: SimState, cfg: SiteConfig) -> float:
    """Design-clog floor plus current-state feasibility; no static 850 guarantee."""
    filter_head = filter_head_loss_m(max(cfg.scheduler.design_clog_index, state.filter.clog_index), cfg.filtration)
    surface = cfg.reservoir.floor_elevation_m
    required_surface = surface
    for zone_cfg in cfg.zones:
        if zone_cfg.feed_mode == "GRAVITY":
            head = gravity_head(zone_cfg, surface, filter_head, zone_cfg.max_flow_m3_s, cfg.hydraulics)
            required_surface = max(required_surface, surface + head.required_m - head.available_m + cfg.scheduler.head_margin_m)
        else:
            pump = pump_requirement(zone_cfg, surface, filter_head, zone_cfg.max_flow_m3_s, cfg.hydraulics)
            allowed_head = pump.head_within_limit_m * (1 - cfg.scheduler.pump_power_margin_fraction)
            required_surface = max(required_surface, surface + pump.total_dynamic_head_m - allowed_head)
    required_volume = (required_surface - surface) * cfg.reservoir.capacity_m3 / cfg.reservoir.depth_at_capacity_m
    # A floor above capacity means the design condition cannot be scheduled.
    return max(cfg.scheduler.operating_inventory_m3, required_volume)


def schedule(requests: list[ZoneRequest], state: SimState, cfg: SiteConfig,
             generation_w: float, committed_load_w: float, flush_water_m3: float) -> Schedule:
    floor = operating_floor_m3(state, cfg)
    deferred: dict[str, schemas.ReasonCode] = {}
    selected: str | None = None
    zones_by_id = state.zones_by_id
    # An active normal session gets its minimum run, then waiting-time fairness.
    ranked = sorted(requests, key=lambda request: (
        not (zones_by_id[request.zone_id].valve_open
             and zones_by_id[request.zone_id].session.active_minutes < cfg.scheduler.minimum_run_minutes),
        -zones_by_id[request.zone_id].session.waiting_steps,
        -request.water_stress, request.zone_id,
    ))
    for request in ranked:
        zone = zones_by_id[request.zone_id]
        if zone.control_mode != "AUTO" or not request.wants_water:
            continue
        if selected is not None:
            deferred[zone.zone_id] = "SCHEDULER_QUEUE"
            continue
        if state.step < zone.session.rest_until_step:
            deferred[zone.zone_id] = "SCHEDULER_REST"
            continue
        restarting = not zone.valve_open
        inventory_margin = cfg.scheduler.restart_inventory_margin_m3 if restarting else 0.0
        session_volume = zone.session.remaining_volume_m3 or request.flow_m3_s * cfg.scheduler.session_minutes * 60
        water_budget = session_volume if restarting else request.flow_m3_s * DT_S
        if state.reservoir_volume_m3 - flush_water_m3 - water_budget < floor + inventory_margin:
            deferred[zone.zone_id] = "SCHEDULER_WATER_HOLD"
            continue
        zone_cfg = next(item for item in cfg.zones if item.zone_id == zone.zone_id)
        if zone_cfg.feed_mode == "PUMPED" and cfg.scheduler.energy_aware:
            pump = pump_requirement(zone_cfg, surface_elevation_m(state.reservoir_volume_m3, cfg.reservoir),
                                    filter_head_loss_m(state.filter.clog_index, cfg.filtration), request.flow_m3_s, cfg.hydraulics)
            deficit_w = max(0.0, committed_load_w + pump.power_w - generation_w)
            reserve_soc = cfg.scheduler.operating_battery_soc + (cfg.scheduler.restart_battery_soc_margin if restarting else 0.0)
            available_j = max(0.0, state.battery_energy_j - reserve_soc * cfg.energy.battery_capacity_j)
            duration_s = session_volume / request.flow_m3_s if restarting else DT_S
            if deficit_w / cfg.energy.battery_discharge_efficiency * duration_s > available_j:
                deferred[zone.zone_id] = "SCHEDULER_ENERGY_HOLD"
                continue
        selected = zone.zone_id
    shaped = [replace(request, action="STOP" if zones_by_id[request.zone_id].valve_open else "KEEP_CLOSED",
                      flow_m3_s=0.0, reason_code=deferred[request.zone_id],
                      explanation="Demand remains latched; this bounded session is deferred by the site resource budget.")
              if request.zone_id in deferred else request for request in requests]
    return Schedule(shaped, deferred, floor)
