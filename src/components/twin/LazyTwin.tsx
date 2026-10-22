"use client";

import dynamic from "next/dynamic";
import { classNames } from "@/lib/classNames";
import styles from "./LazyTwin.module.scss";

// WebGL only runs in the browser, and three.js is too heavy for the initial bundle.
const TwinCanvas = dynamic(
  () => import("./TwinCanvas").then((canvasModule) => canvasModule.TwinCanvas),
  { ssr: false },
);

export function LazyTwin() {
  return (
    <div className={styles.twin}>
      <TwinCanvas />
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
          <span className={classNames(styles.swatch, styles.fault)} />
          Fault
        </li>
        <li className={styles.hint}>Click a terrace to select a zone</li>
      </ul>
    </div>
  );
}
