"""Audit package route (Phase 5 · PR-5d · Screen 6).

    POST /api/cases/{case_id}/runs/{run_id}/audit-package/build
        → Build manifest + zip + html + pdf + HMAC signature. Returns
          bundle_id + download URLs + V&V40 checklist mapping.

    GET  /api/audit-packages/{bundle_id}/manifest.json
    GET  /api/audit-packages/{bundle_id}/bundle.zip
    GET  /api/audit-packages/{bundle_id}/bundle.html
    GET  /api/audit-packages/{bundle_id}/bundle.pdf
    GET  /api/audit-packages/{bundle_id}/bundle.sig
        → Serve individual artifacts. 404 on unknown bundle_id.

Security notes
--------------
- HMAC secret is read from ``CFD_HARNESS_HMAC_SECRET`` via
  :func:`audit_package.get_hmac_secret_from_env`. In dev, the sample
  systemd/.env example should set ``CFD_HARNESS_HMAC_SECRET="text:<dev-key>"``.
  Production deployments should use ``base64:<openssl rand -base64 32>``.
- Bundles are staged under a gitignored per-request directory and served
  as static files by FastAPI. This route does NOT implement TTL cleanup —
  that's a follow-up for production (PR-5e / ops workflow).
- Missing HMAC env var returns HTTP 500 with the ``HmacSecretMissing``
  message (which includes rotation hints). Operators see the error
  message in browser devtools — this is intentional for dev UX.

Non-goals (queued for post-PR-5d):
- Async build with progress streaming (SSE)
- Bundle TTL / cleanup
- Multi-user isolation (staging dir is shared)
- Production-grade key management (env var is sufficient for Phase 5)
"""

from __future__ import annotations

import hashlib
import uuid
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from src.audit_package import (
    HmacSecretMissing,
    PdfBackendUnavailable,
    build_manifest,
    get_hmac_secret_from_env,
    is_pdf_backend_available,
    render_html,
    serialize_pdf,
    serialize_zip,
    sign,
    write_sidecar,
)
from ui.backend.schemas.audit_package import (
    AuditPackageBuildResponse,
    AuditPackageDownloadUrls,
    AuditPackageEvidenceItem,
)
from ui.backend.services.validation_report import (  # noqa: SLF001
    _load_run_measurement,
    is_whitelisted,
)

router = APIRouter()

# Staging dir is repo-local but gitignored (ui/backend/.audit_package_staging/).
# Each POST creates a subdir named by bundle_id. GET serves files from there.
_REPO_ROOT = Path(__file__).resolve().parents[3]
_STAGING_ROOT = _REPO_ROOT / "ui" / "backend" / ".audit_package_staging"


# ---------------------------------------------------------------------------
# Internal evidence-summary mapping (NOT a formal V&V40 template)
# ---------------------------------------------------------------------------
# 8 product-specific V&V concerns + which manifest fields carry the
# supporting evidence. Renamed from `_VV40_CHECKLIST` per Codex PR-5d
# MEDIUM finding: the FDA 2023 CM&S guidance
# (https://www.fda.gov/media/154985/download) structures credibility around
# preliminary steps, credibility evidence categories, and credibility
# factors/goals — NOT this 8-row list. A future PR will align to the
# guidance template; until then, the UI labels this "Internal V&V evidence
# summary" to avoid implying FDA coverage the artifact does not provide.
#
# Some rows reference manifest fields (run.inputs, run.outputs.*,
# measurement.*) that are populated only when run artifacts are attached.
# Skeleton bundles (MOCK / no-run) will show those fields as empty — the
# UI should make that absence visible rather than imply it was provided.

_EVIDENCE_SUMMARY: List[Dict[str, Any]] = [
    {
        "area": "Applicability Justification",
        "description": "Context of use and intended scope for the computational model",
        "manifest_fields": ["case.whitelist_entry", "case.gold_standard"],
    },
    {
        "area": "Code Verification",
        "description": "Solver implementation correctness (convergence, order of accuracy)",
        "manifest_fields": ["run.inputs", "run.outputs.solver_log_tail"],
    },
    {
        "area": "Model Calibration",
        "description": "Input parameter values sourced from reference data",
        "manifest_fields": ["case.whitelist_entry.parameters", "case.gold_standard"],
    },
    {
        "area": "Validation Comparison",
        "description": "Computed vs. reference quantity of interest with tolerance",
        "manifest_fields": ["measurement.key_quantities", "case.gold_standard.observables"],
    },
    {
        "area": "Credibility Evidence",
        "description": "Pass/fail verdict traceable to input and output artifacts",
        "manifest_fields": ["measurement.comparator_verdict", "measurement.audit_concerns"],
    },
    {
        "area": "Uncertainty Quantification",
        "description": "Tolerance band applied to reference values",
        "manifest_fields": ["case.gold_standard.observables", "case.whitelist_entry.gold_standard.tolerance"],
    },
    {
        "area": "Decision Trail",
        "description": "Methodology decisions linked to this case (DEC-V61-* records)",
        "manifest_fields": ["decision_trail"],
    },
    {
        "area": "Provenance Pinning",
        "description": "Git commit SHAs binding manifest content to repo state",
        "manifest_fields": ["git.repo_commit_sha", "git.whitelist_commit_sha", "git.gold_standard_commit_sha"],
    },
]


# ---------------------------------------------------------------------------
# Build endpoint
# ---------------------------------------------------------------------------

@router.post(
    "/cases/{case_id}/runs/{run_id}/audit-package/build",
    response_model=AuditPackageBuildResponse,
)
def build_audit_package(case_id: str, run_id: str) -> AuditPackageBuildResponse:
    """Build a signed audit package bundle for (case_id, run_id).

    Produces manifest.json + bundle.zip + bundle.html + bundle.pdf
    (best-effort) + bundle.sig, all staged under a per-request directory.
    Returns URLs the UI can link to.

    Synchronous for v1 — build is typically < 5s. Async / progress
    streaming is a follow-up (PR-5e).
    """
    # Whitelist gate (Codex PR-5d HIGH #1 + M-PANELS Codex Round 3 P1):
    # refuse to sign a bundle for a case id that isn't in
    # knowledge/whitelist.yaml. A signed "audit package" referencing an
    # imported draft would be misleading to regulatory reviewers — no gold
    # reference, no validation contract, no provenance. Use is_whitelisted()
    # explicitly here: load_case_detail() now also matches imported drafts,
    # so its None-check is no longer a whitelist-only gate.
    if not is_whitelisted(case_id):
        raise HTTPException(
            status_code=404,
            detail=f"unknown case_id: {case_id!r} (not in knowledge/whitelist.yaml)",
        )

    # Load HMAC secret. Missing → 500 with actionable error.
    try:
        hmac_key = get_hmac_secret_from_env()
    except HmacSecretMissing as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Stable build_fingerprint (DEC-V61-019 L3 rename of generated_at):
    # derive from inputs so two identical POSTs produce byte-identical ZIPs
    # and HMAC signatures. The repo's git SHAs in the manifest still pin
    # repo state, so the bundle still differs when the repo changes — but
    # not when only wall-clock time changes. This preserves the byte-
    # reproducibility contract (docs/ui_roadmap.md:220-223,
    # docs/ui_design.md:376-378). Previously this field was named
    # `generated_at`, misleading reviewers who reasonably expected a
    # wall-clock timestamp but got an opaque 16-hex token.
    build_fingerprint = hashlib.sha256(
        f"{case_id}|{run_id}".encode("utf-8")
    ).hexdigest()[:16]

    # Wire audit-real-run fixture data into the manifest when available.
    # Phase 5a: when run_id identifies an audit_real_run measurement (captured
    # by scripts/phase5_audit_run.py), pull its measurement + verdict +
    # audit_concerns into the manifest so the signed bundle reflects the
    # actual solver output rather than a skeleton.
    run_doc = _load_run_measurement(case_id, run_id) or {}
    measurement_doc = run_doc.get("measurement") or None
    audit_concerns_doc = run_doc.get("audit_concerns") or None
    comparator_verdict_doc: str | None = None
    if measurement_doc is not None:
        comparator_verdict_doc = (
            "PASS" if measurement_doc.get("comparator_passed") else "FAIL"
        )

    manifest = build_manifest(
        case_id=case_id,
        run_id=run_id,
        build_fingerprint=build_fingerprint,
        measurement=measurement_doc,
        comparator_verdict=comparator_verdict_doc,
        audit_concerns=audit_concerns_doc,
    )

    # Stage.
    bundle_id = uuid.uuid4().hex
    bundle_dir = _STAGING_ROOT / bundle_id
    bundle_dir.mkdir(parents=True, exist_ok=True)

    zip_path = bundle_dir / "bundle.zip"
    html_path = bundle_dir / "bundle.html"
    pdf_path = bundle_dir / "bundle.pdf"
    sig_path = bundle_dir / "bundle.sig"
    manifest_path = bundle_dir / "manifest.json"

    # Serialize zip + HTML (mandatory).
    serialize_zip(manifest, zip_path)
    html_path.write_text(render_html(manifest), encoding="utf-8")

    # Persist a standalone manifest.json (the zip also has it; this is
    # a convenience for reviewers who just want the JSON).
    import json as _json
    manifest_path.write_text(
        _json.dumps(manifest, sort_keys=True, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    # Serialize PDF (optional — depends on weasyprint native libs).
    pdf_available = False
    pdf_error: str | None = None
    if is_pdf_backend_available():
        try:
            serialize_pdf(manifest, pdf_path)
            pdf_available = True
        except PdfBackendUnavailable as e:
            pdf_error = str(e)
    else:
        pdf_error = (
            "weasyprint native libs unavailable on this host. "
            "See src/audit_package/serialize.py for install instructions."
        )

    # Sign the zip bytes + manifest.
    zip_bytes = zip_path.read_bytes()
    signature = sign(manifest, zip_bytes, hmac_key)
    write_sidecar(signature, sig_path)

    # Build download URLs (relative to API root — frontend prepends origin).
    base = f"/api/audit-packages/{bundle_id}"
    downloads = AuditPackageDownloadUrls(
        manifest_json=f"{base}/manifest.json",
        bundle_zip=f"{base}/bundle.zip",
        bundle_html=f"{base}/bundle.html",
        bundle_pdf=f"{base}/bundle.pdf" if pdf_available else None,
        bundle_sig=f"{base}/bundle.sig",
    )

    return AuditPackageBuildResponse(
        bundle_id=bundle_id,
        manifest_id=manifest["manifest_id"],
        case_id=case_id,
        run_id=run_id,
        build_fingerprint=manifest["build_fingerprint"],
        git_repo_commit_sha=manifest["git"].get("repo_commit_sha"),
        comparator_verdict=manifest["measurement"].get("comparator_verdict"),
        pdf_available=pdf_available,
        pdf_error=pdf_error,
        downloads=downloads,
        evidence_summary=[
            AuditPackageEvidenceItem(**item) for item in _EVIDENCE_SUMMARY
        ],
        signature_hex=signature,
    )


# ---------------------------------------------------------------------------
# Download endpoints
# ---------------------------------------------------------------------------

_BUNDLE_ID_RE = __import__("re").compile(r"^[0-9a-f]{32}$")


def _resolve_bundle_file(bundle_id: str, filename: str) -> Path:
    """Validate bundle_id shape + resolve file path. Raises HTTP 404 on miss."""
    if not _BUNDLE_ID_RE.match(bundle_id):
        raise HTTPException(status_code=404, detail="bundle not found")
    candidate = _STAGING_ROOT / bundle_id / filename
    # Defense against traversal: resolve and verify it stays under staging root.
    try:
        resolved = candidate.resolve()
        resolved.relative_to(_STAGING_ROOT.resolve())
    except (ValueError, OSError):
        raise HTTPException(status_code=404, detail="bundle not found")
    if not resolved.is_file():
        raise HTTPException(status_code=404, detail="bundle not found")
    return resolved


@router.get("/audit-packages/{bundle_id}/manifest.json")
def download_manifest(bundle_id: str) -> FileResponse:
    return FileResponse(
        _resolve_bundle_file(bundle_id, "manifest.json"),
        media_type="application/json",
        filename="manifest.json",
    )


@router.get("/audit-packages/{bundle_id}/bundle.zip")
def download_zip(bundle_id: str) -> FileResponse:
    return FileResponse(
        _resolve_bundle_file(bundle_id, "bundle.zip"),
        media_type="application/zip",
        filename=f"cfd-audit-{bundle_id[:8]}.zip",
    )


@router.get("/audit-packages/{bundle_id}/bundle.html")
def download_html(bundle_id: str) -> FileResponse:
    return FileResponse(
        _resolve_bundle_file(bundle_id, "bundle.html"),
        media_type="text/html; charset=utf-8",
        filename=f"cfd-audit-{bundle_id[:8]}.html",
    )


@router.get("/audit-packages/{bundle_id}/bundle.pdf")
def download_pdf(bundle_id: str) -> FileResponse:
    return FileResponse(
        _resolve_bundle_file(bundle_id, "bundle.pdf"),
        media_type="application/pdf",
        filename=f"cfd-audit-{bundle_id[:8]}.pdf",
    )


@router.get("/audit-packages/{bundle_id}/bundle.sig")
def download_sig(bundle_id: str) -> FileResponse:
    return FileResponse(
        _resolve_bundle_file(bundle_id, "bundle.sig"),
        media_type="text/plain; charset=utf-8",
        filename=f"cfd-audit-{bundle_id[:8]}.sig",
    )
