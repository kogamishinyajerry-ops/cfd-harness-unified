// V72.2 · V72.D · Keyboard navigation spec for the v3 shell.
//
// Asserts the global key bindings registered by useV3Keyboard:
//   - 1..5         → pipeline step
//   - g/m/b/r/p/f  → viewport mode
//   - [ / ]        → cycle right-panel tab
//   - Esc          → collapse bottom panel
//
// Each test goes through the live /workbench/v3/case/:id route so the
// real shell + real react-router state is exercised (no mock harness).
//
// Required by Pillar 11 (interaction_polish · keyboard_nav subscore, 30/100).

import { test, expect } from "@playwright/test";

const CASE_URL = "/workbench/v3/case/lid_driven_cavity?step=1";

test.describe("V72.2 · V3 keyboard navigation", () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto(CASE_URL);
    await page.waitForSelector("[data-testid='workbench-shell-v3']", {
      timeout: 12_000,
    });
  });

  test("number key 4 jumps to pipeline step 4 and auto-expands bottom panel", async ({
    page,
  }) => {
    await page.keyboard.press("4");
    // Step 4 → bottom panel auto-expands
    await expect(
      page.getByTestId("bottom-panel-expanded"),
    ).toBeVisible({ timeout: 4_000 });
    // Pipeline step 4 active
    await expect(page.getByTestId("pipeline-step-4")).toHaveAttribute(
      "data-active",
      "true",
    );
  });

  test("letter 'm' switches viewport to mesh mode", async ({ page }) => {
    await page.keyboard.press("m");
    await expect(page.getByTestId("viewport-mode-mesh")).toHaveAttribute(
      "data-active",
      "true",
    );
  });

  test("bracket ']' cycles right-panel tabs forward", async ({ page }) => {
    // Default: inspector
    await expect(page.getByTestId("right-tab-inspector")).toHaveAttribute(
      "data-active",
      "true",
    );
    await page.keyboard.press("]");
    await expect(page.getByTestId("right-tab-advisor")).toHaveAttribute(
      "data-active",
      "true",
    );
    await page.keyboard.press("]");
    await expect(page.getByTestId("right-tab-truthchain")).toHaveAttribute(
      "data-active",
      "true",
    );
    // wraps around
    await page.keyboard.press("]");
    await expect(page.getByTestId("right-tab-inspector")).toHaveAttribute(
      "data-active",
      "true",
    );
  });

  test("Esc collapses an expanded bottom panel", async ({ page }) => {
    // Jump to step 4 to auto-expand
    await page.keyboard.press("4");
    await expect(
      page.getByTestId("bottom-panel-expanded"),
    ).toBeVisible();
    // Esc collapses
    await page.keyboard.press("Escape");
    await expect(
      page.getByTestId("bottom-panel-collapsed"),
    ).toBeVisible();
  });

  test("keyboard shortcuts are ignored when an editable element is focused", async ({
    page,
  }) => {
    // Simulate an input by injecting one and focusing it
    await page.evaluate(() => {
      const input = document.createElement("input");
      input.id = "__v72_test_input";
      input.type = "text";
      document.body.appendChild(input);
      input.focus();
    });
    // Press '5' while input focused · should NOT jump to step 5
    await page.keyboard.press("5");
    // Pipeline still at step 1
    await expect(page.getByTestId("pipeline-step-1")).toHaveAttribute(
      "data-active",
      "true",
    );
    // Cleanup
    await page.evaluate(() => {
      document.getElementById("__v72_test_input")?.remove();
    });
  });
});
