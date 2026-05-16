// V73.3 · Multi-case comparison ribbon for Step 5 (Postprocess).
//
// Shows the current case alongside up to 4 canonical whitelist references so
// the engineer can read their result against the corpus at a glance. Pulls
// real `/api/cases` data (no hardcoded list) — see V73 reverse-stop rule.
//
// Layout: horizontal strip of equal-width chips. Current case is highlighted
// with the v3 accent (sand-coral), references stay neutral. Each chip names
// the case, shows its gold-standard status, and its contract verdict if
// known. No mutating controls — this is a read-only comparison surface.

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { CaseIndexEntry } from "@/types/validation";

interface MultiCaseRibbonV3Props {
  caseId: string;
}

function useCaseList() {
  return useQuery<CaseIndexEntry[]>({
    queryKey: ["v3-case-list"],
    queryFn: () => api.listCases(),
    staleTime: 30_000,
    retry: 1,
    refetchOnWindowFocus: false,
  });
}

function verdictTone(status?: string): { dot: string; label: string } {
  switch (status) {
    case "audit-passing":
    case "PASS":
      return { dot: "bg-v3-inlet", label: "PASS" };
    case "audit-failing":
    case "FAIL":
      return { dot: "bg-v3-wall", label: "FAIL" };
    case "gold-pending":
    case "PENDING":
      return { dot: "bg-v3-symmetry", label: "PEND" };
    default:
      return { dot: "bg-v3-border", label: "—" };
  }
}

function CaseChip({
  entry,
  isCurrent,
  label,
}: {
  entry: CaseIndexEntry | { case_id: string; name: string };
  isCurrent: boolean;
  label: string;
}) {
  const full = "contract_status" in entry ? entry : null;
  const tone = verdictTone(full?.contract_status as string | undefined);
  return (
    <div
      data-testid={isCurrent ? "multi-case-chip-current" : "multi-case-chip"}
      data-case-id={entry.case_id}
      data-active={isCurrent ? "true" : "false"}
      className={`flex flex-col gap-1 min-w-[160px] flex-1 border rounded-md px-3 py-2 motion-safe:transition-colors ${
        isCurrent
          ? "border-v3-accent bg-v3-surface2"
          : "border-v3-border bg-v3-surface1 hover:border-v3-borderActive"
      }`}
    >
      <div className="flex items-center justify-between">
        <span className="text-[10px] uppercase tracking-[0.08em] text-v3-textTertiary">
          {label}
        </span>
        <span
          className={`inline-flex items-center gap-1 text-[10px] text-v3-textTertiary`}
        >
          <span className={`inline-block w-1.5 h-1.5 rounded-full ${tone.dot}`} />
          {tone.label}
        </span>
      </div>
      <div className="text-[12px] text-v3-textPrimary font-mono truncate">
        {entry.case_id}
      </div>
      <div className="text-[10px] text-v3-textTertiary truncate">
        {entry.name}
      </div>
    </div>
  );
}

export function MultiCaseRibbonV3({ caseId }: MultiCaseRibbonV3Props) {
  const { data: cases, isLoading, isError } = useCaseList();

  const { current, refs } = useMemo(() => {
    if (!Array.isArray(cases)) {
      return {
        current: { case_id: caseId, name: caseId } as const,
        refs: [] as CaseIndexEntry[],
      };
    }
    const found = cases.find((c) => c.case_id === caseId);
    // Reference pool = whitelist cases other than the current one
    const pool = cases.filter(
      (c) => c.case_kind === "whitelist" && c.case_id !== caseId,
    );
    return {
      current: found ?? ({ case_id: caseId, name: caseId } as const),
      refs: pool.slice(0, 4),
    };
  }, [cases, caseId]);

  if (isLoading) {
    return (
      <div
        data-testid="multi-case-ribbon-loading"
        className="h-[90px] border-t border-v3-border bg-v3-bg flex items-center justify-center text-[11px] text-v3-textTertiary"
      >
        loading reference cases…
      </div>
    );
  }

  if (isError || refs.length === 0) {
    return (
      <div
        data-testid="multi-case-ribbon-offline-hint"
        data-source="fallback"
        className="h-[90px] border-t border-v3-border bg-v3-bg flex items-center px-4 text-[11px] text-v3-textTertiary"
      >
        Multi-case comparison unavailable · /api/cases offline. Showing the
        current case only.
      </div>
    );
  }

  return (
    <div
      data-testid="multi-case-ribbon"
      data-source="live"
      className="border-t border-v3-border bg-v3-bg px-4 py-2"
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-[10px] uppercase tracking-[0.10em] text-v3-textTertiary">
          step 5 · this case vs canonical references
        </span>
        <span className="text-[10px] text-v3-textTertiary">
          {refs.length} of {Math.max(refs.length, 4)} references
        </span>
      </div>
      <div className="flex gap-2 overflow-x-auto">
        <CaseChip entry={current} isCurrent label="this case" />
        {refs.map((r) => (
          <CaseChip key={r.case_id} entry={r} isCurrent={false} label="reference" />
        ))}
      </div>
    </div>
  );
}
