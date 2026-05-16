/**
 * V68-A.1 · MSW request handlers.
 *
 * Mocks the minimal `/api/*` surface needed for `/workbench/case/{id}` to
 * render in V67-C SCAFFOLDING → V68-A FULL-MET upgrade. Each handler returns
 * a deterministic shape matching the live FastAPI backend so the React
 * components feel the same data path during dev / e2e / visual baseline runs.
 *
 * Handler set (V68-A.1 minimum 4):
 *   1. GET /api/cases/:caseId                  — case metadata + step states
 *   2. GET /api/cases/:caseId/geometry/render  — geometry artifact URL
 *   3. GET /api/cases/:caseId/mesh/render      — mesh artifact URL
 *   4. GET /api/cases/:caseId/bc/render        — boundary condition render
 *   5. GET /api/cases/:caseId/status           — TopBar truth-source + audit
 */
import { http, HttpResponse, delay } from "msw";

const DEMO_CASE = {
  case_id: "v68a-demo",
  title: "V68-A Demo Case (MSW mocked)",
  created_at: "2026-05-16T00:00:00Z",
  status: "ready",
  steps: {
    import: { state: "done", artifact: "geom.stl" },
    mesh: { state: "done", cells: 89745 },
    bc: { state: "done", patches: 6 },
    solve: { state: "running", iteration: 142 },
    results: { state: "pending" },
  },
};

const DEMO_STATUS = {
  case_id: "v68a-demo",
  truth_source: "msw-mock",
  trust_gate: "audit-passing",
  audit_pct: 87,
  llm_offline: true,
  last_action: "msw mock initialized",
  validation: "geometry+mesh+bc verified",
};

export const handlers = [
  http.get("/api/cases/:caseId", async ({ params }) => {
    await delay(20);
    return HttpResponse.json({ ...DEMO_CASE, case_id: params.caseId });
  }),

  http.get("/api/cases/:caseId/status", async ({ params }) => {
    await delay(20);
    return HttpResponse.json({ ...DEMO_STATUS, case_id: params.caseId });
  }),

  http.get("/api/cases/:caseId/geometry/render", async ({ params }) => {
    await delay(30);
    return HttpResponse.json({
      case_id: params.caseId,
      format: "stl",
      url: `/mocks/${params.caseId}/geom.stl`,
      bbox: { min: [-1, -1, -1], max: [1, 1, 1] },
    });
  }),

  http.get("/api/cases/:caseId/geometry/stl", async () => {
    await delay(10);
    return new HttpResponse(
      "solid mock\nfacet normal 0 0 1\nouter loop\nvertex 0 0 0\nvertex 1 0 0\nvertex 0 1 0\nendloop\nendfacet\nendsolid mock",
      { headers: { "Content-Type": "model/stl" } },
    );
  }),

  http.get("/api/cases/:caseId/mesh/render", async ({ params }) => {
    await delay(30);
    return HttpResponse.json({
      case_id: params.caseId,
      format: "wireframe",
      cells: 89745,
      url: `/mocks/${params.caseId}/mesh.json`,
    });
  }),

  http.get("/api/cases/:caseId/bc/render", async ({ params }) => {
    await delay(30);
    return HttpResponse.json({
      case_id: params.caseId,
      format: "patches",
      patches: [
        { name: "inlet", type: "velocityInlet", color: "#10b981" },
        { name: "outlet", type: "pressureOutlet", color: "#f59e0b" },
        { name: "walls", type: "wall", color: "#9ca3af" },
      ],
    });
  }),

  http.get("/api/import/stl", async () => {
    await delay(10);
    return HttpResponse.json({ ok: true, msw: true });
  }),

  http.get("/api/cases/:caseId/completeness", async ({ params }) => {
    await delay(15);
    return HttpResponse.json({
      case_id: params.caseId,
      // V68-A.5: rolling completeness so TopBar audit% animates through pipeline.
      steps: {
        import: { complete: true, audit_pct: 100 },
        mesh: { complete: true, audit_pct: 100 },
        bc: { complete: true, audit_pct: 100 },
        solve: { complete: false, audit_pct: 60 },
        results: { complete: false, audit_pct: 0 },
      },
      overall_audit_pct: 72,
    });
  }),
];

export const mockCase = DEMO_CASE;
export const mockStatus = DEMO_STATUS;
