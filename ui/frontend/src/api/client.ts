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
    return (await resp.json()) as import("@/types/mesh_imported").MeshSuccessResponse;
  },
};
