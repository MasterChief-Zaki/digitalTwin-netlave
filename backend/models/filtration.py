"""Screen/disc filter clogging, its pressure drop, and the exclusive backflush.

Treated wastewater clogs drip emitters and filters with particulate, chemical
and biological matter (ISO 20419:2018); this is a solids-loading-only model.
"""

from dataclasses import dataclass

import schemas
from config import GRAVITY_M_S2, WATER_DENSITY_KG_M3, EnergyConfig, FiltrationConfig


def filter_pressure_drop_pa(clog_index: float, filtration: FiltrationConfig) -> float:
    """Illustrative linear law: dP = 12 kPa clean plus 40 kPa at a fully clogged filter."""
    return filtration.clean_pressure_drop_pa + filtration.clog_pressure_drop_pa * clog_index


def filter_head_loss_m(clog_index: float, filtration: FiltrationConfig) -> float:
    return filter_pressure_drop_pa(clog_index, filtration) / (WATER_DENSITY_KG_M3 * GRAVITY_M_S2)


@dataclass(frozen=True)
class FlushPlan:
    """What the filter does this step, decided before irrigation is granted."""

    flushing: bool
    started: bool
    blocks_irrigation: schemas.ReasonCode | None
    water_m3: float
    power_w: float


def plan_flush(
    flushing: bool,
    clog_index: float,
    usable_volume_m3: float,
    generation_w: float,
    other_load_w: float,
    battery_above_floor_j: float,
    filtration: FiltrationConfig,
    energy: EnergyConfig,
    dt_s: int,
) -> FlushPlan:
    """Continue a flush, start one at the threshold if its water and energy exist, or hold irrigation."""
    water_per_step_m3 = filtration.flush_water_m3 / filtration.flush_steps
    flush_step = FlushPlan(True, not flushing, "FLUSH_IN_PROGRESS", water_per_step_m3, filtration.flush_power_w)
    if flushing:
        return flush_step
    if clog_index < filtration.flush_threshold:
        return FlushPlan(False, False, None, 0.0, 0.0)

    deficit_w = max(0.0, other_load_w + filtration.flush_power_w - generation_w)
    flush_energy_from_battery_j = deficit_w * dt_s * filtration.flush_steps / energy.battery_discharge_efficiency
    has_water = usable_volume_m3 >= filtration.flush_water_m3
    has_power = deficit_w <= energy.battery_max_discharge_w and flush_energy_from_battery_j <= battery_above_floor_j
    if has_water and has_power:
        return flush_step
    return FlushPlan(False, False, "FILTER_FLUSH_REQUIRED", 0.0, 0.0)


def load_filter(clog_index: float, filtered_m3: float, solids_multiplier: float, filtration: FiltrationConfig) -> float:
    """Solids accumulate only with water that actually passes through the filter."""
    return min(1.0, max(0.0, clog_index + filtration.clog_per_filtered_m3 * solids_multiplier * filtered_m3))
