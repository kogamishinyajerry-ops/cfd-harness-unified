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

  // DEC-V61-204 (M4 C2): engineer-initiated solve. Mirrors the real
  // POST /api/import/{caseId}/solve → SolveSummary so dev/mock mode + MSW
  // tests exercise the V4 run-trigger without a live backend. The real
  // dogfood (C4) runs against the actual solver.
  http.post("/api/import/:caseId/solve", async ({ params }) => {
    await delay(300);
    return HttpResponse.json({
      case_id: String(params.caseId),
      end_time_reached: 100,
      last_initial_residual_p: 8.7e-4,
      last_initial_residual_U: [3.2e-4, 2.9e-4, null],
      last_continuity_error: 1.1e-6,
      n_time_steps_written: 5,
      time_directories: ["0", "20", "40", "60", "80", "100"],
      wall_time_s: 42.3,
      converged: true,
    });
  }),

  // DEC-V61-204 (M4 C3): report-bundle mock. Returns the 4 figure
  // artifacts as inline SVG data-URIs so the V4 Post figures render in
  // dev/mock mode without a real matplotlib backend or PNG endpoints.
  // (The real route serves /api/cases/{id}/report/{name}.png; the matplotlib-
  // absent + 409 fallbacks are exercised by ReportFiguresPanel unit tests.)
  http.get("/api/cases/:caseId/report-bundle", async () => {
    await delay(120);
    const fig = (label: string, color: string) =>
      "data:image/svg+xml," +
      encodeURIComponent(
        `<svg xmlns="http://www.w3.org/2000/svg" width="220" height="150">` +
          `<rect width="220" height="150" fill="${color}"/>` +
          `<text x="110" y="80" font-family="monospace" font-size="13" ` +
          `fill="#ffffff" text-anchor="middle">${label}</text></svg>`,
      );
    return HttpResponse.json({
      final_time: 100,
      cell_count: 89745,
      slab_cell_count: 4096,
      plane_axes: ["x", "y"],
      summary_text: "MSW mock report bundle",
      cache_version: "msw00000",
      case_kind: "lid_driven_cavity",
      artifacts: {
        contour_streamlines: fig("|U| + streamlines", "#1f6f6f"),
        pressure: fig("pressure", "#7a4fb0"),
        vorticity: fig("vorticity", "#b08038"),
        centerline: fig("centerline", "#3a6ea5"),
      },
    });
  }),

  // DEC-V61-205 (M5 C2): post/patches mock. Mock mode has no real
  // foamToVTK output, so return an empty patch set → ModeRendererPost
  // resolves no surface overlay (it relies on the geometry/render GLB
  // mock for the base actor instead). Keeps MSW from logging the request
  // as unhandled.
  http.get("/api/cases/:caseId/post/patches", async () => {
    await delay(20);
    return HttpResponse.json({ patches: [], latest_time: null });
  }),

  http.get("/api/cases/:caseId/completeness", async ({ params }) => {
    await delay(15);
    // V68-B.2 · MSW now mirrors the real backend completeness shape
    // (case_kind / ready_for_archive / blocked_by_critical / percentage)
    // so useCaseStatus can normalize identically against MSW or real fastapi.
    return HttpResponse.json({
      case_id: params.caseId,
      case_kind: "whitelist",
      ready_for_archive: false,
      blocked_by_critical: 0,
      present_count: 12,
      total_count: 16,
      percentage: 75,
      missing: [],
      notes: [],
    });
  }),

  // DEC-V61-202-SUB-M30-CYCLE5 · workbench_frame mock so tests that
  // mount StepPanelShell post default-on (cycle 5 flag flip) don't
  // get a network error. Returns a step-aware shape matching the
  // pydantic WorkbenchFrame schema (ui/backend/schemas/workbench_frame.py).
  http.get("/api/cases/:caseId/workbench_frame", async ({ request, params }) => {
    await delay(20);
    const url = new URL(request.url);
    const stepParam = url.searchParams.get("step");
    const step = stepParam ? Number(stepParam) : 1;
    const focusPatch = url.searchParams.get("focus_patch");

    const railTitleByStep: Record<number, string> = {
      1: "Step 1 · 几何就绪 / Geometry ready",
      2: "Step 2 · 网格就绪 / Mesh ready",
      3: "Step 3 · 物理已设 / Physics set",
      4: "Step 4 · 边界已设 / BCs set",
      5: "Step 5 · 准备求解 / Ready to solve",
    };
    const topbarByStep: Record<number, { kind: string; label: string; target_step: number | null; enabled: boolean; reason: string | null }> = {
      1: { kind: "next_step", label: "下一步", target_step: 2, enabled: true, reason: null },
      2: { kind: "next_step", label: "下一步", target_step: 3, enabled: true, reason: null },
      3: { kind: "next_step", label: "下一步", target_step: 4, enabled: true, reason: null },
      4: { kind: "next_step", label: "下一步", target_step: 5, enabled: true, reason: null },
      5: { kind: "submit_solve", label: "提交求解", target_step: null, enabled: true, reason: null },
    };

    // Build a tiny focus_patch-aware bottom_cards list so the cycle 3
    // focus-bias flow is observable from the frontend in dev/test.
    const bottomCards: Array<Record<string, unknown>> = [];
    if (focusPatch) {
      bottomCards.push({
        kind: "audit_finding",
        title: `${focusPatch} patch issue`,
        body_text: `Focus-bias card for patch=${focusPatch} (MSW mock).`,
        severity: "warn",
        source_artifact: "bc_audit.json",
        field_path: `bc.patches.${focusPatch}`,
      });
    }

    return HttpResponse.json({
      case_id: String(params.caseId),
      step,
      rail_primary: {
        kind: "step_default",
        title: railTitleByStep[step] ?? railTitleByStep[1],
        body: null,
        field_path: null,
        suggested_default: null,
        severity: "info",
        cta_label: null,
        provenance: ["msw-mock"],
      },
      viewport_overlays: [],
      bottom_cards: bottomCards,
      topbar_cta: topbarByStep[step] ?? topbarByStep[1],
      state_sha: "msw" + "0".repeat(61),
      manifest_state_sha: "msw" + "0".repeat(61),
      generated_at: "2026-05-22T00:00:00Z",
    });
  }),

  http.patch("/api/cases/:caseId/manifest", async ({ params }) => {
    await delay(20);
    return HttpResponse.json({
      success: true,
      new_state_sha: "msw_patched" + "0".repeat(53),
      applied_path: "vof_contract.phases",
      validation_errors: [],
      case_kind: "imported_user",
      case_id: String(params.caseId),
    });
  }),
];

export const mockCase = DEMO_CASE;
export const mockStatus = DEMO_STATUS;
