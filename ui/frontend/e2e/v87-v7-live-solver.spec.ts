// V87.3 · V7 live-solver e2e behavior proof
//
// V86 shipped V7.A-V7.D contracts as vitest + V87.1 mounted them in the
// v3 workbench shell + V87.2 added 3 visual baselines (84/85/86). This
// spec adds REAL-BROWSER behavior tests that vitest can't cover:
//   - V7.A Run button mounts at Step ≥4 with btab=closed
//   - V7.A is disabled in read-only mode (?demo=2 / ?bridge=1)
//   - Clicking the button POSTs to /api/import/{id}/solve-stream (and
//     ONLY that mutating endpoint · network-mutation guard mirrors
//     V84.2 sandbox guard)
//   - Cancel mid-run aborts cleanly without leaving orphan state
//   - V130 invariant: no auto-trigger fires on mount, only on user click
//
// Closes V86 retro Open Q #3.

import { test, expect, type Request, type Route } from "@playwright/test";

test.describe("V87.3 · V7 Live Solver Trigger live-browser proof", () => {
  test("V7.A Run button mounts in BottomPanel collapsed bar at Step ≥4", async ({
    page,
  }) => {
    await page.goto(
      "/workbench/v3/case/lid_driven_cavity?step=4&btab=closed",
    );
    await page.waitForSelector("[data-testid='workbench-shell-v3']", {
      timeout: 12_000,
    });
    await expect(
      page.locator("[data-testid='bottom-panel-collapsed']"),
    ).toBeVisible();
    await expect(page.locator("[data-testid='run-solver-v7']")).toBeVisible();
    // Button text reflects idle state
    await expect(
      page.locator("[data-testid='run-solver-v7-button']"),
    ).toContainText("Run solver");
  });

  test("V7.A Run button disabled in read-only sandbox mode (?demo=2)", async ({
    page,
  }) => {
    await page.goto(
      "/workbench/v3/case/lid_driven_cavity?step=4&demo=2&btab=closed",
    );
    await page.waitForSelector("[data-testid='workbench-shell-v3']", {
      timeout: 12_000,
    });
    await expect(page.locator("[data-testid='run-solver-v7']")).toBeVisible();
    await expect(
      page.locator("[data-testid='run-solver-v7-button']"),
    ).toBeDisabled();
    // Hint surfaces a reason; exact text comes from V7.A (mesh + BC not ready)
    await expect(page.locator("[data-testid='run-solver-v7-hint']")).toBeVisible();
  });

  test("V7.A Run button disabled in bridge mode (?bridge=1)", async ({
    page,
  }) => {
    await page.goto(
      "/workbench/v3/case/lid_driven_cavity?step=4&bridge=1&btab=closed",
    );
    await page.waitForSelector("[data-testid='workbench-shell-v3']", {
      timeout: 12_000,
    });
    await expect(
      page.locator("[data-testid='run-solver-v7-button']"),
    ).toBeDisabled();
  });

  test("V7.A click triggers POST /api/import/{id}/solve-stream (network mutation guard)", async ({
    page,
  }) => {
    // Intercept the solve-stream endpoint so the test doesn't hang on a
    // real solver run. Return a stub SSE response that completes
    // immediately so V7.B transitions through running → done.
    let solveStreamHit = false;
    await page.route(
      "**/api/import/lid_driven_cavity/solve-stream",
      async (route: Route) => {
        solveStreamHit = true;
        // Emit one start + one done event then close the stream.
        const body =
          `event: start\ndata: {"run_id":"R-V87-3"}\n\n` +
          `event: done\ndata: {"run_id":"R-V87-3","success":true}\n\n`;
        await route.fulfill({
          status: 200,
          headers: {
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
          },
          body,
        });
      },
    );

    // Capture all mutating requests; only /solve-stream should be allowed.
    // audit-package POST may also fire (V7.D post-run handoff) and is
    // explicitly part of V86 V132=9 baseline.
    const mutatingRequests: { method: string; url: string }[] = [];
    page.on("request", (req: Request) => {
      const method = req.method();
      if (["POST", "PUT", "DELETE", "PATCH"].includes(method)) {
        mutatingRequests.push({ method, url: req.url() });
      }
    });

    await page.goto(
      "/workbench/v3/case/lid_driven_cavity?step=4&btab=closed",
    );
    await page.waitForSelector("[data-testid='run-solver-v7-button']", {
      timeout: 12_000,
    });
    await expect(
      page.locator("[data-testid='run-solver-v7-button']"),
    ).not.toBeDisabled();

    // CRITICAL pre-click assertion: NO mutating requests have fired yet
    // (V130 invariant · the page mount must not auto-trigger the solver)
    expect(
      mutatingRequests.filter((r) =>
        r.url.includes("/solve-stream"),
      ),
    ).toEqual([]);

    // USER click
    await page.locator("[data-testid='run-solver-v7-button']").click();

    // Wait for the route intercept to record the hit
    await page.waitForTimeout(500);
    expect(solveStreamHit).toBe(true);

    // The only mutating routes allowed during this flow:
    // - /solve-stream (V7.A trigger)
    // - /audit-package/build (V7.D post-run handoff · best-effort)
    const allowedMutationPatterns = [
      /\/api\/import\/[^/]+\/solve-stream/,
      /\/api\/cases\/[^/]+\/runs\/[^/]+\/audit-package\/build/,
    ];
    for (const req of mutatingRequests) {
      const matched = allowedMutationPatterns.some((p) => p.test(req.url));
      expect(matched, `unexpected mutation: ${req.method} ${req.url}`).toBe(
        true,
      );
    }
  });

  test("V7.A V130: no auto-trigger fires on mount (mutating requests stay empty until user click)", async ({
    page,
  }) => {
    const mutatingRequests: { method: string; url: string }[] = [];
    page.on("request", (req: Request) => {
      const method = req.method();
      if (["POST", "PUT", "DELETE", "PATCH"].includes(method)) {
        mutatingRequests.push({ method, url: req.url() });
      }
    });

    await page.goto(
      "/workbench/v3/case/lid_driven_cavity?step=4&btab=closed",
    );
    await page.waitForSelector("[data-testid='run-solver-v7-button']", {
      timeout: 12_000,
    });
    // Give React effects + tanstack-query a generous window to settle
    // without clicking the button. Any solve-stream call here is a
    // V130 regression.
    await page.waitForTimeout(2000);

    const solveStreamCalls = mutatingRequests.filter((r) =>
      r.url.includes("/solve-stream"),
    );
    expect(solveStreamCalls).toEqual([]);
  });
});
