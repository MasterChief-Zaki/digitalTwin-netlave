import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/browser",
  workers: 1,
  timeout: 120_000,
  use: { baseURL: "http://127.0.0.1:3100", trace: "retain-on-failure" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command:
        "uv --directory backend run uvicorn main:app --host 127.0.0.1 --port 8100 --workers 1",
      url: "http://127.0.0.1:8100/state",
      reuseExistingServer: false,
    },
    {
      command: "pnpm build && pnpm exec next start --port 3100",
      url: "http://127.0.0.1:3100",
      timeout: 120_000,
      env: {
        SIMULATION_BACKEND_URL: "http://127.0.0.1:8100",
        NEXT_BUILD_DIRECTORY: ".next-browser",
      },
      reuseExistingServer: false,
    },
  ],
});
