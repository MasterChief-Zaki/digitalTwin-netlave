// Runs the Python backend through its virtual environment on any OS:
//   node scripts/backend.mjs setup         create backend/.venv and install requirements
//   node scripts/backend.mjs dev           start FastAPI on 127.0.0.1:8000 (one worker)
//   node scripts/backend.mjs test [args]   run pytest
import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const backendDirectory = join(
  dirname(fileURLToPath(import.meta.url)),
  "..",
  "backend",
);
const isWindows = process.platform === "win32";
const venvPython = join(
  backendDirectory,
  ".venv",
  isWindows ? "Scripts" : "bin",
  isWindows ? "python.exe" : "python",
);

function run(command, commandArguments) {
  const result = spawnSync(command, commandArguments, {
    cwd: backendDirectory,
    stdio: "inherit",
  });
  if (result.error) {
    console.error(result.error.message);
    process.exit(1);
  }
  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}

function requireVenv() {
  if (!existsSync(venvPython)) {
    console.error("backend/.venv is missing. Run `pnpm backend:setup` first.");
    process.exit(1);
  }
}

const [task, ...taskArguments] = process.argv.slice(2);

switch (task) {
  case "setup":
    if (!existsSync(venvPython)) {
      // The Windows launcher picks the newest installed Python 3.
      run(isWindows ? "py" : "python3", [
        ...(isWindows ? ["-3"] : []),
        "-m",
        "venv",
        ".venv",
      ]);
    }
    run(venvPython, ["-m", "pip", "install", "-r", "requirements.txt"]);
    break;
  case "dev":
    requireVenv();
    run(venvPython, [
      "-m",
      "uvicorn",
      "main:app",
      "--host",
      "127.0.0.1",
      "--port",
      "8000",
      "--workers",
      "1",
    ]);
    break;
  case "test":
    requireVenv();
    run(venvPython, ["-m", "pytest", ...taskArguments]);
    break;
  default:
    console.error("usage: node scripts/backend.mjs <setup|dev|test> [args]");
    process.exit(2);
}
