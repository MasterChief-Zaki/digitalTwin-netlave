"use client";

import { useFrame } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import {
  Quaternion,
  Vector3,
  type Color,
  type MeshStandardMaterial,
} from "three";
import { useTwinStore } from "@/store/useTwinStore";
import type { SimulationSnapshot } from "@/types/simulation";

const brightIntensity = 1.1;
const dimIntensity = 0.06;
const smoothingRate = 6;
const pipeRadius = 0.14;
const upAxis = new Vector3(0, 1, 0);

type Point = readonly [number, number, number];

interface PipeProps {
  start: Point;
  end: Point;
  color: Color;
  // Maps the snapshot to a flow in m3/s; the pipe glows while it is positive.
  readFlow: (snapshot: SimulationSnapshot) => number;
}

// A straight pipe segment, colored by its zone and bright while water moves.
export function Pipe({ start, end, color, readFlow }: PipeProps) {
  const materialRef = useRef<MeshStandardMaterial>(null);
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
    if (material === null) {
      return;
    }
    const flowing = readFlow(useTwinStore.getState().snapshot) > 0;
    const target = flowing ? brightIntensity : dimIntensity;
    const blend = 1 - Math.exp(-smoothingRate * delta);
    material.emissiveIntensity += (target - material.emissiveIntensity) * blend;
  });

  return (
    <mesh position={midpoint} quaternion={orientation}>
      <cylinderGeometry args={[pipeRadius, pipeRadius, length, 8]} />
      <meshStandardMaterial
        ref={materialRef}
        color={color}
        emissive={color}
        emissiveIntensity={dimIntensity}
      />
    </mesh>
  );
}
