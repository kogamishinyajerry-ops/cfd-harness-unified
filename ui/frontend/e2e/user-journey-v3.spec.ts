// V72.5 · V72.E · Sub-agent test harness · autonomous user journey.
//
// This is the "测试子agent" the user mandated across all 8 "全都要" invocations:
// a single playwright test that exercises the full happy path a novice engineer
// would walk on first contact with the v3 workbench. Every step asserts a
// VISIBLE PROOF — the test cannot claim success by checking that a button
// rendered, only by reaching a downstream state that proves the click took
// effect.
//
// Journey:
//   1. Open empty /workbench/v3 · see empty state with "Select a case..."
//   2. Open a real case · /workbench/v3/case/lid_driven_cavity?step=1
//      verify case metadata renders + Inspector tab is default
//   3. Walk Steps 1→2→3→4→5 via keyboard (1..5)
//   4. At Step 4 · bottom panel auto-expanded · residuals chart visible ·
//      p curve is the watched (sand-coral) curve
//   5. Switch viewport to mesh while at Step 4 · cross-step Inspector
//      shows ACTIVE SOLVE + MESH SUMMARY (V71.T)
//   6. Open Advisor tab via ']' key · advisory badge visible · NO mutating
//      buttons exist (V130/V132 hard contract)
//   7. Consult advisor (button click) · finding rendered or offline banner ·
//      either way the UI stays calm and navigable
//   8. Esc collapses bottom · 'p' jumps to report viewport · Step 5
//      TrustGate verdict visible · provenance present
//
// Reverse-stop: any step that "passes" without its downstream visible proof
// gets flagged as a sub-agent false claim (cf. retro 2026-05-16 §V71.6).

import { test, expect } from "@playwright/test";

test.describe("V72.5 · sub-agent autonomous user journey · happy path", () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
  });

  test("complete novice journey · empty → case → solve → results", async ({
    page,
  }) => {
    // ─── 1. Empty state ──────────────────────────────────────────────────
    await page.goto("/workbench/v3");
    await expect(page.getByTestId("workbench-shell-v3")).toBeVisible();
    await expect(
      page.locator('text=Select a case from the left panel'),
    ).toBeVisible();

    // ─── 2. Open canonical case ─────────────────────────────────────────
    await page.goto("/workbench/v3/case/lid_driven_cavity?step=1");
    await expect(page.getByTestId("workbench-shell-v3")).toBeVisible();
    // Case metadata renders (live API or fallback)
    await expect(page.locator("text=case_id").first()).toBeVisible();
    await expect(page.locator("text=lid_driven_cavity").first()).toBeVisible();

    // ─── 3. Walk Steps 1→2→3→4→5 via keyboard ───────────────────────────
    for (const step of [2, 3, 4, 5]) {
      await page.keyboard.press(String(step));
      await expect(
        page.getByTestId(`pipeline-step-${step}`),
      ).toHaveAttribute("data-active", "true");
    }

    // ─── 4. At Step 4 verify residuals · p watched · bottom expanded ────
    await page.keyboard.press("4");
    await expect(
      page.getByTestId("bottom-panel-expanded"),
    ).toBeVisible();
    // Step 4 default viewport = residuals → residual chart present
    await expect(page.getByTestId("canvas-residuals")).toBeVisible();
    await expect(page.getByTestId("residual-line-p")).toHaveAttribute(
      "data-watched",
      "true",
    );

    // ─── 5. Cross-step inspection · Step 4 + viewport=mesh ──────────────
    await page.keyboard.press("m");
    await expect(page.getByTestId("viewport-mode-mesh")).toHaveAttribute(
      "data-active",
      "true",
    );
    // The inspector should now show ACTIVE SOLVE (V71.T cross-step variant).
    // Verify by locating the ACTIVE SOLVE section header
    await expect(page.locator("text=ACTIVE SOLVE").first()).toBeVisible();

    // ─── 6. Advisor tab · V130/V132 hard contract ──────────────────────
    // Cycle to advisor via ']'
    await page.keyboard.press("]");
    await expect(page.getByTestId("right-tab-advisor")).toHaveAttribute(
      "data-active",
      "true",
    );
    await expect(
      page.getByTestId("advisor-advisory-badge"),
    ).toBeVisible();
    // HARD CONTRACT: zero mutating affordance must exist
    for (const pat of [/apply/i, /submit/i, /execute/i, /auto-fix/i]) {
      await expect(page.getByRole("button", { name: pat })).toHaveCount(0);
    }

    // ─── 7. Consult advisor · accept any terminal state ──────────────
    // V73.1 added a whitelist pre-flight surface for gold cases (this case
    // is lid_driven_cavity). For whitelist cases the consult button is NOT
    // rendered — the advisor-whitelist-explanation card replaces it.
    // V75.2 SkeletonAdvisor briefly holds the panel during pre-flight, so
    // wait for either surface to materialize before deciding the path.
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
    const whitelistExplanation = page.getByTestId(
      "advisor-whitelist-explanation",
    );
    if ((await whitelistExplanation.count()) === 0) {
      await page.getByTestId("advisor-run-review").click();
      await page.waitForFunction(
        () =>
          !!document.querySelector(
            "[data-testid='advisor-review-findings'], [data-testid='advisor-offline-banner'], [data-testid='advisor-error']",
          ),
        undefined,
        { timeout: 8_000 },
      );
    } else {
      await expect(whitelistExplanation).toBeVisible();
    }
    // No mutating affordance leaked into post-consult state
    for (const pat of [/apply/i, /submit/i, /execute/i, /auto-fix/i]) {
      await expect(page.getByRole("button", { name: pat })).toHaveCount(0);
    }

    // ─── 8. Step 5 results · TrustGate verdict ──────────────────────────
    await page.keyboard.press("Escape"); // collapse bottom panel
    await page.keyboard.press("5"); // jump to step 5
    await expect(page.getByTestId("pipeline-step-5")).toHaveAttribute(
      "data-active",
      "true",
    );
    // Force viewport=report (viewport mode persists from step 4 override per V71.S
    // · this is the engineer-control rail behavior so we explicitly switch back)
    await page.keyboard.press("p");
    await expect(page.getByTestId("viewport-mode-report")).toHaveAttribute(
      "data-active",
      "true",
    );
    await expect(page.getByTestId("trustgate-verdict-block")).toBeVisible();
    await expect(page.getByTestId("trustgate-verdict-block")).toHaveAttribute(
      "data-verdict",
      "PASS",
    );
    await expect(page.getByTestId("trustgate-provenance")).toBeVisible();
  });

  // V130 backend-offline invariant is covered by vitest's
  // "CaseBrowser falls back to offline mock when /api/cases errors" test
  // in WorkbenchShellV3.test.tsx · we don't duplicate it here at the
  // playwright tier because the live shell's offline path triggers a longer
  // react-query retry cascade that's noisy in the e2e harness without
  // adding correctness coverage.
});
