// V81.2 · V4.A + V4.D contract behavior proof
//
// V80.2 landed DemoBannerV4 with vitest contract tests + visual baseline
// re-snap, but no e2e proof that the banner ACTUALLY behaves per blueprint.
// V81.2 closes that gap.
//
// Contract V4.A acceptance test (.planning/blueprints/v4/INDEX.md):
//   - [data-testid='demo-banner'] exists when ?demo=1 query present
//   - Tour CANNOT take over the page (no position:fixed, no scroll-lock)
//   - Dismissing sets localStorage AND removes the banner from DOM
//
// Contract V4.D acceptance test:
//   - Cold visit shows [data-testid='first-time-hint'] in TopBar area
//   - Clicking start sets ?demo=1 and activates the tour
//   - Dismissing sets localStorage AND removes the hint
//   - localStorage state survives reload

import { test, expect } from "@playwright/test";

const STORAGE_KEY = "v80-demo-banner-dismissed";

test.describe("V81.2 · V4.A + V4.D demo banner contract", () => {
  // V81.2 NOTE: Playwright gives each test a fresh browser context by default,
  // so localStorage starts empty without a beforeEach clear. We intentionally
  // do NOT register a context-level addInitScript that wipes localStorage
  // — that would fire on every navigation INCLUDING page.reload(), which
  // would cancel the dismissal-persistence test.

  test("V4.D · cold visit surfaces first-time-hint chip in TopBar area", async ({
    page,
  }) => {
    await page.goto("/workbench/v3/case/lid_driven_cavity?step=1");
    await page.waitForSelector("[data-testid='workbench-shell-v3']", {
      timeout: 12_000,
    });
    const hint = page.getByTestId("first-time-hint");
    await expect(hint).toBeVisible();
    // Hint must be inside the TopBar's row-1 container, NOT a modal overlay
    const isAbsolute = await hint.evaluate(
      (el) => getComputedStyle(el).position === "absolute",
    );
    expect(isAbsolute).toBe(true);
  });

  test("V4.A · ?demo=1 activates the demo banner with tour-step 1", async ({
    page,
  }) => {
    await page.goto("/workbench/v3/case/lid_driven_cavity?step=1&demo=1&tour=1");
    await page.waitForSelector("[data-testid='workbench-shell-v3']", {
      timeout: 12_000,
    });
    const banner = page.getByTestId("demo-banner");
    await expect(banner).toBeVisible();
    await expect(banner).toHaveAttribute("data-tour-step", "1");
    await expect(banner).toHaveAttribute("role", "region");
  });

  test("V4.A · banner does NOT take over the page (no position:fixed, no scroll-lock)", async ({
    page,
  }) => {
    await page.goto("/workbench/v3/case/lid_driven_cavity?step=1&demo=1&tour=1");
    await page.waitForSelector("[data-testid='demo-banner']", {
      timeout: 12_000,
    });
    const banner = page.getByTestId("demo-banner");
    const position = await banner.evaluate(
      (el) => getComputedStyle(el).position,
    );
    expect(position).not.toBe("fixed");
    // body must not have overflow:hidden (no scroll-lock)
    const bodyOverflow = await page.evaluate(
      () => getComputedStyle(document.body).overflow,
    );
    expect(bodyOverflow).not.toBe("hidden");
  });

  test("V4.A · Next advances tour-step and updates URL", async ({ page }) => {
    await page.goto("/workbench/v3/case/lid_driven_cavity?step=1&demo=1&tour=1");
    await page.waitForSelector("[data-testid='demo-banner']", {
      timeout: 12_000,
    });
    await page.getByTestId("demo-banner-next").click();
    await expect(page.getByTestId("demo-banner")).toHaveAttribute(
      "data-tour-step",
      "2",
    );
    expect(new URL(page.url()).searchParams.get("tour")).toBe("2");
  });

  test("V4.A · Skip clears demo + tour from URL", async ({ page }) => {
    await page.goto("/workbench/v3/case/lid_driven_cavity?step=1&demo=1&tour=1");
    await page.waitForSelector("[data-testid='demo-banner']", {
      timeout: 12_000,
    });
    await page.getByTestId("demo-banner-skip").click();
    await expect(page.getByTestId("demo-banner")).toHaveCount(0);
    expect(new URL(page.url()).searchParams.get("demo")).toBeNull();
    expect(new URL(page.url()).searchParams.get("tour")).toBeNull();
  });

  test("V4.D · clicking the hint Start link activates the tour", async ({
    page,
  }) => {
    await page.goto("/workbench/v3/case/lid_driven_cavity?step=1");
    await page.waitForSelector("[data-testid='first-time-hint']", {
      timeout: 12_000,
    });
    await page.getByTestId("first-time-hint-start").click();
    await expect(page.getByTestId("demo-banner")).toBeVisible();
    expect(new URL(page.url()).searchParams.get("demo")).toBe("1");
  });

  test("V4.D · permanent dismissal · localStorage + survives reload", async ({
    page,
  }) => {
    await page.goto("/workbench/v3/case/lid_driven_cavity?step=1");
    await page.waitForSelector("[data-testid='first-time-hint']", {
      timeout: 12_000,
    });
    await page.getByTestId("first-time-hint-dismiss").click();
    // Hint disappears
    await expect(page.getByTestId("first-time-hint")).toHaveCount(0);
    // localStorage is set
    const flag = await page.evaluate(
      (key) => window.localStorage.getItem(key),
      STORAGE_KEY,
    );
    expect(flag).toBe("1");
    // Survives reload
    await page.reload();
    await page.waitForSelector("[data-testid='workbench-shell-v3']", {
      timeout: 12_000,
    });
    await expect(page.getByTestId("first-time-hint")).toHaveCount(0);
  });

  test("V4.A · explicit ?demo=1 overrides permanent dismissal", async ({
    page,
  }) => {
    // Pre-seed localStorage with the dismissed flag (simulate a returning user)
    await page.context().addInitScript((key) => {
      try {
        window.localStorage.setItem(key, "1");
      } catch {
        /* private mode etc. */
      }
    }, STORAGE_KEY);
    await page.goto("/workbench/v3/case/lid_driven_cavity?step=1&demo=1&tour=1");
    await page.waitForSelector("[data-testid='workbench-shell-v3']", {
      timeout: 12_000,
    });
    // Banner shows despite the dismissal flag because ?demo=1 is explicit
    await expect(page.getByTestId("demo-banner")).toBeVisible();
  });
});
