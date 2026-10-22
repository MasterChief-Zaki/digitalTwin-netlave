"use client";

import { useFrame } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import { Color, MeshStandardMaterial, type Group, type Mesh } from "three";
import { useTwinStore } from "@/store/useTwinStore";
import type { SimulationSnapshot, ZoneId } from "@/types/simulation";
import { Label } from "./Label";
import {
  filterPosition,
  findZone,
  pumpPosition,
  reservoirBasinHeight,
  reservoirBottomY,
  reservoirCenter,
  reservoirRadius,
  reservoirTopY,
  solarPosition,
  terraceHeight,
  turbinePosition,
} from "./layout";
import type { TwinPalette } from "./palette";
import { Pipe } from "./Pipe";

const smoothingRate = 3;
const waterRadius = reservoirRadius - 0.1;
const minimumWaterHeight = 0.02;
// Rotor radians per second for each watt of hydro power.
const rotorSpeedPerWatt = 0.01;
const maximumRotorSpeed = 14;
const solarFullPowerW = 6000;

function blendFor(delta: number, rate: number): number {
  return 1 - Math.exp(-rate * delta);
}

function deliveredFlow(snapshot: SimulationSnapshot, id: ZoneId): number {
  return findZone(snapshot, id)?.delivered_flow_m3_s ?? 0;
}

function readGravityFlowA(snapshot: SimulationSnapshot): number {
  return deliveredFlow(snapshot, "A");
}

function readGravityFlowB(snapshot: SimulationSnapshot): number {
  return deliveredFlow(snapshot, "B");
}

function readPumpedFlowC(snapshot: SimulationSnapshot): number {
  return deliveredFlow(snapshot, "C");
}

function readTotalFlow(snapshot: SimulationSnapshot): number {
  return (
    deliveredFlow(snapshot, "A") +
    deliveredFlow(snapshot, "B") +
    deliveredFlow(snapshot, "C")
  );
}

function readHydroPower(snapshot: SimulationSnapshot): number {
  return snapshot.energy.hydro_power_w;
}

interface InfrastructureProps {
  palette: TwinPalette;
}

function Reservoir({ palette }: InfrastructureProps) {
  const waterRef = useRef<Mesh>(null);
  const spillRef = useRef<Mesh>(null);
  const fillRef = useRef(-1);
  const [centerX, centerZ] = reservoirCenter;

  useFrame((_state, delta) => {
    const water = waterRef.current;
    const spill = spillRef.current;
    if (water === null || spill === null) {
      return;
    }
    const { reservoir } = useTwinStore.getState().snapshot;
    const target =
      reservoir.capacity_m3 > 0
        ? Math.min(Math.max(reservoir.volume_m3 / reservoir.capacity_m3, 0), 1)
        : 0;
    // The first frame snaps to the value; later frames ease toward it.
    fillRef.current =
      fillRef.current < 0
        ? target
        : fillRef.current +
          (target - fillRef.current) * blendFor(delta, smoothingRate);
    const height = Math.max(
      fillRef.current * reservoirBasinHeight,
      minimumWaterHeight,
    );
    water.scale.y = height;
    water.position.y = reservoirBottomY + height / 2;
    spill.visible = reservoir.overflow_flow_m3_s > 0;
  });

  return (
    <group position={[centerX, 0, centerZ]}>
      <mesh position={[0, reservoirBottomY / 2, 0]}>
        <cylinderGeometry
          args={[reservoirRadius, reservoirRadius + 0.2, reservoirBottomY, 20]}
        />
        <meshStandardMaterial color={palette.terrace} />
      </mesh>
      <mesh position={[0, reservoirBottomY + reservoirBasinHeight / 2, 0]}>
        <cylinderGeometry
          args={[
            reservoirRadius,
            reservoirRadius,
            reservoirBasinHeight,
            20,
            1,
            true,
          ]}
        />
        <meshStandardMaterial
          color={palette.metal}
          transparent
          opacity={0.35}
          side={2}
        />
      </mesh>
      <mesh position={[0, reservoirBottomY, 0]}>
        <cylinderGeometry args={[waterRadius, waterRadius, 0.04, 20]} />
        <meshStandardMaterial color={palette.border} />
      </mesh>
      <mesh ref={waterRef} position={[0, reservoirBottomY, 0]}>
        <cylinderGeometry args={[waterRadius, waterRadius, 1, 20]} />
        <meshStandardMaterial
          color={palette.water}
          emissive={palette.water}
          emissiveIntensity={0.25}
          transparent
          opacity={0.85}
        />
      </mesh>
      <mesh
        ref={spillRef}
        position={[0, reservoirTopY - 0.6, reservoirRadius + 0.1]}
        visible={false}
      >
        <boxGeometry args={[0.7, 1.2, 0.12]} />
        <meshStandardMaterial
          color={palette.water}
          emissive={palette.water}
          emissiveIntensity={0.8}
        />
      </mesh>
      <Label text="Reservoir" position={[0, reservoirTopY + 1, 0]} />
    </group>
  );
}

function Turbine({ palette }: InfrastructureProps) {
  const rotorRef = useRef<Group>(null);
  const [x, y, z] = turbinePosition;

  useFrame((_state, delta) => {
    const rotor = rotorRef.current;
    if (rotor === null) {
      return;
    }
    const speed = Math.min(
      readHydroPower(useTwinStore.getState().snapshot) * rotorSpeedPerWatt,
      maximumRotorSpeed,
    );
    rotor.rotation.x += speed * delta;
  });

  return (
    <group position={[x, y, z]}>
      <mesh rotation={[0, 0, Math.PI / 2]}>
        <cylinderGeometry args={[0.55, 0.55, 1.2, 12]} />
        <meshStandardMaterial color={palette.metal} />
      </mesh>
      <group ref={rotorRef}>
        {[0, 1, 2, 3].map((blade) => (
          <mesh
            key={blade}
            rotation={[(blade * Math.PI) / 2, 0, 0]}
            position={[0, 0, 0]}
          >
            <boxGeometry args={[0.2, 1.7, 0.18]} />
            <meshStandardMaterial
              color={palette.hydro}
              emissive={palette.hydro}
              emissiveIntensity={0.4}
            />
          </mesh>
        ))}
      </group>
      <Label text="Turbine" position={[0, 1.4, 0]} />
    </group>
  );
}

function SolarPanel({
  palette,
  offset,
}: InfrastructureProps & { offset: number }) {
  const materialRef = useRef<MeshStandardMaterial>(null);

  useFrame((_state, delta) => {
    const material = materialRef.current;
    if (material === null) {
      return;
    }
    const target = Math.min(
      Math.max(
        useTwinStore.getState().snapshot.energy.solar_power_w / solarFullPowerW,
        0,
      ),
      1.5,
    );
    material.emissiveIntensity +=
      (target - material.emissiveIntensity) * blendFor(delta, smoothingRate);
  });

  return (
    <group position={[0, 0.9, offset]} rotation={[0, 0, -0.5]}>
      <mesh>
        <boxGeometry args={[1.8, 0.1, 2]} />
        <meshStandardMaterial
          ref={materialRef}
          color={palette.surface}
          emissive={palette.solar}
          emissiveIntensity={0}
        />
      </mesh>
      <mesh position={[0, -0.45, 0]}>
        <boxGeometry args={[0.1, 0.9, 0.1]} />
        <meshStandardMaterial color={palette.metal} />
      </mesh>
    </group>
  );
}

function SolarArray({ palette }: InfrastructureProps) {
  const [x, y, z] = solarPosition;
  return (
    <group position={[x, y, z]}>
      {[-2.4, 0, 2.4].map((offset) => (
        <SolarPanel key={offset} palette={palette} offset={offset} />
      ))}
      <Label text="Solar" position={[0, 2.4, 0]} />
    </group>
  );
}

function FilterUnit({ palette }: InfrastructureProps) {
  const materialRef = useRef<MeshStandardMaterial>(null);
  const tintTarget = useMemo(() => new Color(), []);
  const elapsedRef = useRef(0);
  const [x, y, z] = filterPosition;

  useFrame((_state, delta) => {
    const material = materialRef.current;
    if (material === null) {
      return;
    }
    const { filtration } = useTwinStore.getState().snapshot;
    const clog = Math.min(Math.max(filtration.clog_index_0_1, 0), 1);
    // Clean (active) to warning at half clogged, then to fault.
    if (clog < 0.5) {
      tintTarget.copy(palette.active).lerp(palette.warning, clog * 2);
    } else {
      tintTarget.copy(palette.warning).lerp(palette.fault, (clog - 0.5) * 2);
    }
    material.color.lerp(tintTarget, blendFor(delta, smoothingRate));
    elapsedRef.current += delta;
    material.emissive.copy(material.color);
    material.emissiveIntensity = filtration.flushing
      ? 0.55 + 0.45 * Math.sin(elapsedRef.current * 9)
      : 0.2;
  });

  return (
    <group position={[x, y, z]}>
      <mesh>
        <cylinderGeometry args={[0.7, 0.7, 1.4, 16]} />
        <meshStandardMaterial
          ref={materialRef}
          color={palette.active}
          emissive={palette.active}
          emissiveIntensity={0.2}
        />
      </mesh>
      <Label text="Filter" position={[0, 1.3, 0]} />
    </group>
  );
}

function PumpUnit({ palette }: InfrastructureProps) {
  const materialRef = useRef<MeshStandardMaterial>(null);
  const tintTarget = useMemo(() => new Color(), []);
  const [x, y, z] = pumpPosition;

  useFrame((_state, delta) => {
    const material = materialRef.current;
    if (material === null) {
      return;
    }
    const running = useTwinStore.getState().snapshot.pump.running;
    tintTarget.copy(running ? palette.active : palette.idle);
    material.color.lerp(tintTarget, blendFor(delta, smoothingRate));
    material.emissive.copy(material.color);
    material.emissiveIntensity = running ? 0.6 : 0.1;
  });

  return (
    <group position={[x, y, z]}>
      <mesh>
        <boxGeometry args={[1.4, 0.9, 1]} />
        <meshStandardMaterial
          ref={materialRef}
          color={palette.idle}
          emissive={palette.idle}
          emissiveIntensity={0.1}
        />
      </mesh>
      <Label text="Pump" position={[0, 1, 0]} />
    </group>
  );
}

// Reservoir, inlet turbine, solar array, shared filter, pump and the pipes.
export function Infrastructure({ palette }: InfrastructureProps) {
  const heightA = useTwinStore((state) => terraceHeight(state.snapshot, "A"));
  const heightB = useTwinStore((state) => terraceHeight(state.snapshot, "B"));
  const heightC = useTwinStore((state) => terraceHeight(state.snapshot, "C"));

  const pipes = useMemo(() => {
    const outlet = [0, 0.7, -4.5] as const;
    const filterTop = [0, 0.7, -2.5] as const;
    return {
      supply: { start: outlet, end: filterTop },
      toA: { start: filterTop, end: [-4.5, heightA + 0.1, 4] as const },
      toB: { start: filterTop, end: [0, heightB + 0.1, 4.5] as const },
      toPump: { start: filterTop, end: pumpPosition },
      pumpToC: {
        start: pumpPosition,
        end: [6.5, Math.max(heightC - 0.3, 0.6), -3] as const,
      },
      inlet: {
        start: [-9, turbinePosition[1], turbinePosition[2]] as const,
        end: [-2.4, turbinePosition[1], turbinePosition[2]] as const,
      },
    };
  }, [heightA, heightB, heightC]);

  return (
    <>
      <Reservoir palette={palette} />
      <Turbine palette={palette} />
      <SolarArray palette={palette} />
      <FilterUnit palette={palette} />
      <PumpUnit palette={palette} />
      <Pipe
        start={pipes.inlet.start}
        end={pipes.inlet.end}
        color={palette.hydro}
        readFlow={readHydroPower}
      />
      <Pipe
        start={pipes.supply.start}
        end={pipes.supply.end}
        color={palette.accent}
        readFlow={readTotalFlow}
      />
      <Pipe
        start={pipes.toA.start}
        end={pipes.toA.end}
        color={palette.zoneA}
        readFlow={readGravityFlowA}
      />
      <Pipe
        start={pipes.toB.start}
        end={pipes.toB.end}
        color={palette.zoneB}
        readFlow={readGravityFlowB}
      />
      <Pipe
        start={pipes.toPump.start}
        end={pipes.toPump.end}
        color={palette.zoneC}
        readFlow={readPumpedFlowC}
      />
      <Pipe
        start={pipes.pumpToC.start}
        end={pipes.pumpToC.end}
        color={palette.zoneC}
        readFlow={readPumpedFlowC}
      />
    </>
  );
}
