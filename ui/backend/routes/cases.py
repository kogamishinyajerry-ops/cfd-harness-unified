"""Case index routes — read-only view of knowledge/whitelist.yaml."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ui.backend.schemas.validation import CaseIndexEntry, CaseDetail
from ui.backend.services.case_completeness import (
    CaseCompletenessReport,
    CaseNotFoundError,
    analyze_case_completeness,
)
from ui.backend.services.validation_report import (
    list_cases,
    load_case_detail,
)

router = APIRouter()


@router.get("/cases", response_model=list[CaseIndexEntry])
def get_cases() -> list[CaseIndexEntry]:
    """Return the 10-case whitelist as an index list.

    Phase 0 gate criterion: length == 10, IDs include the canonical
    benchmarks (lid_driven_cavity, differential_heated_cavity, …).
    """

    return list_cases()


@router.get("/cases/{case_id}", response_model=CaseDetail)
def get_case(case_id: str) -> CaseDetail:
    """Return a single whitelist case + its gold-standard contract."""

    detail = load_case_detail(case_id)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"case_id not found: {case_id}")
    return detail


@router.get(
    "/cases/{case_id}/completeness",
    response_model=CaseCompletenessReport,
)
def get_case_completeness(case_id: str) -> CaseCompletenessReport:
    """DEC-V61-116: governance-aware completeness diff for a case.

    Returns the field-level "still needed" list backing the right-rail
    "距离入库标准还差 N 项" card. 200 with a valid (possibly empty)
    report when the case_id resolves; 404 when it doesn't. The endpoint
    is intentionally tolerant of incomplete data within a case — the
    WHOLE POINT is to surface gaps without crashing.
    """

    try:
        return analyze_case_completeness(case_id)
    except CaseNotFoundError as exc:
        raise HTTPException(
            status_code=404, detail=f"case_id not found: {case_id}"
        ) from exc
