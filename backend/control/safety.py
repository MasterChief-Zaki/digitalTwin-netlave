"""The safety resolver: the only place irrigation is granted.

Requests that want water pass the gates in the documented order:
(1) water quality, (2) no flush, (3) reservoir withdrawal, (4) hydraulic head,
(5) shared manifold and pump envelope, (6) instantaneous electrical power,
(7) battery reserve. The first failing gate denies the whole request (no
fabricated partial flow without a pump curve). Stop and keep-closed requests
are always granted and need no water or energy. A manual open never bypasses
a gate.
"""

from dataclasses import dataclass

import schemas
from config import SiteConfig
from control.policy import ZoneRequest
from models.hydraulics import GravityHead, PumpRequirement


@dataclass(frozen=True)
class Grant:
    zone_id: str
    action: schemas.RequestedAction
    accepted: bool
    reason_code: schemas.ReasonCode
    explanation: str
    flow_m3_s: float
    requested_flow_m3_s: float
    pump_power_w: float = 0.0


@dataclass(frozen=True)
class ZoneHydraulics:
    gravity: GravityHead | None = None
    pump: PumpRequirement | None = None


@dataclass
class SafetyContext:
    dt_s: int
    usable_volume_m3: float
    hydraulics: dict[str, ZoneHydraulics]
    generation_w: float
    battery_energy_j: float
    water_quality: schemas.WaterQuality = "OK"
    filter_blocks_irrigation: schemas.ReasonCode | None = None
    committed_withdrawal_m3: float = 0.0
    committed_gravity_flow_m3_s: float = 0.0
    committed_load_w: float = 0.0
    granted_pump_w: float = 0.0


Denial = tuple[schemas.ReasonCode, str]


def resolve(ranked_requests: list[ZoneRequest], context: SafetyContext, cfg: SiteConfig) -> dict[str, Grant]:
    grants: dict[str, Grant] = {}
    for request in ranked_requests:
        if not request.wants_water:
            grants[request.zone_id] = _grant(request, request.reason_code, request.explanation)
            continue
        hydraulics = context.hydraulics[request.zone_id]
        denial = (
            _quality_gate(request, context)
            or _flush_gate(request, context)
            or _reservoir_gate(request, context, cfg)
            or _head_gate(request, hydraulics)
            or _manifold_gate(request, hydraulics, context, cfg)
            or _power_gate(request, hydraulics, context, cfg)
            or _reserve_gate(request, hydraulics, context, cfg)
        )
        if denial is not None:
            grants[request.zone_id] = _deny(request, *denial)
            continue
        pump_w = hydraulics.pump.power_w if hydraulics.pump is not None else 0.0
        context.committed_withdrawal_m3 += request.flow_m3_s * context.dt_s
        if hydraulics.gravity is not None:
            context.committed_gravity_flow_m3_s += request.flow_m3_s
        context.committed_load_w += pump_w
        context.granted_pump_w += pump_w
        grants[request.zone_id] = _grant(request, request.reason_code, request.explanation, request.flow_m3_s, pump_w)
    return grants


def _quality_gate(request: ZoneRequest, context: SafetyContext) -> Denial | None:
    if context.water_quality == "OK":
        return None
    return (
        "WATER_QUALITY_HOLD",
        f"Synthetic TSE quality flag is {context.water_quality}; irrigation fails closed until it reads OK.",
    )


def _flush_gate(request: ZoneRequest, context: SafetyContext) -> Denial | None:
    if context.filter_blocks_irrigation == "FLUSH_IN_PROGRESS":
        return ("FLUSH_IN_PROGRESS", "The shared filter is backflushing; irrigation is suspended until it finishes.")
    if context.filter_blocks_irrigation == "FILTER_FLUSH_REQUIRED":
        return ("FILTER_FLUSH_REQUIRED", "The filter is clogged past its flush threshold and must be flushed first.")
    return None


def _reservoir_gate(request: ZoneRequest, context: SafetyContext, cfg: SiteConfig) -> Denial | None:
    """Keeping a valve open needs this minute's water; starting one needs a margin, so valves don't chatter."""
    minutes = cfg.reservoir.start_reserve_minutes if request.action == "START" else 1
    needed_m3 = request.flow_m3_s * context.dt_s * minutes
    remaining_m3 = context.usable_volume_m3 - context.committed_withdrawal_m3
    if needed_m3 > remaining_m3:
        window = f"{minutes} minutes of flow" if minutes > 1 else "this minute"
        return (
            "RESERVOIR_LOW",
            f"Zone {request.zone_id} needs {needed_m3:.2f} m3 ({window}) but only {max(0.0, remaining_m3):.2f} m3 "
            "is above the reservoir's dead volume.",
        )
    return None


def _head_gate(request: ZoneRequest, hydraulics: ZoneHydraulics) -> Denial | None:
    gravity = hydraulics.gravity
    if gravity is not None and not gravity.feasible:
        return (
            "INSUFFICIENT_HEAD",
            f"Zone {request.zone_id} has {gravity.available_m:.2f} m of gravity head after the filter but its "
            f"emitters and mainline need {gravity.required_m:.2f} m.",
        )
    pump = hydraulics.pump
    if pump is not None and not pump.within_envelope:
        return (
            "INSUFFICIENT_HEAD",
            f"Zone {request.zone_id} needs {pump.total_dynamic_head_m:.2f} m of pump head, which takes "
            f"{pump.power_w:,.0f} W; the 3 kW pump can add only {pump.head_within_limit_m:.2f} m at this flow.",
        )
    return None


def _manifold_gate(
    request: ZoneRequest, hydraulics: ZoneHydraulics, context: SafetyContext, cfg: SiteConfig
) -> Denial | None:
    if hydraulics.gravity is None:
        return None
    limit_m3_s = cfg.hydraulics.gravity_manifold_limit_m3_s
    if context.committed_gravity_flow_m3_s + request.flow_m3_s > limit_m3_s + 1e-12:
        committed_m3_h = context.committed_gravity_flow_m3_s * 3600
        return (
            "CONCURRENT_FLOW_LIMIT",
            f"The shared gravity manifold already carries {committed_m3_h:.0f} m3/h; adding zone {request.zone_id}'s "
            f"{request.flow_m3_s * 3600:.0f} m3/h would exceed its {cfg.hydraulics.gravity_manifold_limit_m3_h:.0f} m3/h.",
        )
    return None


def _power_gate(
    request: ZoneRequest, hydraulics: ZoneHydraulics, context: SafetyContext, cfg: SiteConfig
) -> Denial | None:
    pump = hydraulics.pump
    if pump is None:
        return None
    supply_limit_w = context.generation_w + cfg.energy.battery_max_discharge_w
    demand_w = context.committed_load_w + pump.power_w
    if demand_w > supply_limit_w:
        return (
            "POWER_DEFICIT",
            f"The pump needs {pump.power_w:,.0f} W on top of {context.committed_load_w:,.0f} W of other loads, but "
            f"generation ({context.generation_w:,.0f} W) plus the battery's {cfg.energy.battery_max_discharge_w:,.0f} W "
            "discharge limit cannot supply it.",
        )
    return None


def _reserve_gate(
    request: ZoneRequest, hydraulics: ZoneHydraulics, context: SafetyContext, cfg: SiteConfig
) -> Denial | None:
    pump = hydraulics.pump
    if pump is None:
        return None
    energy = cfg.energy
    deficit_w = context.committed_load_w + pump.power_w - context.generation_w
    if deficit_w <= 0:
        return None
    reserve_j = energy.pump_reserve_soc * energy.battery_capacity_j
    above_reserve_w = max(0.0, context.battery_energy_j - reserve_j) * energy.battery_discharge_efficiency / context.dt_s
    if deficit_w > above_reserve_w:
        soc = context.battery_energy_j / energy.battery_capacity_j
        return (
            "BATTERY_BELOW_RESERVE",
            f"The pump needs {deficit_w:,.0f} W from the battery beyond generation ({context.generation_w:,.0f} W), "
            f"but the battery at {soc:.0%} has only {above_reserve_w:,.0f} W for this minute above its "
            f"{energy.pump_reserve_soc:.0%} pump reserve.",
        )
    return None


def _grant(
    request: ZoneRequest,
    reason_code: schemas.ReasonCode,
    explanation: str,
    flow_m3_s: float = 0.0,
    pump_power_w: float = 0.0,
) -> Grant:
    return Grant(
        request.zone_id, request.action, True, reason_code, explanation, flow_m3_s, request.flow_m3_s, pump_power_w
    )


def _deny(request: ZoneRequest, reason_code: schemas.ReasonCode, explanation: str) -> Grant:
    return Grant(request.zone_id, request.action, False, reason_code, explanation, 0.0, request.flow_m3_s)
