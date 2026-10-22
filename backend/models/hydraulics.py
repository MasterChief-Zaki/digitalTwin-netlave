"""Static head, Darcy-Weisbach mainline friction, gravity feasibility and the zone C pump.

Clean mainlines use an assumed Darcy friction factor. There is no pump curve:
a pumped zone either gets its full rated flow within the electrical envelope
or none, which is a documented conservative approximation.
"""

import math
from dataclasses import dataclass

from config import GRAVITY_M_S2, WATER_DENSITY_KG_M3, HydraulicsConfig, ZoneConfig


@dataclass(frozen=True)
class GravityHead:
    available_m: float
    required_m: float

    @property
    def feasible(self) -> bool:
        return self.available_m >= self.required_m


@dataclass(frozen=True)
class PumpRequirement:
    total_dynamic_head_m: float
    power_w: float
    # The head the pump could add at this flow without exceeding its electrical limit.
    head_within_limit_m: float
    within_envelope: bool


def friction_head_m(flow_m3_s: float, zone: ZoneConfig, hydraulics: HydraulicsConfig) -> float:
    area_m2 = math.pi * zone.mainline_diameter_m**2 / 4.0
    velocity_m_s = flow_m3_s / area_m2
    return (
        hydraulics.darcy_friction_factor
        * (zone.mainline_length_m / zone.mainline_diameter_m)
        * velocity_m_s**2
        / (2.0 * GRAVITY_M_S2)
    )


def gravity_head(
    zone: ZoneConfig, surface_m: float, filter_head_loss_m: float, flow_m3_s: float, hydraulics: HydraulicsConfig
) -> GravityHead:
    """Gravity needs z_surface - z_field - h_filter >= h_emitter + h_friction."""
    return GravityHead(
        available_m=surface_m - zone.elevation_m - filter_head_loss_m,
        required_m=zone.emitter_head_m + friction_head_m(flow_m3_s, zone, hydraulics),
    )


def pump_requirement(
    zone: ZoneConfig, surface_m: float, filter_head_loss_m: float, flow_m3_s: float, hydraulics: HydraulicsConfig
) -> PumpRequirement:
    """TDH = static lift + emitter head + friction + filter loss; P = rho g Q TDH / eta."""
    total_dynamic_head_m = (
        (zone.elevation_m - surface_m)
        + zone.emitter_head_m
        + friction_head_m(flow_m3_s, zone, hydraulics)
        + filter_head_loss_m
    )
    hydraulic_factor = WATER_DENSITY_KG_M3 * GRAVITY_M_S2 * flow_m3_s / hydraulics.pump_wire_to_water_efficiency
    power_w = hydraulic_factor * total_dynamic_head_m
    return PumpRequirement(
        total_dynamic_head_m=total_dynamic_head_m,
        power_w=power_w,
        head_within_limit_m=hydraulics.pump_power_limit_w / hydraulic_factor if hydraulic_factor > 0 else 0.0,
        within_envelope=power_w <= hydraulics.pump_power_limit_w,
    )


def hydro_power_w(turbine_flow_m3_s: float, recoverable_head_m: float, turbine_efficiency: float) -> float:
    """Recoverable inlet drop only; the head the zones need downstream is not counted twice."""
    return WATER_DENSITY_KG_M3 * GRAVITY_M_S2 * turbine_flow_m3_s * recoverable_head_m * turbine_efficiency
