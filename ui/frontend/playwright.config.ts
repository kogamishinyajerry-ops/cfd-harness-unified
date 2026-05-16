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
  webServer: {
    // V68-A.1: VITE_MSW=1 enables MSW service worker so /workbench/case/{id}
    // can render against the in-browser mock backend without a real fastapi.
    command: "npm run dev -- --port 5173",
    env: { VITE_MSW: "1" },
    url: "http://localhost:5173",
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
});
