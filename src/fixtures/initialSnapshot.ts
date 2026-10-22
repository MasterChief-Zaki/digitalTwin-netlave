import type { SimulationSnapshot } from "@/types/simulation";
import initialSnapshotJson from "./initial-snapshot.json";

// The step-0 snapshot the backend contract tests validate, so the dashboard can
// render before the simulation answers. JSON imports widen string literals, so
// the contract type is asserted here once.
export const initialSnapshot = initialSnapshotJson as SimulationSnapshot;
