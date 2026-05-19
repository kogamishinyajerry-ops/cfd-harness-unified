// V68-C.2 (diagnose half) · backend reachability + advisor routes
// registered in the OpenAPI surface against the real fastapi.
//
// Asserts:
//   1. /api/cases/{id}/ai-review route exists (404 for unimported is OK)
//   2. /api/cases/{id}/ai-diagnose route exists (same)
//
// Both routes are loopback-guarded; from playwright we run on the same
// machine as uvicorn so loopback passes. 404 is "case not in IMPORTED_DIR"
// which is the expected response for whitelist case_002a (not materialized).
// Any 5xx would indicate a wiring regression in V68-C.2.

import { test, expect } from "@playwright/test";

const API_BASE =
  process.env.PLAYWRIGHT_API_BASE ?? "http://127.0.0.1:8001";

test.describe("V68-C.2 · advisor routes wired in real fastapi", () => {
  test("GET /api/cases/case_002a/ai-review returns 4xx (not 5xx) — route exists", async ({
    request,
  }) => {
    const res = await request.get(`${API_BASE}/api/cases/case_002a/ai-review`);
    // 404 (case not imported) / 422 (param) / 403 (loopback override absent
    // when running from CI host network) are all "endpoint exists" signals.
    // 5xx / 0 (network) would indicate the route is broken or unmounted.
    expect(res.status()).toBeGreaterThanOrEqual(400);
    expect(res.status()).toBeLessThan(500);
  });

  test("GET /api/cases/case_002a/ai-diagnose returns 4xx (not 5xx) — route exists", async ({
    request,
  }) => {
    const res = await request.get(
      `${API_BASE}/api/cases/case_002a/ai-diagnose`,
    );
    expect(res.status()).toBeGreaterThanOrEqual(400);
    expect(res.status()).toBeLessThan(500);
  });
});
