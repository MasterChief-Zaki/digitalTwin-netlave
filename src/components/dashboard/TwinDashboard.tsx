"use client";

import { useEffect } from "react";
import { useTwinStore } from "@/store/useTwinStore";
import { Charts } from "./Charts";
import { Compare } from "./Compare";
import { Events } from "./Events";
import { FaultControls } from "./FaultControls";
import { Kpis } from "./Kpis";
import { Metrics } from "./Metrics";
import { Panel } from "./Panel";
import { StatusBar } from "./StatusBar";
import { ZoneControls } from "./ZoneControls";
import styles from "./TwinDashboard.module.scss";

export function TwinDashboard() {
  const connect = useTwinStore((state) => state.connect);
  const notice = useTwinStore((state) => state.notice);

  useEffect(() => {
    void connect();
  }, [connect]);

  return (
    <div className={styles.dashboard}>
      <StatusBar />
      <main id="main" className={styles.content}>
        {notice ? (
          <p className={styles.notice} role="status">
            {notice}
          </p>
        ) : null}
        <Kpis />
        <div className={styles.workspace}>
          <Panel
            label="01 — Site"
            title="Three terraces, one reservoir, one closed loop"
            headingId="site-heading"
            className={styles.sitePanel}
          >
            <div className={styles.twinSlot}>
              <p className={styles.twinPlaceholder}>
                The 3D forest renders here.
              </p>
            </div>
          </Panel>
          <div className={styles.sideColumn}>
            <ZoneControls />
            <FaultControls />
          </div>
        </div>
        <Charts />
        <div className={styles.lowerStrip}>
          <Metrics />
          <Events />
        </div>
        <Compare />
        <p className={styles.disclaimer}>
          Simulation-driven digital twin prototype with synthetic site
          assumptions. It is not calibrated against field measurements, and its
          numbers are simulated scenario outputs, not measured savings.
        </p>
      </main>
    </div>
  );
}
