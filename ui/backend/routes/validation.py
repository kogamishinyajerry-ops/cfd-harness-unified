"""Validation Report route — Phase 0 Screen 4 backend + multi-run extension."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ui.backend.schemas.validation import RunDescriptor, ValidationReport
from ui.backend.services.validation_report import (
    build_validation_report,
    list_runs,
    load_case_detail,
)

router = APIRouter()


@router.get("/validation-report/{case_id}", response_model=ValidationReport)
def get_validation_report(
    case_id: str,
    run_id: str | None = Query(
        None,
        description=(
            "Optional curated run identifier. When omitted, the backend "
            "prefers the first 'reference' run (so default view shows a "
            "PASS narrative where curated); falls back to any run; then "
            "to the legacy {case_id}_measurement.yaml fixture."
        ),
    ),
) -> ValidationReport:
    """Assemble the Screen 4 payload for a single case.

    Reads (no writes):
        - knowledge/whitelist.yaml
        - knowledge/gold_standards/{case_id}.yaml
        - a measurement source (in order):
            * ui/backend/tests/fixtures/runs/{case_id}/{run_id}_measurement.yaml
            * ui/backend/tests/fixtures/{case_id}_measurement.yaml  (legacy)
    """

    report = build_validation_report(case_id, run_id=run_id)
    if report is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Could not build validation report for case_id='{case_id}'"
                + (f", run_id='{run_id}'" if run_id else "")
                + ". Verify the case is in the whitelist and the run fixture exists."
            ),
        )
    return report


@router.get("/cases/{case_id}/runs", response_model=list[RunDescriptor])
def get_case_runs(case_id: str) -> list[RunDescriptor]:
    """List curated + legacy runs for a case. Empty list when no
    fixture exists (the UI should render 'no runs yet' rather than 404
    so students still see the Story tab)."""
    if load_case_detail(case_id) is None:
        raise HTTPException(
            status_code=404, detail=f"case_id not found: {case_id}"
        )
    return list_runs(case_id)
