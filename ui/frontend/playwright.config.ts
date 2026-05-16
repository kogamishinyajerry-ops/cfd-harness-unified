// Playwright config · V67-C bootstrap (V67-C.1).
// Headless browser e2e tests for the workbench UI · run via `npx playwright test`.
// Spawns vite dev server on :5173 if not already running.

import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  // V68-A.4: snapshots land in __visual_baselines__/<projectName>/<test>/<name>
  // so score_visualization.sh's find under __visual_baselines__/ picks them up.
  snapshotPathTemplate:
    "__visual_baselines__/{projectName}/{testFilePath}-snapshots/{arg}{ext}",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: process.env.CI ? "github" : "list",
  timeout: 30_000,
  use: {
    baseURL: "http://localhost:5173",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    headless: true,
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  // V68-B.5 · webServer is an ARRAY · spawns BOTH fastapi backend (port 8001
  // to avoid colliding with a developer's already-running :8000 backend) AND
  // vite frontend (port 5173 · proxies /api → 127.0.0.1:8001).
  //
  // MSW is intentionally OFF here (no VITE_MSW env). The whole point of V68-B
  // is that e2e runs against the real fastapi serving real corpus data.
  // V68-A's MSW-on configuration is still available via `VITE_MSW=1` env var
  // for offline-airplane work or isolation specs that want MSW intercept.
  webServer: [
    {
      command:
        "uv run uvicorn ui.backend.main:app --port 8001 --host 127.0.0.1",
      url: "http://127.0.0.1:8001/api/cases",
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
      cwd: "../../",
    },
    {
      command: "npm run dev -- --port 5173",
      env: { CFD_BACKEND_PORT: "8001" },
      url: "http://localhost:5173",
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
    },
  ],
});
