"""Versioned evaluation definitions, not physical assumptions or controller settings.

See docs/rca/evaluation-spec.md. These tolerances apply to exported cumulative
accounts; they do not replace or relax the engine's per-step balance checks.
"""

import math
from dataclasses import dataclass

PROTOCOL_VERSION = "rca-startup-v1"
REFERENCE_COMMIT = "4ae12eb774e422679c04e0d94c661351ae879747"
REFERENCE_SEEDS = (3, 7, 11)
REFERENCE_HORIZONS_DAYS = (14, 30)


@dataclass(frozen=True)
class AccountTolerance:
    absolute: float
    relative: float = 1e-9

    def assert_close(self, account: str, lhs: float, rhs: float) -> None:
        if not (math.isfinite(lhs) and math.isfinite(rhs)) or not math.isclose(
            lhs, rhs, abs_tol=self.absolute, rel_tol=self.relative
        ):
            raise EvaluationBalanceError(
                f"{account} does not close: lhs={lhs!r}, rhs={rhs!r}, "
                f"absolute_tolerance={self.absolute}, relative_tolerance={self.relative}"
            )


class EvaluationBalanceError(RuntimeError):
    """A cumulative export disagrees with the simulated stock change."""


WATER_TOLERANCE_M3 = AccountTolerance(absolute=1e-6)
ENERGY_TOLERANCE_KWH = AccountTolerance(absolute=1e-6)


def stock_adjusted_delivery_m3(delivered_m3: float, soil_change_m3: float, efficiency: float) -> float:
    """Remove accumulation (or add depletion) of root-zone water at fixed efficiency."""
    if not 0.0 < efficiency <= 1.0:
        raise ValueError("Application efficiency must be in (0, 1].")
    return delivered_m3 - soil_change_m3 / efficiency


def battery_equivalent_full_cycles(bus_discharge_energy_j: float, cfg_capacity_j: float, efficiency: float) -> float:
    """Cell-side discharged energy / nominal capacity; charging is not counted twice."""
    if cfg_capacity_j <= 0.0 or not 0.0 < efficiency <= 1.0:
        raise ValueError("Battery capacity must be positive and discharge efficiency in (0, 1].")
    return bus_discharge_energy_j / efficiency / cfg_capacity_j
