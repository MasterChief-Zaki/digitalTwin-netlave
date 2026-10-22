import type { NextConfig } from "next";

// The FastAPI simulation runs as a single local process; see `pnpm backend:dev`.
const simulationBackendUrl = "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  cacheComponents: true,
  partialPrefetching: true,
  rewrites() {
    return Promise.resolve([
      { source: "/api/:path*", destination: `${simulationBackendUrl}/:path*` },
    ]);
  },
};

export default nextConfig;
