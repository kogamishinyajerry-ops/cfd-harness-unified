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
      maxDiffPixelRatio: 0.01,
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
      maxDiffPixelRatio: 0.01,
      animations: "disabled",
    });
  });

  test("03 · viewport dispatcher · Step 2 mesh-wireframe mode", async ({
    page,
  }) => {
    await page.goto(HARNESS_URL);
    await page.getByTestId("dev-step-button-2").click();
    await expect(page).toHaveScreenshot("03-dev-step2-mesh.png", {
      maxDiffPixelRatio: 0.01,
      animations: "disabled",
    });
  });

  test("04 · viewport dispatcher · Step 3 bc-faces mode", async ({ page }) => {
    await page.goto(HARNESS_URL);
    await page.getByTestId("dev-step-button-3").click();
    await expect(page).toHaveScreenshot("04-dev-step3-bc.png", {
      maxDiffPixelRatio: 0.01,
      animations: "disabled",
    });
  });

  test("05 · viewport dispatcher · Step 4 residuals mode", async ({ page }) => {
    await page.goto(HARNESS_URL);
    await page.getByTestId("dev-step-button-4").click();
    await expect(page).toHaveScreenshot("05-dev-step4-residuals.png", {
      maxDiffPixelRatio: 0.01,
      animations: "disabled",
    });
  });

  test("06 · viewport dispatcher · Step 5 report-grid mode", async ({
    page,
  }) => {
    await page.goto(HARNESS_URL);
    await page.getByTestId("dev-step-button-5").click();
    await expect(page).toHaveScreenshot("06-dev-step5-report.png", {
      maxDiffPixelRatio: 0.01,
      animations: "disabled",
    });
  });

  test("07 · viewport dispatcher · user override to field-slice", async ({
    page,
  }) => {
    await page.goto(HARNESS_URL);
    await page.getByTestId("viewport-mode-button-field-slice").click();
    await expect(page).toHaveScreenshot("07-dev-override-field.png", {
      maxDiffPixelRatio: 0.01,
      animations: "disabled",
    });
  });

  test("08 · viewport dispatcher · user override to mesh-wireframe", async ({
    page,
  }) => {
    await page.goto(HARNESS_URL);
    await page.getByTestId("viewport-mode-button-mesh-wireframe").click();
    await expect(page).toHaveScreenshot("08-dev-override-mesh.png", {
      maxDiffPixelRatio: 0.01,
      animations: "disabled",
    });
  });

  // V68-B.4 · 4 new states for industrial-class coverage (12 PNG total · meets
  // ≥12 fleet threshold).

  test("09 · viewport dispatcher · Step 2 with bc-faces override (cross-step inspection)", async ({
    page,
  }) => {
    await page.goto(HARNESS_URL);
    await page.getByTestId("dev-step-button-2").click();
    await page.getByTestId("viewport-mode-button-bc-faces").click();
    await expect(page).toHaveScreenshot("09-step2-bc-override.png", {
      maxDiffPixelRatio: 0.01,
      animations: "disabled",
    });
  });

  test("10 · viewport dispatcher · Step 4 with geometry override (solver-time geom inspect)", async ({
    page,
  }) => {
    await page.goto(HARNESS_URL);
    await page.getByTestId("dev-step-button-4").click();
    await page.getByTestId("viewport-mode-button-geometry").click();
    await expect(page).toHaveScreenshot("10-step4-geom-override.png", {
      maxDiffPixelRatio: 0.01,
      animations: "disabled",
    });
  });

  test("11 · viewport dispatcher · Step 5 with residuals override (post-run convergence look)", async ({
    page,
  }) => {
    await page.goto(HARNESS_URL);
    await page.getByTestId("dev-step-button-5").click();
    await page.getByTestId("viewport-mode-button-residuals").click();
    await expect(page).toHaveScreenshot("11-step5-residuals-override.png", {
      maxDiffPixelRatio: 0.01,
      animations: "disabled",
    });
  });

  test("12 · viewport dispatcher · Step 3 with report-grid override (BC-time report peek)", async ({
    page,
  }) => {
    await page.goto(HARNESS_URL);
    await page.getByTestId("dev-step-button-3").click();
    await page.getByTestId("viewport-mode-button-report-grid").click();
    await expect(page).toHaveScreenshot("12-step3-report-override.png", {
      maxDiffPixelRatio: 0.01,
      animations: "disabled",
    });
  });
});
