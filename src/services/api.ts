import type {
  AdvanceRequest,
  AdvanceResponse,
  CommandRequest,
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
  return (await response.json()) as ResponseBody;
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
};
