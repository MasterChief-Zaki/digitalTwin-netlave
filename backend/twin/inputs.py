"""Step-indexed environmental inputs: TSE inflow, reference ET and the solar clock.

Inputs depend only on the step, the seed and the site, never on wall time, so a
run replays identically and the A/B comparison can share one input series.
"""

import math
import random
from dataclasses import dataclass
from functools import cache

from config import STEPS_PER_DAY, SiteConfig


@dataclass(frozen=True)
class StepInputs:
    day_index: int
    hour_of_day: float
    tse_inflow_m3_s: float
    et0_mm_day: float
    et0_step_mm: float


def clock(step: int, cfg: SiteConfig) -> tuple[int, int]:
    """Day index and minute of day at the start of `step`."""
    minutes = cfg.start_hour * 60 + step
    return minutes // STEPS_PER_DAY, minutes % STEPS_PER_DAY


def daylight_weight(minute_of_day: int, cfg: SiteConfig) -> float:
    """Normalised share of the daily sine shape that falls in this minute (sums to 1 over a day)."""
    return _raw_daylight_weight(minute_of_day, cfg) / _daylight_weight_total(cfg)


def daily_et0_mm(seed: int, day_index: int, cfg: SiteConfig) -> float:
    """Nominal ET0 with a seeded, deterministic day-to-day variation."""
    variation = random.Random(f"et0:{seed}:{day_index}").uniform(-1.0, 1.0)
    return cfg.climate.et0_nominal_mm_day * (1.0 + cfg.climate.et0_daily_variation * variation)


def tse_inflow_m3_s(hour_of_day: float, cfg: SiteConfig) -> float:
    """Diurnal treatment-plant effluent around the daily mean (the cosine averages to zero)."""
    supply = cfg.supply
    phase = 2.0 * math.pi * (hour_of_day - supply.tse_peak_hour) / 24.0
    return supply.tse_mean_inflow_m3_h / 3600.0 * (1.0 + supply.tse_diurnal_amplitude * math.cos(phase))


def inputs_at(step: int, seed: int, inflow_available: bool, cfg: SiteConfig) -> StepInputs:
    day_index, minute_of_day = clock(step, cfg)
    hour_of_day = (minute_of_day + 0.5) / 60.0
    et0_day = daily_et0_mm(seed, day_index, cfg)
    return StepInputs(
        day_index=day_index,
        hour_of_day=hour_of_day,
        tse_inflow_m3_s=tse_inflow_m3_s(hour_of_day, cfg) if inflow_available else 0.0,
        et0_mm_day=et0_day,
        et0_step_mm=et0_day * daylight_weight(minute_of_day, cfg),
    )


def _raw_daylight_weight(minute_of_day: int, cfg: SiteConfig) -> float:
    hour = (minute_of_day + 0.5) / 60.0
    return max(0.0, math.sin(math.pi * (hour - cfg.energy.sunrise_hour) / cfg.energy.day_length_h))


@cache
def _daylight_weight_total(cfg: SiteConfig) -> float:
    return sum(_raw_daylight_weight(minute, cfg) for minute in range(STEPS_PER_DAY))
