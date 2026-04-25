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
  RunCheckpointsResponse,
} from "@/types/decisions";
import type { AuditPackageBuildResponse } from "@/types/audit_package";
import type { WorkbenchBasics } from "@/types/workbench_basics";

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

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
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

  // Phase 3
  getRunCheckpoints: (caseId: string) =>
    request<RunCheckpointsResponse>(
      `/api/runs/${encodeURIComponent(caseId)}/checkpoints`,
    ),
  runStreamUrl: (caseId: string) =>
    `/api/runs/${encodeURIComponent(caseId)}/stream`,

  // Phase 4
  getDashboard: () => request<DashboardResponse>("/api/dashboard"),

  // Phase 5 — Audit Package Builder (Screen 6)
  buildAuditPackage: (caseId: string, runId: string) =>
    request<AuditPackageBuildResponse>(
      `/api/cases/${encodeURIComponent(caseId)}/runs/${encodeURIComponent(runId)}/audit-package/build`,
      { method: "POST", body: "{}" },
    ),

  // Stage 2 — industrial workbench first-screen
  getWorkbenchBasics: (caseId: string) =>
    request<WorkbenchBasics>(
      `/api/cases/${encodeURIComponent(caseId)}/workbench-basics`,
    ),
};
