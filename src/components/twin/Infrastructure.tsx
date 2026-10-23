"use client";

import { Edges } from "@react-three/drei";
import { useFrame } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import {
  Color,
  DoubleSide,
  type Group,
  type Mesh,
  type MeshStandardMaterial,
} from "three";
import { useTwinStore } from "@/store/useTwinStore";
import { formatNumber, formatPercent } from "@/lib/format";
import { Label } from "./Label";
import {
  batteryPosition,
  filterInlet,
  filterOutlet,
  filterPosition,
  pumpInlet,
  pumpOutlet,
  pumpPosition,
  reservoirCenter,
  reservoirFloorY,
  reservoirRadius,
  reservoirRimY,
  reservoirWaterY,
  solarPosition,
  terraceLayouts,
  turbinePosition,
  zoneInlet,
  type Point,
} from "./layout";
import type { TwinPalette } from "./palette";
import { PipeRoute } from "./Pipe";
import {
  energySignals,
  waterSignals,
  zoneVisualState,
} from "./snapshotVisuals";

interface EquipmentProps {
  palette: TwinPalette;
}
const blend = (delta: number): number => 1 - Math.exp(-4 * delta);

function Reservoir({ palette }: EquipmentProps) {
  const snapshot = useTwinStore((state) => state.snapshot);
  const floorY = reservoirFloorY(snapshot);
  const rimY = reservoirRimY(snapshot);
  const depth = rimY - floorY;
  const waterRef = useRef<Mesh>(null);
  const generation = useRef(-1);
  useFrame((_state, delta) => {
    const water = waterRef.current;
    if (!water) return;
    const current = useTwinStore.getState().snapshot;
    const target = reservoirWaterY(current);
    // Reset is a new run, not an animated physical transition between runs.
    water.position.y =
      generation.current !== current.run_generation
        ? target
        : water.position.y + (target - water.position.y) * blend(delta);
    generation.current = current.run_generation;
    water.visible = current.reservoir.volume_m3 > 0;
  });
  return (
    <group position={[reservoirCenter[0], 0, reservoirCenter[1]]}>
      <mesh position={[0, floorY / 2, 0]} receiveShadow>
        <cylinderGeometry
          args={[reservoirRadius, reservoirRadius + 0.18, floorY, 32]}
        />
        <meshStandardMaterial color={palette.terrace} roughness={0.9} />
        <Edges color={palette.border} />
      </mesh>
      <mesh position={[0, floorY + depth / 2, 0]}>
        <cylinderGeometry
          args={[reservoirRadius, reservoirRadius, depth, 32, 1, true]}
        />
        <meshStandardMaterial
          color={palette.metal}
          transparent
          opacity={0.18}
          side={DoubleSide}
          depthWrite={false}
        />
      </mesh>
      {[floorY, rimY].map((height) => (
        <mesh
          key={height}
          position={[0, height, 0]}
          rotation={[-Math.PI / 2, 0, 0]}
        >
          <torusGeometry args={[reservoirRadius, 0.07, 6, 32]} />
          <meshStandardMaterial color={palette.metal} />
        </mesh>
      ))}
      <mesh
        ref={waterRef}
        name="reservoir-water"
        position={[0, reservoirWaterY(snapshot), 0]}
        rotation={[-Math.PI / 2, 0, 0]}
      >
        <circleGeometry args={[reservoirRadius - 0.08, 32]} />
        <meshStandardMaterial
          color={palette.water}
          emissive={palette.water}
          emissiveIntensity={0.18}
          roughness={0.2}
          metalness={0.2}
          side={DoubleSide}
        />
      </mesh>
      <Label
        text={`RESERVOIR · ${formatNumber(snapshot.reservoir.volume_m3)} m³`}
        position={[0, rimY + 0.85, 0]}
      />
    </group>
  );
}

function Turbine({ palette }: EquipmentProps) {
  const rotor = useRef<Group>(null);
  const power = useTwinStore((state) => state.snapshot.energy.hydro_power_w);
  useFrame((_state, delta) => {
    if (rotor.current)
      rotor.current.rotation.z +=
        Math.min(
          useTwinStore.getState().snapshot.energy.hydro_power_w * 0.012,
          8,
        ) * delta;
  });
  return (
    <group position={turbinePosition}>
      <mesh rotation={[Math.PI / 2, 0, 0]}>
        <cylinderGeometry args={[0.7, 0.7, 0.7, 16]} />
        <meshStandardMaterial color={palette.metal} />
      </mesh>
      <group ref={rotor} position={[0, 0, 0.42]}>
        {[0, 1, 2, 3].map((blade) => (
          <mesh key={blade} rotation={[0, 0, (blade * Math.PI) / 4]}>
            <boxGeometry args={[1.25, 0.1, 0.12]} />
            <meshStandardMaterial
              color={palette.hydro}
              emissive={palette.hydro}
              emissiveIntensity={0.25}
            />
          </mesh>
        ))}
      </group>
      <Label
        text={`HYDRO · ${formatNumber(power)} W`}
        position={[0, 1.15, 0]}
      />
    </group>
  );
}

function SolarArray({ palette }: EquipmentProps) {
  const power = useTwinStore((state) => state.snapshot.energy.solar_power_w);
  return (
    <group position={solarPosition}>
      {[-2.0, 0, 2.0].map((offset) => (
        <group key={offset} position={[0, 0.85, offset]}>
          <mesh rotation={[-0.35, 0, 0]} castShadow>
            <boxGeometry args={[3.1, 0.1, 1.7]} />
            <meshStandardMaterial
              color={palette.zoneB}
              emissive={palette.solar}
              emissiveIntensity={power > 0 ? 0.08 : 0.01}
              metalness={0.25}
              roughness={0.4}
            />
            <Edges color={palette.metal} />
          </mesh>
          {[-0.75, 0.75].map((support) => (
            <mesh key={support} position={[support, -0.35, 0]}>
              <boxGeometry args={[0.08, 0.7, 0.08]} />
              <meshStandardMaterial color={palette.metal} />
            </mesh>
          ))}
          {[-1, 0, 1].map((cell) => (
            <mesh
              key={cell}
              position={[cell, 0.08, 0]}
              rotation={[-0.35, 0, 0]}
            >
              <boxGeometry args={[0.015, 0.01, 1.65]} />
              <meshBasicMaterial color={palette.solar} />
            </mesh>
          ))}
        </group>
      ))}
      <Label text={`SOLAR · ${formatNumber(power)} W`} position={[0, 1.9, 0]} />
    </group>
  );
}

function Battery({ palette }: EquipmentProps) {
  const snapshot = useTwinStore((state) => state.snapshot);
  const fill = useRef<Mesh>(null);
  const generation = useRef(-1);
  useFrame((_state, delta) => {
    if (!fill.current) return;
    const current = useTwinStore.getState().snapshot;
    const target = current.energy.battery_soc_0_1 * 1.4;
    fill.current.scale.y =
      generation.current !== current.run_generation
        ? target
        : fill.current.scale.y + (target - fill.current.scale.y) * blend(delta);
    generation.current = current.run_generation;
    fill.current.position.y = 0.18 + fill.current.scale.y / 2;
  });
  return (
    <group position={batteryPosition}>
      <mesh position={[0, 0.9, 0]}>
        <boxGeometry args={[1.2, 1.8, 0.8]} />
        <meshStandardMaterial
          color={palette.metal}
          transparent
          opacity={0.18}
          depthWrite={false}
        />
        <Edges color={palette.metal} />
      </mesh>
      <mesh
        ref={fill}
        name="battery-charge"
        scale={[1, snapshot.energy.battery_soc_0_1 * 1.4, 1]}
        position={[0, 0.18 + snapshot.energy.battery_soc_0_1 * 0.7, 0]}
      >
        <boxGeometry args={[1, 1, 0.65]} />
        <meshStandardMaterial
          color={palette.solar}
          emissive={palette.solar}
          emissiveIntensity={0.18}
        />
      </mesh>
      <Label
        text={`BATTERY · ${formatPercent(snapshot.energy.battery_soc_0_1, 0)}`}
        position={[0, 2.35, 0]}
      />
    </group>
  );
}

function FilterUnit({ palette }: EquipmentProps) {
  const filter = useTwinStore((state) => state.snapshot.filtration);
  const material = useRef<MeshStandardMaterial>(null);
  const target = useMemo(() => new Color(), []);
  useFrame((_state, delta) => {
    if (!material.current) return;
    const current = useTwinStore.getState().snapshot.filtration;
    target.copy(
      current.flushing || current.flush_required
        ? palette.warning
        : palette.active,
    );
    material.current.color.lerp(target, blend(delta));
    material.current.emissive.copy(material.current.color);
    material.current.emissiveIntensity = current.flushing
      ? 0.5
      : 0.15 + current.clog_index_0_1 * 0.35;
  });
  return (
    <group position={filterPosition}>
      <mesh rotation={[Math.PI / 2, 0, 0]}>
        <cylinderGeometry args={[0.55, 0.55, 1.6, 16]} />
        <meshStandardMaterial
          ref={material}
          color={palette.active}
          emissive={palette.active}
          emissiveIntensity={0.25}
        />
        <Edges color={palette.border} />
      </mesh>
      <mesh position={[0, -0.85, 0]}>
        <boxGeometry args={[1.5, 0.15, 1.8]} />
        <meshStandardMaterial color={palette.metal} />
      </mesh>
      <Label
        text={
          filter.flushing
            ? "FILTER · BACKFLUSH"
            : `FILTER · ${formatNumber(filter.pressure_drop_pa / 1000, 1)} kPa`
        }
        position={[0, 1.05, 0]}
      />
    </group>
  );
}

function PumpUnit({ palette }: EquipmentProps) {
  const running = useTwinStore((state) => state.snapshot.pump.running);
  const material = useRef<MeshStandardMaterial>(null);
  const target = useMemo(() => new Color(), []);
  useFrame((_state, delta) => {
    if (!material.current) return;
    const visual = zoneVisualState(useTwinStore.getState().snapshot, "C");
    target.copy(visual === "waiting" ? palette.warning : palette[visual]);
    material.current.emissive.lerp(target, blend(delta));
  });
  return (
    <group position={pumpPosition}>
      <mesh rotation={[0, 0, Math.PI / 2]}>
        <cylinderGeometry args={[0.4, 0.4, 1.6, 16]} />
        <meshStandardMaterial
          ref={material}
          color={palette.metal}
          emissive={palette.idle}
          emissiveIntensity={0.65}
        />
      </mesh>
      <mesh position={[0, -0.5, 0]}>
        <boxGeometry args={[2, 0.15, 1.2]} />
        <meshStandardMaterial color={palette.terrace} />
        <Edges color={palette.border} />
      </mesh>
      <Label
        text={running ? "PUMP C · RUNNING" : "PUMP C · STOPPED"}
        position={[0, 0.95, 0]}
      />
    </group>
  );
}

export function Infrastructure({ palette }: EquipmentProps) {
  const snapshot = useTwinStore((state) => state.snapshot);
  const rim = reservoirRimY(snapshot);
  const outlet: Point = [
    reservoirCenter[0],
    reservoirFloorY(snapshot) + 0.05,
    reservoirCenter[1] + reservoirRadius,
  ];
  const inletEnd: Point = [
    reservoirCenter[0] - reservoirRadius,
    rim,
    reservoirCenter[1],
  ];
  const batteryBus: Point = [-3, 0.15, -4.3];
  const batteryPort: Point = [batteryPosition[0], 0.15, batteryPosition[2]];
  return (
    <>
      <Reservoir palette={palette} />
      <Turbine palette={palette} />
      <SolarArray palette={palette} />
      <Battery palette={palette} />
      <FilterUnit palette={palette} />
      <PumpUnit palette={palette} />
      <PipeRoute
        points={[
          [-15, turbinePosition[1], turbinePosition[2]],
          turbinePosition,
          [-3, turbinePosition[1], turbinePosition[2]],
          [-3, rim, turbinePosition[2]],
          inletEnd,
        ]}
        color={palette.hydro}
        readSignal={waterSignals.inlet}
        name="tse-inlet"
      />
      <PipeRoute
        points={[outlet, [0, outlet[1], -3.4], filterInlet]}
        color={palette.water}
        readSignal={waterSignals.irrigation}
        name="reservoir-outlet"
      />
      {terraceLayouts
        .filter((layout) => layout.id !== "C")
        .map((layout) => {
          const inlet = zoneInlet(snapshot, layout);
          return (
            <PipeRoute
              key={layout.id}
              points={[
                filterOutlet,
                [0, filterOutlet[1], 0],
                [inlet[0], filterOutlet[1], 0],
                [inlet[0], inlet[1], 0],
                inlet,
              ]}
              color={palette[`zone${layout.id}`]}
              readSignal={waterSignals[layout.id]}
              name={`zone-${layout.id}-feed`}
            />
          );
        })}
      <PipeRoute
        points={[
          filterOutlet,
          [pumpInlet[0], filterOutlet[1], filterOutlet[2]],
          [pumpInlet[0], pumpInlet[1], filterOutlet[2]],
          pumpInlet,
        ]}
        color={palette.zoneC}
        readSignal={waterSignals.C}
      />
      {terraceLayouts
        .filter((layout) => layout.id === "C")
        .map((layout) => {
          const inlet = zoneInlet(snapshot, layout);
          return (
            <PipeRoute
              key={layout.id}
              points={[
                pumpOutlet,
                [6, pumpOutlet[1], pumpOutlet[2]],
                [6, inlet[1], pumpOutlet[2]],
                [6, inlet[1], inlet[2]],
                inlet,
              ]}
              color={palette.zoneC}
              readSignal={waterSignals.C}
              name="zone-C-feed"
            />
          );
        })}
      <PipeRoute
        points={[
          [0, rim, reservoirCenter[1] - reservoirRadius],
          [0, rim, -11],
          [0, 0.05, -11],
          [5, 0.05, -11],
        ]}
        color={palette.water}
        readSignal={waterSignals.overflow}
        name="overflow"
      />
      <Label
        text="OVERFLOW / UNMODELED OUTLET"
        position={[1.5, 0.7, -12]}
        height={0.5}
      />
      <PipeRoute
        points={[
          [solarPosition[0], 0.15, solarPosition[2]],
          [batteryBus[0], 0.15, solarPosition[2]],
          batteryBus,
        ]}
        color={palette.solar}
        readSignal={energySignals.solar}
        radius={0.035}
        dashed
      />
      <PipeRoute
        points={[
          turbinePosition,
          [-5.5, 0.15, -7.5],
          [-5.5, 0.15, -4.3],
          batteryBus,
        ]}
        color={palette.hydro}
        readSignal={energySignals.hydro}
        radius={0.035}
        dashed
      />
      <PipeRoute
        points={[batteryBus, [2, 0.15, -4.3], [2, 0.15, -2.6], pumpInlet]}
        color={palette.solar}
        readSignal={energySignals.pumping}
        radius={0.035}
        dashed
      />
      <PipeRoute
        points={[batteryBus, [batteryPort[0], 0.15, -4.3], batteryPort]}
        color={palette.solar}
        readSignal={energySignals.charging}
        radius={0.03}
        dashed
      />
      <PipeRoute
        points={[
          [batteryPort[0] + 0.15, 0.15, batteryPort[2]],
          [batteryPort[0] + 0.15, 0.15, -4.15],
          [batteryBus[0], 0.15, -4.15],
          batteryBus,
        ]}
        color={palette.accent}
        readSignal={energySignals.discharging}
        radius={0.03}
        dashed
      />
      <Label text="DC BUS" position={[-3, 0.55, -4.3]} height={0.45} />
    </>
  );
}
