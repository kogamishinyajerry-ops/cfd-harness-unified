/**
 * DEC-V61-205 (M5 C3) · real post-processing verdict for the V4 Post pill.
 *
 * Replaces the hardcoded `POST_BLUEPRINT_VERDICT` ("通过 · +4.2% flow") — a
 * fake PASS claim that a truth-chain workbench must never ship — with the
 * real backend gold-vs-measured comparison verdict, or an honest no-baseline
 * state when the case has no reference.
 *
 * Source: GET /api/cases/{caseId}/runs/{runLabel}/comparison-report/context
 * (same endpoint the /learn ScientificComparisonReport consumes). It returns
 * a real `verdict` (PASS/PARTIAL/FAIL) + `verdict_subtitle` + n_pass/n_total
 * for gold-standard cases, a `visual_only` reduced context for cases with
 * renders but no gold, and 404/400 for cases not opted into comparison.
 *
 * State the caller renders:
 *   - "loading"  → enabled fetch genuinely in flight → pill hidden
 *   - "verdict"  → real PASS/PARTIAL/FAIL from gold comparison
 *   - "none"     → no run to compare (disabled) OR no baseline (visual_only /
 *                  404 / 400) → honest neutral pill (never a perpetual pending)
 *   - "error"    → 5xx / network → honest "report unavailable" (never a PASS)
 */
import { useQuery } from "@tanstack/react-query";

import { ApiError } from "@/api/client";

export type VerdictLevel = "PASS" | "PARTIAL" | "FAIL";

/** Minimal slice of the backend ComparisonReportContext (full shape lives in
 *  learn/case_detail/ScientificComparisonReport). V4 only needs the verdict. */
interface ComparisonContextSlice {
  visual_only?: boolean;
  verdict?: VerdictLevel | string | null;
  verdict_subtitle?: string;
  subtitle?: string;
  metrics?: { n_pass: number; n_total: number; max_dev_pct?: number } | null;
}

export type PostVerdictState = "loading" | "verdict" | "none" | "error";

export interface PostVerdict {
  state: PostVerdictState;
  /** Real verdict level when state==="verdict". */
  level: VerdictLevel | null;
  /** Human subtitle (n_pass/n_total etc.) when state==="verdict". */
  detail: string | null;
  nPass: number | null;
  nTotal: number | null;
}

function normalizeVerdict(v: string | null | undefined): VerdictLevel | null {
  if (v === "PASS" || v === "PARTIAL" || v === "FAIL") return v;
  return null;
}

export function useComparisonVerdict(
  caseId: string | null | undefined,
  runLabel: string | null | undefined,
): PostVerdict {
  const enabled =
    typeof caseId === "string" &&
    caseId.length > 0 &&
    typeof runLabel === "string" &&
    runLabel.length > 0;

  const q = useQuery<ComparisonContextSlice, ApiError>({
    queryKey: ["v4-comparison-verdict", caseId ?? "__none__", runLabel ?? "__none__"],
    queryFn: async ({ signal }) => {
      const resp = await fetch(
        `/api/cases/${encodeURIComponent(caseId as string)}/runs/${encodeURIComponent(
          runLabel as string,
        )}/comparison-report/context`,
        { credentials: "same-origin", signal },
      );
      if (!resp.ok) throw new ApiError(resp.status, await resp.text());
      return (await resp.json()) as ComparisonContextSlice;
    },
    enabled,
    retry: false,
    staleTime: 60_000,
    refetchOnWindowFocus: false,
  });

  // Codex M5-C4 R2 P2 · a DISABLED query (no run to compare — unsolved or
  // failed-only case) must resolve to honest "none", NOT a perpetual
  // "loading": the query will never fire on its own, so reusing the pending
  // state would strand the Post surfaces in "对比中…"/"…" forever. "loading"
  // is reserved for an enabled fetch genuinely in flight.
  if (!enabled) {
    return { state: "none", level: null, detail: null, nPass: null, nTotal: null };
  }
  if (q.isLoading) {
    return { state: "loading", level: null, detail: null, nPass: null, nTotal: null };
  }

  if (q.error) {
    // 404/400 = case not opted into comparison → honest "no baseline".
    // 5xx / network = report service problem → honest "unavailable".
    const status = q.error instanceof ApiError ? q.error.status : 0;
    if (status === 404 || status === 400) {
      return { state: "none", level: null, detail: null, nPass: null, nTotal: null };
    }
    return { state: "error", level: null, detail: null, nPass: null, nTotal: null };
  }

  const data = q.data;
  const level = normalizeVerdict(data?.verdict);
  // visual-only (renders but no gold) or a context without a real verdict →
  // no baseline. Never synthesize a PASS.
  if (!data || data.visual_only || level === null) {
    return { state: "none", level: null, detail: null, nPass: null, nTotal: null };
  }

  return {
    state: "verdict",
    level,
    detail: data.verdict_subtitle ?? data.subtitle ?? null,
    nPass: data.metrics?.n_pass ?? null,
    nTotal: data.metrics?.n_total ?? null,
  };
}
