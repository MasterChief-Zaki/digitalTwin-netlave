"""Reporting preserves historical provenance and cannot overwrite raw trials."""

import hashlib
import json
from pathlib import Path

import pytest

from scenarios.validation_report import write_report


def test_report_keeps_recorded_commit_and_raw_artifact_hash(tmp_path: Path) -> None:
    raw = tmp_path / "raw.json"
    accounts = {key: 0.0 for key in ("reservoir_m3", "soil_m3", "electrical_bus_kwh", "battery_cells_kwh")}
    artifact = {
        "data_mode": "SIMULATED", "protocol_version": "rca-paired-v2",
        "provenance": {"git_commit": "recorded-commit", "working_tree_dirty": False},
        "default_policy_promoted": False, "water_only": False,
        "trials": [{"reference": {"account_residuals": accounts}, "candidate": {"account_residuals": accounts}}],
        "summaries": [{"scenario_id": "baseline", "profile_id": "nominal", "zone_id": "C",
                       "service_noninferiority": "INCONCLUSIVE", "additional_et_deficit_mm": {"mean": 0.2, "upper_bound": 0.3}}],
    }
    raw.write_text(json.dumps(artifact), encoding="utf-8")
    contents = raw.read_bytes()
    output = tmp_path / "reports"
    write_report(raw, output)
    report = json.loads((output / "raw.json").read_text(encoding="utf-8"))
    assert report["provenance"]["git_commit"] == "recorded-commit"
    assert report["raw_artifact_sha256"] == hashlib.sha256(contents).hexdigest()
    assert report["all_service_endpoints_pass"] is False
    assert "trials" not in report
    assert raw.read_bytes() == contents
    with pytest.raises(ValueError, match="overwrite"):
        write_report(raw, tmp_path)
