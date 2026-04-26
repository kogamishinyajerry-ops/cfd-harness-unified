"""Run history routes · M3 · Workbench Closed-Loop main-line.

    GET /api/cases/{case_id}/run-history              → table rows (newest-first)
    GET /api/cases/{case_id}/run-history/{run_id}     → full detail

Path is ``/run-history`` (not ``/runs``) so it can't collide with the Learn-
track curated-taxonomy endpoint ``GET /api/cases/{case_id}/runs`` in
``validation.py``, which returns a different shape (``list[RunDescriptor]``
of reference_pass / audit_real_run / etc.). M3 is the dynamic per-run
audit trail; Learn ``/runs`` is the static pedagogy taxonomy. Two
different surfaces, two different URLs.

The ``case_id`` and ``run_id`` path params reuse the same alphabet validation
``case_drafts._draft_path`` enforces upstream — alphanumeric / underscore /
hyphen / colon / period / 'T' / 'Z'. The route returns a clean 400 on unsafe
input rather than letting the service layer ValueError bubble.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ui.backend.schemas.run_history import RunDetail, RunHistoryListResponse
from ui.backend.services.run_history import get_run_detail, list_runs


router = APIRouter()


@router.get("/cases/{case_id}/run-history", response_model=RunHistoryListResponse)
def list_runs_route(case_id: str) -> RunHistoryListResponse:
    try:
        runs = list_runs(case_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RunHistoryListResponse(case_id=case_id, runs=runs)


@router.get(
    "/cases/{case_id}/run-history/{run_id}",
    response_model=RunDetail,
)
def get_run_detail_route(case_id: str, run_id: str) -> RunDetail:
    try:
        return get_run_detail(case_id, run_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=f"run not found: case_id={case_id!r} run_id={run_id!r}",
        ) from exc
