"""Reservoir storage and per-zone soil water buckets with FAO-56 style stress."""

from dataclasses import dataclass

from config import ReservoirConfig, SoilConfig, ZoneConfig


@dataclass(frozen=True)
class ReservoirStepResult:
    volume_m3: float
    overflow_m3: float


@dataclass(frozen=True)
class SoilStepResult:
    theta_m3_m3: float
    infiltrated_m3: float
    application_loss_m3: float
    potential_et_m3: float
    actual_et_m3: float
    drainage_m3: float


def surface_elevation_m(volume_m3: float, reservoir: ReservoirConfig) -> float:
    return reservoir.floor_elevation_m + reservoir.depth_at_capacity_m * volume_m3 / reservoir.capacity_m3


def usable_volume_m3(volume_m3: float, reservoir: ReservoirConfig) -> float:
    return max(0.0, volume_m3 - reservoir.dead_volume_m3)


def update_reservoir(
    volume_m3: float, inflow_m3: float, withdrawal_m3: float, reservoir: ReservoirConfig
) -> ReservoirStepResult:
    """Store inflow, remove accepted withdrawals and spill the actual excess above capacity."""
    unbounded_volume_m3 = volume_m3 + inflow_m3 - withdrawal_m3
    overflow_m3 = max(0.0, unbounded_volume_m3 - reservoir.capacity_m3)
    return ReservoirStepResult(volume_m3=unbounded_volume_m3 - overflow_m3, overflow_m3=overflow_m3)


def soil_storage_m3(theta_m3_m3: float, zone: ZoneConfig, soil: SoilConfig) -> float:
    return theta_m3_m3 * zone.area_m2 * soil.root_depth_m


def stress_coefficient(theta_m3_m3: float, soil: SoilConfig) -> float:
    """Ks: 1 above the irrigation trigger, falling linearly to 0 at the wilting point."""
    span = soil.theta_on_m3_m3 - soil.theta_wp_m3_m3
    return min(1.0, max(0.0, (theta_m3_m3 - soil.theta_wp_m3_m3) / span))


def water_stress(theta_m3_m3: float, soil: SoilConfig) -> float:
    return 1.0 - stress_coefficient(theta_m3_m3, soil)


def update_soil(
    theta_m3_m3: float, delivered_m3: float, et0_step_mm: float, zone: ZoneConfig, soil: SoilConfig
) -> SoilStepResult:
    """dS = infiltration - actual ET - deep percolation, all booked in m3."""
    storage_m3 = soil_storage_m3(theta_m3_m3, zone, soil)
    wilting_storage_m3 = soil_storage_m3(soil.theta_wp_m3_m3, zone, soil)
    field_capacity_storage_m3 = soil_storage_m3(soil.theta_fc_m3_m3, zone, soil)

    infiltrated_m3 = delivered_m3 * soil.application_efficiency
    application_loss_m3 = delivered_m3 - infiltrated_m3

    potential_et_m3 = soil.crop_coefficient * et0_step_mm / 1000.0 * zone.area_m2
    available_for_et_m3 = max(0.0, storage_m3 + infiltrated_m3 - wilting_storage_m3)
    actual_et_m3 = min(stress_coefficient(theta_m3_m3, soil) * potential_et_m3, available_for_et_m3)

    storage_after_et_m3 = storage_m3 + infiltrated_m3 - actual_et_m3
    drainage_m3 = max(0.0, storage_after_et_m3 - field_capacity_storage_m3)
    next_storage_m3 = storage_after_et_m3 - drainage_m3

    return SoilStepResult(
        theta_m3_m3=next_storage_m3 / (zone.area_m2 * soil.root_depth_m),
        infiltrated_m3=infiltrated_m3,
        application_loss_m3=application_loss_m3,
        potential_et_m3=potential_et_m3,
        actual_et_m3=actual_et_m3,
        drainage_m3=drainage_m3,
    )
