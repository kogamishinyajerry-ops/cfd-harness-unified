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
  test("workbench index page renders the SPA shell", async ({ page }) => {
    // Use /workbench (WorkbenchIndexPage) — this route does NOT call
    // StepPanelShell + doesn't require a case-id fixture, so it works
    // offline of the backend.
    await page.goto("/workbench");
    await page.waitForLoadState("networkidle", { timeout: 8_000 }).catch(() => {
      // SSE / polling may keep network open — not a failure
    });

    // SPA shell renders #root + some body text · minimum smoke.
    const root = page.locator("#root");
    await expect(root).toBeAttached();
    const bodyText = await page.locator("body").innerText();
    expect(bodyText.length).toBeGreaterThan(0);
  });
});
