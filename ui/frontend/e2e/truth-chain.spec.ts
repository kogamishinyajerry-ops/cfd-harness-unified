// V67-C.7 · Playwright e2e for Truth Chain visibility (scaffolding stage).
//
// Truth Chain = TopBar 6 fields stay coherent as engineer navigates step 1→5.
// Full Truth Chain requires backend wiring + case fixture (V67-C.6.1 follow-on).
// This spec validates scaffolding: workbench index reachable, no console errors
// from the SPA boot.

import { test, expect } from "@playwright/test";

test.describe("V67-C.7 · Truth Chain scaffolding (route + boot)", () => {
  test("workbench index loads without console errors", async ({ page }) => {
    const consoleErrors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") consoleErrors.push(msg.text());
    });
    page.on("pageerror", (err) => consoleErrors.push(err.message));

    await page.goto("/workbench");
    await page.waitForLoadState("networkidle", { timeout: 8_000 }).catch(() => {});

    // Filter out network-related errors (backend may be offline in fleet runs)
    const nonNetworkErrors = consoleErrors.filter(
      (e) =>
        !/Failed to fetch|Failed to load resource|NetworkError|net::|ECONNREFUSED|aborted|HTTP \d{3}|status of \d{3}|Internal Server Error|Bad Gateway|Service Unavailable/i.test(
          e,
        ),
    );
    expect(
      nonNetworkErrors,
      `Non-network console errors: ${JSON.stringify(nonNetworkErrors, null, 2)}`,
    ).toEqual([]);
  });

  test("workbench index renders SPA root", async ({ page }) => {
    await page.goto("/workbench");
    const root = page.locator("#root");
    await expect(root).toBeAttached();
  });
});
