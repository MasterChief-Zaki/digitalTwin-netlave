"""The one synthetic-parameter table for the prototype site.

Every value is an assumption for a synthetic Egyptian TSE forestry site, not a
Serapium field measurement. A real deployment replaces them with surveyed head,
a measured TSE hydrograph, pipe design, soil laboratory values and
species-specific agronomy. `ASSUMPTIONS` lists each value with its unit, status
and source for `/scenarios` and the README.
"""

from dataclasses import dataclass, field
from typing import Literal

ZoneId = Literal["A", "B", "C"]
FeedMode = Literal["GRAVITY", "PUMPED"]

DT_S = 60
STEPS_PER_DAY = 24 * 60
WATER_DENSITY_KG_M3 = 1000.0
GRAVITY_M_S2 = 9.81


@dataclass(frozen=True)
class ZoneConfig:
    zone_id: ZoneId
    feed_mode: FeedMode
    area_m2: float
    elevation_m: float
    emitter_head_m: float
    max_flow_m3_h: float
    mainline_length_m: float
    mainline_diameter_m: float
    # Fixed-timer policy: daily window start, minutes after midnight.
    timer_start_minute: int

    @property
    def max_flow_m3_s(self) -> float:
        return self.max_flow_m3_h / 3600.0


@dataclass(frozen=True)
class SoilConfig:
    theta_wp_m3_m3: float = 0.10
    theta_fc_m3_m3: float = 0.22
    theta_sat_m3_m3: float = 0.38
    root_depth_m: float = 0.8
    crop_coefficient: float = 0.85
    application_efficiency: float = 0.90
    allowed_depletion_fraction: float = 0.45
    stop_fraction_of_fc: float = 0.90
    leaching_fraction: float = 0.15

    @property
    def theta_on_m3_m3(self) -> float:
        """Start irrigating at 45% depletion of the available water below field capacity."""
        return self.theta_fc_m3_m3 - self.allowed_depletion_fraction * (self.theta_fc_m3_m3 - self.theta_wp_m3_m3)

    @property
    def theta_off_m3_m3(self) -> float:
        return self.stop_fraction_of_fc * self.theta_fc_m3_m3


@dataclass(frozen=True)
class ReservoirConfig:
    capacity_m3: float = 1500.0
    initial_volume_m3: float = 900.0
    dead_volume_m3: float = 50.0
    floor_elevation_m: float = 20.5
    depth_at_capacity_m: float = 2.5


@dataclass(frozen=True)
class HydraulicsConfig:
    darcy_friction_factor: float = 0.025
    gravity_manifold_limit_m3_h: float = 140.0
    pump_power_limit_w: float = 3000.0
    pump_wire_to_water_efficiency: float = 0.55

    @property
    def gravity_manifold_limit_m3_s(self) -> float:
        return self.gravity_manifold_limit_m3_h / 3600.0


@dataclass(frozen=True)
class SupplyConfig:
    tse_mean_inflow_m3_h: float = 60.0
    tse_diurnal_amplitude: float = 0.25
    tse_peak_hour: float = 14.0
    hydro_recoverable_head_m: float = 3.0
    hydro_turbine_efficiency: float = 0.60


@dataclass(frozen=True)
class EnergyConfig:
    solar_peak_w: float = 8000.0
    solar_derate: float = 0.75
    solar_shape_exponent: float = 1.2
    sunrise_hour: float = 6.0
    day_length_h: float = 12.0
    battery_capacity_kwh: float = 15.0
    battery_initial_soc: float = 0.80
    battery_floor_soc: float = 0.10
    pump_reserve_soc: float = 0.20
    battery_max_charge_w: float = 3000.0
    battery_max_discharge_w: float = 3000.0
    battery_charge_efficiency: float = 0.95
    battery_discharge_efficiency: float = 0.95
    aux_power_w: float = 50.0

    @property
    def battery_capacity_j(self) -> float:
        return self.battery_capacity_kwh * 3.6e6


@dataclass(frozen=True)
class FiltrationConfig:
    clean_pressure_drop_pa: float = 12000.0
    clog_pressure_drop_pa: float = 40000.0
    clog_per_filtered_m3: float = 3.5e-4
    flush_threshold: float = 0.60
    clog_after_flush: float = 0.05
    initial_clog_index: float = 0.10
    flush_steps: int = 5
    flush_water_m3: float = 1.5
    flush_power_w: float = 1200.0


@dataclass(frozen=True)
class ClimateConfig:
    et0_nominal_mm_day: float = 4.9
    et0_daily_variation: float = 0.10
    cloud_daily_min: float = 0.85


@dataclass(frozen=True)
class SiteConfig:
    zones: tuple[ZoneConfig, ...]
    soil: SoilConfig = field(default_factory=SoilConfig)
    reservoir: ReservoirConfig = field(default_factory=ReservoirConfig)
    hydraulics: HydraulicsConfig = field(default_factory=HydraulicsConfig)
    supply: SupplyConfig = field(default_factory=SupplyConfig)
    energy: EnergyConfig = field(default_factory=EnergyConfig)
    filtration: FiltrationConfig = field(default_factory=FiltrationConfig)
    climate: ClimateConfig = field(default_factory=ClimateConfig)
    start_hour: int = 6


SITE = SiteConfig(
    zones=(
        ZoneConfig("A", "GRAVITY", 60_000.0, 2.0, 10.0, 120.0, 350.0, 0.20, timer_start_minute=20 * 60),
        ZoneConfig("B", "GRAVITY", 50_000.0, 8.0, 9.0, 100.0, 350.0, 0.20, timer_start_minute=23 * 60),
        ZoneConfig("C", "PUMPED", 40_000.0, 34.0, 10.0, 24.0, 450.0, 0.20, timer_start_minute=8 * 60),
    )
)


@dataclass(frozen=True)
class Assumption:
    name: str
    value: str
    unit: str
    status: Literal["assumed", "derived", "measured"]
    source: str


_PLAN = "Execution plan V5.0, section 5 (synthetic)"

ASSUMPTIONS: tuple[Assumption, ...] = (
    Assumption("Zone areas A / B / C", "6 / 5 / 4", "ha", "assumed", _PLAN),
    Assumption("Zone feed A / B / C", "gravity / gravity / pumped", "-", "assumed", _PLAN),
    Assumption("Zone elevations A / B / C", "+2 / +8 / +34", "m", "assumed", _PLAN),
    Assumption("Emitter head A / B / C", "10 / 9 / 10", "m", "assumed", _PLAN),
    Assumption("Maximum zone flow A / B / C", "120 / 100 / 24", "m3/h", "assumed", _PLAN),
    Assumption("Mainline length / diameter", "350, 350, 450 / 0.20", "m", "assumed", _PLAN),
    Assumption("Darcy friction factor (clean mainline)", "0.025", "-", "assumed", "Execution plan V5.0, section 6.3"),
    Assumption("Shared gravity manifold A+B", "140", "m3/h", "assumed", _PLAN),
    Assumption("Pump electrical limit / wire-to-water efficiency", "3000 / 0.55", "W / -", "assumed", _PLAN),
    Assumption("Reservoir capacity / initial / dead", "1500 / 900 / 50", "m3", "assumed", _PLAN),
    Assumption("Reservoir floor / depth at capacity", "+20.5 / 2.5", "m", "assumed", "Chosen so the surface is +22 m at 900 m3"),
    Assumption("TSE inflow daily mean", "60", "m3/h", "assumed", _PLAN),
    Assumption("TSE diurnal amplitude / peak hour", "25% / 14:00", "- / h", "assumed", "Synthetic treatment-plant effluent profile"),
    Assumption("Hydro recoverable inlet head / turbine efficiency", "3 / 0.60", "m / -", "assumed", _PLAN),
    Assumption("Solar array / derate", "8 / 0.75", "kWp / -", "assumed", _PLAN),
    Assumption("Solar profile", "sin(pi(h-6)/12)^1.2, 06:00-18:00", "-", "assumed", "Synthetic, not an irradiance forecast"),
    Assumption("Battery capacity / initial SoC", "15 / 0.80", "kWh / -", "assumed", _PLAN),
    Assumption("Battery cell floor / pump reserve", "0.10 / 0.20", "SoC", "assumed", "Plan ruling 2"),
    Assumption("Battery charge and discharge limit / efficiency", "3000 / 0.95", "W / -", "assumed", _PLAN),
    Assumption("Auxiliary load / flush load", "50 / 1200", "W", "assumed", _PLAN),
    Assumption("Soil wilting point / field capacity / saturation", "0.10 / 0.22 / 0.38", "m3/m3", "assumed", "Sandy-loam assumption"),
    Assumption("Root depth / crop coefficient / application efficiency", "0.8 / 0.85 / 0.90", "m / - / -", "assumed", _PLAN),
    Assumption("Irrigation start threshold", "0.166", "m3/m3", "derived", "FAO-56 RAW: fc - 0.45 (fc - wp)"),
    Assumption("Irrigation stop threshold", "0.198", "m3/m3", "derived", "0.90 x field capacity"),
    Assumption("Reference ET0 (nominal, seeded +/-10% per day)", "4.9", "mm/day", "assumed", "Constant fallback of plan section 6.2"),
    Assumption("Filter pressure drop", "12000 + 40000 x CI", "Pa", "assumed", "Illustrative, plan section 6.5"),
    Assumption("Filter loading per filtered m3", "3.5e-4", "CI/m3", "assumed", "Chosen to flush about every 2 days at baseline"),
    Assumption("Flush threshold / water / energy", "0.60 / 1.5 / 0.10", "CI / m3 / kWh", "assumed", _PLAN),
    Assumption("Leaching allowance (fixed timer only)", "15", "%", "assumed", "Scenario allowance, not salinity control"),
    Assumption("Water-quality flag", "synthetic OK / HOLD / UNKNOWN", "-", "assumed", "Not an Egyptian regulatory compliance test"),
)
