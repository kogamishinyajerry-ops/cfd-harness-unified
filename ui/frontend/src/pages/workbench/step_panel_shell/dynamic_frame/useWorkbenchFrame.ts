// DEC-V61-202-SUB-M30-CYCLE1 · React Query hook for the dynamic frame.
//
// Polls GET /api/cases/{id}/workbench_frame?step=N&focus_*=...
// Re-fetches when step or focus changes. The backend response includes
// state_sha so we can compare frames cheaply without deep equality.

import { useQuery } from "@tanstack/react-query";

import { api } from "@/api/client";
import type { WorkbenchFrame } from "@/types/workbench_frame";

export interface UseWorkbenchFrameInput {
  caseId: string;
  step: number;
  focusPatch?: string | null;
  focusRegion?: string | null;
  focusPanel?: string | null;
  enabled?: boolean;
}

export function useWorkbenchFrame(input: UseWorkbenchFrameInput) {
  const {
    caseId,
    step,
    focusPatch,
    focusRegion,
    focusPanel,
    enabled = true,
  } = input;

  return useQuery<WorkbenchFrame>({
    queryKey: [
      "workbench-frame",
      caseId,
      step,
      focusPatch ?? null,
      focusRegion ?? null,
      focusPanel ?? null,
    ],
    queryFn: () =>
      api.getWorkbenchFrame(caseId, step, {
        patch: focusPatch,
        region: focusRegion,
        panel: focusPanel,
      }),
    enabled: enabled && Boolean(caseId) && step >= 1 && step <= 5,
    staleTime: 15_000,
    retry: false,
  });
}
