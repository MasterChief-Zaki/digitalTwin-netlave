"use client";

import { useEffect } from "react";
import { ProjectFacts } from "@/components/ProjectFacts";
import truth from "@/content/ground-truth.json";
import { LazyTwin } from "@/components/twin/LazyTwin";
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

const reconnectIntervalMs = 3000;

export function TwinDashboard() {
  const connect = useTwinStore((state) => state.connect);
  const notice = useTwinStore((state) => state.notice);

  useEffect(() => {
    void connect();
    // The backend may start after the page (pnpm demo) or restart mid-demo; keep retrying until live.
    const reconnectTimer = setInterval(() => {
      if (useTwinStore.getState().connection !== "live") {
        void connect();
      }
    }, reconnectIntervalMs);
    return () => {
      clearInterval(reconnectTimer);
    };
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
            title="Three terraces, one reservoir, one shared network"
            headingId="site-heading"
            className={styles.sitePanel}
          >
            <div className={styles.twinSlot}>
              <LazyTwin />
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
        <ProjectFacts />
        <p className={styles.disclaimer}>{truth.safetyBoundary}</p>
      </main>
    </div>
  );
}
