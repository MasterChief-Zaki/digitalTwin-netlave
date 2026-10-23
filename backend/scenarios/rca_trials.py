"""Reproducible startup/fault trials on private states, without the API service.

Run from the repo root with:
    uv --directory backend run python -m scenarios.rca_trials --output ../artifacts/rca/reference.json

The full default matrix is four scenarios x three seeds x two horizons x two
policies. All values come from engine steps; no reported outcome is prescribed.
"""

import argparse
import hashlib
import json
import os
import platform
import struct
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence

import schemas
from config import DT_S, SITE, STEPS_PER_DAY, SiteConfig, ZoneId
from models.water_soil import soil_storage_m3
from scenarios.evaluation import (
    ENERGY_TOLERANCE_KWH,
    PROTOCOL_VERSION,
    REFERENCE_COMMIT,
    REFERENCE_HORIZONS_DAYS,
    REFERENCE_SEEDS,
    WATER_TOLERANCE_M3,
    battery_equivalent_full_cycles,
    stock_adjusted_delivery_m3,
)
from scenarios.presets import SCENARIOS, build_scenario
from scenarios.comparison import _policy_neutral_digest
from twin.engine import step
from twin.state import Metrics, SimState, physical_digest, to_snapshot

REPO_ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = REPO_ROOT / "docs" / "rca" / "evaluation-spec.md"
POLICIES: tuple[schemas.ControlPolicy, ...] = ("FIXED_TIMER", "SMART_HYSTERESIS")


@dataclass(frozen=True)
class ZoneStock:
    zone_id: ZoneId
    root_zone_storage_m3: float


@dataclass(frozen=True)
class Stocks:
    reservoir_volume_m3: float
    battery_energy_j: float
    zones: tuple[ZoneStock, ...]

    @property
    def soil_storage_m3(self) -> float:
        return sum(zone.root_zone_storage_m3 for zone in self.zones)


@dataclass(frozen=True)
class AccountResiduals:
    reservoir_m3: float
    soil_m3: float
    electrical_bus_kwh: float
    battery_cells_kwh: float


@dataclass(frozen=True)
class TrialPolicyResult:
    policy: schemas.ControlPolicy
    input_digest: str
    initial_state_digest: str
    final_state_digest: str
    initial_stocks: Stocks
    final_stocks: Stocks
    metrics: Metrics
    minimum_reservoir_volume_m3: float
    minimum_battery_soc_0_1: float
    soil_stock_adjusted_delivery_m3: float
    battery_equivalent_full_cycles: float
    account_residuals: AccountResiduals


@dataclass(frozen=True)
class TrialPair:
    scenario_id: schemas.ScenarioId
    seed: int
    horizon_days: int
    measurement_start_step: int
    measurement_end_step: int
    fixed_timer: TrialPolicyResult
    smart_hysteresis: TrialPolicyResult


def capture_stocks(state: SimState, cfg: SiteConfig) -> Stocks:
    return Stocks(
        reservoir_volume_m3=state.reservoir_volume_m3,
        battery_energy_j=state.battery_energy_j,
        zones=tuple(
            ZoneStock(zone.zone_id, soil_storage_m3(zone.theta_m3_m3, zone_cfg, cfg.soil))
            for zone, zone_cfg in zip(state.zones, cfg.zones, strict=True)
        ),
    )


def assert_accounts(initial: Stocks, final: Stocks, metrics: Metrics) -> AccountResiduals:
    """Assert cumulative water and bus/cell closure independently of per-step checks."""
    reservoir_change_m3 = final.reservoir_volume_m3 - initial.reservoir_volume_m3
    reservoir_net_m3 = (
        metrics.tse_inflow_m3 - metrics.irrigation_delivered_m3 - metrics.flush_water_m3
        - metrics.overflow_m3 - metrics.other_diversion_m3
    )
    soil_change_m3 = final.soil_storage_m3 - initial.soil_storage_m3
    soil_net_m3 = (
        metrics.irrigation_delivered_m3 - metrics.application_loss_m3
        - metrics.actual_et_m3 - metrics.deep_percolation_m3
    )
    bus_supply_kwh = (
        metrics.hydro_energy_j + metrics.solar_energy_j
        + metrics.battery_discharge_energy_j + metrics.unserved_energy_j
    ) / 3.6e6
    bus_demand_kwh = (
        metrics.required_electrical_energy_j + metrics.battery_charge_energy_j + metrics.curtailed_energy_j
    ) / 3.6e6
    cells_change_kwh = (final.battery_energy_j - initial.battery_energy_j) / 3.6e6
    cells_net_kwh = (
        metrics.battery_charge_energy_j - metrics.battery_discharge_energy_j - metrics.battery_losses_j
    ) / 3.6e6
    WATER_TOLERANCE_M3.assert_close("reservoir_m3", reservoir_change_m3, reservoir_net_m3)
    WATER_TOLERANCE_M3.assert_close("soil_m3", soil_change_m3, soil_net_m3)
    ENERGY_TOLERANCE_KWH.assert_close("electrical_bus_kwh", bus_supply_kwh, bus_demand_kwh)
    ENERGY_TOLERANCE_KWH.assert_close("battery_cells_kwh", cells_change_kwh, cells_net_kwh)
    return AccountResiduals(
        reservoir_change_m3 - reservoir_net_m3,
        soil_change_m3 - soil_net_m3,
        bus_supply_kwh - bus_demand_kwh,
        cells_change_kwh - cells_net_kwh,
    )


def run_trial_policy(
    cfg: SiteConfig, scenario_id: schemas.ScenarioId, seed: int,
    horizon_days: int, policy: schemas.ControlPolicy,
) -> TrialPolicyResult:
    if seed < 0 or horizon_days not in range(1, 31):
        raise ValueError("Seed must be nonnegative and horizon_days must be in [1, 30].")
    state = build_scenario(cfg, scenario_id, seed=seed, control_policy=policy)
    initial_digest = _policy_neutral_digest(state, cfg)
    initial_stocks = capture_stocks(state, cfg)
    minimum_volume_m3 = state.reservoir_volume_m3
    minimum_soc = state.battery_energy_j / cfg.energy.battery_capacity_j
    input_hash = hashlib.sha256()
    for _ in range(horizon_days * STEPS_PER_DAY):
        result = step(state, cfg)
        state = result.state
        input_hash.update(struct.pack(
            "<4d", result.inputs.tse_inflow_m3_s, result.inputs.et0_step_mm,
            state.power.solar_power_w, state.power.hydro_power_w,
        ))
        minimum_volume_m3 = min(minimum_volume_m3, state.reservoir_volume_m3)
        minimum_soc = min(minimum_soc, state.battery_energy_j / cfg.energy.battery_capacity_j)
    final_stocks = capture_stocks(state, cfg)
    residuals = assert_accounts(initial_stocks, final_stocks, state.metrics)
    return TrialPolicyResult(
        policy=policy,
        input_digest=input_hash.hexdigest(),
        initial_state_digest=initial_digest,
        final_state_digest=physical_digest(to_snapshot(state, cfg, run_generation=0, latest_event_id=0)),
        initial_stocks=initial_stocks,
        final_stocks=final_stocks,
        metrics=state.metrics,
        minimum_reservoir_volume_m3=minimum_volume_m3,
        minimum_battery_soc_0_1=minimum_soc,
        soil_stock_adjusted_delivery_m3=stock_adjusted_delivery_m3(
            state.metrics.irrigation_delivered_m3,
            final_stocks.soil_storage_m3 - initial_stocks.soil_storage_m3,
            cfg.soil.application_efficiency,
        ),
        battery_equivalent_full_cycles=battery_equivalent_full_cycles(
            state.metrics.battery_discharge_energy_j, cfg.energy.battery_capacity_j,
            cfg.energy.battery_discharge_efficiency,
        ),
        account_residuals=residuals,
    )


def run_trial_pair(cfg: SiteConfig, scenario_id: schemas.ScenarioId, seed: int, horizon_days: int) -> TrialPair:
    fixed, smart = (
        run_trial_policy(cfg, scenario_id, seed, horizon_days, policy) for policy in POLICIES
    )
    if fixed.input_digest != smart.input_digest or fixed.initial_state_digest != smart.initial_state_digest:
        raise ValueError("Trial policies must share inputs and their physical initial state.")
    return TrialPair(scenario_id, seed, horizon_days, 0, horizon_days * STEPS_PER_DAY, fixed, smart)


def json_digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode("utf-8")).hexdigest()


def text_digest(path: Path) -> str:
    """Canonical LF text hash, independent of Git's Windows checkout line endings."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def source_digest(repo_root: Path) -> str:
    """Hash paths and canonical text of sources/locks/spec, pruning environments."""
    paths: list[Path] = []
    for directory, subdirectories, filenames in os.walk(repo_root / "backend"):
        subdirectories[:] = [name for name in subdirectories if not name.startswith(".") and name != "__pycache__"]
        paths.extend(Path(directory) / name for name in filenames if name.endswith(".py"))
    paths.extend(repo_root / "backend" / name for name in ("pyproject.toml", "uv.lock", ".python-version"))
    paths.append(repo_root / "docs" / "rca" / "evaluation-spec.md")
    digest = hashlib.sha256()
    for path in sorted(paths):
        relative_path = path.relative_to(repo_root).as_posix().encode("utf-8")
        contents = path.read_bytes().replace(b"\r\n", b"\n")
        digest.update(struct.pack("<Q", len(relative_path)))
        digest.update(relative_path)
        digest.update(struct.pack("<Q", len(contents)))
        digest.update(contents)
    return digest.hexdigest()


def provenance(cfg: SiteConfig, require_clean: bool = False) -> dict[str, object]:
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, check=True, capture_output=True, text=True,
    ).stdout.strip()
    dirty = bool(subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=REPO_ROOT, check=True, capture_output=True, text=True,
    ).stdout.strip())
    if require_clean and dirty:
        raise ValueError("Published trial artifacts require a clean working tree.")
    configuration = asdict(cfg)
    return {
        "git_commit": commit,
        "working_tree_dirty": dirty,
        "reference_commit": REFERENCE_COMMIT,
        "source_digest": source_digest(REPO_ROOT),
        "configuration": configuration,
        "configuration_digest": json_digest(configuration),
        "protocol_version": PROTOCOL_VERSION,
        "protocol_spec_digest": text_digest(SPEC_PATH),
        "runtime": {
            "implementation": platform.python_implementation(),
            "python_version": platform.python_version(),
            "platform": sys.platform,
            "machine": platform.machine(),
            "uv_lock_digest": text_digest(REPO_ROOT / "backend" / "uv.lock"),
        },
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seeds", type=int, nargs="+", default=REFERENCE_SEEDS)
    parser.add_argument("--horizons-days", type=int, nargs="+", default=REFERENCE_HORIZONS_DAYS)
    parser.add_argument("--scenarios", nargs="+", choices=[scenario.id for scenario in SCENARIOS],
                        default=[scenario.id for scenario in SCENARIOS])
    parser.add_argument("--require-clean", action="store_true")
    args = parser.parse_args(argv)
    if any(seed < 0 for seed in args.seeds) or any(days not in range(1, 31) for days in args.horizons_days):
        parser.error("Seeds must be nonnegative; horizons must be in [1, 30] days.")
    try:
        manifest = provenance(SITE, require_clean=args.require_clean)
    except ValueError as error:
        parser.error(str(error))
    trials = [
        asdict(run_trial_pair(SITE, scenario_id, seed, days))
        for scenario_id in args.scenarios for seed in args.seeds for days in args.horizons_days
    ]
    final_manifest = provenance(SITE, require_clean=args.require_clean)
    if final_manifest != manifest:
        raise RuntimeError("Evaluation provenance changed during the sweep; discard the results and rerun.")
    artifact = {
        "data_mode": "SIMULATED",
        "evaluation_mode": "STARTUP_FAULT",
        "dt_s": DT_S,
        "provenance": manifest,
        "trials": trials,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(trials)} paired trials to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
