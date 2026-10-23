"""Build auditable paired-validation summaries from recorded raw trial artifacts.

Reporting never reruns physics or silently replaces the raw artifact's provenance.
Run with uv --directory backend run python -m scenarios.validation_report
    --input ../artifacts/rca/combined-validation.json --output-directory ../docs/rca/validation
"""

import argparse
import hashlib
import json
from pathlib import Path


def write_report(artifact_path: Path, output_directory: Path) -> None:
    contents = artifact_path.read_bytes()
    artifact = json.loads(contents)
    if artifact.get("data_mode") != "SIMULATED" or artifact.get("protocol_version") != "rca-paired-v2":
        raise ValueError("Expected a simulated paired-v2 validation artifact.")
    if artifact.get("default_policy_promoted") is not False:
        raise ValueError("Reports cannot promote the default policy.")
    trials = artifact["trials"]
    if not trials or not artifact["summaries"]:
        raise ValueError("A validation report requires recorded trials and summaries.")
    summary = {key: value for key, value in artifact.items() if key != "trials"}
    summary["raw_artifact_sha256"] = hashlib.sha256(contents).hexdigest()
    summary["trial_count"] = len(trials)
    summary["all_service_endpoints_pass"] = all(
        item["service_noninferiority"] == "PASS" for item in artifact["summaries"]
    )
    summary["maximum_absolute_account_residuals"] = {
        account: max(abs(trial[policy]["account_residuals"][account]) for trial in trials for policy in ("reference", "candidate"))
        for account in ("reservoir_m3", "soil_m3", "electrical_bus_kwh", "battery_cells_kwh")
    }
    output_directory.mkdir(parents=True, exist_ok=True)
    output_path = output_directory / artifact_path.name
    if output_path.resolve() == artifact_path.resolve():
        raise ValueError("Report output must not overwrite raw trials.")
    output_path.write_text(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    title = "Water-only scheduler validation" if artifact["water_only"] else "Combined water and energy validation"
    passed = sum(item["service_noninferiority"] == "PASS" for item in artifact["summaries"])
    lines = [
        f"# {title}", "", "**Decision: no automatic default-policy promotion.**", "",
        f"Recorded trial commit: `{artifact['provenance']['git_commit']}`.",
        f"Working tree dirty during trials: `{artifact['provenance']['working_tree_dirty']}`.",
        f"{len(trials)} paired trials; {passed}/{len(artifact['summaries'])} service endpoints pass.",
        "", "These are simulated model results, not field measurements. See the paired",
        "protocol and design/deployment boundary; a service PASS is not hardware approval.", "",
        "| Scenario | Profile | Zone | Mean extra ET deficit (mm) | Upper bound (mm) | Result |",
        "| --- | --- | --- | ---: | ---: | --- |",
    ]
    for item in artifact["summaries"]:
        interval = item["additional_et_deficit_mm"]
        lines.append(
            f"| {item['scenario_id']} | {item['profile_id']} | {item['zone_id']} | "
            f"{interval['mean']:.6f} | {interval['upper_bound']:.6f} | {item['service_noninferiority']} |"
        )
    lines.extend(["", "The JSON companion preserves protocol/config/runtime/source provenance, paired",
                  "effect intervals, residuals and the SHA-256 of the raw artifact. It does not",
                  "rewrite trial provenance to the reporting commit. Raw trials remain in",
                  "ignored artifacts/rca/. No threshold relaxation or policy promotion is implied.", ""])
    output_path.with_suffix(".md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output-directory", required=True, type=Path)
    args = parser.parse_args()
    write_report(args.input, args.output_directory)


if __name__ == "__main__":
    main()
