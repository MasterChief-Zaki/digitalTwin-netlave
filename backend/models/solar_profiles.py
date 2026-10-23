"""Held-out synthetic solar inputs; evaluated at the current step only."""

from config import STEPS_PER_DAY, EnergyConfig
from models.energy import solar_power_w


def profile_solar_power_w(hour_of_day: float, cloud_factor: float, energy: EnergyConfig,
                          profile_id: str, elapsed_steps: int) -> float:
    if profile_id == "shifted_sun":
        return solar_power_w((hour_of_day - 2.0) % 24.0, cloud_factor, energy)
    if profile_id == "cloud_pulses":
        attenuation = 0.15 if 9.0 <= hour_of_day < 14.0 else 0.8
        return solar_power_w(hour_of_day, cloud_factor * attenuation, energy)
    if profile_id == "three_day_dark":
        day = elapsed_steps // STEPS_PER_DAY
        attenuation = 0.05 if day % 10 in (2, 3, 4) else 1.0
        return solar_power_w(hour_of_day, cloud_factor * attenuation, energy)
    if profile_id != "nominal":
        raise ValueError("Unknown solar input profile.")
    return solar_power_w(hour_of_day, cloud_factor, energy)
