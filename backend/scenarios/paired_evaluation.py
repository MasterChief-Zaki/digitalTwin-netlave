"""Matched-state trials and pre-registered paired bootstrap non-inferiority bounds.

No live service and no controller access to future realized solar. Held-out
profiles alter the simulated input in the engine, not an evaluation outcome.
"""

import argparse
import json
import math
import random
import statistics
from dataclasses import asdict, dataclass
from pathlib import Path

import schemas
from config import SITE, STEPS_PER_DAY, SiteConfig
from scenarios.presets import SCENARIOS, build_scenario
from scenarios.rca_trials import TrialPolicyResult, provenance, run_trial_policy, json_model
from twin.engine import step
from twin.state import SimState, reset_accounts

PROTOCOL = "rca-paired-v2"
VALIDATION_SEEDS = tuple(range(100, 120))
PROFILE_IDS = ("nominal", "shifted_sun", "cloud_pulses", "three_day_dark")
BOOTSTRAP_REPLICATES = 20000
BOOTSTRAP_SEED = 20261023


@dataclass(frozen=True)
class PairedTrial:
    scenario_id: schemas.ScenarioId
    profile_id: str
    seed: int
    warmup_days: int
    measurement_start_step: int
    measurement_end_step: int
    reference: TrialPolicyResult
    candidate: TrialPolicyResult


def matched_initial_state(cfg: SiteConfig, scenario_id: schemas.ScenarioId, seed: int, warmup_days: int) -> SimState:
    if warmup_days not in (0, 5, 10, 20):
        raise ValueError("Warm-up must be 0, 5, 10 or 20 days.")
    state = build_scenario(cfg, scenario_id, seed, "FIXED_TIMER")
    # The one-time fault belongs to the measured window, not preconditioning.
    if scenario_id == "tse_interrupt":
        state.environment.inflow_outage_steps = None
    for _ in range(warmup_days * STEPS_PER_DAY):
        state = step(state, cfg).state
    if scenario_id == "tse_interrupt":
        state.environment.inflow_outage_steps = (state.step + 30, state.step + 390)
    for zone in state.zones:
        zone.valve_open = False
        zone.irrigation_latched = False
        zone.requested_flow_m3_s = zone.delivered_flow_m3_s = 0.0
    state.pump.running = False
    reset_accounts(state, cfg)
    return state


def run_paired_trial(
    cfg: SiteConfig, scenario_id: schemas.ScenarioId, seed: int, horizon_days: int = 30,
    warmup_days: int = 10, profile_id: str = "nominal",
    candidate_policy: schemas.ControlPolicy = "SMART_HYSTERESIS",
) -> PairedTrial:
    if profile_id not in PROFILE_IDS:
        raise ValueError("Unknown held-out solar profile.")
    initial = matched_initial_state(cfg, scenario_id, seed, warmup_days)
    initial.environment.solar_profile_id = profile_id
    initial.environment.profile_start_step = initial.step
    reference = run_trial_policy(cfg, scenario_id, seed, horizon_days, "SMART_HYSTERESIS", initial)
    candidate = run_trial_policy(cfg, scenario_id, seed, horizon_days, candidate_policy, initial)
    if reference.input_digest != candidate.input_digest or reference.initial_state_digest != candidate.initial_state_digest:
        raise ValueError("Paired trials are not matched.")
    return PairedTrial(scenario_id, profile_id, seed, warmup_days, initial.step,
                       initial.step + horizon_days * STEPS_PER_DAY, reference, candidate)


def paired_interval(differences: list[float], endpoint_count: int, replicates: int = BOOTSTRAP_REPLICATES) -> dict[str, float | int]:
    if len(differences) < 2 or endpoint_count < 1 or replicates < 100:
        raise ValueError("Paired intervals require >=2 seeds, >=1 endpoint and >=100 replicates.")
    if not all(math.isfinite(value) for value in differences):
        raise ValueError("Effects must be finite.")
    generator = random.Random(BOOTSTRAP_SEED)
    count = len(differences)
    means = sorted(statistics.fmean(generator.choices(differences, k=count)) for _ in range(replicates))
    alpha = 0.05 / endpoint_count
    return {
        "mean": statistics.fmean(differences),
        "standard_deviation": statistics.stdev(differences),
        "minimum": min(differences), "maximum": max(differences),
        "lower_bound": means[min(replicates - 1, math.floor(alpha * replicates))],
        "upper_bound": means[min(replicates - 1, math.ceil((1.0 - alpha) * replicates) - 1)],
        "negative_count": sum(value < 0 for value in differences), "seed_count": count,
    }


def summarize(trials: list[PairedTrial]) -> list[dict[str, object]]:
    groups = sorted({(trial.scenario_id, trial.profile_id, trial.warmup_days) for trial in trials})
    endpoint_count = len(groups) * len(SITE.zones) * 2
    summaries: list[dict[str, object]] = []
    for scenario_id, profile_id, warmup_days in groups:
        paired = [trial for trial in trials if (trial.scenario_id, trial.profile_id, trial.warmup_days) == (scenario_id, profile_id, warmup_days)]
        for zone_index, zone_cfg in enumerate(SITE.zones):
            deficits = [trial.candidate.zones[zone_index].et_deficit_mm - trial.reference.zones[zone_index].et_deficit_mm for trial in paired]
            degradation = [
                (trial.candidate.zones[zone_index].et_deficit_m3 - trial.reference.zones[zone_index].et_deficit_m3)
                / trial.reference.zones[zone_index].potential_et_m3
                for trial in paired
            ]
            deficit_interval = paired_interval(deficits, endpoint_count)
            service_interval = paired_interval(degradation, endpoint_count)
            pass_service = deficit_interval["upper_bound"] <= 0.10 and service_interval["upper_bound"] <= 0.005
            summaries.append({
                "scenario_id": scenario_id, "profile_id": profile_id, "warmup_days": warmup_days,
                "zone_id": zone_cfg.zone_id, "additional_et_deficit_mm": deficit_interval,
                "et_service_degradation_fraction": service_interval,
                "service_noninferiority": "PASS" if pass_service and len(paired) >= 20 else "INCONCLUSIVE",
                "water_delivery_difference_m3": statistics.fmean(
                    trial.candidate.metrics.irrigation_delivered_m3 - trial.reference.metrics.irrigation_delivered_m3 for trial in paired),
                "stock_adjusted_delivery_difference_m3": statistics.fmean(
                    trial.candidate.soil_stock_adjusted_delivery_m3 - trial.reference.soil_stock_adjusted_delivery_m3 for trial in paired),
            })
    return summaries


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seeds", nargs="+", type=int, default=VALIDATION_SEEDS)
    parser.add_argument("--horizon-days", type=int, default=30)
    parser.add_argument("--warmup-days", nargs="+", type=int, choices=(0, 5, 10, 20), default=[10])
    parser.add_argument("--profiles", nargs="+", choices=PROFILE_IDS, default=PROFILE_IDS)
    parser.add_argument("--candidate", choices=("SMART_HYSTERESIS", "SMART_RESOURCE_AWARE"), default="SMART_RESOURCE_AWARE")
    parser.add_argument("--require-clean", action="store_true")
    args = parser.parse_args()
    manifest = provenance(SITE, args.require_clean)
    trials = [run_paired_trial(SITE, scenario.id, seed, args.horizon_days, warmup, profile, args.candidate)
              for scenario in SCENARIOS for profile in args.profiles for warmup in args.warmup_days for seed in args.seeds]
    if provenance(SITE, args.require_clean) != manifest:
        raise RuntimeError("Sources changed during validation.")
    artifact = {"data_mode": "SIMULATED", "protocol_version": PROTOCOL, "provenance": manifest,
                "summaries": summarize(trials), "trials": [asdict(trial) for trial in trials],
                "default_policy_promoted": False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, indent=2, sort_keys=True, allow_nan=False, default=json_model) + "\n", encoding="utf-8")
    print(f"Wrote {len(trials)} paired validation trials to {args.output}")


if __name__ == "__main__":
    main()
