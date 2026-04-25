"""Preflight route · Stage 4 GuardedRun MVP.

GET /api/cases/{case_id}/preflight

Aggregates 5 categories of preflight checks (physics / schema / mesh /
gold_standard / adapter) and returns a JSON payload sized for the
`<RunRail>` UI primitive. Idempotent and read-only.
"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ui.backend.services.preflight import build_preflight
from ui.backend.services.run_ids import _validate_segment

router = APIRouter()


@router.get(
    "/cases/{case_id}/preflight",
    tags=["preflight"],
)
def get_preflight(case_id: str) -> JSONResponse:
    _validate_segment(case_id, "case_id")
    summary = build_preflight(case_id)
    return JSONResponse(summary.model_dump(by_alias=True, exclude_none=True))
