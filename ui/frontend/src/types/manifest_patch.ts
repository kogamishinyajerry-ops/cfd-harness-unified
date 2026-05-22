// DEC-V61-202-SUB-M30-CYCLE2 · TS mirror of backend manifest_patch schemas.
//
// Stay byte-equivalent to ui/backend/schemas/manifest_patch.py.

export type PatchOp = "set" | "unset";

export type ManifestPatchCaseKind =
  | "imported_user"
  | "draft"
  | "whitelist"
  | "whitelist_forked";

export interface ManifestPatchRequest {
  field_path: string;
  value: unknown;
  op?: PatchOp;
  expected_state_sha: string;
}

export interface ManifestPatchResponse {
  success: boolean;
  applied_path: string;
  new_state_sha: string;
  case_kind: ManifestPatchCaseKind;
  validation_errors: string[];
}

/** HTTP 409 detail payload — frontend can use current_state_sha to
 *  avoid a separate GET to recover from a concurrency conflict. */
export interface ManifestPatchConflictDetail {
  message: string;
  current_state_sha: string;
}
