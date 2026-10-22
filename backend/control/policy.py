"""Controller policies. They only propose; the safety resolver alone grants water."""

from dataclasses import dataclass

import schemas
from config import SiteConfig, ZoneConfig
from twin.state import ZoneState


@dataclass(frozen=True)
class ZoneRequest:
    zone_id: str
    action: schemas.RequestedAction
    # The reason recorded if the request is granted.
    reason_code: schemas.ReasonCode
    explanation: str
    flow_m3_s: float
    water_stress: float
    irrigation_latched: bool

    @property
    def wants_water(self) -> bool:
        return self.action in ("START", "KEEP_OPEN")


def propose(
    zone: ZoneState,
    zone_config: ZoneConfig,
    water_stress: float,
    policy: schemas.ControlPolicy,
    minute_of_day: int,
    cfg: SiteConfig,
) -> ZoneRequest:
    if zone.control_mode == "MANUAL_OPEN":
        return _request(zone, zone_config, water_stress, True, "MANUAL_OVERRIDE_OK", "Operator holds the valve open.")
    if zone.control_mode == "MANUAL_CLOSED":
        return _request(zone, zone_config, water_stress, False, "MANUAL_STOP_OK", "Operator holds the valve closed.")
    if policy == "FIXED_TIMER":
        return _fixed_timer(zone, zone_config, water_stress, minute_of_day, cfg)
    return _smart_hysteresis(zone, zone_config, water_stress, cfg)


def _smart_hysteresis(zone: ZoneState, zone_config: ZoneConfig, water_stress: float, cfg: SiteConfig) -> ZoneRequest:
    theta = zone.theta_m3_m3
    theta_on = cfg.soil.theta_on_m3_m3
    theta_off = cfg.soil.theta_off_m3_m3
    if zone.irrigation_latched and theta >= theta_off:
        return _request(
            zone, zone_config, water_stress, False, "MOISTURE_TARGET_REACHED",
            f"Soil moisture {theta:.3f} reached the {theta_off:.3f} stop threshold.", latched=False,
        )
    if zone.irrigation_latched or theta < theta_on:
        reason: schemas.ReasonCode = "KEEP_OPEN" if zone.valve_open else "SOIL_BELOW_THRESHOLD"
        return _request(
            zone, zone_config, water_stress, True, reason,
            f"Soil moisture {theta:.3f} is below the {theta_off:.3f} stop threshold after crossing {theta_on:.3f}.",
            latched=True,
        )
    return _request(
        zone, zone_config, water_stress, False, "KEEP_CLOSED",
        f"Soil moisture {theta:.3f} is above the {theta_on:.3f} start threshold.",
    )


def _fixed_timer(
    zone: ZoneState, zone_config: ZoneConfig, water_stress: float, minute_of_day: int, cfg: SiteConfig
) -> ZoneRequest:
    window_minutes = fixed_timer_window_minutes(zone_config, cfg)
    minutes_into_window = (minute_of_day - zone_config.timer_start_minute) % (24 * 60)
    if minutes_into_window < window_minutes:
        return _request(
            zone, zone_config, water_stress, True, "SCHEDULE_WINDOW_OPEN",
            f"Daily {window_minutes:.0f}-minute timer window is open.",
        )
    reason: schemas.ReasonCode = "SCHEDULE_WINDOW_CLOSED" if zone.valve_open else "KEEP_CLOSED"
    return _request(zone, zone_config, water_stress, False, reason, "Daily timer window is closed.")


def fixed_timer_window_minutes(zone_config: ZoneConfig, cfg: SiteConfig) -> float:
    """Daily gross depth from nominal ETc, application efficiency and the leaching allowance."""
    soil = cfg.soil
    net_m3 = soil.crop_coefficient * cfg.climate.et0_nominal_mm_day / 1000.0 * zone_config.area_m2
    gross_m3 = net_m3 / (soil.application_efficiency * (1.0 - soil.leaching_fraction))
    return gross_m3 / zone_config.max_flow_m3_h * 60.0


def _request(
    zone: ZoneState,
    zone_config: ZoneConfig,
    water_stress: float,
    wants_water: bool,
    reason_code: schemas.ReasonCode,
    explanation: str,
    latched: bool | None = None,
) -> ZoneRequest:
    if wants_water:
        action: schemas.RequestedAction = "KEEP_OPEN" if zone.valve_open else "START"
    else:
        action = "STOP" if zone.valve_open else "KEEP_CLOSED"
    return ZoneRequest(
        zone_id=zone.zone_id,
        action=action,
        reason_code=reason_code,
        explanation=explanation,
        flow_m3_s=zone_config.max_flow_m3_s if wants_water else 0.0,
        water_stress=water_stress,
        irrigation_latched=zone.irrigation_latched if latched is None else latched,
    )
