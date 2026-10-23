"""Synthetic P1 fixed-flow derating, energy, pipe and filter candidate study.

No invented pump curve, no default SITE modification and no hardware approval.
Each candidate runs both original policies on identical hardware and inputs.
"""

import argparse
import json
from dataclasses import asdict, replace
from pathlib import Path

from config import SITE, SiteConfig
from models.filtration import filter_head_loss_m
from models.hydraulics import gravity_head, pump_requirement
from models.water_soil import surface_elevation_m
from scenarios.rca_trials import json_model, provenance, run_trial_pair


def candidates() -> dict[str, SiteConfig]:
    return {
        "reference": SITE,
        "pump_derated_18_m3_h": replace(SITE, zones=tuple(replace(zone, max_flow_m3_h=18.0) if zone.zone_id == "C" else zone for zone in SITE.zones)),
        "solar_12_kwp": replace(SITE, energy=replace(SITE.energy, solar_peak_w=12000.0)),
        "battery_30_kwh": replace(SITE, energy=replace(SITE.energy, battery_capacity_kwh=30.0)),
        "zone_b_pipe_025_m": replace(SITE, zones=tuple(replace(zone, mainline_diameter_m=0.25) if zone.zone_id == "B" else zone for zone in SITE.zones)),
        "filter_loading_halved": replace(SITE, filtration=replace(SITE.filtration, clog_per_filtered_m3=SITE.filtration.clog_per_filtered_m3 / 2.0)),
    }


def hydraulic_margins(cfg: SiteConfig) -> dict[str, float]:
    clogged_head = filter_head_loss_m(cfg.filtration.flush_threshold, cfg.filtration)
    dead_surface = surface_elevation_m(cfg.reservoir.dead_volume_m3, cfg.reservoir)
    full_surface = surface_elevation_m(cfg.reservoir.capacity_m3, cfg.reservoir)
    zone_b, zone_c = cfg.zones[1], cfg.zones[2]
    pump = pump_requirement(zone_c, dead_surface, clogged_head, zone_c.max_flow_m3_s, cfg.hydraulics)
    gravity = gravity_head(zone_b, full_surface, clogged_head, zone_b.max_flow_m3_s, cfg.hydraulics)
    return {"worst_case_pump_power_w": pump.power_w,
            "pump_margin_fraction": 1.0 - pump.power_w / cfg.hydraulics.pump_power_limit_w,
            "zone_b_full_clogged_head_margin_m": gravity.available_m - gravity.required_m}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--horizon-days", type=int, default=30)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()
    manifest = provenance(SITE)
    studies = []
    for name, cfg in candidates().items():
        for scenario in ("low_solar", "clogged_filter"):
            pair = run_trial_pair(cfg, scenario, args.seed, args.horizon_days)
            studies.append({"candidate": name, "configuration": asdict(cfg), "hydraulic_margins": hydraulic_margins(cfg), "trial": asdict(pair)})
    if provenance(SITE) != manifest:
        raise RuntimeError("Sources changed during design study.")
    artifact = {"data_mode": "SIMULATED", "provenance": manifest, "studies": studies,
                "deployment_approved": False,
                "limitations": "Fixed-flow derating only; measured pump curve and site/compliance review required."}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, indent=2, sort_keys=True, allow_nan=False, default=json_model) + "\n", encoding="utf-8")
    print(f"Wrote {len(studies)} design comparisons to {args.output}")


if __name__ == "__main__":
    main()
