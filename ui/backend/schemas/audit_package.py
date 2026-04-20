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


class AuditPackageEvidenceItem(BaseModel):
    """One internal evidence-summary area + manifest-field mapping.

    This is a product-specific summary table; it is NOT a faithful
    rendering of the FDA/ASME V&V40 framework, which structures credibility
    around preliminary steps, credibility evidence categories, and
    credibility factors/goals. A future PR will align this to the guidance
    template. Per-row manifest_fields may reference data that is only
    populated when run artifacts are attached — skeleton (no-run) bundles
    will show empty values for run.inputs / run.outputs / measurement.*.
    """

    area: str
    description: str
    manifest_fields: List[str]


class AuditPackageBuildResponse(BaseModel):
    """Returned by POST /cases/{id}/runs/{rid}/audit-package/build."""

    bundle_id: str = Field(..., description="32-hex uuid4; opaque to the UI")
    manifest_id: str
    case_id: str
    run_id: str
    build_fingerprint: str = Field(
        ...,
        description=(
            "Deterministic 16-hex identifier derived from (case_id, run_id). "
            "Renamed from `generated_at` per DEC-V61-019 L3 finding: the "
            "value is an opaque hash, not a wall-clock timestamp, so the "
            "old name misled reviewers."
        ),
    )
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
    evidence_summary: List[AuditPackageEvidenceItem] = Field(
        ...,
        description=(
            "Internal evidence-summary mapping from manifest fields to "
            "V&V concerns. NOT a faithful FDA/ASME V&V40 template — renamed "
            "from `vv40_checklist` per Codex PR-5d MEDIUM finding."
        ),
    )
    signature_hex: str = Field(
        ...,
        description=(
            "64-char hex HMAC-SHA256. UI may display or hide — the sidecar "
            ".sig file is the canonical persistence."
        ),
    )
