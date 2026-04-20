// Phase 5 · Screen 6 — Audit Package Builder types.
// Mirrors ui/backend/schemas/audit_package.py.

export interface AuditPackageDownloadUrls {
  manifest_json: string;
  bundle_zip: string;
  bundle_html: string;
  bundle_pdf: string | null;
  bundle_sig: string;
}

export interface AuditPackageVvChecklistItem {
  area: string;
  description: string;
  manifest_fields: string[];
}

export interface AuditPackageBuildResponse {
  bundle_id: string;
  manifest_id: string;
  case_id: string;
  run_id: string;
  generated_at: string;
  git_repo_commit_sha: string | null;
  comparator_verdict: string | null;
  pdf_available: boolean;
  pdf_error: string | null;
  downloads: AuditPackageDownloadUrls;
  vv40_checklist: AuditPackageVvChecklistItem[];
  signature_hex: string;
}
