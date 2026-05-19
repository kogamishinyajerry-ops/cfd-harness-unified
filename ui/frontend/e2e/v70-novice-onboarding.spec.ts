// V70.3 · Novice onboarding e2e
//
// Validates that a first-time engineer can reach the lid_driven_cavity
// starter case via either (a) the FirstTimeBanner banner link OR (b) the
// /workbench/tutorial route. Anchors V70-DONE-3.

import { test, expect } from "@playwright/test";

test.describe("V70.3 · novice onboarding (first-time engineer path)", () => {
  test("FirstTimeBanner present on /workbench + points to lid_driven_cavity starter", async ({
    page,
  }) => {
    // Fresh tab; banner should appear on first visit
    await page.goto("/workbench");
    const banner = page.getByTestId("first-time-banner");
    await expect(banner).toBeVisible({ timeout: 8_000 });

    // Banner must mention lid_driven_cavity as starter
    await expect(banner).toContainText(/lid_driven_cavity|starter/i);

    // Starter link href points to the right case-detail route
    const starterLink = page.getByTestId("first-time-banner-starter-link");
    await expect(starterLink).toBeVisible();
    const href = await starterLink.getAttribute("href");
    expect(href).toContain("lid_driven_cavity");

    // Dismiss button removes the banner
    await page.getByTestId("first-time-banner-dismiss").click();
    await expect(banner).toBeHidden();
  });

  test("/workbench/tutorial route renders the 5-step tutorial", async ({
    page,
  }) => {
    await page.goto("/workbench/tutorial");
    const tutorialPage = page.getByTestId("workbench-tutorial-page");
    await expect(tutorialPage).toBeVisible({ timeout: 8_000 });

    // All 5 step anchors present
    for (const step of [1, 2, 3, 4, 5]) {
      await expect(page.locator(`#step-${step}`)).toBeVisible();
    }

    // Starter link at the bottom of the tutorial → lid_driven_cavity Step 1
    const startLink = page.getByTestId("tutorial-start-link");
    await expect(startLink).toBeVisible();
    const href = await startLink.getAttribute("href");
    expect(href).toContain("lid_driven_cavity");
    expect(href).toContain("step=1");
  });

  test("dismissed banner stays dismissed across re-visits (localStorage persistence)", async ({
    page,
  }) => {
    await page.goto("/workbench");
    await page.getByTestId("first-time-banner").waitFor({
      state: "visible",
      timeout: 8_000,
    });
    await page.getByTestId("first-time-banner-dismiss").click();

    // Reload → banner should NOT reappear
    await page.reload();
    await page.waitForLoadState("networkidle", { timeout: 8_000 }).catch(() => {});
    await expect(page.getByTestId("first-time-banner")).toHaveCount(0);
  });
});
