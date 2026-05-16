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
 * In V67-C TopBar fed entirely from caller props (StepPanelShell:488 passed
 * only caseId). V68-A.2 wires real backend data via this hook; in offline /
 * pre-MSW environments the hook returns the blueprint-safe defaults so the
 * UI never flashes raw nulls.
 */
import { useQuery } from "@tanstack/react-query";

export interface CaseStatusRaw {
  case_id?: string;
  truth_source?: string | null;
  trust_gate?: string | null;
  audit_pct?: number | null;
  llm_offline?: boolean | null;
  last_action?: string | null;
  validation?: string | null;
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

export function normalizeCaseStatus(
  caseId: string,
  raw: CaseStatusRaw | undefined | null,
): CaseStatus {
  const truthSource =
    raw?.truth_source != null && raw.truth_source !== ""
      ? TRUTH_SOURCE_MAP[raw.truth_source]
      : undefined;
  const trustGate =
    raw?.trust_gate != null && raw.trust_gate !== ""
      ? TRUST_GATE_MAP[raw.trust_gate]
      : undefined;
  return {
    caseId,
    truthSource: truthSource ?? "unknown",
    trustGate: trustGate ?? "PENDING",
    auditPct:
      typeof raw?.audit_pct === "number" &&
      raw.audit_pct >= 0 &&
      raw.audit_pct <= 100
        ? raw.audit_pct
        : null,
    // V130 invariant: default to true (offline-first guarantee). Only flip
    // to false when the backend explicitly reports llm_offline=false.
    llmOffline: raw?.llm_offline === false ? false : true,
    lastAction: raw?.last_action ?? null,
    validation: raw?.validation ?? null,
  };
}

async function fetchCaseStatus(caseId: string): Promise<CaseStatusRaw> {
  const res = await fetch(`/api/cases/${encodeURIComponent(caseId)}/status`, {
    method: "GET",
  });
  if (!res.ok) {
    // V130 invariant: never throw on /status — surface PENDING instead so the
    // UI doesn't escalate a transient backend hiccup to an audit failure.
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
