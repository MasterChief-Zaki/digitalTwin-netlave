"""Service accounting is engine-owned and independent of event deduplication."""

import math

from config import SITE
from scenarios.presets import build_scenario
from twin.engine import step
from twin.state import reset_accounts, to_snapshot


def test_zone_accounts_reconcile_with_site_and_root_zone_stocks() -> None:
    state = build_scenario(SITE, "low_solar", seed=7)
    for _ in range(1440):
        state = step(state, SITE).state
    snapshot = to_snapshot(state, SITE, 0, 0)
    for key in ("irrigation_delivered_m3", "potential_et_m3", "actual_et_m3"):
        assert math.isclose(sum(getattr(zone.service, key) for zone in snapshot.zones), getattr(state.metrics, key), abs_tol=1e-8)
    assert snapshot.diagnostics.electrical_autonomy_0_1 == 1.0
    pumped = snapshot.zones[2].service
    assert pumped.et_deficit_mm > 0
    assert pumped.below_trigger_min == 1440
    assert pumped.denied_by_reason_min["BATTERY_BELOW_RESERVE"] > 100
    for zone, zone_cfg in zip(snapshot.zones, SITE.zones, strict=True):
        service = zone.service
        change = service.final_root_zone_storage_m3 - service.initial_root_zone_storage_m3
        # This one-day low-solar run has no drainage in C; account for measured site drainage separately elsewhere.
        if zone.id == "C":
            assert math.isclose(change, service.irrigation_delivered_m3 * SITE.soil.application_efficiency - service.actual_et_m3, abs_tol=1e-8)
        assert math.isclose(service.final_root_zone_storage_m3, zone.soil_moisture_m3_m3 * zone_cfg.area_m2 * SITE.soil.root_depth_m)


def test_below_trigger_uses_strict_pre_step_entry_threshold() -> None:
    state = build_scenario(SITE, "baseline", seed=7)
    state.zones[0].theta_m3_m3 = SITE.soil.theta_on_m3_m3
    reset_accounts(state, SITE)
    result = step(state, SITE).state
    assert result.zones[0].accounts.below_trigger_min == 0
    assert result.zones[1].accounts.below_trigger_min == 1


def test_clone_owns_nested_service_dictionaries() -> None:
    original = build_scenario(SITE, "baseline", seed=7)
    copied = original.clone()
    copied.zones[0].accounts.denied_by_reason_min["RESERVOIR_LOW"] = 1
    copied.zones[0].accounts.deferred_by_reason_min["WAIT"] = 1
    assert not original.zones[0].accounts.denied_by_reason_min
    assert not original.zones[0].accounts.deferred_by_reason_min


def test_measured_reset_keeps_physics_and_clock_but_discards_accounts() -> None:
    state = build_scenario(SITE, "baseline", seed=7)
    for _ in range(60):
        state = step(state, SITE).state
    volume, energy, moisture, clock = state.reservoir_volume_m3, state.battery_energy_j, state.zones[0].theta_m3_m3, state.step
    reset_accounts(state, SITE)
    assert (state.reservoir_volume_m3, state.battery_energy_j, state.zones[0].theta_m3_m3, state.step) == (volume, energy, moisture, clock)
    assert state.metrics.irrigation_delivered_m3 == 0
    assert state.zones[0].accounts.irrigation_delivered_m3 == 0
    assert state.initial_reservoir_volume_m3 == volume
