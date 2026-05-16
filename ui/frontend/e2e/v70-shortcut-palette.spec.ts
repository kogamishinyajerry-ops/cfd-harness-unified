// V70.4 · ShortcutPalette e2e (V70-UI-IMPROVEMENT-A)
//
// Validates that `?` opens the keyboard shortcut palette + Esc closes it.
// Closes Industrial-UI benchmark Axis 2 (Keyboard Shortcuts) substrate gap.

import { test, expect } from "@playwright/test";

test.describe("V70.4 · ShortcutPalette (keyboard shortcut substrate)", () => {
  test("`?` key opens the palette + Esc closes", async ({ page }) => {
    await page.goto("/workbench");
    await page.waitForLoadState("networkidle", { timeout: 8_000 }).catch(() => {});

    // Press `?` to open
    await page.keyboard.type("?");
    const palette = page.getByTestId("shortcut-palette");
    await expect(palette).toBeVisible({ timeout: 4_000 });

    // Shortcut list contains expected items
    await expect(palette).toContainText("Toggle this shortcut palette");
    await expect(palette).toContainText(/Cmd\+K|Step navigation|tutorial/i);

    // Esc closes
    await page.keyboard.press("Escape");
    await expect(palette).toBeHidden();
  });

  test("click-outside-overlay closes the palette", async ({ page }) => {
    await page.goto("/workbench");
    await page.keyboard.type("?");
    const palette = page.getByTestId("shortcut-palette");
    await expect(palette).toBeVisible({ timeout: 4_000 });

    // Click on the overlay (not the inner palette)
    await page.getByTestId("shortcut-palette-overlay").click({
      position: { x: 5, y: 5 },
    });
    await expect(palette).toBeHidden();
  });
});
