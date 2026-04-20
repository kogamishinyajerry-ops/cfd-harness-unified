"""Case index routes — read-only view of knowledge/whitelist.yaml."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ui.backend.schemas.validation import CaseIndexEntry, CaseDetail
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
