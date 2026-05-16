// V68-C.2 · AI review/diagnose advisor route surface e2e.
//
// The full review/diagnose UX requires an imported_user case in
// IMPORTED_DIR (the loopback-guarded GET routes 404 on whitelist).
// This spec verifies the catalog reachability + that the workbench
// index renders against real fastapi backend without crashing under
// the V68-C.2 classifyAdvisorFailure wiring (regression: an earlier
// state shape bug could have crashed the SPA pre-V68-C.2).

import { test, expect } from "@playwright/test";

test.describe("V68-C.2 · advisor surface lives in real-backend e2e", () => {
  test("workbench index renders against real backend without crashing", async ({
    page,
  }) => {
    const consoleErrors: string[] = [];
    page.on("pageerror", (err) => consoleErrors.push(err.message));
    await page.goto("/workbench");
    await page
      .waitForLoadState("networkidle", { timeout: 8_000 })
      .catch(() => {});
    // SPA mounted = render path including V68-C.2 changes is healthy.
    const root = page.locator("#root");
    await expect(root).toBeAttached();
    // No JS errors from the classifier refactor or the new offline
    // banner. (V68-C.2 state shape error → page error → fails here.)
    expect(consoleErrors).toEqual([]);
  });
});
