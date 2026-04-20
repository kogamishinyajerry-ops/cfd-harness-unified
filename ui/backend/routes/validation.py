"""Validation Report route — Phase 0 Screen 4 backend."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ui.backend.schemas.validation import ValidationReport
from ui.backend.services.validation_report import build_validation_report

router = APIRouter()


@router.get("/validation-report/{case_id}", response_model=ValidationReport)
def get_validation_report(case_id: str) -> ValidationReport:
    """Assemble the Screen 4 payload for a single case.

    Reads (no writes):
        - knowledge/whitelist.yaml
        - knowledge/gold_standards/{case_id}.yaml
        - a measurement source:
            * latest reports/**/slice_metrics.yaml for the case, or
            * ui/backend/tests/fixtures/{case_id}_measurement.yaml
              (Phase 0 fallback fixture when slice_metrics is absent)

    Returns a ValidationReport with reference / measured / tolerance /
    pass-fail / audit-concern / preconditions / decisions-trail sections.
    """

    report = build_validation_report(case_id)
    if report is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Could not build validation report for case_id '{case_id}'. "
                "Either the case is not in the whitelist or no measurement "
                "fixture / slice_metrics file is available yet."
            ),
        )
    return report
