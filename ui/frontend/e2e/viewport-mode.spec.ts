// V68-A.4 · Playwright e2e for Viewport mode dispatcher (6 modes).
//
// Spec target (per V68-A fleet criteria): ≥4 PASS to clear the
// score_visualization mode_switch threshold.
//
// Strategy · the dispatcher is exercised against the dev-only harness
// route `/workbench/dev/viewport-mode` (ViewportModeDevPage) which mounts
// just the dispatcher + a step-id picker, in isolation from the heavy
// StepPanelShell tree. This eliminates StrictMode + Suspense + Step3State
// remount races that previously made the spec flaky on the case-detail
// route. The dispatcher itself is the same component used in production.

import { test, expect } from "@playwright/test";

const HARNESS_URL = "/workbench/dev/viewport-mode";

test.describe("V68-A.4 · viewport mode dispatcher", () => {
  test("workbench index renders without crash", async ({ page }) => {
    await page.goto("/workbench");
    await expect(page).toHaveTitle(/cfd-harness|workbench|harness/i, {
      timeout: 10_000,
    });
  });

  test("workbench SPA root mounts cleanly", async ({ page }) => {
    await page.goto("/workbench");
    await page.waitForLoadState("networkidle", { timeout: 8_000 }).catch(() => {});
    const root = page.locator("#root");
    await expect(root).toBeAttached();
  });

  test("dev harness mounts dispatcher with default mode for step 1", async ({
    page,
  }) => {
    await page.goto(HARNESS_URL);
    const dispatcher = page.getByTestId("viewport-mode-dispatcher");
    await expect(dispatcher).toBeAttached({ timeout: 10_000 });
    await expect(dispatcher).toHaveAttribute(
      "data-viewport-mode",
      "geometry",
    );
  });

  test("dispatcher renders all 6 mode buttons", async ({ page }) => {
    await page.goto(HARNESS_URL);
    await page.waitForSelector("[data-testid='viewport-mode-dispatcher']", {
      timeout: 10_000,
    });
    const modes = [
      "geometry",
      "mesh-wireframe",
      "bc-faces",
      "field-slice",
      "residuals",
      "report-grid",
    ];
    for (const m of modes) {
      const btn = page.getByTestId(`viewport-mode-button-${m}`);
      await expect(btn).toBeAttached({ timeout: 5_000 });
    }
  });

  test("clicking a mode button updates data-viewport-mode attribute", async ({
    page,
  }) => {
    await page.goto(HARNESS_URL);
    const dispatcher = page.getByTestId("viewport-mode-dispatcher");
    await expect(dispatcher).toBeAttached({ timeout: 10_000 });

    await page.getByTestId("viewport-mode-button-field-slice").click();
    await expect(dispatcher).toHaveAttribute(
      "data-viewport-mode",
      "field-slice",
    );

    await page.getByTestId("viewport-mode-button-report-grid").click();
    await expect(dispatcher).toHaveAttribute(
      "data-viewport-mode",
      "report-grid",
    );
  });

  test("toolbar marks active button with data-active=true", async ({
    page,
  }) => {
    await page.goto(HARNESS_URL);
    await page.waitForSelector("[data-testid='viewport-mode-dispatcher']", {
      timeout: 10_000,
    });
    await page.getByTestId("viewport-mode-button-mesh-wireframe").click();
    await expect(
      page.getByTestId("viewport-mode-button-mesh-wireframe"),
    ).toHaveAttribute("data-active", "true");
  });

  test("changing step id remounts with new default mode", async ({ page }) => {
    await page.goto(HARNESS_URL);
    const dispatcher = page.getByTestId("viewport-mode-dispatcher");
    await expect(dispatcher).toBeAttached({ timeout: 10_000 });
    // Step 1 → geometry
    await expect(dispatcher).toHaveAttribute(
      "data-viewport-mode",
      "geometry",
    );
    // Step 2 → mesh-wireframe
    await page.getByTestId("dev-step-button-2").click();
    await expect(dispatcher).toHaveAttribute(
      "data-viewport-mode",
      "mesh-wireframe",
    );
    // Step 5 → report-grid
    await page.getByTestId("dev-step-button-5").click();
    await expect(dispatcher).toHaveAttribute(
      "data-viewport-mode",
      "report-grid",
    );
  });
});
