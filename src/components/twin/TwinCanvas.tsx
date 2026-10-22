"use client";

import { OrbitControls } from "@react-three/drei";
import { Canvas } from "@react-three/fiber";
import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { Forest } from "./Forest";
import { Infrastructure } from "./Infrastructure";
import { reservoirTopY } from "./layout";
import { readPalette, type TwinPalette } from "./palette";

function browserSupportsWebGl(): boolean {
  const probe = document.createElement("canvas");
  return (probe.getContext("webgl2") ?? probe.getContext("webgl")) !== null;
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
      camera={{ position: [27, 21, 30], fov: 38 }}
      fallback={unavailable}
    >
      <color attach="background" args={[palette.background]} />
      <ambientLight intensity={0.9} />
      <directionalLight position={[12, 22, 10]} intensity={2.2} />
      <OrbitControls
        enableDamping
        enablePan={false}
        target={[0, reservoirTopY, 0]}
        minPolarAngle={0.35}
        maxPolarAngle={Math.PI / 2.15}
        minDistance={22}
        maxDistance={85}
      />
      <Forest palette={palette} />
      <Infrastructure palette={palette} />
    </Canvas>
  );
}
