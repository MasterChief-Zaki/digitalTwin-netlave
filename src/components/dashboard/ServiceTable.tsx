"use client";

import { formatNumber, formatPercent } from "@/lib/format";
import type { ZoneService } from "@/types/simulation";
import styles from "./Metrics.module.scss";

export function ServiceTable({ zones }: { zones: ZoneService[] }) {
  return (
    <div>
      {zones.map((zone) => (
        <table className={styles.ledger} key={zone.zone_id}>
          <caption>Zone {zone.zone_id} — simulated irrigation service</caption>
          <tbody>
            <tr>
              <th scope="row">ET service</th>
              <td>
                {zone.et_service_ratio_0_1 === null
                  ? "Not yet measured"
                  : formatPercent(zone.et_service_ratio_0_1, 2)}
              </td>
            </tr>
            <tr>
              <th scope="row">ET deficit</th>
              <td>{formatNumber(zone.et_deficit_mm, 3)} mm</td>
            </tr>
            <tr>
              <th scope="row">Below entry trigger</th>
              <td>{formatNumber(zone.below_trigger_min)} min</td>
            </tr>
            <tr>
              <th scope="row">Requested / delivered</th>
              <td>
                {formatNumber(zone.irrigation_requested_m3, 1)} /{" "}
                {formatNumber(zone.irrigation_delivered_m3, 1)} m³
              </td>
            </tr>
            <tr>
              <th scope="row">Root-zone storage initial / final</th>
              <td>
                {formatNumber(zone.initial_root_zone_storage_m3, 1)} /{" "}
                {formatNumber(zone.final_root_zone_storage_m3, 1)} m³
              </td>
            </tr>
            <tr>
              <th scope="row">Soil-stock-adjusted delivery</th>
              <td>
                {formatNumber(zone.soil_stock_adjusted_delivery_m3, 1)} m³
              </td>
            </tr>
            {Object.entries(zone.denied_by_reason_min).map(
              ([reason, minutes]) => (
                <tr key={reason}>
                  <th scope="row">Safety denial · {reason}</th>
                  <td>{formatNumber(minutes)} zone-min</td>
                </tr>
              ),
            )}
            {Object.entries(zone.deferred_by_reason_min).map(
              ([reason, minutes]) => (
                <tr key={reason}>
                  <th scope="row">Scheduling deferral · {reason}</th>
                  <td>{formatNumber(minutes)} zone-min</td>
                </tr>
              ),
            )}
            <tr>
              <th scope="row">Sessions / pauses / resumes</th>
              <td>
                {zone.session_count} / {zone.pause_count} / {zone.resume_count}
              </td>
            </tr>
          </tbody>
        </table>
      ))}
      {zones
        .filter(
          (zone) =>
            zone.et_service_ratio_0_1 !== null &&
            zone.et_service_ratio_0_1 < 0.95,
        )
        .map((zone) => (
          <p role="status" key={zone.zone_id}>
            Zone {zone.zone_id} service failure: more than 5% of potential ET is
            unmet. Electrical autonomy only covers admitted loads.
          </p>
        ))}
      <p>
        ET deficit is a simulated irrigation-adequacy proxy, not proof of forest
        health.
      </p>
    </div>
  );
}
