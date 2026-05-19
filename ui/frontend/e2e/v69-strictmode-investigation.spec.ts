// V69.4 · StrictMode investigation spec.
//
// V68-A.4 documented persistent flakiness on /workbench/case/:id under
// React StrictMode + Playwright (industrial-dogfood.spec.ts §11). V69.4
// re-investigates: if a single navigation works deterministically against
// a real-backend case, the V68-A workaround (dev harness route) can be
// considered "documented + tolerated" rather than "deeply broken".
//
// Per V69 charter §"Reverse-stop log": "StrictMode investigation turns
// into a 4-hour deep refactor that blocks other arc work" → this spec
// is bounded: ONE test, hits ONE case, asserts ONE thing (page mounts
// without crash). If it passes, document workaround as official; if it
// fails repeatedly, document the failure mode and keep dev harness.

import { test, expect } from "@playwright/test";

test.describe("V69.4 · StrictMode investigation (case-detail route)", () => {
  test("V68-A documented workaround verified: /workbench/case/:id mounts cleanly for a whitelist case", async ({
    page,
  }) => {
    const consoleErrors: string[] = [];
    page.on("pageerror", (err) => consoleErrors.push(err.message));

    await page.goto("/workbench/case/lid_driven_cavity?step=3");
    // Light wait; we just need SPA to mount without crashing
    await page
      .waitForLoadState("networkidle", { timeout: 12_000 })
      .catch(() => {});

    // Root element present + no JS errors during mount = StrictMode +
    // case-detail surface co-exists at single-navigation level. The V68-A
    // flakiness was iteration-flake (multiple step transitions in one
    // session); this spec only asserts the one-shot mount works.
    const root = page.locator("#root");
    await expect(root).toBeAttached();
    expect(consoleErrors, `pageerrors: ${consoleErrors.join("\n")}`).toEqual([]);
  });
});
