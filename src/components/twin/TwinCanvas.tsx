"use client";

import { OrbitControls } from "@react-three/drei";
import { Canvas } from "@react-three/fiber";
import { useEffect, useState } from "react";
import { Forest } from "./Forest";
import { Infrastructure } from "./Infrastructure";
import { reservoirTopY } from "./layout";
import { readPalette, type TwinPalette } from "./palette";

// The only entry point to three.js; load it through LazyTwin so it stays out of the initial bundle.
export function TwinCanvas() {
  const [palette, setPalette] = useState<TwinPalette | undefined>(undefined);

  useEffect(() => {
    // Tokens live in CSS, so they can only be read after mounting in the browser.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setPalette(readPalette());
  }, []);

  if (palette === undefined) {
    return null;
  }

  return (
    <Canvas
      dpr={[1, 1.5]}
      camera={{ position: [27, 21, 30], fov: 38 }}
      fallback={<p>WebGL is not available, so the 3D site view cannot load.</p>}
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
