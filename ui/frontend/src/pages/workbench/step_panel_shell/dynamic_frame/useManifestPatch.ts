// DEC-V61-202-SUB-M30-CYCLE2 · React Query mutation for field-path PATCH.
//
// Closes the observation → action → state-change loop. On success,
// invalidates the workbench-frame query so the next render reflects
// the new manifest state.
//
// Failure modes:
//   - 409 (state_sha conflict): frontend caller should refetch frame
//     (the conflict detail includes current_state_sha for cheap recovery)
//   - 400 (malformed field_path): bug in caller; surface to user
//   - 422 (request shape invalid): bug in caller
//   - 200 + success=false: schema-validation rejection; payload's
//     validation_errors[] is the engineer-readable list

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "@/api/client";
import type {
  ManifestPatchRequest,
  ManifestPatchResponse,
} from "@/types/manifest_patch";

export interface UseManifestPatchInput {
  caseId: string;
  onSuccess?: (response: ManifestPatchResponse) => void;
  onError?: (error: unknown) => void;
}

export function useManifestPatch(input: UseManifestPatchInput) {
  const { caseId, onSuccess, onError } = input;
  const qc = useQueryClient();

  return useMutation<ManifestPatchResponse, unknown, ManifestPatchRequest>({
    mutationFn: (request) => api.patchCaseManifest(caseId, request),
    onSuccess: (response) => {
      // Invalidate the workbench-frame query so the next render
      // re-fetches with the new state. Keyed by caseId — covers all
      // (step, focus) combinations of frame.
      qc.invalidateQueries({
        queryKey: ["workbench-frame", caseId],
      });
      // Also invalidate completeness, since field writes affect
      // the missing-field list directly.
      qc.invalidateQueries({
        queryKey: ["case-completeness", caseId],
      });
      onSuccess?.(response);
    },
    onError,
  });
}
