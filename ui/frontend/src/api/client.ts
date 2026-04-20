// Thin fetch wrapper. Vite proxies /api → 127.0.0.1:8000 in dev (see
// vite.config.ts); in production the frontend is served from the same
// origin as the FastAPI app, so the same relative paths work unchanged.

import type {
  CaseDetail,
  CaseIndexEntry,
  ValidationReport,
} from "@/types/validation";

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(path, {
    method: "GET",
    headers: { Accept: "application/json" },
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
  health: () => getJson<{ status: string; version: string }>("/api/health"),
  listCases: () => getJson<CaseIndexEntry[]>("/api/cases"),
  getCase: (caseId: string) =>
    getJson<CaseDetail>(`/api/cases/${encodeURIComponent(caseId)}`),
  getValidationReport: (caseId: string) =>
    getJson<ValidationReport>(
      `/api/validation-report/${encodeURIComponent(caseId)}`,
    ),
};
