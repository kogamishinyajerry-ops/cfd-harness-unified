// Thin fetch wrapper. Vite proxies /api → 127.0.0.1:8000 in dev (see
// vite.config.ts); in production the frontend is served from the same
// origin as the FastAPI app, so the same relative paths work unchanged.

import type {
  CaseDetail,
  CaseIndexEntry,
  RunDescriptor,
  ValidationReport,
} from "@/types/validation";
import type {
  CaseYamlLintResult,
  CaseYamlPayload,
  CaseYamlSaveResult,
} from "@/types/editor";
import type {
  DashboardResponse,
  DecisionsQueueResponse,
} from "@/types/decisions";
import type { AuditPackageBuildResponse } from "@/types/audit_package";
import type { BatchMatrix } from "@/types/batch_matrix";
import type { CaseCompletenessReport } from "@/types/case_completeness";
import type { ExportManifest } from "@/types/exports";
import type { MeshMetrics } from "@/types/mesh_metrics";
import type { PreflightSummary } from "@/types/preflight";
import type {
  DraftCreateRequest,
  DraftCreateResponse,
  TemplateListResponse,
  WizardPreviewResponse,
} from "@/types/wizard";
import type { WorkbenchBasics } from "@/types/workbench_basics";
import type {
  DemoFixture,
  ImportRejectionDetail,
  ImportSTLResponse,
} from "@/types/import_geometry";
import type {
  RecentRunsResponse,
  RunDetail,
  RunHistoryListResponse,
} from "@/types/run_history";

async function request<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(path, {
    method: init?.method ?? "GET",
    headers: {
      Accept: "application/json",
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...(init?.headers ?? {}),
    },
    body: init?.body,
    credentials: "same-origin",
  });
  if (!response.ok) {
    const body = await response.text();
    throw new ApiError(response.status, body || response.statusText);
  }
  return (await response.json()) as T;
}

export class ApiError extends Error {
  status: number;
  detail?: unknown;

  constructor(status: number, message: string, detail?: unknown) {
    super(message);
    this.status = status;
    this.name = "ApiError";
    this.detail = detail;
  }
}

// V127 R4 P2: any backend route that mutates a case's polyMesh must
// dispatch this event so caches keyed on the polyMesh (notably
// MeshQualityCard's module-level cache) re-fetch on next remount. The
// listeners are registered inside the consumers; this helper is the
// single point where producers fire.
function dispatchMeshMutated(caseId: string): void {
  if (typeof window === "undefined") return;
  window.dispatchEvent(
    new CustomEvent("mesh:mutated", { detail: { caseId } }),
  );
}

export const api = {
  // Phase 0
  health: () => request<{ status: string; version: string }>("/api/health"),
  listCases: () => request<CaseIndexEntry[]>("/api/cases"),
  getCase: (caseId: string) =>
    request<CaseDetail>(`/api/cases/${encodeURIComponent(caseId)}`),
  getValidationReport: (caseId: string, runId?: string) => {
    const q = runId ? `?run_id=${encodeURIComponent(runId)}` : "";
    return request<ValidationReport>(
      `/api/validation-report/${encodeURIComponent(caseId)}${q}`,
    );
  },
  listCaseRuns: (caseId: string) =>
    request<RunDescriptor[]>(
      `/api/cases/${encodeURIComponent(caseId)}/runs`,
    ),

  // Phase 1
  getCaseYaml: (caseId: string) =>
    request<CaseYamlPayload>(
      `/api/cases/${encodeURIComponent(caseId)}/yaml`,
    ),
  putCaseYaml: (payload: CaseYamlPayload) =>
    request<CaseYamlSaveResult>(
      `/api/cases/${encodeURIComponent(payload.case_id)}/yaml`,
      { method: "PUT", body: JSON.stringify(payload) },
    ),
  lintCaseYaml: (payload: CaseYamlPayload) =>
    request<CaseYamlLintResult>(
      `/api/cases/${encodeURIComponent(payload.case_id)}/yaml/lint`,
      { method: "POST", body: JSON.stringify(payload) },
    ),
  revertCaseYaml: (caseId: string) =>
    request<CaseYamlPayload>(
      `/api/cases/${encodeURIComponent(caseId)}/yaml`,
      { method: "DELETE" },
    ),

  // Phase 2
  listDecisions: () => request<DecisionsQueueResponse>("/api/decisions"),

  // Phase 3 run-monitor endpoints removed 2026-04-26 (M1) — Phase-3 synthetic
  // residual stream retired. Real solver SSE lives at /api/wizard/run/:id/stream
  // driven by RealSolverDriver in wizard_drivers.py.

  // Phase 4
  getDashboard: () => request<DashboardResponse>("/api/dashboard"),

  // Phase 5 — Audit Package Builder (Screen 6)
  buildAuditPackage: (caseId: string, runId: string) =>
    request<AuditPackageBuildResponse>(
      `/api/cases/${encodeURIComponent(caseId)}/runs/${encodeURIComponent(runId)}/audit-package/build`,
      { method: "POST", body: "{}" },
    ),

  // M3 (2026-04-26) — Workbench run history. Path is `/run-history` (not
  // `/runs`) to dodge the Learn-track curated-taxonomy collision —
  // GET /api/cases/{id}/runs is owned by validation.py and returns a
  // different shape (list[RunDescriptor]).
  listRuns: (caseId: string) =>
    request<RunHistoryListResponse>(
      `/api/cases/${encodeURIComponent(caseId)}/run-history`,
    ),
  getRunDetail: (caseId: string, runId: string) =>
    request<RunDetail>(
      `/api/cases/${encodeURIComponent(caseId)}/run-history/${encodeURIComponent(runId)}`,
    ),
  // 60-day extension #3 — cross-case "today's runs" feed for the
  // /workbench/today dashboard. Path is /api/run-history/recent so it
  // doesn't collide with the per-case /api/cases/{id}/run-history surface.
  listRecentRuns: (limit = 50) =>
    request<RecentRunsResponse>(`/api/run-history/recent?limit=${limit}`),

  // Stage 2 — industrial workbench first-screen
  getWorkbenchBasics: (caseId: string) =>
    request<WorkbenchBasics>(
      `/api/cases/${encodeURIComponent(caseId)}/workbench-basics`,
    ),

  // Stage 3 — MeshTrust QC band
  getMeshMetrics: (caseId: string) =>
    request<MeshMetrics>(
      `/api/cases/${encodeURIComponent(caseId)}/mesh-metrics`,
    ),

  // Stage 4 — GuardedRun preflight
  getPreflight: (caseId: string) =>
    request<PreflightSummary>(
      `/api/cases/${encodeURIComponent(caseId)}/preflight`,
    ),

  // DEC-V61-116 — governance-aware completeness diff for the
  // right-rail "距离入库标准还差 N 项" card.
  getCaseCompleteness: (caseId: string) =>
    request<CaseCompletenessReport>(
      `/api/cases/${encodeURIComponent(caseId)}/completeness`,
    ),

  // Stage 5 — GoldOps batch matrix
  getBatchMatrix: () => request<BatchMatrix>(`/api/batch-matrix`),

  // Stage 6 — ExportPack manifest (download URLs are constructed inline)
  getExportManifest: () => request<ExportManifest>(`/api/exports/manifest`),

  // Stage 8a — Onboarding Workbench wizard
  listWizardTemplates: () =>
    request<TemplateListResponse>("/api/wizard/templates"),
  previewWizardYaml: (payload: DraftCreateRequest) =>
    request<WizardPreviewResponse>("/api/wizard/preview", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  createWizardDraft: (payload: DraftCreateRequest) =>
    request<DraftCreateResponse>("/api/wizard/draft", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  wizardRunStreamUrl: (caseId: string) =>
    `/api/wizard/run/${encodeURIComponent(caseId)}/stream`,

  // M5.0 · STL case import. Multipart upload — bypasses the JSON-only
  // request() helper because FormData sets its own Content-Type boundary
  // and the route returns a structured rejection body on 4xx that the
  // UI needs preserved as ApiError.detail.
  importStl: async (file: File): Promise<ImportSTLResponse> => {
    const fd = new FormData();
    fd.append("file", file);
    const resp = await fetch("/api/import/stl", {
      method: "POST",
      body: fd,
      credentials: "same-origin",
    });
    if (!resp.ok) {
      let detail: ImportRejectionDetail | string | undefined;
      try {
        const body = await resp.json();
        detail = body?.detail ?? body;
      } catch {
        detail = await resp.text();
      }
      const message =
        typeof detail === "object" && detail !== null && "reason" in detail
          ? (detail as ImportRejectionDetail).reason
          : typeof detail === "string"
            ? detail
            : `import failed (${resp.status})`;
      throw new ApiError(resp.status, message, detail);
    }
    return (await resp.json()) as ImportSTLResponse;
  },

  // M-PANELS Step 10 demo entry: list + one-click import of the
  // checked-in demo STLs in examples/imports/. The import endpoint
  // returns the same ImportSTLResponse shape as /api/import/stl, so
  // the post-upload navigation logic in ImportPage is shared.
  listDemoFixtures: () => request<DemoFixture[]>("/api/demo-fixtures"),
  importDemoFixture: async (name: string): Promise<ImportSTLResponse> => {
    const resp = await fetch(
      `/api/demo-fixtures/${encodeURIComponent(name)}/import`,
      { method: "POST", credentials: "same-origin" },
    );
    if (!resp.ok) {
      let detail: ImportRejectionDetail | string | undefined;
      try {
        const body = await resp.json();
        detail = body?.detail ?? body;
      } catch {
        detail = await resp.text();
      }
      const message =
        typeof detail === "object" && detail !== null && "reason" in detail
          ? (detail as ImportRejectionDetail).reason
          : typeof detail === "string"
            ? detail
            : `demo import failed (${resp.status})`;
      throw new ApiError(resp.status, message, detail);
    }
    return (await resp.json()) as ImportSTLResponse;
  },

  // M6.0 · gmsh meshing for an imported case. Returns a mesh summary +
  // optional warning (5M soft cap exceeded). Errors come back with a
  // failing_check enum on .detail so the page can render a targeted
  // remediation hint per failure mode.
  meshImported: async (
    caseId: string,
    meshMode: import("@/types/mesh_imported").MeshMode,
  ): Promise<import("@/types/mesh_imported").MeshSuccessResponse> => {
    const resp = await fetch(
      `/api/import/${encodeURIComponent(caseId)}/mesh`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ mesh_mode: meshMode }),
        credentials: "same-origin",
      },
    );
    if (!resp.ok) {
      let detail: import("@/types/mesh_imported").MeshRejectionDetail | string | undefined;
      try {
        const body = await resp.json();
        detail = body?.detail ?? body;
      } catch {
        detail = await resp.text();
      }
      const message =
        typeof detail === "object" && detail !== null && "reason" in detail
          ? (detail as { reason: string }).reason
          : typeof detail === "string"
            ? detail
            : `mesh failed (${resp.status})`;
      throw new ApiError(resp.status, message, detail);
    }
    const result = (await resp.json()) as import(
      "@/types/mesh_imported"
    ).MeshSuccessResponse;
    dispatchMeshMutated(caseId);
    return result;
  },

  // Phase-1A LDC demo (DEC-V61-097): the back-half routes wire Steps
  // 3 (setup-bc), 4 (solve), 5 (results) of the M-PANELS step panel.
  setupBC: async (
    caseId: string,
  ): Promise<import("@/types/case_solve").SetupBcSummary> => {
    const resp = await fetch(
      `/api/import/${encodeURIComponent(caseId)}/setup-bc`,
      {
        method: "POST",
        headers: { Accept: "application/json" },
        credentials: "same-origin",
      },
    );
    if (!resp.ok) {
      let detail: unknown;
      try {
        const body = await resp.json();
        detail = body?.detail ?? body;
      } catch {
        detail = await resp.text();
      }
      const message =
        typeof detail === "object" && detail !== null && "detail" in detail
          ? (detail as { detail: string }).detail
          : typeof detail === "string"
            ? detail
            : `setup-bc failed (${resp.status})`;
      throw new ApiError(resp.status, message, detail);
    }
    const result = (await resp.json()) as import(
      "@/types/case_solve"
    ).SetupBcSummary;
    // setup-bc rewrites constant/polyMesh/boundary; treat as polyMesh
    // mutation so the mesh-quality cache re-fetches.
    dispatchMeshMutated(caseId);
    return result;
  },

  // M-AI-COPILOT (DEC-V61-098 spec_v2 §B.4): envelope-mode setup-bc.
  // Same backend route, different response shape under ?envelope=1.
  // ``forceUncertain`` / ``forceBlocked`` drive the LDC dialog dogfood
  // path so the engineer can practice the bidirectional dialog flow
  // without needing real arbitrary-STL ambiguity.
  setupBCWithEnvelope: async (
    caseId: string,
    options: {
      forceUncertain?: boolean;
      forceBlocked?: boolean;
    } = {},
  ): Promise<
    import("@/pages/workbench/step_panel_shell/types").AIActionEnvelope
  > => {
    const params = new URLSearchParams({ envelope: "1" });
    if (options.forceUncertain) params.set("force_uncertain", "1");
    if (options.forceBlocked) params.set("force_blocked", "1");
    const resp = await fetch(
      `/api/import/${encodeURIComponent(caseId)}/setup-bc?${params.toString()}`,
      {
        method: "POST",
        headers: { Accept: "application/json" },
        credentials: "same-origin",
      },
    );
    if (!resp.ok) {
      let detail: unknown;
      try {
        const body = await resp.json();
        detail = body?.detail ?? body;
      } catch {
        detail = await resp.text();
      }
      const message =
        typeof detail === "object" && detail !== null && "detail" in detail
          ? (detail as { detail: string }).detail
          : typeof detail === "string"
            ? detail
            : `setup-bc envelope failed (${resp.status})`;
      throw new ApiError(resp.status, message, detail);
    }
    const result = (await resp.json()) as import(
      "@/pages/workbench/step_panel_shell/types"
    ).AIActionEnvelope;
    // R6 P2: polyMesh-mutation map for setupBCWithEnvelope
    // (ui/backend/services/ai_actions/__init__.py
    // setup_bc_with_annotations):
    //   * force_blocked=1 → short-circuits BEFORE setup_ldc_bc;
    //     confidence='blocked'; NO polyMesh write.
    //   * force_uncertain=1 → runs setup_ldc_bc THEN wraps as
    //     'uncertain' for the dogfood dialog; polyMesh IS written.
    //   * neither force flag → classifier may short-circuit
    //     ('uncertain'/'blocked' without writing) or fall through to
    //     setup_ldc_bc/setup_channel_bc and return 'confident' (which
    //     always means polyMesh was written).
    // Therefore: dispatch on confidence×caller-intent:
    //   * confident  → always write
    //   * uncertain  → write only when forceUncertain (force_uncertain
    //     post-setup wrap); plain classifier-uncertain has no write
    //   * blocked    → never write (force_blocked short-circuits, AND
    //     force_blocked wins over force_uncertain server-side per
    //     /api/import/.../setup-bc spec_v2 §A3)
    // R7 P3: gating on the response confidence first avoids the
    // both-debug-flags-set case where forceUncertain is true but the
    // backend returned 'blocked' (no write happened).
    const polyMeshMutated =
      result.confidence === "confident" ||
      (result.confidence === "uncertain" && options.forceUncertain === true);
    if (polyMeshMutated) {
      dispatchMeshMutated(caseId);
    }
    return result;
  },

  // M-AI-COPILOT face-annotations endpoints (DEC-V61-098 spec_v2 §A4).
  getFaceAnnotations: async (
    caseId: string,
  ): Promise<
    import("@/pages/workbench/step_panel_shell/types").AnnotationsDocument
  > => {
    const resp = await fetch(
      `/api/cases/${encodeURIComponent(caseId)}/face-annotations`,
      {
        method: "GET",
        headers: { Accept: "application/json" },
        credentials: "same-origin",
      },
    );
    if (!resp.ok) {
      let detail: unknown;
      try {
        detail = (await resp.json())?.detail;
      } catch {
        detail = await resp.text();
      }
      throw new ApiError(
        resp.status,
        `getFaceAnnotations failed (${resp.status})`,
        detail,
      );
    }
    return (await resp.json()) as import(
      "@/pages/workbench/step_panel_shell/types"
    ).AnnotationsDocument;
  },

  /** PUT /face-annotations. Returns the new state with bumped revision.
   *  Throws ApiError with status=409 + RevisionConflictDetail body when
   *  ``if_match_revision`` is stale (caller should re-fetch + retry).
   */
  putFaceAnnotations: async (
    caseId: string,
    body: import(
      "@/pages/workbench/step_panel_shell/types"
    ).AnnotationsPutBody,
  ): Promise<
    import("@/pages/workbench/step_panel_shell/types").AnnotationsDocument
  > => {
    const resp = await fetch(
      `/api/cases/${encodeURIComponent(caseId)}/face-annotations`,
      {
        method: "PUT",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        credentials: "same-origin",
        body: JSON.stringify(body),
      },
    );
    if (!resp.ok) {
      let detail: unknown;
      try {
        detail = (await resp.json())?.detail;
      } catch {
        detail = await resp.text();
      }
      throw new ApiError(
        resp.status,
        `putFaceAnnotations failed (${resp.status})`,
        detail,
      );
    }
    return (await resp.json()) as import(
      "@/pages/workbench/step_panel_shell/types"
    ).AnnotationsDocument;
  },

  /** GET /face-index — cell-id → face_id mapping for the boundary glb.
   *  Used by the Viewport pickMode (DEC-V61-098 spec_v2 §A6) to resolve
   *  a vtkCellPicker hit to a stable face_id. The mapping is stable
   *  per polyMesh, so callers can cache it for the case lifetime.
   */
  getFaceIndex: async (
    caseId: string,
  ): Promise<
    import("@/pages/workbench/step_panel_shell/types").FaceIndexDocument
  > => {
    const resp = await fetch(
      `/api/cases/${encodeURIComponent(caseId)}/face-index`,
      {
        method: "GET",
        headers: { Accept: "application/json" },
        credentials: "same-origin",
      },
    );
    if (!resp.ok) {
      let detail: unknown;
      try {
        detail = (await resp.json())?.detail;
      } catch {
        detail = await resp.text();
      }
      throw new ApiError(
        resp.status,
        `getFaceIndex failed (${resp.status})`,
        detail,
      );
    }
    return (await resp.json()) as import(
      "@/pages/workbench/step_panel_shell/types"
    ).FaceIndexDocument;
  },

  // DEC-V61-108 Phase A · per-patch BC classification overrides.
  // GET → state · PUT → upsert one (returns merged state) · DELETE
  // → clear one (returns merged state). The store layer (backend)
  // owns case_lock + symlink containment + atomic write — see
  // services/case_solve/patch_classification_store.py.
  /** DEC-V61-122 + V126: GET /api/cases/{case_id}/mesh-quality.
   *  Pass ``runCheckmesh=true`` to opt into V126's Docker checkMesh
   *  augmentation (max skewness, non-orthogonality, aspect ratio).
   *  When the cfd-openfoam container is unavailable, the V126
   *  graceful-degradation contract returns the base V122 shape with
   *  checkmesh_* fields stay null — same response_model union backs
   *  both shapes via the ``report_kind`` discriminator. */
  getMeshQuality: async (
    caseId: string,
    options: { runCheckmesh?: boolean } = {},
  ): Promise<
    import("@/pages/workbench/step_panel_shell/types").MeshQualityReport
  > => {
    const url = `/api/cases/${encodeURIComponent(caseId)}/mesh-quality${
      options.runCheckmesh ? "?run_checkmesh=true" : ""
    }`;
    const resp = await fetch(url, {
      method: "GET",
      headers: { Accept: "application/json" },
      credentials: "same-origin",
    });
    if (!resp.ok) {
      let detail: unknown;
      try {
        detail = (await resp.json())?.detail;
      } catch {
        detail = await resp.text();
      }
      throw new ApiError(
        resp.status,
        `getMeshQuality failed (${resp.status})`,
        detail,
      );
    }
    return (await resp.json()) as import(
      "@/pages/workbench/step_panel_shell/types"
    ).MeshQualityReport;
  },

  getPatchClassification: async (
    caseId: string,
  ): Promise<
    import(
      "@/pages/workbench/step_panel_shell/types"
    ).PatchClassificationState
  > => {
    const resp = await fetch(
      `/api/cases/${encodeURIComponent(caseId)}/patch-classification`,
      {
        method: "GET",
        headers: { Accept: "application/json" },
        credentials: "same-origin",
      },
    );
    if (!resp.ok) {
      let detail: unknown;
      try {
        detail = (await resp.json())?.detail;
      } catch {
        detail = await resp.text();
      }
      throw new ApiError(
        resp.status,
        `getPatchClassification failed (${resp.status})`,
        detail,
      );
    }
    return (await resp.json()) as import(
      "@/pages/workbench/step_panel_shell/types"
    ).PatchClassificationState;
  },

  putPatchClassification: async (
    caseId: string,
    body: import(
      "@/pages/workbench/step_panel_shell/types"
    ).PatchClassificationPutBody,
  ): Promise<
    import(
      "@/pages/workbench/step_panel_shell/types"
    ).PatchClassificationState
  > => {
    const resp = await fetch(
      `/api/cases/${encodeURIComponent(caseId)}/patch-classification`,
      {
        method: "PUT",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        credentials: "same-origin",
        body: JSON.stringify(body),
      },
    );
    if (!resp.ok) {
      let detail: unknown;
      try {
        detail = (await resp.json())?.detail;
      } catch {
        detail = await resp.text();
      }
      throw new ApiError(
        resp.status,
        `putPatchClassification failed (${resp.status})`,
        detail,
      );
    }
    return (await resp.json()) as import(
      "@/pages/workbench/step_panel_shell/types"
    ).PatchClassificationState;
  },

  deletePatchClassification: async (
    caseId: string,
    patchName: string,
  ): Promise<
    import(
      "@/pages/workbench/step_panel_shell/types"
    ).PatchClassificationState
  > => {
    const params = new URLSearchParams({ patch_name: patchName });
    const resp = await fetch(
      `/api/cases/${encodeURIComponent(caseId)}/patch-classification?${params.toString()}`,
      {
        method: "DELETE",
        headers: { Accept: "application/json" },
        credentials: "same-origin",
      },
    );
    if (!resp.ok) {
      let detail: unknown;
      try {
        detail = (await resp.json())?.detail;
      } catch {
        detail = await resp.text();
      }
      throw new ApiError(
        resp.status,
        `deletePatchClassification failed (${resp.status})`,
        detail,
      );
    }
    return (await resp.json()) as import(
      "@/pages/workbench/step_panel_shell/types"
    ).PatchClassificationState;
  },

  solve: async (
    caseId: string,
  ): Promise<import("@/types/case_solve").SolveSummary> => {
    const resp = await fetch(
      `/api/import/${encodeURIComponent(caseId)}/solve`,
      {
        method: "POST",
        headers: { Accept: "application/json" },
        credentials: "same-origin",
      },
    );
    if (!resp.ok) {
      let detail: unknown;
      try {
        const body = await resp.json();
        detail = body?.detail ?? body;
      } catch {
        detail = await resp.text();
      }
      const message =
        typeof detail === "object" && detail !== null && "detail" in detail
          ? (detail as { detail: string }).detail
          : typeof detail === "string"
            ? detail
            : `solve failed (${resp.status})`;
      throw new ApiError(resp.status, message, detail);
    }
    return (await resp.json()) as import("@/types/case_solve").SolveSummary;
  },

  resultsSummary: async (
    caseId: string,
  ): Promise<import("@/types/case_solve").ResultsSummary> => {
    const resp = await fetch(
      `/api/cases/${encodeURIComponent(caseId)}/results-summary`,
      {
        method: "GET",
        headers: { Accept: "application/json" },
        credentials: "same-origin",
      },
    );
    if (!resp.ok) {
      let detail: unknown;
      try {
        const body = await resp.json();
        detail = body?.detail ?? body;
      } catch {
        detail = await resp.text();
      }
      const message =
        typeof detail === "object" && detail !== null && "detail" in detail
          ? (detail as { detail: string }).detail
          : typeof detail === "string"
            ? detail
            : `results-summary failed (${resp.status})`;
      throw new ApiError(resp.status, message, detail);
    }
    return (await resp.json()) as import("@/types/case_solve").ResultsSummary;
  },

  /** Step 5 multi-figure post-processing bundle (2026-04-30 dogfood
   *  feedback). Returns metadata + URLs to the four cached PNGs:
   *  contour+streamlines, pressure, vorticity, centerline.
   */
  reportBundle: async (
    caseId: string,
  ): Promise<import("@/types/case_solve").ReportBundle> => {
    const resp = await fetch(
      `/api/cases/${encodeURIComponent(caseId)}/report-bundle`,
      {
        method: "GET",
        headers: { Accept: "application/json" },
        credentials: "same-origin",
      },
    );
    if (!resp.ok) {
      let detail: unknown;
      try {
        const body = await resp.json();
        detail = body?.detail ?? body;
      } catch {
        detail = await resp.text();
      }
      const message =
        typeof detail === "object" && detail !== null && "detail" in detail
          ? (detail as { detail: string }).detail
          : typeof detail === "string"
            ? detail
            : `report-bundle failed (${resp.status})`;
      throw new ApiError(resp.status, message, detail);
    }
    return (await resp.json()) as import("@/types/case_solve").ReportBundle;
  },

  // ──────────── M-RESCUE Phase 2 · raw dict GET/POST/list ────────────
  // DEC-V61-102 — engineer manual override of AI-authored OpenFOAM
  // dicts (system/controlDict, fvSchemes, fvSolution, etc.). Inline
  // fetch wrappers preserve the structured `detail` body on 4xx so
  // the UI can branch on failing_check (etag_mismatch / validation_failed
  // / symlink_escape) rather than just status code.

  listRawDicts: async (
    caseId: string,
  ): Promise<import("@/types/case_dicts").RawDictAllowlistEntry[]> => {
    return request<import("@/types/case_dicts").RawDictAllowlistEntry[]>(
      `/api/cases/${encodeURIComponent(caseId)}/dicts`,
    );
  },

  getRawDict: async (
    caseId: string,
    relativePath: string,
  ): Promise<import("@/types/case_dicts").RawDictGet> => {
    const url = `/api/cases/${encodeURIComponent(caseId)}/dicts/${relativePath
      .split("/")
      .map(encodeURIComponent)
      .join("/")}`;
    const resp = await fetch(url, {
      method: "GET",
      headers: { Accept: "application/json" },
      credentials: "same-origin",
    });
    if (!resp.ok) {
      let detail: unknown;
      try {
        const body = await resp.json();
        detail = body?.detail ?? body;
      } catch {
        detail = await resp.text();
      }
      throw new ApiError(
        resp.status,
        typeof detail === "object" && detail !== null && "hint" in detail
          ? (detail as { hint: string }).hint
          : `getRawDict failed (${resp.status})`,
        detail,
      );
    }
    return (await resp.json()) as import("@/types/case_dicts").RawDictGet;
  },

  postRawDict: async (
    caseId: string,
    relativePath: string,
    body: import("@/types/case_dicts").RawDictPostBody,
    options?: { force?: boolean },
  ): Promise<import("@/types/case_dicts").RawDictPostResponse> => {
    const url = `/api/cases/${encodeURIComponent(caseId)}/dicts/${relativePath
      .split("/")
      .map(encodeURIComponent)
      .join("/")}${options?.force ? "?force=1" : ""}`;
    const resp = await fetch(url, {
      method: "POST",
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      body: JSON.stringify(body),
      credentials: "same-origin",
    });
    if (!resp.ok) {
      let detail: unknown;
      try {
        const parsed = await resp.json();
        detail = parsed?.detail ?? parsed;
      } catch {
        detail = await resp.text();
      }
      throw new ApiError(
        resp.status,
        typeof detail === "object" && detail !== null && "hint" in detail
          ? (detail as { hint: string }).hint
          : `postRawDict failed (${resp.status})`,
        detail,
      );
    }
    return (await resp.json()) as import("@/types/case_dicts").RawDictPostResponse;
  },
};

// ────────── DEC-V61-120 · AI coach streaming consumer ──────────

export interface StreamAICoachRequest {
  case_id: string;
  user_message: string;
  history?: Array<{ role: "user" | "assistant"; content: string }>;
  model?: string;
  temperature?: number;
  max_tokens?: number;
}

export interface StreamAICoachCallbacks {
  /** Called for each non-terminal delta frame (incremental text). */
  onDelta: (delta: string) => void;
  /** Called once on the terminal frame (done=true) with usage + model_used. */
  onDone: (final: {
    usage?: Record<string, number>;
    model_used: string;
  }) => void;
  /**
   * Called once on any error path:
   *   - kind="http": pre-stream HTTP error (401/429/400/404/502/500),
   *     status + detail surfaced from FastAPI HTTPException body.
   *   - kind="stream": mid-stream SSE error event from V61-119 R1 P1
   *     terminal-error-frame contract.
   *   - kind="abort": user cancelled via handle.cancel(); UI should
   *     silently clean up (do NOT show as error).
   *   - kind="network": fetch-level failure (offline, DNS, CORS).
   *
   * Exactly one of onDone or onError fires per request — they are
   * mutually exclusive terminal callbacks.
   */
  onError: (err: {
    kind: "http" | "stream" | "abort" | "network";
    status?: number;
    detail: string;
  }) => void;
}

export interface StreamAICoachHandle {
  /** Abort the in-flight fetch + reader; triggers onError(kind="abort"). */
  cancel: () => void;
}

/**
 * POST /api/ai-coach/stream and consume the SSE response.
 *
 * Pre-stream HTTP errors (typed in V61-119 R1 P1) raise via onError
 * BEFORE any onDelta fires. Mid-stream errors arrive as a final
 * `data: {"error": "...", "detail": "...", "done": true}` frame and
 * also raise via onError after any prior deltas.
 *
 * The returned handle's `cancel()` aborts the fetch via AbortController.
 * AbortError is silently translated to onError(kind="abort") so callers
 * can implement stop buttons without wiring console-noise filters.
 */
export function streamAICoach(
  req: StreamAICoachRequest,
  cb: StreamAICoachCallbacks,
): StreamAICoachHandle {
  const controller = new AbortController();
  let cancelled = false;

  void (async () => {
    let response: Response;
    try {
      response = await fetch("/api/ai-coach/stream", {
        method: "POST",
        headers: {
          Accept: "text/event-stream",
          "Content-Type": "application/json",
        },
        body: JSON.stringify(req),
        credentials: "same-origin",
        signal: controller.signal,
      });
    } catch (err) {
      if (cancelled || (err as Error)?.name === "AbortError") {
        cb.onError({ kind: "abort", detail: "cancelled by user" });
      } else {
        cb.onError({
          kind: "network",
          detail: (err as Error)?.message ?? "network failure",
        });
      }
      return;
    }

    if (!response.ok) {
      // Pre-stream HTTP error per V61-119 R1 P1. Body is FastAPI's
      // HTTPException JSON: {"detail": "..."}.
      let detail = response.statusText;
      try {
        const body = await response.json();
        detail =
          typeof body?.detail === "string" ? body.detail : JSON.stringify(body);
      } catch {
        try {
          detail = (await response.text()) || response.statusText;
        } catch {
          /* keep statusText */
        }
      }
      cb.onError({ kind: "http", status: response.status, detail });
      return;
    }

    if (!response.body) {
      cb.onError({
        kind: "stream",
        detail: "response had no body (browser does not support streaming)",
      });
      return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let terminated = false;

    try {
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        // SSE event separator is "\n\n". Process complete events; keep
        // any incomplete tail in `buffer` for the next read (Risk-1).
        let sep = buffer.indexOf("\n\n");
        while (sep !== -1) {
          const eventBlock = buffer.slice(0, sep);
          buffer = buffer.slice(sep + 2);
          sep = buffer.indexOf("\n\n");
          // An event block is a sequence of lines; we only care about
          // the `data:` line per V61-119's wire format.
          for (const line of eventBlock.split("\n")) {
            if (!line.startsWith("data:")) continue;
            const payload = line.slice("data:".length).trim();
            if (!payload) continue;
            let parsed: Record<string, unknown>;
            try {
              parsed = JSON.parse(payload) as Record<string, unknown>;
            } catch {
              cb.onError({
                kind: "stream",
                detail: "received malformed SSE event from server",
              });
              terminated = true;
              break;
            }
            if (typeof parsed.error === "string") {
              cb.onError({
                kind: "stream",
                detail:
                  typeof parsed.detail === "string"
                    ? parsed.detail
                    : (parsed.error as string),
              });
              terminated = true;
              break;
            }
            if (parsed.done === true) {
              cb.onDone({
                model_used:
                  typeof parsed.model_used === "string"
                    ? parsed.model_used
                    : "unknown",
                usage:
                  typeof parsed.usage === "object" && parsed.usage !== null
                    ? (parsed.usage as Record<string, number>)
                    : undefined,
              });
              terminated = true;
              break;
            }
            if (typeof parsed.delta === "string" && parsed.delta.length > 0) {
              cb.onDelta(parsed.delta);
            }
          }
          if (terminated) break;
        }
        if (terminated) break;
      }
    } catch (err) {
      if (cancelled || (err as Error)?.name === "AbortError") {
        cb.onError({ kind: "abort", detail: "cancelled by user" });
      } else {
        cb.onError({
          kind: "stream",
          detail: (err as Error)?.message ?? "stream read failure",
        });
      }
      return;
    } finally {
      try {
        reader.releaseLock();
      } catch {
        /* releaseLock can throw if already released — best-effort */
      }
    }

    if (!terminated) {
      // Server closed the stream without an explicit done frame.
      // Synthesize one so the UI cleans up its streaming state.
      cb.onDone({ model_used: "unknown" });
    }
  })();

  return {
    cancel: () => {
      cancelled = true;
      controller.abort();
    },
  };
}

// ────────── DEC-V61-121 · Apply AI proposal ──────────

export interface ApplyAIProposalRequest {
  case_id: string;
  tool: string;
  args: Record<string, unknown>;
  model_used?: string | null;
  conversation_turn_id?: string | null;
}

export interface ApplyAIProposalResponse {
  applied: true;
  tool: string;
  summary: string;
  state_after: Record<string, unknown>;
  audit_id: string | null;
  audit_warning?: string;
}

/**
 * POST /api/ai-coach/apply-proposal — apply a proposal the engineer
 * [Accepted] in the AICoachPanel ProposalCard. Validates against the
 * V121 tool registry server-side and writes an audit entry.
 *
 * Throws ApiError on non-2xx; the route's structured `detail` body
 * is preserved on the error so the UI can surface the failing_check
 * + tool name + arg-validation errors.
 */
export async function applyAIProposal(
  req: ApplyAIProposalRequest,
): Promise<ApplyAIProposalResponse> {
  const resp = await fetch("/api/ai-coach/apply-proposal", {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(req),
    credentials: "same-origin",
  });
  if (!resp.ok) {
    let detail: unknown;
    try {
      const parsed = await resp.json();
      detail = parsed?.detail ?? parsed;
    } catch {
      try {
        detail = await resp.text();
      } catch {
        detail = resp.statusText;
      }
    }
    // V123 R2 P2-2: prefer inner_failing_check when present so the
    // ApiError.message surfaces the actionable code (cell_cap_exceeded /
    // symlink_escape / gmshToFoam_failed etc) rather than the wrapping
    // 'underlying_service_error'. ProposalCard reads the same field
    // off detail; both paths now agree.
    const message =
      typeof detail === "object" && detail !== null && "failing_check" in detail
        ? `apply-proposal failed: ${
            (detail as { inner_failing_check?: string }).inner_failing_check ??
            (detail as { failing_check: string }).failing_check
          }`
        : `apply-proposal failed (${resp.status})`;
    throw new ApiError(resp.status, message, detail);
  }
  return (await resp.json()) as ApplyAIProposalResponse;
}
