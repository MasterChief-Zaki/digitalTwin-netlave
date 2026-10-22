"use client";

import { Edges } from "@react-three/drei";
import { useFrame, type ThreeEvent } from "@react-three/fiber";
import { useEffect, useMemo, useRef } from "react";
import {
  Color,
  ConeGeometry,
  CylinderGeometry,
  MeshStandardMaterial,
  Object3D,
  type InstancedMesh,
} from "three";
import { useTwinStore } from "@/store/useTwinStore";
import type { SimulationSnapshot, ZoneId } from "@/types/simulation";
import { Label } from "./Label";
import {
  findZone,
  terraceHeight,
  terraceLayouts,
  type TerraceLayout,
} from "./layout";
import type { TwinPalette } from "./palette";

const treesPerTerrace = 50;
const smoothingRate = 4;
const treeSeedByZone: Record<ZoneId, number> = { A: 11, B: 23, C: 37 };

interface TreePlacement {
  x: number;
  z: number;
  scale: number;
}

// Small deterministic PRNG so the forest looks the same on every load.
function createRandom(seed: number): () => number {
  let state = seed;
  return () => {
    state = (state + 0x6d2b79f5) | 0;
    let mixed = Math.imul(state ^ (state >>> 15), 1 | state);
    mixed = (mixed + Math.imul(mixed ^ (mixed >>> 7), 61 | mixed)) ^ mixed;
    return ((mixed ^ (mixed >>> 14)) >>> 0) / 4294967296;
  };
}

function placeTrees(layout: TerraceLayout): TreePlacement[] {
  const random = createRandom(treeSeedByZone[layout.id]);
  const placements: TreePlacement[] = [];
  for (let index = 0; index < treesPerTerrace; index += 1) {
    placements.push({
      x: (random() - 0.5) * (layout.width - 0.8),
      z: (random() - 0.5) * (layout.depth - 0.8),
      scale: 0.7 + random() * 0.6,
    });
  }
  return placements;
}

// Trees are decorative; let clicks pass through to the terrace beneath.
function ignoreRaycast() {
  return undefined;
}

function zoneStateColor(
  snapshot: SimulationSnapshot,
  id: ZoneId,
  palette: TwinPalette,
): Color {
  const rejected = snapshot.decisions.some(
    (decision) => decision.zone_id === id && !decision.accepted,
  );
  if (rejected) {
    return palette.fault;
  }
  return findZone(snapshot, id)?.valve_open === true
    ? palette.active
    : palette.idle;
}

interface TreesProps {
  layout: TerraceLayout;
  palette: TwinPalette;
  canopyGeometry: ConeGeometry;
  trunkGeometry: CylinderGeometry;
  trunkMaterial: MeshStandardMaterial;
}

function Trees({
  layout,
  palette,
  canopyGeometry,
  trunkGeometry,
  trunkMaterial,
}: TreesProps) {
  const placements = useMemo(() => placeTrees(layout), [layout]);
  const canopyMaterial = useMemo(
    () => new MeshStandardMaterial({ color: palette.healthyCanopy }),
    [palette],
  );
  const canopyTarget = useMemo(() => new Color(), []);
  const canopyRef = useRef<InstancedMesh>(null);
  const trunkRef = useRef<InstancedMesh>(null);

  useEffect(() => {
    const canopy = canopyRef.current;
    const trunk = trunkRef.current;
    if (canopy === null || trunk === null) {
      return;
    }
    const dummy = new Object3D();
    placements.forEach((placement, index) => {
      dummy.position.set(placement.x, 0.2 * placement.scale, placement.z);
      dummy.scale.setScalar(placement.scale);
      dummy.updateMatrix();
      trunk.setMatrixAt(index, dummy.matrix);
      dummy.position.set(placement.x, 0.4 * placement.scale + 0.6, placement.z);
      dummy.updateMatrix();
      canopy.setMatrixAt(index, dummy.matrix);
    });
    canopy.instanceMatrix.needsUpdate = true;
    trunk.instanceMatrix.needsUpdate = true;
  }, [placements]);

  useEffect(() => {
    return () => {
      canopyMaterial.dispose();
    };
  }, [canopyMaterial]);

  useFrame((_state, delta) => {
    const zone = findZone(useTwinStore.getState().snapshot, layout.id);
    const stress = zone?.water_stress_0_1 ?? 0;
    canopyTarget
      .copy(palette.healthyCanopy)
      .lerp(palette.dryCanopy, Math.min(Math.max(stress, 0), 1));
    canopyMaterial.color.lerp(
      canopyTarget,
      1 - Math.exp(-smoothingRate * delta),
    );
  });

  return (
    <>
      <instancedMesh
        ref={trunkRef}
        args={[trunkGeometry, trunkMaterial, treesPerTerrace]}
        raycast={ignoreRaycast}
      />
      <instancedMesh
        ref={canopyRef}
        args={[canopyGeometry, canopyMaterial, treesPerTerrace]}
        raycast={ignoreRaycast}
      />
    </>
  );
}

interface TerraceProps extends Omit<TreesProps, "layout"> {
  layout: TerraceLayout;
}

function Terrace({ layout, palette, ...treeProps }: TerraceProps) {
  const height = useTwinStore((state) =>
    terraceHeight(state.snapshot, layout.id),
  );
  const selected = useTwinStore((state) => state.selectedZoneId === layout.id);
  const selectZone = useTwinStore((state) => state.selectZone);
  const tintTarget = useMemo(() => new Color(), []);
  const topMaterial = useMemo(
    () =>
      new MeshStandardMaterial({
        color: palette.terrace,
        emissive: palette.idle,
        emissiveIntensity: 0.35,
      }),
    [palette],
  );

  useEffect(() => {
    return () => {
      topMaterial.dispose();
    };
  }, [topMaterial]);

  useFrame((_state, delta) => {
    tintTarget.copy(
      zoneStateColor(useTwinStore.getState().snapshot, layout.id, palette),
    );
    topMaterial.emissive.lerp(tintTarget, 1 - Math.exp(-smoothingRate * delta));
  });

  const handleClick = (event: ThreeEvent<MouseEvent>) => {
    event.stopPropagation();
    selectZone(layout.id);
  };
  const handlePointerOver = (event: ThreeEvent<PointerEvent>) => {
    event.stopPropagation();
    document.body.style.cursor = "pointer";
  };
  const handlePointerOut = () => {
    document.body.style.cursor = "auto";
  };

  return (
    <group position={[layout.center[0], 0, layout.center[1]]}>
      <mesh
        position={[0, height / 2, 0]}
        scale={[layout.width, height, layout.depth]}
        material={topMaterial}
        onClick={handleClick}
        onPointerOver={handlePointerOver}
        onPointerOut={handlePointerOut}
      >
        <boxGeometry />
        <Edges
          visible
          color={selected ? palette.accent : palette.border}
          lineWidth={selected ? 3 : 1}
        />
      </mesh>
      <group position={[0, height, 0]}>
        <Trees layout={layout} palette={palette} {...treeProps} />
      </group>
      <Label
        text={`Zone ${layout.id}`}
        position={[0, height + 2.6, layout.depth / 2 - 0.5]}
      />
    </group>
  );
}

interface ForestProps {
  palette: TwinPalette;
}

// The ground plane, three elevated terraces and ~150 instanced trees.
export function Forest({ palette }: ForestProps) {
  const canopyGeometry = useMemo(() => new ConeGeometry(0.5, 1.2, 7), []);
  const trunkGeometry = useMemo(
    () => new CylinderGeometry(0.08, 0.1, 0.4, 5),
    [],
  );
  const trunkMaterial = useMemo(
    () => new MeshStandardMaterial({ color: palette.trunk }),
    [palette],
  );

  useEffect(() => {
    return () => {
      canopyGeometry.dispose();
      trunkGeometry.dispose();
      trunkMaterial.dispose();
    };
  }, [canopyGeometry, trunkGeometry, trunkMaterial]);

  return (
    <>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[-1, -0.01, 0]}>
        <planeGeometry args={[44, 30]} />
        <meshStandardMaterial color={palette.surface} />
      </mesh>
      {terraceLayouts.map((layout) => (
        <Terrace
          key={layout.id}
          layout={layout}
          palette={palette}
          canopyGeometry={canopyGeometry}
          trunkGeometry={trunkGeometry}
          trunkMaterial={trunkMaterial}
        />
      ))}
    </>
  );
}
