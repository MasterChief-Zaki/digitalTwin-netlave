import type {
  AdvanceRequest,
  AdvanceResponse,
  CommandRequest,
  CompareRequest,
  CompareResponse,
  ConflictDetail,
  EventsPage,
  ResetRequest,
  ScenariosResponse,
  SimulationSnapshot,
} from "@/types/simulation";

// Every route goes through the Next.js rewrite to the FastAPI process (next.config.ts).
const apiBase = "/api";

export class SimulationConflictError extends Error {
  constructor(readonly detail: ConflictDetail) {
    super(detail.message);
    this.name = "SimulationConflictError";
  }
}

export class SimulationUnavailableError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "SimulationUnavailableError";
  }
}

function validateSnapshotCompatibility(payload: unknown): void {
  if (typeof payload !== "object" || payload === null) return;
  if ("snapshot" in payload) {
    validateSnapshotCompatibility(payload.snapshot);
    return;
  }
  if (!("schema_version" in payload)) return;
  if (payload.schema_version !== "1.2") {
    throw new SimulationUnavailableError(
      "The simulation backend is out of date. Restart it with `pnpm backend:dev` (or restart `pnpm demo`) to load schema 1.2. The scene is showing the last compatible snapshot.",
    );
  }
  if (
    !("reservoir" in payload) ||
    typeof payload.reservoir !== "object" ||
    payload.reservoir === null
  ) {
    throw new SimulationUnavailableError(
      "The simulation snapshot is missing reservoir geometry.",
    );
  }
  const reservoir = payload.reservoir;
  for (const key of [
    "floor_elevation_m",
    "depth_at_capacity_m",
    "surface_elevation_m",
    "volume_m3",
    "capacity_m3",
  ] as const) {
    if (!(key in reservoir)) {
      throw new SimulationUnavailableError(
        `The simulation snapshot is missing reservoir ${key}. Restart the backend.`,
      );
    }
    const value: unknown = Reflect.get(reservoir, key);
    if (typeof value !== "number" || !Number.isFinite(value)) {
      throw new SimulationUnavailableError(
        `The simulation snapshot has invalid reservoir ${key}.`,
      );
    }
  }
}

async function requestJson<ResponseBody>(
  path: string,
  init?: RequestInit,
): Promise<ResponseBody> {
  let response: Response;
  try {
    response = await fetch(`${apiBase}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json" },
      cache: "no-store",
    });
  } catch {
    throw new SimulationUnavailableError(
      "The simulation backend is not reachable. Start it with `pnpm backend:dev`.",
    );
  }
  if (response.status === 409) {
    throw new SimulationConflictError(
      (await response.json()) as ConflictDetail,
    );
  }
  if (!response.ok) {
    throw new SimulationUnavailableError(
      `The simulation backend answered ${String(response.status)} for ${path}.`,
    );
  }
  const payload: unknown = await response.json();
  validateSnapshotCompatibility(payload);
  return payload as ResponseBody;
}

function postJson<ResponseBody>(path: string, body: unknown) {
  return requestJson<ResponseBody>(path, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export const simulationApi = {
  getState: () => requestJson<SimulationSnapshot>("/state"),
  advance: (request: AdvanceRequest) =>
    postJson<AdvanceResponse>("/advance", request),
  command: (request: CommandRequest) =>
    postJson<SimulationSnapshot>("/command", request),
  reset: (request: ResetRequest) =>
    postJson<SimulationSnapshot>("/reset", request),
  getEvents: (sinceId: number) =>
    requestJson<EventsPage>(`/events?since_id=${String(sinceId)}`),
  getScenarios: () => requestJson<ScenariosResponse>("/scenarios"),
  compare: (request: CompareRequest) =>
    postJson<CompareResponse>("/compare", request),
};
