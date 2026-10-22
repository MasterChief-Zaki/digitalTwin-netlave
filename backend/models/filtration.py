"""Screen/disc filter clogging: pressure drop and the head it takes from every zone."""

from config import GRAVITY_M_S2, WATER_DENSITY_KG_M3, FiltrationConfig


def filter_pressure_drop_pa(clog_index: float, filtration: FiltrationConfig) -> float:
    """Illustrative linear law: dP = 12 kPa clean plus 40 kPa at a fully clogged filter."""
    return filtration.clean_pressure_drop_pa + filtration.clog_pressure_drop_pa * clog_index


def filter_head_loss_m(clog_index: float, filtration: FiltrationConfig) -> float:
    return filter_pressure_drop_pa(clog_index, filtration) / (WATER_DENSITY_KG_M3 * GRAVITY_M_S2)
