"use client";

import { useState } from "react";
import { classNames } from "@/lib/classNames";
import { formatNumber, formatPercent } from "@/lib/format";
import { simulationApi } from "@/services/api";
import { useTwinStore } from "@/store/useTwinStore";
import buttonStyles from "@/styles/buttons.module.scss";
import type { CompareResponse, PolicyReport } from "@/types/simulation";
import { Panel } from "./Panel";
import styles from "./Compare.module.scss";

interface ReportRow {
  label: string;
  unit: string;
  fractionDigits: number;
  read: (report: PolicyReport) => number;
  // Which direction is better for a reader scanning the table; undefined = neither.
  lowerIsBetter?: boolean;
}

const reportRows: ReportRow[] = [
  {
    label: "Irrigation delivered",
    unit: "m³",
    fractionDigits: 0,
    read: (report) => report.irrigation_delivered_m3,
  },
  {
    label: "Requested, not delivered",
    unit: "m³",
    fractionDigits: 0,
    read: (report) => report.requested_undelivered_m3,
  },
  {
    label: "ET deficit (tree water stress)",
    unit: "mm",
    fractionDigits: 2,
    read: (report) => report.et_deficit_mm,
    lowerIsBetter: true,
  },
  {
    label: "Deep percolation",
    unit: "m³",
    fractionDigits: 0,
    read: (report) => report.deep_percolation_m3,
  },
  {
    label: "Overflow / diversion",
    unit: "m³",
    fractionDigits: 0,
    read: (report) => report.overflow_m3,
  },
  {
    label: "Pump energy",
    unit: "kWh",
    fractionDigits: 1,
    read: (report) => report.pump_energy_kwh,
    lowerIsBetter: true,
  },
  {
    label: "Pump energy per delivered m³",
    unit: "kWh/m³",
    fractionDigits: 3,
    read: (report) => report.pump_kwh_per_delivered_m3,
    lowerIsBetter: true,
  },
  {
    label: "Unserved electrical load",
    unit: "kWh",
    fractionDigits: 2,
    read: (report) => report.unserved_kwh,
    lowerIsBetter: true,
  },
  {
    label: "Electrical autonomy",
    unit: "%",
    fractionDigits: 1,
    read: (report) => report.electrical_autonomy_0_1 * 100,
  },
  {
    label: "Final battery",
    unit: "% SoC",
    fractionDigits: 0,
    read: (report) => report.final_battery_soc_0_1 * 100,
  },
  {
    label: "Filter flushes",
    unit: "",
    fractionDigits: 0,
    read: (report) => report.flush_count,
  },
];

function betterSide(row: ReportRow, fixed: number, smart: number) {
  if (row.lowerIsBetter === undefined || fixed === smart) {
    return null;
  }
  return smart < fixed === row.lowerIsBetter ? "smart" : "fixed";
}

function ReportTable({ report }: { report: CompareResponse }) {
  const { fixed_timer: fixed, smart_hysteresis: smart } = report;
  return (
    <div className={styles.tableScroll}>
      <table className={styles.reportTable}>
        <thead>
          <tr>
            <th scope="col">Simulated over {report.horizon_days} days</th>
            <th scope="col">Fixed timer</th>
            <th scope="col">Smart hysteresis</th>
          </tr>
        </thead>
        <tbody>
          {reportRows.map((row) => {
            const fixedValue = row.read(fixed);
            const smartValue = row.read(smart);
            const better = betterSide(row, fixedValue, smartValue);
            return (
              <tr key={row.label}>
                <th scope="row">{row.label}</th>
                <td
                  className={classNames(
                    better === "fixed" ? styles.better : undefined,
                  )}
                >
                  {formatNumber(fixedValue, row.fractionDigits)}{" "}
                  <span className={styles.unit}>{row.unit}</span>
                </td>
                <td
                  className={classNames(
                    better === "smart" ? styles.better : undefined,
                  )}
                >
                  {formatNumber(smartValue, row.fractionDigits)}{" "}
                  <span className={styles.unit}>{row.unit}</span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export function Compare() {
  const scenarioId = useTwinStore((state) => state.snapshot.scenario_id);
  const seed = useTwinStore((state) => state.snapshot.seed);
  const connection = useTwinStore((state) => state.connection);
  const [horizonDays, setHorizonDays] = useState(14);
  const [report, setReport] = useState<CompareResponse | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function runComparison() {
    setRunning(true);
    setError(null);
    try {
      setReport(
        await simulationApi.compare({
          scenario_id: scenarioId,
          seed,
          horizon_days: horizonDays,
        }),
      );
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "The comparison failed.",
      );
    } finally {
      setRunning(false);
    }
  }

  const sameInputs =
    report !== null &&
    report.fixed_timer.input_digest === report.smart_hysteresis.input_digest &&
    report.fixed_timer.initial_state_digest ===
      report.smart_hysteresis.initial_state_digest;

  return (
    <Panel
      label="07 — Experiment"
      title="Fixed timer versus smart hysteresis"
      headingId="compare-heading"
      actions={
        <form
          className={styles.controls}
          onSubmit={(event) => {
            event.preventDefault();
            void runComparison();
          }}
        >
          <label className={styles.field}>
            <span className={styles.fieldLabel}>Days</span>
            <input
              className={styles.daysInput}
              type="number"
              min={1}
              max={30}
              value={horizonDays}
              onChange={(event) => {
                setHorizonDays(
                  Math.min(
                    30,
                    Math.max(1, Math.trunc(Number(event.target.value))),
                  ),
                );
              }}
            />
          </label>
          <button
            type="submit"
            className={buttonStyles.primaryButton}
            disabled={running || connection !== "live"}
          >
            {running ? "Running…" : "Run A/B"}
          </button>
        </form>
      }
    >
      <p className={styles.note}>
        A headless Python run of the current scenario ({scenarioId}, seed {seed}
        ) from its starting state. Both controllers see the same site, weather,
        TSE inflow, initial state and safety gates; only the request policy
        differs. The live run is not touched.
      </p>
      {error ? <p className={styles.error}>{error}</p> : null}
      {report ? (
        <>
          <ReportTable report={report} />
          <p className={styles.summary}>
            Water applied by the smart controller:{" "}
            <strong>
              {report.water_savings_fraction >= 0 ? "−" : "+"}
              {formatPercent(Math.abs(report.water_savings_fraction), 1)}
            </strong>{" "}
            versus the fixed timer, with an ET deficit of{" "}
            {formatNumber(report.smart_hysteresis.et_deficit_mm, 2)} mm against{" "}
            {formatNumber(report.fixed_timer.et_deficit_mm, 2)} mm. Less water
            only counts as a saving if the trees are not more stressed.
          </p>
          <p className={styles.provenance}>
            {sameInputs
              ? "Identical input series and initial state (matching digests)"
              : "Input digests differ — the comparison is not matched"}{" "}
            · {report.steps.toLocaleString("en-US")} steps per policy · computed
            in {formatNumber(report.elapsed_s, 2)} s · simulated scenario
            outputs, not measured savings.
          </p>
        </>
      ) : null}
    </Panel>
  );
}
