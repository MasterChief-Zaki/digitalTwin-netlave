"""Keep the static cross-site reference aligned with the physical authority."""

import json
from pathlib import Path

import pytest

from config import DT_S, GRAVITY_M_S2, SITE, WATER_DENSITY_KG_M3
from scenarios.presets import SCENARIOS


def test_shared_site_assumptions_match_python_authority() -> None:
    reference = json.loads(
        (Path(__file__).parents[2] / "src/content/ground-truth.json").read_text(encoding="utf-8")
    )
    assumptions = reference["siteAssumptions"]
    expected = {
        "forestAreaHa": sum(zone.area_m2 for zone in SITE.zones) / 10_000,
        "reservoirCapacityM3": SITE.reservoir.capacity_m3,
        "initialReservoirM3": SITE.reservoir.initial_volume_m3,
        "meanInflowM3Hour": SITE.supply.tse_mean_inflow_m3_h,
        "solarCapacityKwp": SITE.energy.solar_peak_w / 1000,
        "batteryCapacityKwh": SITE.energy.battery_capacity_kwh,
        "pumpLimitKw": SITE.hydraulics.pump_power_limit_w / 1000,
        "hydroHeadM": SITE.supply.hydro_recoverable_head_m,
        "gravityManifoldM3Hour": SITE.hydraulics.gravity_manifold_limit_m3_h,
        "moistureStartM3M3": SITE.soil.theta_on_m3_m3,
        "moistureStopM3M3": SITE.soil.theta_off_m3_m3,
        "pumpReserveSoc": SITE.energy.pump_reserve_soc,
        "stepSeconds": DT_S,
    }
    for key, value in expected.items():
        assert assumptions[key] == pytest.approx(value), key
    hydro_w = (
        WATER_DENSITY_KG_M3
        * GRAVITY_M_S2
        * SITE.supply.tse_mean_inflow_m3_h / 3600
        * SITE.supply.hydro_recoverable_head_m
        * SITE.supply.hydro_turbine_efficiency
    )
    assert assumptions["hydroPowerW"] == round(hydro_w)
    for published, zone in zip(reference["zones"], SITE.zones, strict=True):
        assert published["id"] == zone.zone_id
        assert published["areaHa"] == zone.area_m2 / 10_000
        assert published["feed"].upper() == zone.feed_mode
        assert published["elevationM"] == zone.elevation_m
        assert published["maxFlowM3Hour"] == zone.max_flow_m3_h
    assert [scenario["id"] for scenario in reference["scenarios"]] == [scenario.id for scenario in SCENARIOS]
