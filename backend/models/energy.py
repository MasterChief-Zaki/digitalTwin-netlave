"""Synthetic solar profile and battery dispatch on one DC bus.

Bus, each step:   P_hydro + P_solar + P_discharge + P_unserved = P_loads + P_charge + P_curtail
Cells, each step: dE = (eta_c * P_charge - P_discharge / eta_d) * dt
Nothing is created by clamping the state of charge: whatever the cells cannot
absorb is curtailed, and whatever they cannot supply is unserved.
"""

import math
from dataclasses import dataclass

from config import EnergyConfig


@dataclass(frozen=True)
class Dispatch:
    charge_power_w: float
    discharge_power_w: float
    curtail_power_w: float
    unserved_power_w: float
    battery_energy_j: float
    losses_j: float


def solar_power_w(hour_of_day: float, cloud_factor: float, energy: EnergyConfig) -> float:
    """8 kWp x 0.75 derate x max(0, sin(pi (h - 6) / 12))^1.2 x cloud factor; not a forecast."""
    shape = max(0.0, math.sin(math.pi * (hour_of_day - energy.sunrise_hour) / energy.day_length_h))
    return energy.solar_peak_w * energy.solar_derate * shape**energy.solar_shape_exponent * cloud_factor


def max_discharge_w(battery_energy_j: float, floor_soc: float, energy: EnergyConfig, dt_s: int) -> float:
    """Bus power the cells can deliver for a whole step without dropping below `floor_soc`."""
    usable_j = max(0.0, battery_energy_j - floor_soc * energy.battery_capacity_j)
    return min(energy.battery_max_discharge_w, usable_j * energy.battery_discharge_efficiency / dt_s)


def dispatch(generation_w: float, load_w: float, battery_energy_j: float, energy: EnergyConfig, dt_s: int) -> Dispatch:
    net_w = generation_w - load_w
    charge_w = discharge_w = curtail_w = unserved_w = 0.0
    if net_w >= 0:
        headroom_j = max(0.0, energy.battery_capacity_j - battery_energy_j)
        charge_w = min(net_w, energy.battery_max_charge_w, headroom_j / (energy.battery_charge_efficiency * dt_s))
        curtail_w = net_w - charge_w
    else:
        discharge_w = min(-net_w, max_discharge_w(battery_energy_j, energy.battery_floor_soc, energy, dt_s))
        unserved_w = -net_w - discharge_w

    stored_j = energy.battery_charge_efficiency * charge_w * dt_s
    drawn_j = discharge_w / energy.battery_discharge_efficiency * dt_s
    return Dispatch(
        charge_power_w=charge_w,
        discharge_power_w=discharge_w,
        curtail_power_w=curtail_w,
        unserved_power_w=unserved_w,
        battery_energy_j=battery_energy_j + stored_j - drawn_j,
        losses_j=(charge_w * dt_s - stored_j) + (drawn_j - discharge_w * dt_s),
    )
