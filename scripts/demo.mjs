// Starts the simulation backend (port 8000) and the production Next.js server
// (port 3000) together for an offline demo. `pnpm demo` builds the dashboard
// first: production React redraws the dashboard several times faster than
// development mode. Ctrl+C stops both.
//
// Each server is stopped with its whole process tree. Stopping only `pnpm` can
// leave uvicorn or Next running on its port, and the next start then fails.
import { spawn, spawnSync } from "node:child_process";

const isWindows = process.platform === "win32";
const servers = [
  { name: "backend", scriptName: "backend:dev" },
  { name: "dashboard", scriptName: "start" },
];
let stopping = false;

const children = servers.map(({ name, scriptName }) => {
  const child = spawn("pnpm", [scriptName], {
    stdio: "inherit",
    shell: isWindows,
    detached: !isWindows,
  });
  child.on("exit", (code) => {
    if (!stopping) {
      console.error(
        `The ${name} stopped (exit ${String(code)}); stopping the demo.`,
      );
      stopAll(code ?? 1);
    }
  });
  return child;
});

console.log(
  "netLave digital twin: dashboard on http://localhost:3000, simulation API on http://127.0.0.1:8000. Ctrl+C stops both.",
);

function stopProcessTree(child) {
  if (child.pid === undefined || child.exitCode !== null) {
    return;
  }
  if (isWindows) {
    spawnSync("taskkill", ["/pid", String(child.pid), "/T", "/F"], {
      stdio: "ignore",
    });
  } else {
    try {
      process.kill(-child.pid, "SIGTERM");
    } catch {
      // Already gone.
    }
  }
}

function stopAll(exitCode) {
  stopping = true;
  children.forEach(stopProcessTree);
  process.exit(exitCode);
}

process.on("SIGINT", () => {
  stopAll(0);
});
process.on("SIGTERM", () => {
  stopAll(0);
});
