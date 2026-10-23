"use client";

import { useFrame } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import { OrthographicCamera, Vector3 } from "three";
import { useTwinStore } from "@/store/useTwinStore";
import { zoneVisualState } from "./snapshotVisuals";

// Fit the schematic on resize. OrbitControls still owns user zoom between resizes.
// The canvas metadata exposes actual rendered transforms for connection diagnostics.
export function SceneTelemetry() {
  const viewport = useRef({ width: 0, height: 0 });
  const projection = useMemo(() => new Vector3(), []);
  const elapsed = useRef(0);
  useFrame(({ gl, scene, camera, size }, delta) => {
    if (
      camera instanceof OrthographicCamera &&
      (size.width !== viewport.current.width ||
        size.height !== viewport.current.height)
    ) {
      camera.zoom = Math.min(size.width / 37, size.height / 27);
      camera.updateProjectionMatrix();
      viewport.current.width = size.width;
      viewport.current.height = size.height;
    }
    elapsed.current += delta;
    if (elapsed.current < 0.15) return;
    elapsed.current = 0;
    const snapshot = useTwinStore.getState().snapshot;
    const canvas = gl.domElement;
    const water = scene.getObjectByName("reservoir-water");
    const battery = scene.getObjectByName("battery-charge");
    canvas.dataset.renderedStep = String(snapshot.step);
    canvas.dataset.renderedGeneration = String(snapshot.run_generation);
    canvas.dataset.selectedZone = useTwinStore.getState().selectedZoneId;
    canvas.dataset.waterElevationY = String(water?.position.y ?? "");
    canvas.dataset.batteryFill = String(battery?.scale.y ?? "");
    canvas.dataset.inletMoving = String(
      scene.getObjectByName("tse-inlet-1-direction")?.visible ?? false,
    );
    canvas.dataset.pumpedWaterMoving = String(
      scene.getObjectByName("zone-C-feed-1-direction")?.visible ?? false,
    );
    canvas.dataset.overflowMoving = String(
      scene.getObjectByName("overflow-1-direction")?.visible ?? false,
    );
    for (const zone of snapshot.zones) {
      const terrace = scene.getObjectByName(`terrace-${zone.id}`);
      if (!terrace) continue;
      terrace.getWorldPosition(projection);
      projection.project(camera);
      canvas.dataset[`zone${zone.id}ScreenX`] = String(
        ((projection.x + 1) * size.width) / 2,
      );
      canvas.dataset[`zone${zone.id}ScreenY`] = String(
        ((1 - projection.y) * size.height) / 2,
      );
      canvas.dataset[`zone${zone.id}State`] = zoneVisualState(
        snapshot,
        zone.id,
      );
    }
  });
  return null;
}
