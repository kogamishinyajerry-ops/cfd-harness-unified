// V88.6 · V8 solver-config-editor e2e behavior proof
//
// V88.2 shipped V8.A SolverConfigEditor + V88.3 V8.B validator + V88.4
// V8.C diff + V88.5 V8.D hook. This spec adds REAL-BROWSER behavior
// tests that vitest can't cover:
//   - V8.A "Config" tab mounts in BottomPanel expanded view at Step ≥3
//   - V8.A is hidden in read-only modes (?demo=2 / ?bridge=1)
//   - V130 invariant: no POST /dicts fires on mount, only on explicit
//     user Confirm-Commit click inside the diff preview
//   - V8.C diff preview gates commit (cancel does NOT POST)
//   - validation errors block Confirm button (V88 reverse-stop #24)
//
// Closes V88 charter §3 V88.6 e2e substrate target.

import { test, expect, type Request, type Route } from "@playwright/test";

const STUB_CONTROLDICT = `
FoamFile { version 2.0; }
application     icoFoam;
endTime         10.0;
deltaT          0.005;
writeInterval   0.5;
writeFormat     ascii;
`;

test.describe("V88.6 · V8 Solver Config Editor live-browser proof", () => {
  test("V8.A Config tab mounts in expanded BottomPanel at Step ≥3", async ({
    page,
  }) => {
    await page.route(
      "**/api/cases/lid_driven_cavity/dicts/system/controlDict",
      async (route: Route) => {
        if (route.request().method() === "GET") {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              case_id: "lid_driven_cavity",
              path: "system/controlDict",
              content: STUB_CONTROLDICT,
              source: "user",
              etag: "etag-v1",
              edited_at: null,
            }),
          });
        } else {
          await route.continue();
        }
      },
    );

    await page.goto(
      "/workbench/v3/case/lid_driven_cavity?step=4&btab=open",
    );
    await page.waitForSelector("[data-testid='workbench-shell-v3']", {
      timeout: 12_000,
    });
    await expect(
      page.locator("[data-testid='bottom-panel-expanded']"),
    ).toBeVisible();
    await expect(page.locator("[data-testid='bottom-tab-config']")).toBeVisible();
    // Click into Config tab and ensure the editor renders
    await page.locator("[data-testid='bottom-tab-config']").click();
    await expect(
      page.locator("[data-testid='solver-config-editor-v8']"),
    ).toBeVisible();
  });

  test("V8.A Config tab HIDDEN in sandbox read-only mode (?demo=2)", async ({
    page,
  }) => {
    await page.goto(
      "/workbench/v3/case/lid_driven_cavity?step=4&demo=2&btab=open",
    );
    await page.waitForSelector("[data-testid='workbench-shell-v3']", {
      timeout: 12_000,
    });
    // Tab strip should NOT include the config tab in read-only mode
    await expect(page.locator("[data-testid='bottom-tab-config']")).toHaveCount(0);
  });

  test("V8.A Config tab HIDDEN in bridge read-only mode (?bridge=1)", async ({
    page,
  }) => {
    await page.goto(
      "/workbench/v3/case/lid_driven_cavity?step=4&bridge=1&btab=open",
    );
    await page.waitForSelector("[data-testid='workbench-shell-v3']", {
      timeout: 12_000,
    });
    await expect(page.locator("[data-testid='bottom-tab-config']")).toHaveCount(0);
  });

  test("V8 V130: no POST /dicts fires on mount (mutating requests stay empty until user Confirm-Commit click)", async ({
    page,
  }) => {
    await page.route(
      "**/api/cases/lid_driven_cavity/dicts/system/controlDict",
      async (route: Route) => {
        if (route.request().method() === "GET") {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              case_id: "lid_driven_cavity",
              path: "system/controlDict",
              content: STUB_CONTROLDICT,
              source: "user",
              etag: "etag-v1",
              edited_at: null,
            }),
          });
        } else {
          await route.continue();
        }
      },
    );

    const mutatingRequests: { method: string; url: string }[] = [];
    page.on("request", (req: Request) => {
      const method = req.method();
      if (["POST", "PUT", "DELETE", "PATCH"].includes(method)) {
        mutatingRequests.push({ method, url: req.url() });
      }
    });

    await page.goto(
      "/workbench/v3/case/lid_driven_cavity?step=4&btab=open",
    );
    await page.waitForSelector("[data-testid='workbench-shell-v3']", {
      timeout: 12_000,
    });
    await page.locator("[data-testid='bottom-tab-config']").click();
    await expect(
      page.locator("[data-testid='solver-config-editor-v8']"),
    ).toBeVisible();

    // Give React effects + tanstack-query a generous window to settle
    // without typing or clicking. Any POST /dicts here is a V130 regression.
    await page.waitForTimeout(2000);

    const dictPosts = mutatingRequests.filter(
      (r) => r.url.includes("/dicts/system/controlDict"),
    );
    expect(dictPosts).toEqual([]);
  });

  test("V8.C diff preview opens before commit · Cancel does NOT POST", async ({
    page,
  }) => {
    await page.route(
      "**/api/cases/lid_driven_cavity/dicts/system/controlDict",
      async (route: Route) => {
        if (route.request().method() === "GET") {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              case_id: "lid_driven_cavity",
              path: "system/controlDict",
              content: STUB_CONTROLDICT,
              source: "user",
              etag: "etag-v1",
              edited_at: null,
            }),
          });
        } else {
          await route.continue();
        }
      },
    );

    const postRequests: string[] = [];
    page.on("request", (req: Request) => {
      if (
        req.method() === "POST" &&
        req.url().includes("/dicts/system/controlDict")
      ) {
        postRequests.push(req.url());
      }
    });

    await page.goto(
      "/workbench/v3/case/lid_driven_cavity?step=4&btab=open",
    );
    await page.locator("[data-testid='bottom-tab-config']").click();
    await expect(
      page.locator("[data-testid='solver-config-editor-v8']"),
    ).toBeVisible();

    // Edit endTime field
    const endTime = page.locator(
      "[data-testid='solver-config-editor-v8-input-endTime']",
    );
    await endTime.fill("20.0");

    // Click Review changes → diff preview opens
    await page.locator("[data-testid='solver-config-editor-v8-review']").click();
    await expect(
      page.locator("[data-testid='solver-config-diff-v8']"),
    ).toBeVisible();

    // Click Cancel → diff closes, NO POST fires
    await page.locator("[data-testid='solver-config-diff-v8-cancel']").click();
    await expect(page.locator("[data-testid='solver-config-diff-v8']")).toHaveCount(0);

    await page.waitForTimeout(500);
    expect(postRequests).toEqual([]);
  });

  test("V8 validation errors block Confirm in diff preview (reverse-stop #24)", async ({
    page,
  }) => {
    await page.route(
      "**/api/cases/lid_driven_cavity/dicts/system/controlDict",
      async (route: Route) => {
        if (route.request().method() === "GET") {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              case_id: "lid_driven_cavity",
              path: "system/controlDict",
              content: STUB_CONTROLDICT,
              source: "user",
              etag: "etag-v1",
              edited_at: null,
            }),
          });
        } else {
          await route.continue();
        }
      },
    );

    await page.goto(
      "/workbench/v3/case/lid_driven_cavity?step=4&btab=open",
    );
    await page.locator("[data-testid='bottom-tab-config']").click();

    // Type an invalid endTime ("-5")
    const endTime = page.locator(
      "[data-testid='solver-config-editor-v8-input-endTime']",
    );
    await endTime.fill("-5");

    // Editor surfaces inline error on the bad field
    await expect(
      page.locator("[data-testid='solver-config-editor-v8-fielderror-endTime']"),
    ).toBeVisible();

    // Review-changes button is disabled (has validation errors)
    await expect(
      page.locator("[data-testid='solver-config-editor-v8-review']"),
    ).toBeDisabled();
  });
});
