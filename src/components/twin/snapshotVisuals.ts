import { reasonPresentation } from "@/lib/reasonCodes";
import type { SimulationSnapshot, ZoneId } from "@/types/simulation";
import { findZone } from "./layout";

export type ZoneVisualState = "active" | "idle" | "waiting" | "fault";

// Presentation only: never grants flow or infers unmet physical demand.
export function zoneVisualState(
  snapshot: SimulationSnapshot,
  id: ZoneId,
): ZoneVisualState {
  const decision = snapshot.decisions.find((item) => item.zone_id === id);
  if (decision?.reason_code.startsWith("SCHEDULER_")) return "waiting";
  if (decision && !decision.accepted) {
    return reasonPresentation[decision.reason_code].tone === "warning"
      ? "waiting"
      : "fault";
  }
  return findZone(snapshot, id)?.valve_open ? "active" : "idle";
}

export const waterSignals = {
  inlet: (snapshot: SimulationSnapshot): number =>
    snapshot.reservoir.inflow_m3_s,
  irrigation: (snapshot: SimulationSnapshot): number =>
    snapshot.zones.reduce((total, zone) => total + zone.delivered_flow_m3_s, 0),
  A: (snapshot: SimulationSnapshot): number =>
    findZone(snapshot, "A")?.delivered_flow_m3_s ?? 0,
  B: (snapshot: SimulationSnapshot): number =>
    findZone(snapshot, "B")?.delivered_flow_m3_s ?? 0,
  C: (snapshot: SimulationSnapshot): number =>
    findZone(snapshot, "C")?.delivered_flow_m3_s ?? 0,
  overflow: (snapshot: SimulationSnapshot): number =>
    snapshot.reservoir.overflow_flow_m3_s,
};

export const energySignals = {
  solar: (snapshot: SimulationSnapshot): number =>
    snapshot.energy.solar_power_w,
  hydro: (snapshot: SimulationSnapshot): number =>
    snapshot.energy.hydro_power_w,
  charging: (snapshot: SimulationSnapshot): number =>
    snapshot.energy.charge_power_w,
  discharging: (snapshot: SimulationSnapshot): number =>
    snapshot.energy.discharge_power_w,
  pumping: (snapshot: SimulationSnapshot): number =>
    snapshot.energy.pump_power_w,
};
