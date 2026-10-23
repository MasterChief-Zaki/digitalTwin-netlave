"use client";

import {
  cubicMetresPerSecondToPerHour,
  formatNumber,
  formatPercent,
  formatSimulatedClock,
  joulesToKilowattHours,
} from "@/lib/format";
import { classNames } from "@/lib/classNames";
import { reasonPresentation, toneSymbol } from "@/lib/reasonCodes";
import type { StatusTone } from "@/lib/reasonCodes";
import { useTwinStore } from "@/store/useTwinStore";
import type { ReasonCode } from "@/types/simulation";
import styles from "./Kpis.module.scss";

interface KpiTileProps {
  label: string;
  value: string;
  unit: string;
  detail: string;
  tone?: StatusTone;
  // Words rather than a number: a smaller face so the label fits the tile.
  textValue?: boolean;
}

function KpiTile({
  label,
  value,
  unit,
  detail,
  tone,
  textValue = false,
}: KpiTileProps) {
  return (
    <li className={styles.tile}>
      <p className={styles.tileLabel}>
        {label}
        <span className={styles.simulatedTag}>sim</span>
      </p>
      <p
        className={classNames(
          styles.tileValue,
          textValue ? styles.tileValueText : undefined,
        )}
      >
        {tone ? (
          <span
            className={classNames(styles.toneSymbol, styles[tone])}
            aria-hidden="true"
          >
            {toneSymbol[tone]}
          </span>
        ) : null}
        {value}
        <span className={styles.tileUnit}>{unit}</span>
      </p>
      <p className={styles.tileDetail}>{detail}</p>
    </li>
  );
}

export function Kpis() {
  const snapshot = useTwinStore((state) => state.snapshot);
  const events = useTwinStore((state) => state.events);
  const { reservoir, energy, filtration, metrics, zones, diagnostics } =
    snapshot;

  const deliveredFlowM3S = zones.reduce(
    (total, zone) => total + zone.delivered_flow_m3_s,
    0,
  );
  const latestDenial = events.findLast((event) => event.category === "DENIAL");
  const moistureSummary = zones
    .map((zone) => `${zone.id} ${formatNumber(zone.soil_moisture_m3_m3, 3)}`)
    .join(" · ");
  const lowestMoisture = Math.min(
    ...zones.map((zone) => zone.soil_moisture_m3_m3),
  );
  const trigger = zones[0]?.moisture_trigger_m3_m3 ?? 0;
  const hasDecision = (reasonCode: ReasonCode) =>
    snapshot.decisions.some((decision) => decision.reason_code === reasonCode);

  return (
    <section className={styles.kpis} aria-labelledby="kpi-heading">
      <h2 id="kpi-heading" className={styles.heading}>
        Simulated readings
      </h2>
      <ul className={styles.tiles}>
        <KpiTile
          label="ET service · zone C"
          value={
            zones.find((zone) => zone.id === "C")?.service
              .et_service_ratio_0_1 === null
              ? "Pending"
              : formatPercent(
                  zones.find((zone) => zone.id === "C")?.service
                    .et_service_ratio_0_1 ?? 0,
                  1,
                )
          }
          unit=""
          detail="Simulated actual / potential ET · see service ledger"
        />
        <KpiTile
          label="Electrical autonomy"
          value={
            diagnostics.electrical_autonomy_0_1 === null
              ? "Pending"
              : formatPercent(diagnostics.electrical_autonomy_0_1, 1)
          }
          unit=""
          detail="Admitted loads only — not irrigation service"
        />
        <KpiTile
          label="Reservoir"
          value={formatNumber(reservoir.volume_m3)}
          unit="m³"
          detail={`${formatPercent(reservoir.volume_m3 / reservoir.capacity_m3)} full · surface +${formatNumber(reservoir.surface_elevation_m, 1)} m`}
          tone={hasDecision("RESERVOIR_LOW") ? "fault" : undefined}
        />
        <KpiTile
          label="TSE inflow"
          value={formatNumber(
            cubicMetresPerSecondToPerHour(reservoir.inflow_m3_s),
            1,
          )}
          unit="m³/h"
          detail={`${formatNumber(metrics.tse_inflow_m3)} m³ received`}
          tone={
            snapshot.step > 0 && reservoir.inflow_m3_s === 0
              ? "warning"
              : undefined
          }
        />
        <KpiTile
          label="Irrigation"
          value={formatNumber(cubicMetresPerSecondToPerHour(deliveredFlowM3S))}
          unit="m³/h"
          detail={`${formatNumber(metrics.irrigation_delivered_m3)} m³ delivered`}
        />
        <KpiTile
          label="Soil moisture"
          value={formatNumber(lowestMoisture, 3)}
          unit="m³/m³ low"
          detail={moistureSummary}
          tone={lowestMoisture < trigger ? "warning" : undefined}
        />
        <KpiTile
          label="Hydro"
          value={formatNumber(energy.hydro_power_w)}
          unit="W"
          detail={`${formatNumber(joulesToKilowattHours(metrics.hydro_energy_j), 1)} kWh generated`}
        />
        <KpiTile
          label="Solar"
          value={formatNumber(energy.solar_power_w)}
          unit="W"
          detail={`${formatNumber(joulesToKilowattHours(metrics.solar_energy_j), 1)} kWh · cloud ${formatNumber(snapshot.environment.cloud_factor, 2)}`}
        />
        <KpiTile
          label="Pump · zone C"
          value={formatNumber(energy.pump_power_w)}
          unit="W"
          detail={`needs ${formatNumber(snapshot.pump.required_power_w)} W · ${formatNumber(snapshot.pump.total_dynamic_head_m, 1)} m`}
          tone={snapshot.pump.running ? "active" : undefined}
        />
        <KpiTile
          label="Battery"
          value={formatPercent(energy.battery_soc_0_1, 1)}
          unit="SoC"
          detail={
            energy.discharge_power_w > 0
              ? `discharging ${formatNumber(energy.discharge_power_w)} W`
              : `charging ${formatNumber(energy.charge_power_w)} W`
          }
          tone={
            energy.unserved_power_w > 0 || hasDecision("BATTERY_BELOW_RESERVE")
              ? "fault"
              : undefined
          }
        />
        <KpiTile
          label="Filter ΔP"
          value={formatNumber(filtration.pressure_drop_pa / 1000, 1)}
          unit="kPa"
          detail={
            filtration.flushing
              ? `flushing · ${String(filtration.flush_steps_remaining)} min left`
              : `clog index ${formatNumber(filtration.clog_index_0_1, 2)}${filtration.flush_required ? " · flush due" : ""}`
          }
          tone={
            filtration.flushing || filtration.flush_required
              ? "warning"
              : undefined
          }
        />
        <KpiTile
          label="Overflow"
          value={formatNumber(metrics.overflow_m3)}
          unit="m³"
          detail={`${formatNumber(cubicMetresPerSecondToPerHour(reservoir.overflow_flow_m3_s), 1)} m³/h now`}
          tone={reservoir.overflow_flow_m3_s > 0 ? "warning" : undefined}
        />
        <KpiTile
          label="Recent denial"
          textValue
          value={
            latestDenial
              ? reasonPresentation[latestDenial.reason_code].label
              : "None"
          }
          unit={latestDenial?.zone_id ? `zone ${latestDenial.zone_id}` : ""}
          detail={
            latestDenial
              ? formatSimulatedClock(latestDenial.step, snapshot.start_hour)
              : "no request denied yet"
          }
          tone={latestDenial ? "fault" : undefined}
        />
      </ul>
    </section>
  );
}
