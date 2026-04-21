"""Phase 7c — CFD vs Gold comparison report route.

GET  /api/cases/{case_id}/runs/{run_label}/comparison-report         → HTML
GET  /api/cases/{case_id}/runs/{run_label}/comparison-report.pdf     → PDF
POST /api/cases/{case_id}/runs/{run_label}/comparison-report/build   → rebuild PDF + return manifest

Uses FileResponse pattern per Phase 7a user ratification #1 (no StaticFiles).
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from ui.backend.services.comparison_report import (
    ReportError,
    build_report_context,
    render_report_html,
    render_report_pdf,
)
from ui.backend.services.run_ids import _validate_segment

router = APIRouter()


def _validate_ids(case_id: str, run_label: str) -> None:
    """Reuse Phase 7a traversal defense on case_id + run_label segments."""
    _validate_segment(case_id, "case_id")
    _validate_segment(run_label, "run_label")


@router.get(
    "/cases/{case_id}/runs/{run_label}/comparison-report",
    response_class=HTMLResponse,
    tags=["comparison-report"],
)
def get_comparison_report_html(case_id: str, run_label: str) -> HTMLResponse:
    """Return rendered HTML report (suitable for iframe embedding)."""
    _validate_ids(case_id, run_label)
    try:
        html = render_report_html(case_id, run_label)
    except ReportError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return HTMLResponse(html)


@router.get(
    "/cases/{case_id}/runs/{run_label}/comparison-report/context",
    tags=["comparison-report"],
)
def get_comparison_report_context(case_id: str, run_label: str) -> JSONResponse:
    """Return the raw template context as JSON (for frontend custom rendering
    if it wants to skip the server-rendered HTML and compose its own)."""
    _validate_ids(case_id, run_label)
    try:
        ctx = build_report_context(case_id, run_label)
    except ReportError as e:
        raise HTTPException(status_code=404, detail=str(e))
    # Strip non-JSON-serializable entries (e.g., numpy arrays).
    # per_point_dev_pct is already list(); metrics keys are all primitives.
    return JSONResponse(ctx)


@router.get(
    "/cases/{case_id}/runs/{run_label}/comparison-report.pdf",
    tags=["comparison-report"],
)
def get_comparison_report_pdf(case_id: str, run_label: str) -> FileResponse:
    """Render (or re-render) PDF and stream it back."""
    _validate_ids(case_id, run_label)
    try:
        path = render_report_pdf(case_id, run_label)
    except ReportError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except (ImportError, OSError) as e:
        # ImportError: weasyprint package missing.
        # OSError: native dep (libgobject / libcairo / libpango) failed to load
        # on this host — typically macOS missing DYLD_FALLBACK_LIBRARY_PATH.
        raise HTTPException(
            status_code=503,
            detail=(
                "WeasyPrint unavailable on this server. "
                "Ensure DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib is set and "
                "brew install pango cairo gdk-pixbuf has been run. "
                f"Underlying: {type(e).__name__}: {str(e)[:120]}"
            ),
        )
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=f"{case_id}__{run_label}__comparison_report.pdf",
    )


@router.post(
    "/cases/{case_id}/runs/{run_label}/comparison-report/build",
    tags=["comparison-report"],
)
def build_comparison_report(case_id: str, run_label: str) -> JSONResponse:
    """Force-rebuild HTML + PDF, return manifest."""
    _validate_ids(case_id, run_label)
    try:
        html = render_report_html(case_id, run_label)
        pdf_path = render_report_pdf(case_id, run_label)
    except ReportError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except (ImportError, OSError) as e:
        # Codex round 3 MED follow-up: this POST path had only ImportError;
        # native libgobject/libcairo/libpango load failures surface as OSError
        # on macOS when DYLD_FALLBACK_LIBRARY_PATH is missing.
        raise HTTPException(
            status_code=503,
            detail=(
                "WeasyPrint unavailable on this server. "
                "Ensure DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib is set and "
                "brew install pango cairo gdk-pixbuf has been run. "
                f"Underlying: {type(e).__name__}: {str(e)[:120]}"
            ),
        )
    return JSONResponse({
        "case_id": case_id,
        "run_label": run_label,
        "pdf_path": str(pdf_path),
        "html_bytes": len(html),
    })
