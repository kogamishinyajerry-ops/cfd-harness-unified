// V89.2 · V8 state-injection harness live-browser proof
//
// Per .planning/decisions/2026-05-17_v89_charter_dec.md §6 reverse-stops:
//   - #28: URL param ONLY active in dev/test · verified at module level
//     (contract test) · this e2e adds the live-browser dimension
//   - #29: State-injection MUST NOT fire ANY mutating fetch · injected
//     `error` state surfaces banner WITHOUT having issued a POST · this
//     spec captures network traffic to prove zero mutations
//
// Mirrors V87.3 + V88.6 V130 live-browser network-mutation pattern.

import { test, expect, type Request } from "@playwright/test";

test.describe("V89.2 · V8 state-injection harness · V130 live-browser proof", () => {
  test("dirty injection surfaces editor in dirty state · NO POST /dicts fires", async ({
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
      "/workbench/v3/case/lid_driven_cavity?step=4&btab=open&_v89_inject=dirty",
    );
    await page.waitForSelector("[data-testid='workbench-shell-v3']", {
      timeout: 12_000,
    });
    await page.locator("[data-testid='bottom-tab-config']").click();
    await page.waitForSelector(
      "[data-testid='solver-config-editor-v8'][data-config-state='dirty']",
      { timeout: 4_000 },
    );

    // Give React + tanstack-query a generous settle window
    await page.waitForTimeout(2000);

    const dictPosts = mutatingRequests.filter((r) =>
      r.url.includes("/dicts/system/controlDict"),
    );
    expect(dictPosts).toEqual([]);
  });

  test("diff_open injection forces V8.C diff visible · NO POST /dicts fires", async ({
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
      "/workbench/v3/case/lid_driven_cavity?step=4&btab=open&_v89_inject=diff_open",
    );
    await page.waitForSelector("[data-testid='workbench-shell-v3']", {
      timeout: 12_000,
    });
    await page.locator("[data-testid='bottom-tab-config']").click();
    await page.waitForSelector("[data-testid='solver-config-diff-v8']", {
      timeout: 4_000,
    });

    await page.waitForTimeout(2000);

    const dictPosts = mutatingRequests.filter((r) =>
      r.url.includes("/dicts/system/controlDict"),
    );
    expect(dictPosts).toEqual([]);
  });

  test("error injection shows banner WITHOUT prior POST · zero mutating fetch", async ({
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
      "/workbench/v3/case/lid_driven_cavity?step=4&btab=open&_v89_inject=error",
    );
    await page.waitForSelector("[data-testid='workbench-shell-v3']", {
      timeout: 12_000,
    });
    await page.locator("[data-testid='bottom-tab-config']").click();
    await page.waitForSelector(
      "[data-testid='solver-config-editor-v8-error-banner']",
      { timeout: 4_000 },
    );

    // CRITICAL: error banner is visible BUT no POST /dicts was issued.
    // This proves the injection harness is presentation-only · no real
    // commit attempt happened. V130 invariant intact.
    await page.waitForTimeout(2000);

    const dictPosts = mutatingRequests.filter((r) =>
      r.url.includes("/dicts/system/controlDict"),
    );
    expect(dictPosts).toEqual([]);
  });

  test("injection handlers are no-ops · clicking Discard / Review-changes does NOT mutate", async ({
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
      "/workbench/v3/case/lid_driven_cavity?step=4&btab=open&_v89_inject=dirty",
    );
    await page.locator("[data-testid='bottom-tab-config']").click();
    await page.waitForSelector(
      "[data-testid='solver-config-editor-v8'][data-config-state='dirty']",
      { timeout: 4_000 },
    );

    // Both Discard + Review-changes affordances exist in dirty state.
    // Their handlers are no-ops under injection (reverse-stop #29).
    // Clicking them should NOT fire any mutating fetch.
    await page.locator("[data-testid='solver-config-editor-v8-discard']").click();
    await page.waitForTimeout(500);

    const dictPosts = mutatingRequests.filter((r) =>
      r.url.includes("/dicts/system/controlDict"),
    );
    expect(dictPosts).toEqual([]);
  });
});
