"use client";

import dynamic from "next/dynamic";
import { classNames } from "@/lib/classNames";
import styles from "./LazyTwin.module.scss";
import { SceneErrorBoundary } from "./SceneErrorBoundary";

// WebGL only runs in the browser, and three.js is too heavy for the initial bundle.
const TwinCanvas = dynamic(
  () => import("./TwinCanvas").then((canvasModule) => canvasModule.TwinCanvas),
  { ssr: false },
);

const sceneUnavailable = (
  <p className={styles.unavailable}>
    The 3D site view needs WebGL, which this browser cannot provide. Every
    simulated value is still shown in the dashboard.
  </p>
);

export function LazyTwin() {
  return (
    <div className={styles.twin}>
      <SceneErrorBoundary fallback={sceneUnavailable}>
        <TwinCanvas unavailable={sceneUnavailable} />
      </SceneErrorBoundary>
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
        <li className={styles.hint}>Click a terrace to select a zone</li>
      </ul>
    </div>
  );
}
