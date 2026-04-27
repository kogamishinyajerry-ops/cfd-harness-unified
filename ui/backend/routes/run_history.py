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

from fastapi import APIRouter, HTTPException, Query

from ui.backend.schemas.run_history import (
    RecentRunsResponse,
    RunDetail,
    RunHistoryListResponse,
)
from ui.backend.services.run_compare import compare_runs
from ui.backend.services.run_history import (
    get_run_detail,
    list_recent_runs_across_cases,
    list_runs,
)
from ui.backend.services.run_ids import _validate_segment


router = APIRouter()


@router.get("/run-history/recent", response_model=RecentRunsResponse)
def recent_runs_route(
    limit: int = Query(50, ge=1, le=500),
) -> RecentRunsResponse:
    """Cross-case newest-first feed for the /workbench/today dashboard.

    Walks one level under ``reports/`` for any case bucket whose name
    passes the same alphabet ``case_drafts._draft_path`` enforces. Caps
    output at ``limit`` (default 50, max 500) so a workspace with
    thousands of historical runs doesn't pay the full sort cost on
    every poll.
    """
    runs = list_recent_runs_across_cases(limit=limit)
    return RecentRunsResponse(runs=runs, total=len(runs))


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


@router.get(
    "/cases/{case_id}/run-history/{run_a_id}/compare/{run_b_id}",
)
def compare_runs_route(
    case_id: str, run_a_id: str, run_b_id: str
) -> dict:
    """Run-vs-run diff (ROADMAP §60-day item).

    Returns task_spec_diff + scalar_diffs + array_diffs + residual_diffs
    + verdict_diff. Distinct from /comparison-report (run-vs-gold).
    Response is a free-form dict (not RunDetail) because the diff shape
    is heterogeneous: scalar/array/skipped buckets each carry different
    fields. Frontend reads keys directly.

    Per Codex r1 P1.1: explicitly validate all three path segments via
    run_ids._validate_segment to reject `..` / percent-encoded traversal
    with HTTP 400, instead of letting it 404 ambiguously through
    get_run_detail's filesystem check.
    """
    _validate_segment(case_id, "case_id")
    _validate_segment(run_a_id, "run_a_id")
    _validate_segment(run_b_id, "run_b_id")
    try:
        return compare_runs(case_id, run_a_id, run_b_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=f"run not found: case_id={case_id!r} a={run_a_id!r} b={run_b_id!r} ({exc})",
        ) from exc
