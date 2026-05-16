/**
 * V68-A.2 · React Query hook backing TopBar's 4 dynamic fields:
 *   - truth_source → TopBar truthSource
 *   - trust_gate   → TopBar trustGate
 *   - audit_pct    → TopBar auditPct
 *   - llm_offline  → TopBar llmOffline (V130 invariant indicator)
 *
 * The hook normalises the backend payload (snake_case) into the TopBar's
 * camelCase props vocabulary, and clamps invalid/missing values to the
 * blueprint's safe-default zone (PENDING / unknown / null).
 *
 * V68-B.2 · Endpoint repointed from /api/cases/:id/status (V68-A invented)
 * to the real backend's /api/cases/:id/completeness so the hook drives off
 * real audit verdicts (Phase-0 contract: percentage, ready_for_archive,
 * blocked_by_critical, case_kind). MSW handler still serves a /status-style
 * fallback shape for the legacy raw fields — `normalizeCaseStatus` accepts
 * either shape (real-backend or legacy) and converges on the TopBar vocab.
 */
import { useQuery } from "@tanstack/react-query";

export interface CaseStatusRaw {
  case_id?: string;
  // Legacy V68-A /status shape
  truth_source?: string | null;
  trust_gate?: string | null;
  audit_pct?: number | null;
  llm_offline?: boolean | null;
  last_action?: string | null;
  validation?: string | null;
  // V68-B real /completeness shape
  case_kind?: string | null;
  ready_for_archive?: boolean | null;
  blocked_by_critical?: number | null;
  percentage?: number | null;
  // Carried-but-unused fields from /completeness — typed so tests / fixtures
  // can construct realistic payloads without TS2353.
  present_count?: number;
  total_count?: number;
  missing?: unknown[];
  notes?: unknown[];
}

export interface CaseStatus {
  caseId: string;
  truthSource: "openfoam_native" | "mock" | "unknown";
  trustGate: "PASS" | "PASS_WITH_DISCLAIMER" | "FAIL" | "PENDING";
  auditPct: number | null;
  llmOffline: boolean;
  lastAction: string | null;
  validation: string | null;
}

const TRUST_GATE_MAP: Record<string, CaseStatus["trustGate"]> = {
  "audit-passing": "PASS",
  "audit-passing-with-disclaimer": "PASS_WITH_DISCLAIMER",
  "audit-failing": "FAIL",
  "audit-pending": "PENDING",
  PASS: "PASS",
  PASS_WITH_DISCLAIMER: "PASS_WITH_DISCLAIMER",
  FAIL: "FAIL",
  PENDING: "PENDING",
};

const TRUTH_SOURCE_MAP: Record<string, CaseStatus["truthSource"]> = {
  "openfoam-native": "openfoam_native",
  openfoam_native: "openfoam_native",
  "msw-mock": "mock",
  mock: "mock",
  unknown: "unknown",
};

function deriveTruthSource(
  raw: CaseStatusRaw | undefined | null,
): CaseStatus["truthSource"] | undefined {
  // V68-A legacy fast-path (MSW handler or any caller providing truth_source).
  if (raw?.truth_source != null && raw.truth_source !== "") {
    return TRUTH_SOURCE_MAP[raw.truth_source];
  }
  // V68-B real-backend path: case_kind="whitelist" / "imported_user" / ...
  // whitelist cases come from corpus = openfoam_native truth; user imports = unknown
  // until they reach archive state (V132 advisor-only invariant).
  const kind = raw?.case_kind;
  if (kind === "whitelist") return "openfoam_native";
  if (kind === "imported_user" || kind === "imported") return "unknown";
  return undefined;
}

function deriveTrustGate(
  raw: CaseStatusRaw | undefined | null,
): CaseStatus["trustGate"] | undefined {
  // V68-A legacy fast-path.
  if (raw?.trust_gate != null && raw.trust_gate !== "") {
    return TRUST_GATE_MAP[raw.trust_gate];
  }
  // V68-B real-backend path: derive from ready_for_archive + blocked_by_critical.
  if (typeof raw?.ready_for_archive === "boolean") {
    if (raw.ready_for_archive) return "PASS";
    if ((raw.blocked_by_critical ?? 0) > 0) return "FAIL";
    return "PASS_WITH_DISCLAIMER";
  }
  return undefined;
}

function deriveAuditPct(
  raw: CaseStatusRaw | undefined | null,
): number | null {
  // V68-A legacy fast-path.
  if (
    typeof raw?.audit_pct === "number" &&
    raw.audit_pct >= 0 &&
    raw.audit_pct <= 100
  ) {
    return raw.audit_pct;
  }
  // V68-B real-backend path: completeness `percentage` field.
  if (
    typeof raw?.percentage === "number" &&
    raw.percentage >= 0 &&
    raw.percentage <= 100
  ) {
    return raw.percentage;
  }
  return null;
}

export function normalizeCaseStatus(
  caseId: string,
  raw: CaseStatusRaw | undefined | null,
): CaseStatus {
  return {
    caseId,
    truthSource: deriveTruthSource(raw) ?? "unknown",
    trustGate: deriveTrustGate(raw) ?? "PENDING",
    auditPct: deriveAuditPct(raw),
    // V130 invariant: default to true (offline-first guarantee). Only flip
    // to false when the backend explicitly reports llm_offline=false.
    llmOffline: raw?.llm_offline === false ? false : true,
    lastAction: raw?.last_action ?? null,
    validation: raw?.validation ?? null,
  };
}

async function fetchCaseStatus(caseId: string): Promise<CaseStatusRaw> {
  // V68-B.2 · hit real backend's /api/cases/:id/completeness route.
  const res = await fetch(
    `/api/cases/${encodeURIComponent(caseId)}/completeness`,
    { method: "GET" },
  );
  if (!res.ok) {
    // V130 invariant: never throw on case-status — surface PENDING instead so
    // the UI doesn't escalate a transient backend hiccup to an audit failure.
    return {};
  }
  return (await res.json()) as CaseStatusRaw;
}

export function useCaseStatus(caseId: string | null | undefined) {
  const query = useQuery({
    queryKey: ["case-status", caseId],
    queryFn: () => fetchCaseStatus(caseId!),
    enabled: Boolean(caseId),
    staleTime: 15_000,
    refetchOnWindowFocus: false,
  });

  const status = normalizeCaseStatus(caseId ?? "", query.data);
  return { status, isLoading: query.isLoading, isError: query.isError };
}
