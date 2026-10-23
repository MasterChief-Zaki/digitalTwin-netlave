"use client";

import dynamic from "next/dynamic";
import { classNames } from "@/lib/classNames";
import styles from "./LazyTwin.module.scss";
import { SceneErrorBoundary } from "./SceneErrorBoundary";
import { useTwinStore } from "@/store/useTwinStore";
import { reasonPresentation } from "@/lib/reasonCodes";
import { formatNumber } from "@/lib/format";
import { zoneVisualState } from "./snapshotVisuals";

// WebGL only runs in the browser, and three.js is too heavy for the initial bundle.
const TwinCanvas = dynamic(
  () => import("./TwinCanvas").then((canvasModule) => canvasModule.TwinCanvas),
  {
    ssr: false,
    loading: () => <p className={styles.unavailable}>Loading schematic…</p>,
  },
);

const sceneUnavailable = (
  <p className={styles.unavailable}>
    The 3D site view needs WebGL, which this browser cannot provide. Every
    simulated value is still shown in the dashboard.
  </p>
);

export function LazyTwin() {
  const snapshot = useTwinStore((state) => state.snapshot);
  const selected = useTwinStore((state) => state.selectedZoneId);
  const selectZone = useTwinStore((state) => state.selectZone);
  const zone = snapshot.zones.find((item) => item.id === selected);
  const decision = snapshot.decisions.find((item) => item.zone_id === selected);
  return (
    <div className={styles.twin}>
      <SceneErrorBoundary fallback={sceneUnavailable}>
        <TwinCanvas unavailable={sceneUnavailable} />
      </SceneErrorBoundary>
      <div className={styles.readout} aria-label="Schematic snapshot status">
        <p className={styles.readoutHeading}>
          SCHEMATIC · SIMULATED · STEP {snapshot.step}
        </p>
        <div
          className={styles.zoneButtons}
          role="group"
          aria-label="Schematic zone selection"
        >
          {snapshot.zones.map((item) => (
            <button
              key={item.id}
              type="button"
              aria-pressed={selected === item.id}
              onClick={() => {
                selectZone(item.id);
              }}
              className={classNames(
                styles.zoneButton,
                styles[zoneVisualState(snapshot, item.id)],
              )}
            >
              Zone {item.id}
            </button>
          ))}
        </div>
        <p>
          {decision
            ? reasonPresentation[decision.reason_code].label
            : "No decision"}{" "}
          · {formatNumber((zone?.delivered_flow_m3_s ?? 0) * 3600, 1)} m³/h
        </p>
        <p className={styles.readoutNote}>
          Canopy tint = moisture stress proxy, not growth.
        </p>
      </div>
      <ul className={styles.legend} aria-label="3D view legend">
        <li className={styles.legendItem}>
          <span className={classNames(styles.swatch, styles.active)} />
          Active
        </li>
        <li className={styles.legendItem}>
          <span className={classNames(styles.swatch, styles.idle)} />
          Idle
        </li>
        <li className={styles.legendItem}>
          <span className={classNames(styles.swatch, styles.waiting)} />
          Waiting
        </li>
        <li className={styles.legendItem}>
          <span className={classNames(styles.swatch, styles.fault)} />
          Fault
        </li>
        <li className={styles.hint}>
          Solid: water · thin: DC energy · schematic scale · drag to orbit
        </li>
      </ul>
    </div>
  );
}
