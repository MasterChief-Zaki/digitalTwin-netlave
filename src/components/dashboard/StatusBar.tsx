"use client";

import { useState } from "react";
import { classNames } from "@/lib/classNames";
import { formatSimulatedClock } from "@/lib/format";
import { speedPresets, useTwinStore } from "@/store/useTwinStore";
import buttonStyles from "@/styles/buttons.module.scss";
import type { ControlPolicy, ScenarioId } from "@/types/simulation";
import styles from "./StatusBar.module.scss";

const fallbackScenarios: { id: ScenarioId; title: string }[] = [
  { id: "baseline", title: "Baseline" },
  { id: "clogged_filter", title: "Clogged filter" },
  { id: "low_solar", title: "Low solar (sandstorm)" },
  { id: "tse_interrupt", title: "TSE interruption" },
];

const connectionLabels = {
  fixture: "Fixture · connecting",
  live: "Live backend",
  offline: "Backend offline",
} as const;

export function StatusBar() {
  const snapshot = useTwinStore((state) => state.snapshot);
  const connection = useTwinStore((state) => state.connection);
  const playing = useTwinStore((state) => state.playing);
  const requestInFlight = useTwinStore((state) => state.requestInFlight);
  const stepsPerRequest = useTwinStore((state) => state.stepsPerRequest);
  const scenarios = useTwinStore((state) => state.scenarios);
  const { play, pause, advance, fastForward, setStepsPerRequest, resetRun } =
    useTwinStore.getState();

  const [scenarioId, setScenarioId] = useState<ScenarioId>(
    snapshot.scenario_id,
  );
  const [controlPolicy, setControlPolicy] = useState<ControlPolicy>(
    snapshot.environment.control_policy,
  );
  const [seed, setSeed] = useState(snapshot.seed);

  const scenarioOptions = scenarios.length > 0 ? scenarios : fallbackScenarios;
  const isLive = connection === "live";
  const stepping = playing || requestInFlight;

  return (
    <header className={styles.statusBar}>
      <div className={styles.identity}>
        <p className={styles.wordmark}>netLave</p>
        <p className={styles.product}>Digital Twin · TSE forest, Egypt</p>
      </div>

      <div className={styles.clock} aria-live="polite">
        <p className={styles.clockTime}>
          {formatSimulatedClock(snapshot.step, snapshot.start_hour)}
        </p>
        <p className={styles.clockMeta}>
          Step {snapshot.step.toLocaleString("en-US")} · 60 s per step · run{" "}
          {snapshot.run_generation}
        </p>
      </div>

      <div className={styles.badges}>
        <span className={styles.simulatedBadge}>Simulated</span>
        <span className={classNames(styles.connection, styles[connection])}>
          {connectionLabels[connection]}
        </span>
      </div>

      <div className={styles.playback} role="group" aria-label="Playback">
        <button
          type="button"
          className={buttonStyles.primaryButton}
          onClick={playing ? pause : play}
          disabled={!isLive}
        >
          {playing ? "Pause" : "Play"}
        </button>
        <button
          type="button"
          className={buttonStyles.secondaryButton}
          onClick={() => void advance(1)}
          disabled={!isLive || stepping}
        >
          +1 min
        </button>
        <button
          type="button"
          className={buttonStyles.secondaryButton}
          onClick={() => void fastForward(60)}
          disabled={!isLive || stepping}
        >
          +1 h
        </button>
        <button
          type="button"
          className={buttonStyles.secondaryButton}
          onClick={() => void fastForward(1440)}
          disabled={!isLive || stepping}
        >
          +1 day
        </button>
        <label className={styles.field}>
          <span className={styles.fieldLabel}>Speed</span>
          <select
            className={styles.select}
            value={stepsPerRequest}
            onChange={(event) => {
              setStepsPerRequest(Number(event.target.value));
            }}
          >
            {speedPresets.map((preset) => (
              <option
                key={preset.stepsPerRequest}
                value={preset.stepsPerRequest}
              >
                {preset.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <form
        className={styles.scenarioForm}
        onSubmit={(event) => {
          event.preventDefault();
          void resetRun(scenarioId, seed, controlPolicy);
        }}
      >
        <label className={styles.field}>
          <span className={styles.fieldLabel}>Scenario</span>
          <select
            className={styles.select}
            value={scenarioId}
            onChange={(event) => {
              const selected = scenarioOptions.find(
                (scenario) => scenario.id === event.target.value,
              );
              if (selected) {
                setScenarioId(selected.id);
              }
            }}
          >
            {scenarioOptions.map((scenario) => (
              <option key={scenario.id} value={scenario.id}>
                {scenario.title}
              </option>
            ))}
          </select>
        </label>
        <label className={styles.field}>
          <span className={styles.fieldLabel}>Control</span>
          <select
            className={styles.select}
            value={controlPolicy}
            onChange={(event) => {
              setControlPolicy(
                event.target.value === "FIXED_TIMER"
                  ? "FIXED_TIMER"
                  : "SMART_HYSTERESIS",
              );
            }}
          >
            <option value="SMART_HYSTERESIS">Smart hysteresis</option>
            <option value="FIXED_TIMER">Fixed timer</option>
          </select>
        </label>
        <label className={styles.field}>
          <span className={styles.fieldLabel}>Seed</span>
          <input
            className={classNames(styles.select, styles.seedInput)}
            type="number"
            min={0}
            value={seed}
            onChange={(event) => {
              setSeed(Math.max(0, Math.trunc(Number(event.target.value))));
            }}
          />
        </label>
        <button
          type="submit"
          className={buttonStyles.secondaryButton}
          disabled={!isLive}
        >
          Load run
        </button>
      </form>
    </header>
  );
}
