"use client";

import { classNames } from "@/lib/classNames";
import { cubicMetresPerSecondToPerHour, formatNumber } from "@/lib/format";
import { reasonPresentation, toneSymbol } from "@/lib/reasonCodes";
import { useTwinStore } from "@/store/useTwinStore";
import type { ControlMode, Decision, Zone } from "@/types/simulation";
import { Panel } from "./Panel";
import styles from "./ZoneControls.module.scss";

const controlModes: { mode: ControlMode; label: string }[] = [
  { mode: "AUTO", label: "Auto" },
  { mode: "MANUAL_OPEN", label: "Open" },
  { mode: "MANUAL_CLOSED", label: "Close" },
];

// The moisture gauge spans wilting point to field capacity, the plant-available range.
const gaugeMinimum = 0.1;
const gaugeMaximum = 0.22;

function gaugePosition(moisture: number): string {
  const fraction = (moisture - gaugeMinimum) / (gaugeMaximum - gaugeMinimum);
  return `${String(Math.min(100, Math.max(0, fraction * 100)))}%`;
}

interface ZoneCardProps {
  zone: Zone;
  decision: Decision | undefined;
  selected: boolean;
}

function ZoneCard({ zone, decision, selected }: ZoneCardProps) {
  const { selectZone, sendCommand } = useTwinStore.getState();
  const connection = useTwinStore((state) => state.connection);
  const presentation = decision
    ? reasonPresentation[decision.reason_code]
    : reasonPresentation.KEEP_CLOSED;
  const headMargin = zone.head_available_m - zone.head_required_m;
  const headIsComputed = zone.head_required_m > 0;

  return (
    <article
      className={classNames(
        styles.zoneCard,
        selected ? styles.selected : undefined,
      )}
      aria-labelledby={`zone-${zone.id}-name`}
    >
      <button
        type="button"
        className={styles.zoneSelect}
        onClick={() => {
          selectZone(zone.id);
        }}
        aria-pressed={selected}
      >
        <span
          className={classNames(styles.zoneSwatch, styles[`swatch${zone.id}`])}
          aria-hidden="true"
        />
        <span id={`zone-${zone.id}-name`} className={styles.zoneName}>
          Zone {zone.id}
        </span>
        <span className={styles.zoneMeta}>
          {zone.feed_mode === "PUMPED" ? "pumped" : "gravity"} ·{" "}
          {formatNumber(zone.area_m2 / 10000)} ha · +
          {formatNumber(zone.elevation_m)} m
        </span>
        <span
          className={classNames(
            styles.valve,
            zone.valve_open ? styles.valveOpen : undefined,
          )}
        >
          {zone.valve_open ? "Valve open" : "Valve closed"}
        </span>
      </button>

      <div className={styles.moisture}>
        <div className={styles.moistureRow}>
          <span>Soil moisture</span>
          <span className={styles.value}>
            {formatNumber(zone.soil_moisture_m3_m3, 3)} m³/m³
          </span>
        </div>
        <div
          className={styles.gauge}
          role="img"
          aria-label={`Moisture ${formatNumber(zone.soil_moisture_m3_m3, 3)}, starts below ${formatNumber(zone.moisture_trigger_m3_m3, 3)}, stops at ${formatNumber(zone.moisture_target_m3_m3, 3)}`}
        >
          <span
            className={styles.gaugeBand}
            style={{
              left: gaugePosition(zone.moisture_trigger_m3_m3),
              right: `calc(100% - ${gaugePosition(zone.moisture_target_m3_m3)})`,
            }}
          />
          <span
            className={styles.gaugeMarker}
            style={{ left: gaugePosition(zone.soil_moisture_m3_m3) }}
          />
        </div>
        <div className={styles.gaugeScale}>
          <span>wilting 0.10</span>
          <span>
            start {formatNumber(zone.moisture_trigger_m3_m3, 3)} · stop{" "}
            {formatNumber(zone.moisture_target_m3_m3, 3)}
          </span>
          <span>field cap. 0.22</span>
        </div>
      </div>

      <dl className={styles.facts}>
        <div>
          <dt>Requested</dt>
          <dd>
            {formatNumber(
              cubicMetresPerSecondToPerHour(zone.requested_flow_m3_s),
            )}{" "}
            m³/h
          </dd>
        </div>
        <div>
          <dt>Delivered</dt>
          <dd>
            {formatNumber(
              cubicMetresPerSecondToPerHour(zone.delivered_flow_m3_s),
            )}{" "}
            m³/h
          </dd>
        </div>
        <div>
          <dt>
            {zone.feed_mode === "PUMPED" ? "Pump head" : "Head available"}
          </dt>
          <dd>{formatNumber(zone.head_available_m, 2)} m</dd>
        </div>
        <div>
          <dt>{zone.feed_mode === "PUMPED" ? "TDH needed" : "Head needed"}</dt>
          <dd>{formatNumber(zone.head_required_m, 2)} m</dd>
        </div>
        <div>
          <dt>Margin</dt>
          <dd
            className={
              headIsComputed && headMargin < 0 ? styles.negative : undefined
            }
          >
            {headIsComputed
              ? `${headMargin >= 0 ? "+" : ""}${formatNumber(headMargin, 2)} m`
              : "–"}
          </dd>
        </div>
        <div>
          <dt>Water stress</dt>
          <dd>{formatNumber(zone.water_stress_0_1, 2)}</dd>
        </div>
      </dl>

      <div className={styles.decision}>
        <p
          className={classNames(styles.reasonBadge, styles[presentation.tone])}
        >
          <span aria-hidden="true">{toneSymbol[presentation.tone]}</span>
          {presentation.label}
          <span className={styles.reasonCode}>
            {decision?.requested_action ?? "KEEP_CLOSED"} ·{" "}
            {decision?.accepted === false ? "denied" : "granted"}
          </span>
        </p>
        <p className={styles.explanation}>
          {decision?.explanation ?? "No step has been simulated yet."}
        </p>
      </div>

      <div
        className={styles.modes}
        role="group"
        aria-label={`Zone ${zone.id} control mode`}
      >
        {controlModes.map(({ mode, label }) => (
          <button
            key={mode}
            type="button"
            className={classNames(
              styles.modeButton,
              zone.control_mode === mode ? styles.modeActive : undefined,
            )}
            aria-pressed={zone.control_mode === mode}
            disabled={connection !== "live"}
            onClick={() => {
              void sendCommand({
                type: "set_zone_mode",
                zone_id: zone.id,
                mode,
              });
            }}
          >
            {label}
          </button>
        ))}
      </div>
    </article>
  );
}

export function ZoneControls() {
  const zones = useTwinStore((state) => state.snapshot.zones);
  const decisions = useTwinStore((state) => state.snapshot.decisions);
  const selectedZoneId = useTwinStore((state) => state.selectedZoneId);

  return (
    <Panel
      label="02 — Zones"
      title="Requests, gates and decisions"
      headingId="zones-heading"
      className={styles.zonesPanel}
    >
      <p className={styles.note}>
        The controller only proposes. A manual open still passes every safety
        gate: water quality, flush, reservoir, head, manifold, power and battery
        reserve.
      </p>
      <div className={styles.zoneList}>
        {zones.map((zone) => (
          <ZoneCard
            key={zone.id}
            zone={zone}
            decision={decisions.find(
              (decision) => decision.zone_id === zone.id,
            )}
            selected={zone.id === selectedZoneId}
          />
        ))}
      </div>
    </Panel>
  );
}
