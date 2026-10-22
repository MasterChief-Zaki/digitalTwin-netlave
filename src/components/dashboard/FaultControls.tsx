"use client";

import { classNames } from "@/lib/classNames";
import { formatNumber } from "@/lib/format";
import { useTwinStore } from "@/store/useTwinStore";
import type { WaterQuality } from "@/types/simulation";
import { Panel } from "./Panel";
import styles from "./FaultControls.module.scss";

const waterQualityOptions: WaterQuality[] = ["OK", "HOLD", "UNKNOWN"];

// Faults change the environment or the inputs; the engine produces whatever follows.
export function FaultControls() {
  const environment = useTwinStore((state) => state.snapshot.environment);
  const connection = useTwinStore((state) => state.connection);
  const { sendCommand } = useTwinStore.getState();
  const disabled = connection !== "live";
  const dirtyEffluent = environment.solids_loading_multiplier > 1;
  const sandstorm = environment.cloud_factor < 1;

  return (
    <Panel
      label="03 — Faults"
      title="Inject an event"
      headingId="faults-heading"
    >
      <div className={styles.faults}>
        <button
          type="button"
          className={classNames(
            styles.fault,
            dirtyEffluent ? styles.faultOn : undefined,
          )}
          aria-pressed={dirtyEffluent}
          disabled={disabled}
          onClick={() => {
            void sendCommand({
              type: "set_solids_multiplier",
              multiplier: dirtyEffluent ? 1 : 8,
            });
          }}
        >
          <span className={styles.faultName}>Dirty effluent</span>
          <span className={styles.faultState}>
            solids ×{formatNumber(environment.solids_loading_multiplier, 0)}
          </span>
        </button>
        <button
          type="button"
          className={classNames(
            styles.fault,
            sandstorm ? styles.faultOn : undefined,
          )}
          aria-pressed={sandstorm}
          disabled={disabled}
          onClick={() => {
            void sendCommand({
              type: "set_cloud_factor",
              cloud_factor: sandstorm ? 1 : 0.25,
            });
          }}
        >
          <span className={styles.faultName}>Sandstorm</span>
          <span className={styles.faultState}>
            cloud factor {formatNumber(environment.cloud_factor, 2)}
          </span>
        </button>
        <button
          type="button"
          className={classNames(
            styles.fault,
            environment.inflow_available ? "" : styles.faultOn,
          )}
          aria-pressed={!environment.inflow_available}
          disabled={disabled}
          onClick={() => {
            void sendCommand({
              type: "set_inflow_available",
              available: !environment.inflow_available,
            });
          }}
        >
          <span className={styles.faultName}>Cut TSE inflow</span>
          <span className={styles.faultState}>
            {environment.inflow_available ? "arriving" : "cut"}
          </span>
        </button>
        <label className={styles.qualityField}>
          <span className={styles.faultName}>Synthetic quality flag</span>
          <select
            className={styles.qualitySelect}
            value={environment.water_quality}
            disabled={disabled}
            onChange={(event) => {
              const status = waterQualityOptions.find(
                (option) => option === event.target.value,
              );
              if (status) {
                void sendCommand({ type: "set_water_quality", status });
              }
            }}
          >
            {waterQualityOptions.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </label>
      </div>
      <p className={styles.disclaimer}>
        The quality flag is synthetic. It is not an Egyptian regulatory
        compliance test and never permits real-world irrigation.
      </p>
    </Panel>
  );
}
