import { create } from "zustand";
import { initialSnapshot } from "@/fixtures/initialSnapshot";
import {
  SimulationConflictError,
  SimulationUnavailableError,
  simulationApi,
} from "@/services/api";
import type {
  AssumptionRow,
  Command,
  ControlPolicy,
  ScenarioId,
  ScenarioInfo,
  SimulationEvent,
  SimulationSnapshot,
  ZoneId,
} from "@/types/simulation";

// The store only holds what the backend returned plus UI-only state
// (selection, play/pause, speed, chart window). It never computes physics.

export interface ChartPoint {
  step: number;
  zoneAMoisture: number;
  zoneBMoisture: number;
  zoneCMoisture: number;
  reservoirVolumeM3: number;
  solarPowerW: number;
  hydroPowerW: number;
  pumpPowerW: number;
}

export type ConnectionStatus = "fixture" | "live" | "offline";

export const speedPresets = [
  { stepsPerRequest: 1, label: "1 min / tick" },
  { stepsPerRequest: 5, label: "5 min / tick" },
  { stepsPerRequest: 15, label: "15 min / tick" },
  { stepsPerRequest: 60, label: "1 h / tick" },
] as const;

const chartWindowPoints = 720;
const eventFeedLimit = 200;
const tickPauseMs = 150;
// One id per page load, so two tabs never share request ids. Created lazily
// in the browser so prerendering stays deterministic.
let tabId: string | null = null;
function getTabId(): string {
  tabId ??= crypto.randomUUID().slice(0, 8);
  return tabId;
}

interface TwinState {
  snapshot: SimulationSnapshot;
  connection: ConnectionStatus;
  notice: string | null;
  playing: boolean;
  requestInFlight: boolean;
  stepsPerRequest: number;
  selectedZoneId: ZoneId;
  events: SimulationEvent[];
  chartPoints: ChartPoint[];
  scenarios: ScenarioInfo[];
  assumptions: AssumptionRow[];
  connect: () => Promise<void>;
  play: () => void;
  pause: () => void;
  advance: (steps: number) => Promise<boolean>;
  fastForward: (totalSteps: number) => Promise<void>;
  setStepsPerRequest: (stepsPerRequest: number) => void;
  selectZone: (zoneId: ZoneId) => void;
  sendCommand: (command: Command) => Promise<void>;
  resetRun: (
    scenarioId: ScenarioId,
    seed: number,
    controlPolicy: ControlPolicy,
  ) => Promise<void>;
}

// Every request that depends on the current step (advance, command, reset)
// runs one at a time, in click order, and reads the step when it starts. So a
// fast-forward, a Play press, an operator command and a reset never race, and
// a late reply can never overwrite a newer run.
let exclusiveQueue: Promise<unknown> = Promise.resolve();
function runExclusive<Result>(task: () => Promise<Result>): Promise<Result> {
  const run = exclusiveQueue.then(task, task);
  exclusiveQueue = run.catch(() => undefined);
  return run;
}

function toChartPoint(snapshot: SimulationSnapshot): ChartPoint {
  const [zoneA, zoneB, zoneC] = snapshot.zones;
  return {
    step: snapshot.step,
    zoneAMoisture: zoneA?.soil_moisture_m3_m3 ?? 0,
    zoneBMoisture: zoneB?.soil_moisture_m3_m3 ?? 0,
    zoneCMoisture: zoneC?.soil_moisture_m3_m3 ?? 0,
    reservoirVolumeM3: snapshot.reservoir.volume_m3,
    solarPowerW: snapshot.energy.solar_power_w,
    hydroPowerW: snapshot.energy.hydro_power_w,
    pumpPowerW: snapshot.energy.pump_power_w,
  };
}

function appendBounded<Item>(
  items: Item[],
  additions: Item[],
  limit: number,
): Item[] {
  return [...items, ...additions].slice(-limit);
}

function describeError(error: unknown): string {
  if (
    error instanceof SimulationUnavailableError ||
    error instanceof SimulationConflictError
  ) {
    return error.message;
  }
  return "Unexpected error talking to the simulation.";
}

export const useTwinStore = create<TwinState>()((set, get) => {
  async function refreshAfterConflict(message: string) {
    set({ playing: false, notice: message });
    try {
      const [snapshot, eventsPage] = await Promise.all([
        simulationApi.getState(),
        simulationApi.getEvents(0),
      ]);
      set({
        snapshot,
        events: eventsPage.events.slice(-eventFeedLimit),
        chartPoints: [toChartPoint(snapshot)],
        connection: "live",
      });
    } catch (error) {
      set({ connection: "offline", notice: describeError(error) });
    }
  }

  async function handleFailure(error: unknown) {
    if (error instanceof SimulationConflictError) {
      await refreshAfterConflict(
        `Another client moved the run to step ${String(error.detail.current_step)}. Playback paused and the view refreshed.`,
      );
      return;
    }
    set({
      playing: false,
      connection: "offline",
      notice: describeError(error),
    });
  }

  async function advanceNow(steps: number): Promise<boolean> {
    const { snapshot } = get();
    set({ requestInFlight: true });
    try {
      const reply = await simulationApi.advance({
        run_generation: snapshot.run_generation,
        expected_step: snapshot.step,
        steps,
        request_id: `${getTabId()}-${String(snapshot.run_generation)}-${String(snapshot.step)}`,
      });
      set((current) => ({
        snapshot: reply.snapshot,
        connection: "live",
        events: appendBounded(current.events, reply.events, eventFeedLimit),
        chartPoints: appendBounded(
          current.chartPoints,
          [toChartPoint(reply.snapshot)],
          chartWindowPoints,
        ),
        notice: reply.events_truncated
          ? "Long fast-forward: only the latest events are shown in the feed."
          : current.notice,
      }));
      return true;
    } catch (error) {
      await handleFailure(error);
      return false;
    } finally {
      set({ requestInFlight: false });
    }
  }

  async function sendCommandNow(command: Command): Promise<void> {
    const { snapshot } = get();
    try {
      const updated = await simulationApi.command({
        run_generation: snapshot.run_generation,
        expected_step: snapshot.step,
        command,
      });
      const eventsPage = await simulationApi.getEvents(
        updated.latest_event_id - 1,
      );
      set((current) => ({
        snapshot: updated,
        events: appendBounded(
          current.events,
          eventsPage.events,
          eventFeedLimit,
        ),
      }));
    } catch (error) {
      await handleFailure(error);
    }
  }

  async function resetRunNow(
    scenarioId: ScenarioId,
    seed: number,
    controlPolicy: ControlPolicy,
  ): Promise<void> {
    try {
      const snapshot = await simulationApi.reset({
        scenario_id: scenarioId,
        seed,
        control_policy: controlPolicy,
      });
      const eventsPage = await simulationApi.getEvents(
        snapshot.latest_event_id - 1,
      );
      set((current) => ({
        snapshot,
        connection: "live",
        notice: null,
        chartPoints: [toChartPoint(snapshot)],
        events: appendBounded(
          current.events,
          eventsPage.events,
          eventFeedLimit,
        ),
      }));
    } catch (error) {
      await handleFailure(error);
    }
  }

  return {
    snapshot: initialSnapshot,
    connection: "fixture",
    notice: null,
    playing: false,
    requestInFlight: false,
    stepsPerRequest: 5,
    selectedZoneId: "C",
    events: [],
    chartPoints: [toChartPoint(initialSnapshot)],
    scenarios: [],
    assumptions: [],

    async connect() {
      try {
        const [snapshot, eventsPage, scenarios] = await Promise.all([
          simulationApi.getState(),
          simulationApi.getEvents(0),
          simulationApi.getScenarios(),
        ]);
        set({
          snapshot,
          connection: "live",
          notice: null,
          events: eventsPage.events.slice(-eventFeedLimit),
          chartPoints: [toChartPoint(snapshot)],
          scenarios: scenarios.scenarios,
          assumptions: scenarios.assumptions,
        });
      } catch (error) {
        set({ connection: "offline", notice: describeError(error) });
      }
    },

    play() {
      if (get().playing || get().connection !== "live") {
        return;
      }
      set({ playing: true, notice: null });
      // One request at a time: await each reply before scheduling the next.
      const loop = async () => {
        while (get().playing) {
          const advanced = await get().advance(get().stepsPerRequest);
          if (!advanced) {
            return;
          }
          await new Promise((resolve) => setTimeout(resolve, tickPauseMs));
        }
      };
      void loop();
    },

    pause() {
      // Stops future requests; one in flight may still finish and be shown.
      set({ playing: false });
    },

    advance(steps) {
      return runExclusive(() => advanceNow(steps));
    },

    async fastForward(totalSteps) {
      get().pause();
      let remaining = totalSteps;
      while (remaining > 0) {
        const batch = Math.min(60, remaining);
        const advanced = await get().advance(batch);
        if (!advanced) {
          return;
        }
        remaining -= batch;
      }
    },

    setStepsPerRequest(stepsPerRequest) {
      set({ stepsPerRequest });
    },

    selectZone(zoneId) {
      set({ selectedZoneId: zoneId });
    },

    sendCommand(command) {
      return runExclusive(() => sendCommandNow(command));
    },

    resetRun(scenarioId, seed, controlPolicy) {
      set({ playing: false });
      return runExclusive(() => resetRunNow(scenarioId, seed, controlPolicy));
    },
  };
});
