"use client";

import { Edges } from "@react-three/drei";
import { useFrame, type ThreeEvent } from "@react-three/fiber";
import { useEffect, useMemo, useRef } from "react";
import {
  Color,
  IcosahedronGeometry,
  CylinderGeometry,
  MeshStandardMaterial,
  Object3D,
  type InstancedMesh,
} from "three";
import { useTwinStore } from "@/store/useTwinStore";
import { Label } from "./Label";
import {
  findZone,
  terraceHeight,
  terraceLayouts,
  type TerraceLayout,
} from "./layout";
import type { TwinPalette } from "./palette";
import { PipeRoute } from "./Pipe";
import { waterSignals, zoneVisualState } from "./snapshotVisuals";

const columns = 8;
const rows = 5;
const treeCount = columns * rows;

interface TreesProps {
  layout: TerraceLayout;
  palette: TwinPalette;
  canopyGeometry: IcosahedronGeometry;
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
  const canopyRef = useRef<InstancedMesh>(null);
  const trunkRef = useRef<InstancedMesh>(null);
  const target = useMemo(() => new Color(), []);
  const canopyMaterial = useMemo(
    () =>
      new MeshStandardMaterial({
        color: palette.healthyCanopy,
        roughness: 0.95,
      }),
    [palette],
  );
  useEffect(() => {
    const canopy = canopyRef.current;
    const trunk = trunkRef.current;
    if (!canopy || !trunk) return;
    const placement = new Object3D();
    for (let index = 0; index < treeCount; index += 1) {
      const column = index % columns;
      const row = Math.floor(index / columns);
      const height = 0.9 + ((index * 17 + layout.id.charCodeAt(0)) % 7) * 0.045;
      const horizontal = (column / (columns - 1) - 0.5) * (layout.width - 1.1);
      const depth = (row / (rows - 1) - 0.5) * (layout.depth - 1.6);
      placement.position.set(horizontal, 0.3 * height, depth);
      placement.scale.set(1, height, 1);
      placement.updateMatrix();
      trunk.setMatrixAt(index, placement.matrix);
      placement.position.y = 0.88 * height;
      placement.scale.set(0.85, 1.2 * height, 0.85);
      placement.rotation.y = index * 0.7;
      placement.updateMatrix();
      canopy.setMatrixAt(index, placement.matrix);
    }
    canopy.instanceMatrix.needsUpdate = true;
    trunk.instanceMatrix.needsUpdate = true;
    canopy.computeBoundingSphere();
    trunk.computeBoundingSphere();
  }, [layout]);
  useEffect(
    () => () => {
      canopyMaterial.dispose();
    },
    [canopyMaterial],
  );
  useFrame((_state, delta) => {
    const stress =
      findZone(useTwinStore.getState().snapshot, layout.id)?.water_stress_0_1 ??
      0;
    target
      .copy(palette.healthyCanopy)
      .lerp(palette.dryCanopy, Math.min(1, Math.max(0, stress)));
    canopyMaterial.color.lerp(target, 1 - Math.exp(-4 * delta));
  });
  return (
    <>
      <instancedMesh
        ref={trunkRef}
        args={[trunkGeometry, trunkMaterial, treeCount]}
        raycast={() => null}
      />
      <instancedMesh
        ref={canopyRef}
        args={[canopyGeometry, canopyMaterial, treeCount]}
        raycast={() => null}
        castShadow
      />
    </>
  );
}

function Terrace({ layout, palette, ...treeProps }: TreesProps) {
  const zone = useTwinStore((state) => findZone(state.snapshot, layout.id));
  const height = useTwinStore((state) =>
    terraceHeight(state.snapshot, layout.id),
  );
  const selected = useTwinStore((state) => state.selectedZoneId === layout.id);
  const selectZone = useTwinStore((state) => state.selectZone);
  const materialRef = useRef<MeshStandardMaterial>(null);
  const target = useMemo(() => new Color(), []);
  const color = palette[`zone${layout.id}`];
  const laterals = useMemo(
    () =>
      Array.from({ length: rows }, (_, row) => {
        const depth = (row / (rows - 1) - 0.5) * (layout.depth - 1.6);
        return [
          [-layout.width / 2 + 0.3, 0.04, depth],
          [layout.width / 2 - 0.3, 0.04, depth],
        ] as const;
      }),
    [layout],
  );
  useFrame((_state, delta) => {
    const visual = zoneVisualState(useTwinStore.getState().snapshot, layout.id);
    const material = materialRef.current;
    if (!material) return;
    target.copy(visual === "waiting" ? palette.warning : palette[visual]);
    material.emissive.lerp(target, 1 - Math.exp(-4 * delta));
  });
  const click = (event: ThreeEvent<MouseEvent>) => {
    event.stopPropagation();
    selectZone(layout.id);
  };
  return (
    <group position={[layout.center[0], 0, layout.center[1]]}>
      <mesh position={[0, height / 2 - 0.12, 0]} onClick={click} receiveShadow>
        <boxGeometry args={[layout.width, height + 0.24, layout.depth]} />
        <meshStandardMaterial color={palette.terrace} roughness={0.95} />
        <Edges color={palette.border} />
      </mesh>
      <group position={[0, height, 0]}>
        <mesh
          name={`terrace-${layout.id}`}
          position={[0, 0.02, 0]}
          onClick={click}
          onPointerOver={(event) => {
            event.stopPropagation();
            document.body.style.cursor = "pointer";
          }}
          onPointerOut={() => {
            document.body.style.cursor = "auto";
          }}
          receiveShadow
        >
          <boxGeometry
            args={[layout.width + 0.06, 0.08, layout.depth + 0.06]}
          />
          <meshStandardMaterial
            ref={materialRef}
            color={palette.surface}
            emissive={palette.idle}
            emissiveIntensity={0.3}
          />
          <Edges
            color={selected ? palette.accent : color}
            lineWidth={selected ? 3 : 1}
          />
        </mesh>
        <Trees layout={layout} palette={palette} {...treeProps} />
        {laterals.map((points, index) => (
          <PipeRoute
            key={index}
            points={points}
            color={color}
            readSignal={waterSignals[layout.id]}
            radius={0.025}
          />
        ))}
        <PipeRoute
          points={[
            [0, 0.12, -layout.depth / 2],
            [-layout.width / 2 + 0.3, 0.12, -layout.depth / 2],
            [-layout.width / 2 + 0.3, 0.12, layout.depth / 2 - 0.8],
          ]}
          color={color}
          readSignal={waterSignals[layout.id]}
          radius={0.05}
        />
        <Label
          text={`ZONE ${layout.id} · ${zone?.feed_mode === "PUMPED" ? "PUMPED" : "GRAVITY"} · +${String(zone?.elevation_m ?? 0)} m`}
          position={[0, 1.9, layout.depth / 2]}
          height={0.65}
        />
      </group>
    </group>
  );
}

export function Forest({ palette }: { palette: TwinPalette }) {
  const canopyGeometry = useMemo(() => new IcosahedronGeometry(0.38, 0), []);
  const trunkGeometry = useMemo(
    () => new CylinderGeometry(0.05, 0.07, 0.6, 5),
    [],
  );
  const trunkMaterial = useMemo(
    () => new MeshStandardMaterial({ color: palette.trunk }),
    [palette],
  );
  useEffect(
    () => () => {
      canopyGeometry.dispose();
      trunkGeometry.dispose();
      trunkMaterial.dispose();
    },
    [canopyGeometry, trunkGeometry, trunkMaterial],
  );
  return (
    <>
      <mesh position={[0, -0.45, 0]} receiveShadow>
        <boxGeometry args={[33, 0.5, 25]} />
        <meshStandardMaterial color={palette.surface} roughness={1} />
        <Edges color={palette.border} />
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
      <Label
        text="TSE FOREST / SCHEMATIC"
        position={[-10, 0.2, 11]}
        height={0.6}
      />
    </>
  );
}
