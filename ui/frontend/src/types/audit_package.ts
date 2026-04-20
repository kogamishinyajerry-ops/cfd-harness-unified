// Phase 5 · Screen 6 — Audit Package Builder types.
// Mirrors ui/backend/schemas/audit_package.py.

export interface AuditPackageDownloadUrls {
  manifest_json: string;
  bundle_zip: string;
  bundle_html: string;
  bundle_pdf: string | null;
  bundle_sig: string;
}

// Renamed from AuditPackageVvChecklistItem per Codex PR-5d MEDIUM finding:
// the 8-row table is a product-specific summary, not a faithful rendering
// of the FDA/ASME V&V40 framework.
export interface AuditPackageEvidenceItem {
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
  evidence_summary: AuditPackageEvidenceItem[];
  signature_hex: string;
}
