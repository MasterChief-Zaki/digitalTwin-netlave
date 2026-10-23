"use client";

import {
  formatNumber,
  formatPercent,
  joulesToKilowattHours,
} from "@/lib/format";
import { useTwinStore } from "@/store/useTwinStore";
import { Panel } from "./Panel";
import { ServiceTable } from "./ServiceTable";
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
  const { metrics, diagnostics, zones } = useTwinStore(
    (state) => state.snapshot,
  );
  const cubicMetres = (value: number) => `${formatNumber(value, 1)} m³`;
  const kilowattHours = (value: number) =>
    `${formatNumber(joulesToKilowattHours(value), 2)} kWh`;
  const autonomy = diagnostics.electrical_autonomy_0_1;

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
              label: "Repeated denied-request integral (not crop shortage)",
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
              label: "Electrical autonomy — admitted loads",
              value:
                autonomy === null
                  ? "Not yet measured"
                  : `${formatPercent(autonomy, 1)} of ${kilowattHours(metrics.required_electrical_energy_j)} admitted`,
            },
            {
              label: "Minimum battery / equivalent full cycles",
              value: `${formatPercent(diagnostics.minimum_battery_soc_0_1, 1)} / ${formatNumber(diagnostics.battery_equivalent_full_cycles, 2)}`,
            },
            {
              label: "Reservoir initial / final",
              value: `${cubicMetres(diagnostics.initial_reservoir_volume_m3)} / ${cubicMetres(diagnostics.final_reservoir_volume_m3)}`,
            },
            {
              label: "Battery initial / final",
              value: `${kilowattHours(diagnostics.initial_battery_energy_j)} / ${kilowattHours(diagnostics.final_battery_energy_j)}`,
            },
          ]}
        />
      </div>
      <ServiceTable zones={zones.map((zone) => zone.service)} />
    </Panel>
  );
}
