// V68-C.1 · MaterialCard e2e against real backend.
//
// Verifies the catalog index lists case_002a (V68-C.3) AND that the
// /workbench index acknowledges the V68-C.1 wiring at the catalog level
// (the deep Step3SetupBC card render is exercised via vitest because
// the real-shell route still has StrictMode flakiness · industrial-
// dogfood.spec.ts §11 documented).

import { test, expect } from "@playwright/test";

test.describe("V68-C.1 · MaterialCard surface (catalog level)", () => {
  test("workbench index reaches case_002a (post V68-C.3 catalog grew to 11)", async ({
    page,
  }) => {
    await page.goto("/workbench");
    await page
      .waitForLoadState("networkidle", { timeout: 8_000 })
      .catch(() => {});
    // case_002a card surfaces with gold-pending semantics — V68-C.3 wired.
    // Use the data-testid added by WorkbenchIndexPage.CaseCard.
    const apuCard = page.getByTestId("case-card-case_002a");
    await expect(apuCard).toBeAttached({ timeout: 12_000 });
    await expect(apuCard).toHaveAttribute("data-case-kind", "imported_user");
    await expect(apuCard).toHaveAttribute("data-gold-pending", "true");
  });
});
