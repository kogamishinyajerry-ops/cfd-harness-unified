"""Pydantic schemas for Screen 6 audit-package builder
(Phase 5 · PR-5d · DEC-V61-018)."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class AuditPackageDownloadUrls(BaseModel):
    """Server-relative URLs the UI links to for downloads."""

    manifest_json: str = Field(..., description="JSON manifest alone (convenience)")
    bundle_zip: str = Field(..., description="Byte-reproducible zip bundle")
    bundle_html: str = Field(..., description="Human-readable semantic HTML")
    bundle_pdf: Optional[str] = Field(
        None,
        description=(
            "PDF render (weasyprint). None when native libs unavailable; "
            "see `pdf_error` for actionable install hint."
        ),
    )
    bundle_sig: str = Field(..., description="HMAC-SHA256 hex signature sidecar (.sig)")


class AuditPackageVvChecklistItem(BaseModel):
    """One FDA V&V40 credibility-evidence area + manifest-field mapping."""

    area: str
    description: str
    manifest_fields: List[str]


class AuditPackageBuildResponse(BaseModel):
    """Returned by POST /cases/{id}/runs/{rid}/audit-package/build."""

    bundle_id: str = Field(..., description="32-hex uuid4; opaque to the UI")
    manifest_id: str
    case_id: str
    run_id: str
    generated_at: str
    git_repo_commit_sha: Optional[str]
    comparator_verdict: Optional[str] = Field(
        None, description="PASS | FAIL | HAZARD | None (no comparator run recorded)"
    )
    pdf_available: bool
    pdf_error: Optional[str] = Field(
        None,
        description=(
            "Install hint when PDF render failed. Expect non-None when "
            "`pdf_available` is False."
        ),
    )
    downloads: AuditPackageDownloadUrls
    vv40_checklist: List[AuditPackageVvChecklistItem]
    signature_hex: str = Field(
        ...,
        description=(
            "64-char hex HMAC-SHA256. UI may display or hide — the sidecar "
            ".sig file is the canonical persistence."
        ),
    )
