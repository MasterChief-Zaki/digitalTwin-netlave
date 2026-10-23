import type { NextConfig } from "next";
import { fileURLToPath } from "node:url";

// The FastAPI simulation runs as a single local process; see `pnpm backend:dev`.
const simulationBackendUrl =
  process.env.SIMULATION_BACKEND_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  turbopack: { root: fileURLToPath(new URL(".", import.meta.url)) },
  distDir: process.env.NEXT_BUILD_DIRECTORY ?? ".next",
  typescript: {
    tsconfigPath: process.env.NEXT_TYPESCRIPT_CONFIG ?? "tsconfig.json",
  },
  cacheComponents: true,
  partialPrefetching: true,
  rewrites() {
    return Promise.resolve([
      { source: "/api/:path*", destination: `${simulationBackendUrl}/:path*` },
    ]);
  },
};

export default nextConfig;
