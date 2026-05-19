// V69.4 · advisor-regression smoke e2e (real backend).
//
// Asserts the canonical advisor SSOT (assemble_stack route + canonical
// eval set) is wired into the real fastapi backend. Differs from
// V69.2's static-parse harness: this spec invokes the live POST
// /api/ai-review route to confirm route + advisor_stack imports
// resolve cleanly under uvicorn.

import { test, expect } from "@playwright/test";

const API_BASE =
  process.env.PLAYWRIGHT_API_BASE ?? "http://127.0.0.1:8001";

test.describe("V69.4 · advisor regression smoke", () => {
  test("POST /api/ai-review with empty body returns 200 + advisor_count ≥ 0", async ({
    request,
  }) => {
    // Empty body = no artifacts → no advisors should fire; report is
    // valid + advisor_count=0. Critical: must NOT 500 — that would
    // indicate the advisor_stack import path is broken.
    const res = await request.post(`${API_BASE}/api/ai-review`, {
      data: { case_dir: null, llm_enhance: false },
    });
    expect(res.status()).toBe(200);
    const body = (await res.json()) as {
      report: { advisor_count: number; findings: unknown[] };
      audit_artifact_path: string;
    };
    expect(typeof body.report.advisor_count).toBe("number");
    expect(body.report.advisor_count).toBeGreaterThanOrEqual(0);
    expect(body.audit_artifact_path).toMatch(/\.planning\/audits\//);
  });

  test("GET /api/cases includes canonical-eval-covered cases", async ({
    request,
  }) => {
    const res = await request.get(`${API_BASE}/api/cases`);
    expect(res.status()).toBe(200);
    const body = (await res.json()) as Array<{ case_id: string }>;
    const ids = new Set(body.map((e) => e.case_id));
    // Canonical eval anchors most of these cases — at least a couple
    // must be reachable via /api/cases so the cross-reference works.
    expect(ids).toContain("lid_driven_cavity");
    expect(ids).toContain("naca0012_airfoil");
    expect(ids).toContain("case_002a");
  });
});
