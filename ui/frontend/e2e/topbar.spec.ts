// V67-C.1 · Playwright e2e for TopBar 6-field visibility.
//
// Minimum viable e2e: load /workbench (WorkbenchIndexPage), verify the page
// loads without crashes and basic layout chrome is present. Full TopBar
// 6-field verification waits until /workbench/case/{id} can be loaded in
// e2e (needs backend fixture · V67-C.2 territory). For now this spec
// validates the bootstrap is healthy.

import { test, expect } from "@playwright/test";

test.describe("V67-C.1 · workbench shell loads (Playwright bootstrap)", () => {
  test("workbench index page renders without crash", async ({ page }) => {
    await page.goto("/workbench");
    // The vite dev server should respond with 200 + the SPA chrome.
    await expect(page).toHaveTitle(/cfd-harness|workbench|harness/i, {
      timeout: 10_000,
    });
    // body should not be empty
    const bodyText = await page.locator("body").innerText();
    expect(bodyText.length).toBeGreaterThan(0);
  });

  test("root redirects to /workbench", async ({ page }) => {
    await page.goto("/");
    await page.waitForURL(/\/workbench/, { timeout: 10_000 });
    expect(page.url()).toMatch(/\/workbench/);
  });
});

test.describe("V67-C.1 · TopBar 6-field smoke (component-render check)", () => {
  test("TopBar testid present when StepPanelShell renders", async ({
    page,
  }) => {
    // Use the demo / fixture caseId convention. If the backend isn't
    // running, the page may still render the shell with empty/error
    // state — TopBar should still be in the DOM because it's a pure
    // component above any data-fetching boundary.
    await page.goto("/workbench/case/demo_topbar_smoke");
    // Allow some time for the SPA route to render
    await page.waitForLoadState("networkidle", { timeout: 8_000 }).catch(() => {
      // network may stay open via SSE / polling — not a failure
    });

    // Look for any of the TopBar testids — minimal smoke
    const candidates = [
      "top-bar",
      "top-bar-case-id",
      "top-bar-truth-source",
      "top-bar-trust-gate",
      "top-bar-llm-offline",
      "top-bar-audit-pct",
      "top-bar-ai-advisor",
    ];
    let foundAny = false;
    for (const tid of candidates) {
      const count = await page.locator(`[data-testid="${tid}"]`).count();
      if (count > 0) {
        foundAny = true;
        break;
      }
    }
    // V67-C.1 minimum: at least the TopBar wrapper renders. If the
    // route requires backend data and it's unavailable, the page may
    // show an error state; in that case foundAny stays false and we
    // surface the failure honestly rather than skipping the test.
    expect(foundAny, "expected at least one TopBar testid in DOM").toBe(true);
  });
});
