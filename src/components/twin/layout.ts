import type { SimulationSnapshot, Zone, ZoneId } from "@/types/simulation";

// Compressed schematic footprints, not surveyed horizontal distances.
// All elevation values use the same metres-to-scene display scale.
export const verticalScale = 0.16;
export type Point = readonly [number, number, number];
export const cameraTarget: Point = [0, 1.6, 0];
export const cameraPosition: Point = [30, 28, 34];

export interface TerraceLayout {
  id: ZoneId;
  center: readonly [number, number];
  width: number;
  depth: number;
}

export const terraceLayouts: readonly TerraceLayout[] = [
  { id: "A", center: [-8, 5], width: 7, depth: 5.6 },
  { id: "B", center: [1, 7], width: 7, depth: 5.6 },
  { id: "C", center: [10, -2], width: 7, depth: 5.6 },
];

export function terraceHeight(
  snapshot: SimulationSnapshot,
  id: ZoneId,
): number {
  return (findZone(snapshot, id)?.elevation_m ?? 0) * verticalScale;
}

export function findZone(
  snapshot: SimulationSnapshot,
  id: ZoneId,
): Zone | undefined {
  return snapshot.zones.find((zone) => zone.id === id);
}

export const reservoirCenter: readonly [number, number] = [0, -7.5];
export const reservoirRadius = 2.4;
export const filterPosition: Point = [0, 1.3, -2.6];
export const pumpPosition: Point = [4, 0.7, -2.6];
export const turbinePosition: Point = [-5.5, 2.8, -7.5];
export const solarPosition: Point = [-11, 0, -3.2];
export const batteryPosition: Point = [-6, 0, -1.5];
export const filterInlet: Point = [0, 1.3, -3.4];
export const filterOutlet: Point = [0, 1.3, -1.8];
export const pumpInlet: Point = [3.2, 0.7, -2.6];
export const pumpOutlet: Point = [4.8, 0.7, -2.6];

export function reservoirFloorY(snapshot: SimulationSnapshot): number {
  return snapshot.reservoir.floor_elevation_m * verticalScale;
}

export function reservoirRimY(snapshot: SimulationSnapshot): number {
  return (
    (snapshot.reservoir.floor_elevation_m +
      snapshot.reservoir.depth_at_capacity_m) *
    verticalScale
  );
}

export function reservoirWaterY(snapshot: SimulationSnapshot): number {
  return snapshot.reservoir.surface_elevation_m * verticalScale;
}

export function zoneInlet(
  snapshot: SimulationSnapshot,
  layout: TerraceLayout,
): Point {
  return [
    layout.center[0],
    terraceHeight(snapshot, layout.id) + 0.12,
    layout.center[1] - layout.depth / 2,
  ];
}
