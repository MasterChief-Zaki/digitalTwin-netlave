"""Reference reproducibility, accounting semantics and private trial isolation."""

import json
import math
import subprocess
from dataclasses import asdict, replace
from pathlib import Path

import pytest

import schemas
import scenarios.rca_trials as rca_trials
from config import DT_S, SITE, STEPS_PER_DAY
from scenarios.comparison import run_comparison
from scenarios.evaluation import (
    ENERGY_TOLERANCE_KWH,
    PROTOCOL_VERSION,
    REFERENCE_COMMIT,
    WATER_TOLERANCE_M3,
    EvaluationBalanceError,
    battery_equivalent_full_cycles,
    stock_adjusted_delivery_m3,
)
from scenarios.presets import SCENARIOS, build_scenario
from scenarios.rca_trials import (
    REPO_ROOT,
    Stocks,
    ZoneStock,
    assert_accounts,
    capture_stocks,
    json_digest,
    main,
    provenance,
    run_trial_pair,
    run_trial_policy,
    source_digest,
    text_digest,
)
from twin.engine import step
from twin.state import Metrics, physical_digest, to_snapshot

REFERENCE_PATH = Path(__file__).parent / "fixtures" / "rca-reference.json"
# Every numeric field in the old comparison export has an explicit unit mapping.
HISTORICAL_FLOAT_UNITS = {
    "tse_inflow_m3": "m3",
    "irrigation_delivered_m3": "m3",
    "requested_undelivered_m3": "m3",
    "potential_et_m3": "m3",
    "actual_et_m3": "m3",
    "et_deficit_m3": "m3",
    "et_deficit_mm": "mm",
    "deep_percolation_m3": "m3",
    "overflow_m3": "m3",
    "flush_water_m3": "m3",
    "pump_energy_kwh": "kwh",
    "pump_kwh_per_delivered_m3": "kwh/m3",
    "required_electrical_kwh": "kwh",
    "unserved_kwh": "kwh",
    "electrical_autonomy_0_1": "fraction",
    "final_battery_soc_0_1": "fraction",
    "final_mean_moisture_m3_m3": "moisture",
}


def test_historical_reference_is_pinned_to_code_and_configuration() -> None:
    reference = json.loads(REFERENCE_PATH.read_text(encoding="utf-8"))
    manifest = reference["provenance"]
    assert manifest["git_commit"] == REFERENCE_COMMIT
    historical_config = asdict(SITE)
    historical_config.pop("scheduler")
    assert manifest["configuration_digest"] == json_digest(historical_config)
    assert manifest["runtime"]["uv_lock_digest"] == text_digest(REPO_ROOT / "backend" / "uv.lock")
    assert {trial["scenario_id"] for trial in reference["trials"]} == {scenario.id for scenario in SCENARIOS}


@pytest.mark.parametrize("scenario_id", [scenario.id for scenario in SCENARIOS])
def test_primary_results_reproduce_the_pinned_commit(scenario_id: schemas.ScenarioId) -> None:
    reference = json.loads(REFERENCE_PATH.read_text(encoding="utf-8"))
    expected = next(trial for trial in reference["trials"] if trial["scenario_id"] == scenario_id)
    actual = asdict(run_comparison(SITE, scenario_id, seed=7, horizon_days=14))
    assert actual["scenario_id"] == expected["scenario_id"]
    assert actual["seed"] == expected["seed"]
    assert actual["horizon_days"] == expected["horizon_days"]
    assert actual["steps"] == expected["steps"]
    assert math.isclose(actual["water_savings_fraction"], expected["water_savings_fraction"],
                        abs_tol=1e-12, rel_tol=1e-9)
    for policy in ("fixed_timer", "smart_hysteresis"):
        assert expected[policy].keys() <= actual[policy].keys()
        float_fields = {name for name, value in expected[policy].items() if isinstance(value, float)}
        assert float_fields == HISTORICAL_FLOAT_UNITS.keys()
        for name in expected[policy]:
            value = actual[policy][name]
            if isinstance(value, float):
                unit = HISTORICAL_FLOAT_UNITS[name]
                absolute = 1e-6 if unit in ("m3", "kwh") else 1e-12
                assert math.isclose(value, expected[policy][name], abs_tol=absolute, rel_tol=1e-9), name
            else:
                assert value == expected[policy][name], name


@pytest.mark.parametrize("scenario_id", [scenario.id for scenario in SCENARIOS])
def test_trial_pairs_match_inputs_and_close_all_accounts(scenario_id: schemas.ScenarioId) -> None:
    pair = run_trial_pair(SITE, scenario_id, seed=7, horizon_days=1)
    assert pair.measurement_start_step == 0
    assert pair.measurement_end_step == STEPS_PER_DAY
    assert pair.fixed_timer.input_digest == pair.smart_hysteresis.input_digest
    assert pair.fixed_timer.initial_state_digest == pair.smart_hysteresis.initial_state_digest
    for result in (pair.fixed_timer, pair.smart_hysteresis):
        assert abs(result.account_residuals.reservoir_m3) < WATER_TOLERANCE_M3.absolute
        assert abs(result.account_residuals.soil_m3) < WATER_TOLERANCE_M3.absolute
        assert abs(result.account_residuals.electrical_bus_kwh) < ENERGY_TOLERANCE_KWH.absolute
        assert abs(result.account_residuals.battery_cells_kwh) < ENERGY_TOLERANCE_KWH.absolute
        assert result.minimum_reservoir_volume_m3 <= result.initial_stocks.reservoir_volume_m3
        assert result.minimum_battery_soc_0_1 <= result.initial_stocks.battery_energy_j / SITE.energy.battery_capacity_j
        soil_change_m3 = result.final_stocks.soil_storage_m3 - result.initial_stocks.soil_storage_m3
        assert result.soil_stock_adjusted_delivery_m3 == stock_adjusted_delivery_m3(
            result.metrics.irrigation_delivered_m3, soil_change_m3, SITE.soil.application_efficiency,
        )


def test_trial_replay_is_exact_and_separate_runs_own_their_metrics() -> None:
    first = run_trial_pair(SITE, "baseline", seed=11, horizon_days=1)
    second = run_trial_pair(SITE, "baseline", seed=11, horizon_days=1)
    assert first == second
    assert first.fixed_timer.metrics is not second.fixed_timer.metrics
    assert first.fixed_timer.metrics is not first.smart_hysteresis.metrics


def test_trial_accounts_agree_with_existing_comparison() -> None:
    pair = run_trial_pair(SITE, "baseline", seed=7, horizon_days=1)
    comparison = run_comparison(SITE, "baseline", seed=7, horizon_days=1)
    for trial, report in ((pair.fixed_timer, comparison.fixed_timer), (pair.smart_hysteresis, comparison.smart_hysteresis)):
        assert trial.input_digest == report.input_digest
        assert trial.metrics.irrigation_delivered_m3 == report.irrigation_delivered_m3
        assert trial.metrics.pump_energy_j / 3.6e6 == report.pump_energy_kwh


def test_root_zone_stock_uses_configured_depth_and_area() -> None:
    state = build_scenario(SITE, "baseline", seed=7)
    cfg = replace(SITE, soil=replace(SITE.soil, root_depth_m=0.4))
    stocks = capture_stocks(state, cfg)
    assert stocks.soil_storage_m3 == sum(zone.area_m2 * 0.4 * 0.165 for zone in cfg.zones)


def test_stock_adjustment_removes_accumulation_and_restores_mined_water() -> None:
    efficiency = SITE.soil.application_efficiency
    delivered_m3 = 100.0
    assert stock_adjusted_delivery_m3(delivered_m3, 9.0, efficiency) == 90.0
    assert stock_adjusted_delivery_m3(delivered_m3, -9.0, efficiency) == 110.0
    assert stock_adjusted_delivery_m3(90.0, -9.0, efficiency) == delivered_m3
    for invalid_efficiency in (0.0, -0.1, 1.1, float("nan")):
        with pytest.raises(ValueError):
            stock_adjusted_delivery_m3(delivered_m3, 0.0, invalid_efficiency)


def test_cycle_convention_counts_cell_discharge_not_double_throughput() -> None:
    capacity_j = SITE.energy.battery_capacity_j
    efficiency = SITE.energy.battery_discharge_efficiency
    assert battery_equivalent_full_cycles(capacity_j * efficiency, capacity_j, efficiency) == 1.0
    assert battery_equivalent_full_cycles(0.0, capacity_j, efficiency) == 0.0


@pytest.mark.parametrize("field_name", [
    "irrigation_delivered_m3", "application_loss_m3", "battery_losses_j", "solar_energy_j",
])
def test_cumulative_accounts_reject_drift(field_name: str) -> None:
    stocks = Stocks(900.0, 1e7, (ZoneStock("A", 1000.0),))
    metrics = Metrics()
    setattr(metrics, field_name, 1.0 if field_name.endswith("m3") else 3.6e6)
    with pytest.raises(EvaluationBalanceError):
        assert_accounts(stocks, stocks, metrics)


@pytest.mark.parametrize("invalid", [float("inf"), float("-inf"), float("nan")])
def test_account_tolerance_rejects_nonfinite_values(invalid: float) -> None:
    with pytest.raises(EvaluationBalanceError):
        WATER_TOLERANCE_M3.assert_close("invalid", invalid, invalid)


def test_clone_and_step_do_not_alias_nested_mutable_state() -> None:
    original = build_scenario(SITE, "baseline", seed=7)
    before = to_snapshot(original, SITE, run_generation=0, latest_event_id=0)
    copied = original.clone()
    assert copied is not original
    for field_name in ("zones", "filter", "environment", "power", "pump", "metrics", "decisions"):
        assert getattr(copied, field_name) is not getattr(original, field_name)
    for copied_zone, original_zone in zip(copied.zones, original.zones, strict=True):
        assert copied_zone is not original_zone
    copied.zones[0].theta_m3_m3 = 0.20
    copied.filter.clog_index = 0.5
    copied.environment.cloud_factor = 0.25
    copied.power.solar_power_w = 10.0
    copied.pump.running = True
    copied.metrics.irrigation_delivered_m3 = 20.0
    copied.decisions.clear()
    stepped = step(original, SITE).state
    assert stepped.step == 1
    assert physical_digest(to_snapshot(original, SITE, 0, 0)) == physical_digest(before)


def test_tse_outage_is_scored_not_discarded() -> None:
    pair = run_trial_pair(SITE, "tse_interrupt", seed=7, horizon_days=1)
    baseline = run_trial_policy(SITE, "baseline", seed=7, horizon_days=1, policy="FIXED_TIMER")
    assert pair.measurement_start_step == 0
    assert pair.fixed_timer.metrics.tse_inflow_m3 < baseline.metrics.tse_inflow_m3
    assert pair.fixed_timer.metrics.hydro_energy_j < baseline.metrics.hydro_energy_j


def test_provenance_records_code_config_protocol_and_runtime() -> None:
    manifest = provenance(SITE)
    assert len(manifest["git_commit"]) == 40
    assert manifest["reference_commit"] == REFERENCE_COMMIT
    assert manifest["protocol_version"] == PROTOCOL_VERSION
    assert manifest["configuration_digest"] == json_digest(asdict(SITE))
    assert manifest["source_digest"] == source_digest(REPO_ROOT)
    assert manifest["protocol_spec_digest"] == text_digest(REPO_ROOT / "docs" / "rca" / "evaluation-spec.md")
    assert manifest["runtime"]["implementation"] == "CPython"


def test_source_hash_covers_source_paths_contents_locks_and_spec(tmp_path: Path) -> None:
    backend = tmp_path / "backend"
    backend.mkdir()
    for name in ("engine.py", "pyproject.toml", "uv.lock", ".python-version"):
        (backend / name).write_text("reference", encoding="utf-8")
    spec = tmp_path / "docs" / "rca" / "evaluation-spec.md"
    spec.parent.mkdir(parents=True)
    spec.write_text("protocol", encoding="utf-8")
    initial = source_digest(tmp_path)
    (backend / "engine.py").write_text("changed", encoding="utf-8")
    assert source_digest(tmp_path) != initial
    (backend / "engine.py").write_text("reference", encoding="utf-8")
    assert source_digest(tmp_path) == initial
    (backend / "engine.py").write_bytes(b"reference\r\n")
    with_crlf = source_digest(tmp_path)
    (backend / "engine.py").write_bytes(b"reference\n")
    assert source_digest(tmp_path) == with_crlf
    (backend / "engine.py").write_text("reference", encoding="utf-8")
    environment = backend / ".venv"
    environment.mkdir()
    (environment / "ignored.py").write_text("runtime", encoding="utf-8")
    assert source_digest(tmp_path) == initial
    (backend / "engine.py").rename(backend / "renamed.py")
    assert source_digest(tmp_path) != initial


def test_clean_publication_rejects_a_dirty_working_tree(monkeypatch: pytest.MonkeyPatch) -> None:
    def git_response(*arguments: object, **options: object) -> subprocess.CompletedProcess[str]:
        command = arguments[0]
        output = REFERENCE_COMMIT if command == ["git", "rev-parse", "HEAD"] else " M backend/config.py\n"
        return subprocess.CompletedProcess(args=command, returncode=0, stdout=output, stderr="")

    monkeypatch.setattr(rca_trials.subprocess, "run", git_response)
    assert provenance(SITE)["working_tree_dirty"] is True
    with pytest.raises(ValueError, match="clean working tree"):
        provenance(SITE, require_clean=True)


def test_cli_discards_results_if_provenance_changes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0

    def changed_provenance(*arguments: object, **options: object) -> dict[str, object]:
        nonlocal calls
        calls += 1
        return {"source_digest": "before" if calls == 1 else "after"}

    monkeypatch.setattr(rca_trials, "provenance", changed_provenance)
    output = tmp_path / "changed.json"
    with pytest.raises(RuntimeError, match="provenance changed"):
        main(["--output", str(output), "--scenarios", "baseline", "--seeds", "7", "--horizons-days", "1"])
    assert not output.exists()


def test_cli_writes_strict_json_without_wall_time(tmp_path: Path) -> None:
    output = tmp_path / "nested" / "trials.json"
    assert main(["--output", str(output), "--scenarios", "baseline", "--seeds", "7", "--horizons-days", "1"]) == 0
    artifact = json.loads(output.read_text(encoding="utf-8"))
    assert artifact["data_mode"] == "SIMULATED"
    assert artifact["evaluation_mode"] == "STARTUP_FAULT"
    assert artifact["dt_s"] == DT_S
    assert len(artifact["trials"]) == 1
    assert "elapsed_s" not in output.read_text(encoding="utf-8")


@pytest.mark.parametrize("arguments", [["--seeds", "-1"], ["--horizons-days", "0"], ["--horizons-days", "31"]])
def test_cli_rejects_invalid_runs_without_writing_output(tmp_path: Path, arguments: list[str]) -> None:
    output = tmp_path / "invalid.json"
    with pytest.raises(SystemExit) as error:
        main(["--output", str(output), *arguments])
    assert error.value.code == 2
    assert not output.exists()
