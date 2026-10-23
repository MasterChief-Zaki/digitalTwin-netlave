"use client";

import { OrbitControls } from "@react-three/drei";
import { Canvas } from "@react-three/fiber";
import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { Forest } from "./Forest";
import { Infrastructure } from "./Infrastructure";
import { cameraPosition, cameraTarget } from "./layout";
import { SceneTelemetry } from "./SceneTelemetry";
import { readPalette, type TwinPalette } from "./palette";

function browserSupportsWebGl(): boolean {
  const probe = document.createElement("canvas");
  // The installed three.js renderer requires WebGL2, not WebGL1.
  const context = probe.getContext("webgl2");
  if (!context) return false;
  context.getExtension("WEBGL_lose_context")?.loseContext();
  return true;
}

interface TwinCanvasProps {
  // Shown instead of the scene when the browser cannot create a WebGL context.
  unavailable: ReactNode;
}

// The only entry point to three.js; load it through LazyTwin so it stays out of the initial bundle.
export function TwinCanvas({ unavailable }: TwinCanvasProps) {
  const [palette, setPalette] = useState<TwinPalette | undefined>(undefined);
  const [webGlSupported, setWebGlSupported] = useState(true);

  useEffect(() => {
    // Tokens live in CSS and WebGL support is a browser fact, so both are read after mounting.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setWebGlSupported(browserSupportsWebGl());
    setPalette(readPalette());
  }, []);

  if (!webGlSupported) {
    return unavailable;
  }
  if (palette === undefined) {
    return null;
  }

  return (
    <Canvas
      dpr={[1, 1.5]}
      orthographic
      shadows="percentage"
      camera={{ position: [...cameraPosition], zoom: 19, near: 0.1, far: 150 }}
      aria-label="Live schematic forest digital twin"
      fallback={unavailable}
    >
      <color attach="background" args={[palette.background]} />
      <ambientLight intensity={0.85} />
      <directionalLight
        position={[8, 22, 12]}
        intensity={2.2}
        castShadow
        shadow-mapSize={[1024, 1024]}
        shadow-camera-left={-20}
        shadow-camera-right={20}
        shadow-camera-top={18}
        shadow-camera-bottom={-18}
        shadow-bias={-0.001}
      />
      <directionalLight
        position={[-12, 8, -10]}
        intensity={0.7}
        color={palette.accent}
      />
      <OrbitControls
        enableDamping
        enablePan={false}
        target={[...cameraTarget]}
        minPolarAngle={0.35}
        maxPolarAngle={Math.PI / 2.15}
        minZoom={10}
        maxZoom={32}
      />
      <Forest palette={palette} />
      <Infrastructure palette={palette} />
      <SceneTelemetry />
    </Canvas>
  );
}
