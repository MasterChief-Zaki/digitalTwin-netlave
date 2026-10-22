"use client";

import {
  formatNumber,
  formatPercent,
  joulesToKilowattHours,
} from "@/lib/format";
import { useTwinStore } from "@/store/useTwinStore";
import { Panel } from "./Panel";
import styles from "./Metrics.module.scss";

interface LedgerRow {
  label: string;
  value: string;
}

function Ledger({ caption, rows }: { caption: string; rows: LedgerRow[] }) {
  return (
    <table className={styles.ledger}>
      <caption>{caption}</caption>
      <tbody>
        {rows.map((row) => (
          <tr key={row.label}>
            <th scope="row">{row.label}</th>
            <td>{row.value}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

// Monotonic counters straight from the backend; nothing here is re-derived physics.
export function Metrics() {
  const metrics = useTwinStore((state) => state.snapshot.metrics);
  const cubicMetres = (value: number) => `${formatNumber(value, 1)} m³`;
  const kilowattHours = (value: number) =>
    `${formatNumber(joulesToKilowattHours(value), 2)} kWh`;
  const autonomy =
    metrics.required_electrical_energy_j > 0
      ? 1 - metrics.unserved_energy_j / metrics.required_electrical_energy_j
      : 1;

  return (
    <Panel
      label="05 — Ledger"
      title="Cumulative water and energy"
      headingId="metrics-heading"
    >
      <div className={styles.ledgers}>
        <Ledger
          caption="Water"
          rows={[
            { label: "TSE inflow", value: cubicMetres(metrics.tse_inflow_m3) },
            {
              label: "Irrigation delivered",
              value: cubicMetres(metrics.irrigation_delivered_m3),
            },
            {
              label: "Requested, not delivered",
              value: cubicMetres(metrics.requested_undelivered_m3),
            },
            { label: "Overflow", value: cubicMetres(metrics.overflow_m3) },
            {
              label: "Flush water",
              value: `${cubicMetres(metrics.flush_water_m3)} · ${String(metrics.flush_count)} flushes`,
            },
            {
              label: "Application loss",
              value: cubicMetres(metrics.application_loss_m3),
            },
            {
              label: "Deep percolation",
              value: cubicMetres(metrics.deep_percolation_m3),
            },
            {
              label: "ET actual / potential",
              value: `${formatNumber(metrics.actual_et_m3, 1)} / ${cubicMetres(metrics.potential_et_m3)}`,
            },
            { label: "ET deficit", value: cubicMetres(metrics.et_deficit_m3) },
          ]}
        />
        <Ledger
          caption="Energy"
          rows={[
            { label: "Hydro", value: kilowattHours(metrics.hydro_energy_j) },
            { label: "Solar", value: kilowattHours(metrics.solar_energy_j) },
            { label: "Pump", value: kilowattHours(metrics.pump_energy_j) },
            {
              label: "Auxiliary / flush",
              value: `${formatNumber(joulesToKilowattHours(metrics.aux_energy_j), 2)} / ${kilowattHours(metrics.flush_energy_j)}`,
            },
            {
              label: "Battery in / out",
              value: `${formatNumber(joulesToKilowattHours(metrics.battery_charge_energy_j), 2)} / ${kilowattHours(metrics.battery_discharge_energy_j)}`,
            },
            {
              label: "Battery losses",
              value: kilowattHours(metrics.battery_losses_j),
            },
            {
              label: "Curtailed",
              value: kilowattHours(metrics.curtailed_energy_j),
            },
            {
              label: "Unserved",
              value: kilowattHours(metrics.unserved_energy_j),
            },
            {
              label: "Electrical autonomy",
              value: `${formatPercent(autonomy, 1)} of ${kilowattHours(metrics.required_electrical_energy_j)} required`,
            },
          ]}
        />
      </div>
    </Panel>
  );
}
