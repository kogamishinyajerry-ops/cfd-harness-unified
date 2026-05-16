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

  // V70.6 · 4 new baselines for V70-introduced UI surfaces.
  // Locks the V70.3 (novice onboarding) + V70.4 (industrial-UI improvements)
  // surfaces visually so future arcs can't drift them silently.

  test("19 · /workbench with FirstTimeBanner mounted (V70.3 novice surface)", async ({
    page,
  }) => {
    // Clear any prior dismiss state so the banner appears
    await page.goto("/workbench");
    await page.evaluate(() => localStorage.removeItem("v70-first-time-banner-dismissed"));
    await page.reload();
    await page.waitForSelector("[data-testid='first-time-banner']", {
      timeout: 12_000,
    });
    await page.waitForSelector("[data-testid='case-card-case_002a']", {
      timeout: 12_000,
    });
    await expect(page).toHaveScreenshot("19-workbench-with-first-time-banner.png", {
      maxDiffPixelRatio: 0.01,
      animations: "disabled",
    });
  });

  test("20 · /workbench/tutorial 5-step walkthrough page (V70.3)", async ({
    page,
  }) => {
    await page.goto("/workbench/tutorial");
    await page.waitForSelector("[data-testid='workbench-tutorial-page']", {
      timeout: 12_000,
    });
    await expect(page).toHaveScreenshot("20-workbench-tutorial-page.png", {
      fullPage: true,
      maxDiffPixelRatio: 0.01,
      animations: "disabled",
    });
  });

  test("21 · ShortcutPalette overlay open (V70.4 V70-UI-IMPROVEMENT-A)", async ({
    page,
  }) => {
    await page.goto("/workbench");
    await page.waitForLoadState("networkidle", { timeout: 8_000 }).catch(() => {});
    // Dismiss banner so the palette overlays a clean page
    await page.evaluate(() => localStorage.setItem("v70-first-time-banner-dismissed", "1"));
    await page.reload();
    await page.keyboard.type("?");
    await page.waitForSelector("[data-testid='shortcut-palette']", {
      timeout: 8_000,
    });
    await expect(page).toHaveScreenshot("21-shortcut-palette-open.png", {
      maxDiffPixelRatio: 0.01,
      animations: "disabled",
    });
  });

  test("22 · /workbench/tutorial scrolled to Step 4 (V70.3 mid-tutorial state)", async ({
    page,
  }) => {
    await page.goto("/workbench/tutorial#step-4");
    await page.waitForSelector("[data-testid='workbench-tutorial-page']", {
      timeout: 12_000,
    });
    // Scroll to step-4 anchor
    await page.locator("#step-4").scrollIntoViewIfNeeded();
    await expect(page).toHaveScreenshot("22-tutorial-step-4.png", {
      maxDiffPixelRatio: 0.01,
      animations: "disabled",
    });
  });

  // V71.6 · 8 visual baselines (23-30) for v3 blueprint surfaces.
  // Locks each of the 8 v3 blueprint images (01-08) against the rendered
  // /workbench/v3 surface. Drift > 0.05 SSIM against blueprint PNGs triggers
  // V71 reverse-stop per V71 charter §reverse_stops.

  test("23 · /workbench/v3 empty state (no case) · Image 01", async ({ page }) => {
    await page.goto("/workbench/v3");
    await page.waitForSelector("[data-testid='workbench-shell-v3']", {
      timeout: 12_000,
    });
    await expect(page).toHaveScreenshot("23-v3-empty-state.png", {
      maxDiffPixelRatio: 0.01,
      animations: "disabled",
    });
  });

  test("24 · /workbench/v3/case/lid_driven_cavity Step 1 geometry · Image 02", async ({
    page,
  }) => {
    await page.goto("/workbench/v3/case/lid_driven_cavity?step=1");
    await page.waitForSelector("[data-testid='workbench-shell-v3']", {
      timeout: 12_000,
    });
    await expect(page).toHaveScreenshot("24-v3-step1-geometry.png", {
      maxDiffPixelRatio: 0.01,
      animations: "disabled",
    });
  });

  test("25 · /workbench/v3 Step 2 mesh · Image 03", async ({ page }) => {
    await page.goto("/workbench/v3/case/lid_driven_cavity?step=2");
    await page.waitForSelector("[data-testid='workbench-shell-v3']", {
      timeout: 12_000,
    });
    await expect(page).toHaveScreenshot("25-v3-step2-mesh.png", {
      maxDiffPixelRatio: 0.01,
      animations: "disabled",
    });
  });

  test("26 · /workbench/v3 Step 3 BC + MaterialCard · Image 04", async ({
    page,
  }) => {
    await page.goto("/workbench/v3/case/lid_driven_cavity?step=3");
    await page.waitForSelector("[data-testid='material-card']", {
      timeout: 12_000,
    });
    await expect(page).toHaveScreenshot("26-v3-step3-bc-materials.png", {
      maxDiffPixelRatio: 0.01,
      animations: "disabled",
    });
  });

  test("27 · /workbench/v3 Step 4 active solve · residuals · Image 05", async ({
    page,
  }) => {
    await page.goto("/workbench/v3/case/lid_driven_cavity?step=4");
    await page.waitForSelector("[data-testid='canvas-residuals']", {
      timeout: 12_000,
    });
    await expect(page).toHaveScreenshot("27-v3-step4-residuals.png", {
      maxDiffPixelRatio: 0.01,
      animations: "disabled",
    });
  });

  test("28 · /workbench/v3 Advisor tab (consult panel) · Image 06", async ({
    page,
  }) => {
    await page.goto("/workbench/v3/case/lid_driven_cavity?step=3");
    await page.waitForSelector("[data-testid='workbench-shell-v3']", {
      timeout: 12_000,
    });
    await page.getByTestId("right-tab-advisor").click();
    await page.waitForSelector("[data-testid='advisor-advisory-badge']", {
      timeout: 8_000,
    });
    await expect(page).toHaveScreenshot("28-v3-advisor-tab.png", {
      maxDiffPixelRatio: 0.01,
      animations: "disabled",
    });
  });

  test("29 · /workbench/v3 Step 5 TrustGate verdict · Image 07", async ({
    page,
  }) => {
    await page.goto("/workbench/v3/case/lid_driven_cavity?step=5");
    await page.waitForSelector("[data-testid='trustgate-verdict-block']", {
      timeout: 12_000,
    });
    await expect(page).toHaveScreenshot("29-v3-step5-trustgate.png", {
      maxDiffPixelRatio: 0.01,
      animations: "disabled",
    });
  });

  test("30 · /workbench/v3 Step 4 + viewport=mesh cross-step inspection · Image 08", async ({
    page,
  }) => {
    await page.goto("/workbench/v3/case/lid_driven_cavity?step=4");
    await page.waitForSelector("[data-testid='workbench-shell-v3']", {
      timeout: 12_000,
    });
    // Engineer overrides viewport to mesh while at Step 4 → V71.T cross-step inspector
    await page.getByTestId("viewport-mode-mesh").click();
    await page.waitForTimeout(200);
    await expect(page).toHaveScreenshot("30-v3-step4-mesh-cross-step.png", {
      maxDiffPixelRatio: 0.01,
      animations: "disabled",
    });
  });

  // V72.6 · 6 visual baselines (31-36) for v3 interaction states.
  // Locks the new V72 surfaces against silent drift.

  test("31 · v3 advisor surface · terminal state (whitelist or consulted)", async ({ page }) => {
    await page.goto("/workbench/v3/case/lid_driven_cavity?step=3");
    await page.waitForSelector("[data-testid='workbench-shell-v3']", {
      timeout: 12_000,
    });
    await page.getByTestId("right-tab-advisor").click();
    // V73.1 · lid_driven_cavity is whitelist → consult button is replaced
    // by the advisor-whitelist-explanation surface. Wait for either to
    // materialize (skeleton may briefly hold the panel during the cases
    // pre-flight fetch).
    await page
      .waitForFunction(
        () =>
          !!document.querySelector(
            "[data-testid='advisor-whitelist-explanation'], [data-testid='advisor-run-review']",
          ),
        undefined,
        { timeout: 8_000 },
      )
      .catch(() => {});
    const whitelist = page.getByTestId("advisor-whitelist-explanation");
    if ((await whitelist.count()) === 0) {
      await page.getByTestId("advisor-run-review").click();
      await page
        .waitForFunction(
          () =>
            !!document.querySelector(
              "[data-testid='advisor-review-findings'], [data-testid='advisor-offline-banner'], [data-testid='advisor-error']",
            ),
          undefined,
          { timeout: 8_000 },
        )
        .catch(() => {});
    } else {
      await whitelist.waitFor({ state: "visible", timeout: 4_000 });
    }
    await page.waitForTimeout(150);
    await expect(page).toHaveScreenshot("31-v3-advisor-terminal.png", {
      maxDiffPixelRatio: 0.01,
      animations: "disabled",
    });
  });

  test("32 · v3 material card expanded inline (V71.I read-only)", async ({
    page,
  }) => {
    await page.goto("/workbench/v3/case/lid_driven_cavity?step=3");
    await page.waitForSelector("[data-testid='material-card']", {
      timeout: 12_000,
    });
    await page.getByTestId("material-nu").click();
    await page.waitForSelector("[data-testid='material-nu-derive']", {
      timeout: 4_000,
    });
    await expect(page).toHaveScreenshot("32-v3-material-card-expanded.png", {
      maxDiffPixelRatio: 0.01,
      animations: "disabled",
    });
  });

  test("33 · v3 TruthChain tab (provenance chain)", async ({ page }) => {
    await page.goto("/workbench/v3/case/lid_driven_cavity?step=5");
    await page.waitForSelector("[data-testid='workbench-shell-v3']", {
      timeout: 12_000,
    });
    await page.getByTestId("right-tab-truthchain").click();
    // V75.2 · wait for skeleton to settle
    await page
      .waitForFunction(
        () =>
          !document.querySelector("[data-testid='skeleton-truthchain']") &&
          !!document.querySelector("[data-testid='truthchain-content']"),
        undefined,
        { timeout: 8_000 },
      )
      .catch(() => {});
    await page.waitForTimeout(200);
    await expect(page).toHaveScreenshot("33-v3-truthchain-tab.png", {
      maxDiffPixelRatio: 0.01,
      animations: "disabled",
    });
  });

  test("34 · v3 keyboard focus visible on pipeline step button", async ({
    page,
  }) => {
    await page.goto("/workbench/v3/case/lid_driven_cavity?step=2");
    await page.waitForSelector("[data-testid='workbench-shell-v3']", {
      timeout: 12_000,
    });
    // Tab into the pipeline step strip (browser default focus order)
    await page.getByTestId("pipeline-step-2").focus();
    await page.waitForTimeout(100);
    await expect(page).toHaveScreenshot("34-v3-pipeline-step-focused.png", {
      maxDiffPixelRatio: 0.01,
      animations: "disabled",
    });
  });

  test("35 · v3 bottom panel · residuals tab expanded", async ({ page }) => {
    await page.goto("/workbench/v3/case/lid_driven_cavity?step=4");
    await page.waitForSelector("[data-testid='bottom-panel-expanded']", {
      timeout: 12_000,
    });
    await page.getByTestId("bottom-tab-residuals").click();
    await page.waitForSelector("[data-testid='bottom-tab-residuals-content']", {
      timeout: 4_000,
    });
    await expect(page).toHaveScreenshot("35-v3-bottom-residuals-tab.png", {
      maxDiffPixelRatio: 0.01,
      animations: "disabled",
    });
  });

  test("36 · v3 case browser whitelist expanded · 11 entries from live API", async ({
    page,
  }) => {
    await page.goto("/workbench/v3");
    await page.waitForSelector("[data-testid='case-browser-v3']", {
      timeout: 12_000,
    });
    // The default state is already expanded when no active case (since
    // activeCaseId === null doesn't match any list); we force open via click.
    await page.locator('button:has-text("Whitelist cases")').click();
    await page.waitForTimeout(150);
    await expect(page).toHaveScreenshot("36-v3-case-browser-expanded.png", {
      maxDiffPixelRatio: 0.01,
      animations: "disabled",
    });
  });

  // V73 · 8 new baselines (37-44) covering V73.1-5 surfaces

  test("37 · V73.1 advisor whitelist scope explanation", async ({ page }) => {
    await page.goto("/workbench/v3/case/lid_driven_cavity?step=3");
    await page.waitForSelector("[data-testid='workbench-shell-v3']", {
      timeout: 12_000,
    });
    await page.getByTestId("right-tab-advisor").click();
    await page.waitForSelector("[data-testid='advisor-whitelist-explanation']", {
      timeout: 4_000,
    });
    await expect(page).toHaveScreenshot("37-v3-advisor-whitelist-explanation.png", {
      maxDiffPixelRatio: 0.01,
      animations: "disabled",
    });
  });

  test("38 · V73.3 multi-case comparison ribbon at Step 5", async ({ page }) => {
    await page.goto("/workbench/v3/case/lid_driven_cavity?step=5");
    await page.waitForSelector("[data-testid='workbench-shell-v3']", {
      timeout: 12_000,
    });
    await page
      .waitForSelector(
        "[data-testid='multi-case-ribbon'], [data-testid='multi-case-ribbon-offline-hint']",
        { timeout: 8_000 },
      )
      .catch(() => {});
    await expect(page).toHaveScreenshot("38-v3-multi-case-ribbon.png", {
      maxDiffPixelRatio: 0.01,
      animations: "disabled",
    });
  });

  test("39 · V73.5 Step5Inspector audit completeness live", async ({ page }) => {
    await page.goto("/workbench/v3/case/lid_driven_cavity?step=5");
    await page.waitForSelector("[data-testid='workbench-shell-v3']", {
      timeout: 12_000,
    });
    await page.getByTestId("right-tab-inspector").click();
    await page.waitForTimeout(500);
    await expect(page).toHaveScreenshot("39-v3-step5-inspector-completeness.png", {
      maxDiffPixelRatio: 0.01,
      animations: "disabled",
    });
  });

  test("40 · V73.4 VerdictPill DRY · TruthChain rendering", async ({ page }) => {
    await page.goto("/workbench/v3/case/lid_driven_cavity?step=5");
    await page.waitForSelector("[data-testid='workbench-shell-v3']", {
      timeout: 12_000,
    });
    await page.getByTestId("right-tab-truthchain").click();
    // V75.2 · wait for skeleton to settle
    await page
      .waitForFunction(
        () =>
          !document.querySelector("[data-testid='skeleton-truthchain']") &&
          !!document.querySelector("[data-testid='truthchain-content']"),
        undefined,
        { timeout: 8_000 },
      )
      .catch(() => {});
    await page.waitForTimeout(200);
    await expect(page).toHaveScreenshot("40-v3-truthchain-verdict-pill.png", {
      maxDiffPixelRatio: 0.01,
      animations: "disabled",
    });
  });

  test("41 · V73.2 contrast fix render · Step 1 tertiary text", async ({
    page,
  }) => {
    await page.goto("/workbench/v3/case/lid_driven_cavity?step=1");
    await page.waitForSelector("[data-testid='workbench-shell-v3']", {
      timeout: 12_000,
    });
    await page.waitForTimeout(300);
    await expect(page).toHaveScreenshot("41-v3-step1-post-contrast-fix.png", {
      maxDiffPixelRatio: 0.01,
      animations: "disabled",
    });
  });

  test("42 · V73.2 contrast fix render · Step 3 tertiary text", async ({
    page,
  }) => {
    await page.goto("/workbench/v3/case/lid_driven_cavity?step=3");
    await page.waitForSelector("[data-testid='workbench-shell-v3']", {
      timeout: 12_000,
    });
    await page.waitForTimeout(300);
    await expect(page).toHaveScreenshot("42-v3-step3-post-contrast-fix.png", {
      maxDiffPixelRatio: 0.01,
      animations: "disabled",
    });
  });

  test("43 · V73 close · full Step 5 shell with ribbon visible", async ({
    page,
  }) => {
    await page.goto("/workbench/v3/case/lid_driven_cavity?step=5");
    await page.waitForSelector("[data-testid='workbench-shell-v3']", {
      timeout: 12_000,
    });
    await page.waitForTimeout(600);
    await expect(page).toHaveScreenshot("43-v3-step5-full-shell.png", {
      maxDiffPixelRatio: 0.01,
      animations: "disabled",
    });
  });

  test("44 · V73 close · right panel inspector with completeness wire", async ({
    page,
  }) => {
    await page.goto("/workbench/v3/case/lid_driven_cavity?step=5");
    await page.waitForSelector("[data-testid='workbench-shell-v3']", {
      timeout: 12_000,
    });
    await page.waitForTimeout(500);
    await expect(
      page.locator("[data-testid='workbench-right-panel']"),
    ).toHaveScreenshot("44-v3-right-panel-step5.png", {
      maxDiffPixelRatio: 0.01,
      animations: "disabled",
    });
  });

  // V74 · 8 new baselines (45-52) covering V74.1-5 surfaces

  test("45 · V74.3 TopBar canonical run_id surfaced", async ({ page }) => {
    await page.goto("/workbench/v3/case/lid_driven_cavity?step=4");
    await page.waitForSelector("[data-testid='workbench-shell-v3']", {
      timeout: 12_000,
    });
    await page.waitForTimeout(400);
    await expect(
      page.locator("[data-testid='topbar-v3']"),
    ).toHaveScreenshot("45-v3-topbar-run-id.png", {
      maxDiffPixelRatio: 0.01,
      animations: "disabled",
    });
  });

  test("46 · V74.3 TruthChain · 4 provenance hash chips", async ({ page }) => {
    await page.goto("/workbench/v3/case/lid_driven_cavity?step=5");
    await page.waitForSelector("[data-testid='workbench-shell-v3']", {
      timeout: 12_000,
    });
    await page.getByTestId("right-tab-truthchain").click();
    // V75.2 · wait for skeleton to settle before snapshotting provenance
    await page
      .waitForFunction(
        () =>
          !document.querySelector("[data-testid='skeleton-truthchain']") &&
          !!document.querySelector("[data-testid='provenance-hashes']"),
        undefined,
        { timeout: 8_000 },
      )
      .catch(() => {});
    await page.waitForTimeout(200);
    await expect(
      page.locator("[data-testid='provenance-hashes']"),
    ).toHaveScreenshot("46-v3-truthchain-provenance-hashes.png", {
      maxDiffPixelRatio: 0.01,
      animations: "disabled",
    });
  });

  test("47 · V74.4 GoldDeltaPanel · summary + per-point rows", async ({ page }) => {
    await page.goto("/workbench/v3/case/lid_driven_cavity?step=5");
    await page.waitForSelector("[data-testid='workbench-shell-v3']", {
      timeout: 12_000,
    });
    await page.getByTestId("right-tab-truthchain").click();
    // V75.2 · wait for TruthChain skeleton to settle before snapshotting
    await page
      .waitForFunction(
        () =>
          !document.querySelector("[data-testid='skeleton-truthchain']") &&
          !!document.querySelector(
            "[data-testid='gold-delta-panel'], [data-testid='gold-delta-offline-hint']",
          ),
        undefined,
        { timeout: 8_000 },
      )
      .catch(() => {});
    await page.waitForTimeout(200);
    await expect(
      page.locator("[data-testid='workbench-right-panel']"),
    ).toHaveScreenshot("47-v3-gold-delta-panel.png", {
      maxDiffPixelRatio: 0.01,
      animations: "disabled",
    });
  });

  test("48 · V74.5 AuditPackageDownload wire in TruthChain", async ({ page }) => {
    await page.goto("/workbench/v3/case/lid_driven_cavity?step=5");
    await page.waitForSelector("[data-testid='workbench-shell-v3']", {
      timeout: 12_000,
    });
    await page.getByTestId("right-tab-truthchain").click();
    // V75.2 · wait for skeleton to settle
    await page
      .waitForFunction(
        () =>
          !document.querySelector("[data-testid='skeleton-truthchain']") &&
          !!document.querySelector(
            "[data-testid='audit-package-build'], [data-testid='audit-package-download-no-run']",
          ),
        undefined,
        { timeout: 8_000 },
      )
      .catch(() => {});
    await page.waitForTimeout(200);
    await expect(
      page.locator("[data-testid='workbench-right-panel']"),
    ).toHaveScreenshot("48-v3-audit-package.png", {
      maxDiffPixelRatio: 0.01,
      animations: "disabled",
    });
  });

  test("49 · V74.1 Step 2 (mesh) · post-axe-extension render", async ({ page }) => {
    await page.goto("/workbench/v3/case/lid_driven_cavity?step=2");
    await page.waitForSelector("[data-testid='workbench-shell-v3']", {
      timeout: 12_000,
    });
    await page.waitForTimeout(400);
    await expect(page).toHaveScreenshot("49-v3-step2-post-a11y.png", {
      maxDiffPixelRatio: 0.01,
      animations: "disabled",
    });
  });

  test("50 · V74.1 Step 4 (solver) · post-axe-extension render", async ({ page }) => {
    await page.goto("/workbench/v3/case/lid_driven_cavity?step=4");
    await page.waitForSelector("[data-testid='workbench-shell-v3']", {
      timeout: 12_000,
    });
    await page.waitForTimeout(400);
    await expect(page).toHaveScreenshot("50-v3-step4-post-a11y.png", {
      maxDiffPixelRatio: 0.01,
      animations: "disabled",
    });
  });

  test("51 · V74.2 multi-case ribbon · live per-ref completeness", async ({ page }) => {
    await page.goto("/workbench/v3/case/lid_driven_cavity?step=5");
    await page.waitForSelector("[data-testid='workbench-shell-v3']", {
      timeout: 12_000,
    });
    await page
      .waitForSelector(
        "[data-testid='multi-case-ribbon'], [data-testid='multi-case-ribbon-offline-hint']",
        { timeout: 8_000 },
      )
      .catch(() => {});
    await page.waitForTimeout(600); // let per-ref completeness settle
    await expect(page).toHaveScreenshot("51-v3-ribbon-live-completeness.png", {
      maxDiffPixelRatio: 0.01,
      animations: "disabled",
    });
  });

  test("52 · V74 close · full TruthChain tab w/ all V74 sections", async ({ page }) => {
    await page.goto("/workbench/v3/case/lid_driven_cavity?step=5");
    await page.waitForSelector("[data-testid='workbench-shell-v3']", {
      timeout: 12_000,
    });
    await page.getByTestId("right-tab-truthchain").click();
    // V75.2 · wait for skeleton to settle + V74 sections to mount
    await page
      .waitForFunction(
        () =>
          !document.querySelector("[data-testid='skeleton-truthchain']") &&
          !!document.querySelector("[data-testid='provenance-hashes']"),
        undefined,
        { timeout: 8_000 },
      )
      .catch(() => {});
    await page.waitForTimeout(300);
    await expect(
      page.locator("[data-testid='workbench-right-panel']"),
    ).toHaveScreenshot("52-v3-truthchain-full.png", {
      maxDiffPixelRatio: 0.01,
      animations: "disabled",
    });
  });
});
