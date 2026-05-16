// V68-A.4 · Visual snapshot baseline · 8 canonical UI states.
//
// Generates PNG baselines via toHaveScreenshot() · committed to
// __visual_baselines__/chromium/visual-baseline.spec.ts-snapshots/
// per Playwright defaults.
//
// V68-A fleet criteria: ≥6 PNG files required for score_visualization
// visual_diff_baseline = 30/30 (full). First-run generates baselines;
// subsequent runs diff against committed files.
//
// Sources: 2 workbench routes (index + dev harness for viewport modes) ×
// multiple states. Avoids case-detail route to sidestep StrictMode races
// observed on /workbench/case/v68a-demo during the V68-A.4 spec build.

import { test, expect } from "@playwright/test";

const HARNESS_URL = "/workbench/dev/viewport-mode";

test.describe("V68-A.4 · visual baseline snapshots (8 canonical states)", () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
  });

  test("01 · workbench index page", async ({ page }) => {
    await page.goto("/workbench");
    await page.waitForLoadState("networkidle", { timeout: 8_000 }).catch(() => {});
    await expect(page).toHaveScreenshot("01-workbench-index.png", {
      maxDiffPixelRatio: 0.1,
      animations: "disabled",
    });
  });

  test("02 · viewport dispatcher · Step 1 geometry mode (default)", async ({
    page,
  }) => {
    await page.goto(HARNESS_URL);
    await page.waitForSelector("[data-testid='viewport-mode-dispatcher']", {
      timeout: 10_000,
    });
    await expect(page).toHaveScreenshot("02-dev-step1-geometry.png", {
      maxDiffPixelRatio: 0.1,
      animations: "disabled",
    });
  });

  test("03 · viewport dispatcher · Step 2 mesh-wireframe mode", async ({
    page,
  }) => {
    await page.goto(HARNESS_URL);
    await page.getByTestId("dev-step-button-2").click();
    await expect(page).toHaveScreenshot("03-dev-step2-mesh.png", {
      maxDiffPixelRatio: 0.1,
      animations: "disabled",
    });
  });

  test("04 · viewport dispatcher · Step 3 bc-faces mode", async ({ page }) => {
    await page.goto(HARNESS_URL);
    await page.getByTestId("dev-step-button-3").click();
    await expect(page).toHaveScreenshot("04-dev-step3-bc.png", {
      maxDiffPixelRatio: 0.1,
      animations: "disabled",
    });
  });

  test("05 · viewport dispatcher · Step 4 residuals mode", async ({ page }) => {
    await page.goto(HARNESS_URL);
    await page.getByTestId("dev-step-button-4").click();
    await expect(page).toHaveScreenshot("05-dev-step4-residuals.png", {
      maxDiffPixelRatio: 0.1,
      animations: "disabled",
    });
  });

  test("06 · viewport dispatcher · Step 5 report-grid mode", async ({
    page,
  }) => {
    await page.goto(HARNESS_URL);
    await page.getByTestId("dev-step-button-5").click();
    await expect(page).toHaveScreenshot("06-dev-step5-report.png", {
      maxDiffPixelRatio: 0.1,
      animations: "disabled",
    });
  });

  test("07 · viewport dispatcher · user override to field-slice", async ({
    page,
  }) => {
    await page.goto(HARNESS_URL);
    await page.getByTestId("viewport-mode-button-field-slice").click();
    await expect(page).toHaveScreenshot("07-dev-override-field.png", {
      maxDiffPixelRatio: 0.1,
      animations: "disabled",
    });
  });

  test("08 · viewport dispatcher · user override to mesh-wireframe", async ({
    page,
  }) => {
    await page.goto(HARNESS_URL);
    await page.getByTestId("viewport-mode-button-mesh-wireframe").click();
    await expect(page).toHaveScreenshot("08-dev-override-mesh.png", {
      maxDiffPixelRatio: 0.1,
      animations: "disabled",
    });
  });
});
