import type { SimulationSnapshot, Zone, ZoneId } from "@/types/simulation";

// Scene geometry. One scene unit is one metre horizontally; heights use a
// vertical scale so the terraces stay readable: metres of elevation * scale.
export const verticalScale = 0.12;

export interface TerraceLayout {
  id: ZoneId;
  center: readonly [number, number];
  width: number;
  depth: number;
}

export const terraceLayouts: readonly TerraceLayout[] = [
  { id: "A", center: [-8, 5], width: 7, depth: 5 },
  { id: "B", center: [1, 7], width: 7, depth: 5 },
  { id: "C", center: [10, -4], width: 7, depth: 5 },
];

// Used if a zone is missing from the snapshot.
const fallbackElevationM: Record<ZoneId, number> = { A: 2, B: 8, C: 34 };

export function terraceHeight(snapshot: SimulationSnapshot, id: ZoneId) {
  const zone = findZone(snapshot, id);
  return (zone?.elevation_m ?? fallbackElevationM[id]) * verticalScale;
}

export function findZone(
  snapshot: SimulationSnapshot,
  id: ZoneId,
): Zone | undefined {
  return snapshot.zones.find((zone) => zone.id === id);
}

export const reservoirCenter: readonly [number, number] = [0, -7];
export const reservoirRadius = 2.4;
export const reservoirBasinHeight = 1.6;
// The reservoir surface sits around +22 m when full.
export const reservoirTopY = 22 * verticalScale;
export const reservoirBottomY = reservoirTopY - reservoirBasinHeight;

export const filterPosition: readonly [number, number, number] = [0, 0.7, -2.5];
export const pumpPosition: readonly [number, number, number] = [4, 0.5, -2];
export const turbinePosition: readonly [number, number, number] = [
  -5.5, 1.2, -7,
];
export const solarPosition: readonly [number, number, number] = [-12, 0, -3];
