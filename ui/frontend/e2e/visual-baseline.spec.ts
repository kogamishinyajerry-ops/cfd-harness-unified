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

  // V68-C.4 · 4 new baselines for the V68-C UI surfaces (charter §4
  // ≥16 PNG threshold). Each snapshot covers a V68-C-introduced state
  // that didn't exist in V68-A/B baselines.

  test("13 · workbench index with case_002a gold-pending card (V68-C.3)", async ({
    page,
  }) => {
    await page.goto("/workbench");
    await page
      .waitForLoadState("networkidle", { timeout: 8_000 })
      .catch(() => {});
    await page.waitForSelector("[data-testid='case-card-case_002a']", {
      timeout: 12_000,
    });
    await expect(page).toHaveScreenshot("13-index-with-apu-bay.png", {
      maxDiffPixelRatio: 0.01,
      animations: "disabled",
    });
  });

  test("14 · case_002a card cropped detail (gold-pending badge + disclaimer)", async ({
    page,
  }) => {
    await page.goto("/workbench");
    const card = page.getByTestId("case-card-case_002a");
    await card.waitFor({ state: "attached", timeout: 12_000 });
    await expect(card).toHaveScreenshot("14-apu-bay-card-cropped.png", {
      maxDiffPixelRatio: 0.01,
      animations: "disabled",
    });
  });

  test("15 · workbench index full layout (post V68-C catalog 11 entries)", async ({
    page,
  }) => {
    await page.goto("/workbench");
    await page
      .waitForLoadState("networkidle", { timeout: 8_000 })
      .catch(() => {});
    await page.waitForSelector("[data-testid='case-card-case_002a']", {
      timeout: 12_000,
    });
    // Capture full page (long viewport) to lock in 11-card layout.
    await expect(page).toHaveScreenshot("15-index-fullpage.png", {
      fullPage: true,
      maxDiffPixelRatio: 0.01,
      animations: "disabled",
    });
  });

  test("16 · viewport dispatcher harness control rail (V68-A→C stable surface)", async ({
    page,
  }) => {
    await page.goto(HARNESS_URL);
    await page.waitForSelector("[data-testid='viewport-mode-dispatcher']", {
      timeout: 10_000,
    });
    // Snapshot the rail buttons specifically — proves the V68-C
    // changes didn't drift the existing UI substrate.
    const rail = page.locator("[data-testid='viewport-mode-button-geometry']").locator("..");
    await expect(rail).toHaveScreenshot("16-rail-control.png", {
      maxDiffPixelRatio: 0.01,
      animations: "disabled",
    });
  });

  // V69.4 · 2 new baselines for V69 UI surfaces (charter §4 ≥18 PNG)
  test("17 · case-detail StrictMode mount snapshot (V69-DONE-5 verified)", async ({
    page,
  }) => {
    // V69.4 StrictMode investigation: single-navigation mount of
    // /workbench/case/:id is deterministic. This baseline locks in
    // the rendered card structure so a future StrictMode regression
    // gets caught visually.
    await page.goto("/workbench/case/lid_driven_cavity?step=3");
    await page
      .waitForLoadState("networkidle", { timeout: 12_000 })
      .catch(() => {});
    await expect(page).toHaveScreenshot("17-case-detail-strictmode.png", {
      maxDiffPixelRatio: 0.01,
      animations: "disabled",
    });
  });

  test("18 · catalog with 11 entries + gold_pending case_002a (V69 regression)", async ({
    page,
  }) => {
    // Distinct from baseline 13 (V68-C.4): this one is a wide-format
    // catalog view at a different viewport size to lock the 11-card
    // grid + ⏳ badge under V69 advisor-stack changes.
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto("/workbench");
    await page.waitForSelector("[data-testid='case-card-case_002a']", {
      timeout: 12_000,
    });
    await expect(page).toHaveScreenshot("18-catalog-wide-v69.png", {
      maxDiffPixelRatio: 0.01,
      animations: "disabled",
    });
  });
});
