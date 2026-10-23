"use client";

import { useFrame } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import {
  Quaternion,
  Vector3,
  type Color,
  type Mesh,
  type MeshStandardMaterial,
} from "three";
import { useTwinStore } from "@/store/useTwinStore";
import type { SimulationSnapshot } from "@/types/simulation";
import type { Point } from "./layout";

const upAxis = new Vector3(0, 1, 0);

interface PipeProps {
  start: Point;
  end: Point;
  color: Color;
  // Positive measured signal animates direction, never synthetic flow.
  readSignal: (snapshot: SimulationSnapshot) => number;
  radius?: number;
  dashed?: boolean;
  name?: string;
}

// Straight segment with a directional marker; speed is symbolic, not a velocity model.
export function Pipe({
  start,
  end,
  color,
  readSignal,
  radius = 0.09,
  dashed = false,
  name,
}: PipeProps) {
  const materialRef = useRef<MeshStandardMaterial>(null);
  const markerRef = useRef<Mesh>(null);
  const phase = useRef(0);
  const { midpoint, length, orientation } = useMemo(() => {
    const from = new Vector3(...start);
    const to = new Vector3(...end);
    const direction = to.clone().sub(from);
    return {
      midpoint: from.clone().add(to).multiplyScalar(0.5),
      length: direction.length(),
      orientation: new Quaternion().setFromUnitVectors(
        upAxis,
        direction.normalize(),
      ),
    };
  }, [start, end]);

  useFrame((_state, delta) => {
    const material = materialRef.current;
    const marker = markerRef.current;
    if (!material || !marker) return;
    const flowing = readSignal(useTwinStore.getState().snapshot) > 0;
    material.emissiveIntensity +=
      ((flowing ? 0.85 : 0.04) - material.emissiveIntensity) *
      (1 - Math.exp(-6 * delta));
    marker.visible = flowing;
    if (flowing) phase.current = (phase.current + delta * 0.45) % 1;
    marker.position.y = (phase.current - 0.5) * length;
  });

  return (
    <group position={midpoint} quaternion={orientation}>
      <mesh name={name}>
        <cylinderGeometry args={[radius, radius, length, 8]} />
        <meshStandardMaterial
          ref={materialRef}
          color={color}
          emissive={color}
          emissiveIntensity={0.04}
          transparent={dashed}
          opacity={dashed ? 0.45 : 1}
          roughness={0.5}
        />
      </mesh>
      <mesh
        ref={markerRef}
        name={name ? `${name}-direction` : undefined}
        visible={false}
        raycast={() => null}
      >
        <coneGeometry args={[radius * 2.6, radius * 6, 8]} />
        <meshBasicMaterial color={color} toneMapped={false} />
      </mesh>
    </group>
  );
}

export function PipeRoute({
  points,
  color,
  readSignal,
  radius,
  dashed,
  name,
}: Omit<PipeProps, "start" | "end"> & { points: readonly Point[] }) {
  return (
    <>
      {points.map((end, index) => {
        const start = points[index - 1];
        return start ? (
          <Pipe
            key={index}
            start={start}
            end={end}
            color={color}
            readSignal={readSignal}
            radius={radius}
            dashed={dashed}
            name={name ? `${name}-${String(index)}` : undefined}
          />
        ) : null;
      })}
    </>
  );
}
