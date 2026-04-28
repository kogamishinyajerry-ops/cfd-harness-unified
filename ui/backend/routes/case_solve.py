"""Phase-1A LDC solve routes (DEC-V61-097).

Three POST/GET endpoints:

* ``POST /api/import/{case_id}/setup-bc`` — split polyMesh + author dicts.
* ``POST /api/import/{case_id}/solve`` — run icoFoam in cfd-openfoam.
* ``GET  /api/cases/{case_id}/results-summary`` — parse final U field.

These wire the missing back half of the M-PANELS demo flow that
DEC-V61-096 deferred to M-AI-COPILOT / M7-redefined / M-VIZ.results.
The deferral is now lifted (per user direction 2026-04-29: full demo
end-to-end on the LDC fixture).

Scope: LDC only. The cylinder + naca0012 demos require an external-
flow pipeline (blockMesh + sHM) that is NOT shipped here; their
demo buttons remain "import + mesh only" pending Phase-2.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException

from ui.backend.schemas.case_solve import (
    ResultsRejection,
    ResultsSummaryWire,
    SetupBcRejection,
    SetupBcSummary,
    SolveRejection,
    SolveSummary,
)
from ui.backend.services.case_drafts import is_safe_case_id
from ui.backend.services.case_scaffold import IMPORTED_DIR
from ui.backend.services.case_solve import (
    BCSetupError,
    ResultsExtractError,
    SolverRunError,
    extract_results_summary,
    run_icofoam,
    setup_ldc_bc,
)


router = APIRouter()


def _resolve_case_dir(case_id: str) -> Path:
    if not is_safe_case_id(case_id):
        raise HTTPException(
            status_code=400,
            detail=SetupBcRejection(
                failing_check="bad_case_id",
                detail=f"unsafe case_id: {case_id!r}",
            ).model_dump(),
        )
    case_dir = IMPORTED_DIR / case_id
    if not case_dir.is_dir():
        raise HTTPException(
            status_code=404,
            detail=SetupBcRejection(
                failing_check="case_not_found",
                detail=f"imported case {case_id!r} not found",
            ).model_dump(),
        )
    return case_dir


@router.post(
    "/import/{case_id}/setup-bc",
    response_model=SetupBcSummary,
    tags=["case-solve"],
)
def setup_bc(case_id: str) -> SetupBcSummary:
    """Split gmshToFoam's single patch into ``lid`` + ``fixedWalls`` and
    author OpenFOAM dicts for icoFoam Re=100. Idempotent.
    """
    case_dir = _resolve_case_dir(case_id)
    try:
        result = setup_ldc_bc(case_dir, case_id=case_id)
    except BCSetupError as exc:
        msg = str(exc)
        # Distinguish user-geometry rejection from backend faults.
        if "axis-aligned cube" in msg or "no boundary faces match" in msg:
            raise HTTPException(
                status_code=400,
                detail=SetupBcRejection(
                    failing_check="not_an_ldc_cube",
                    detail=msg,
                ).model_dump(),
            ) from exc
        if "no constant/polyMesh" in msg or "boundary file" in msg:
            raise HTTPException(
                status_code=409,
                detail=SetupBcRejection(
                    failing_check="mesh_missing",
                    detail=msg,
                ).model_dump(),
            ) from exc
        raise HTTPException(
            status_code=500,
            detail=SetupBcRejection(
                failing_check="write_failed",
                detail=msg,
            ).model_dump(),
        ) from exc

    return SetupBcSummary(
        case_id=result.case_id,
        n_lid_faces=result.n_lid_faces,
        n_wall_faces=result.n_wall_faces,
        lid_velocity=result.lid_velocity,
        nu=result.nu,
        reynolds=result.reynolds,
        written_files=list(result.written_files),
    )


@router.post(
    "/import/{case_id}/solve",
    response_model=SolveSummary,
    tags=["case-solve"],
)
def solve(case_id: str) -> SolveSummary:
    """Run icoFoam inside the cfd-openfoam container. Blocks until the
    solver finishes (≈60s wall-time for the default LDC config).
    """
    case_dir = _resolve_case_dir(case_id)
    try:
        result = run_icofoam(case_host_dir=case_dir)
    except SolverRunError as exc:
        msg = str(exc)
        if "no system/controlDict" in msg:
            raise HTTPException(
                status_code=409,
                detail=SolveRejection(
                    failing_check="bc_not_setup",
                    detail=msg,
                ).model_dump(),
            ) from exc
        if "container" in msg.lower() and (
            "not running" in msg.lower() or "not found" in msg.lower()
        ):
            raise HTTPException(
                status_code=503,
                detail=SolveRejection(
                    failing_check="container_unavailable",
                    detail=msg,
                ).model_dump(),
            ) from exc
        if "exited with code" in msg:
            raise HTTPException(
                status_code=502,
                detail=SolveRejection(
                    failing_check="solver_diverged",
                    detail=msg,
                ).model_dump(),
            ) from exc
        raise HTTPException(
            status_code=502,
            detail=SolveRejection(
                failing_check="post_stage_failed",
                detail=msg,
            ).model_dump(),
        ) from exc

    return SolveSummary(
        case_id=result.case_id,
        end_time_reached=result.end_time_reached,
        last_initial_residual_p=result.last_initial_residual_p,
        last_initial_residual_U=result.last_initial_residual_U,
        last_continuity_error=result.last_continuity_error,
        n_time_steps_written=result.n_time_steps_written,
        time_directories=list(result.time_directories),
        wall_time_s=result.wall_time_s,
        converged=result.converged,
    )


@router.get(
    "/cases/{case_id}/results-summary",
    response_model=ResultsSummaryWire,
    tags=["case-solve"],
)
def results_summary(case_id: str) -> ResultsSummaryWire:
    """Parse the final U field, return summary statistics. Read-only:
    re-running this is cheap and idempotent.
    """
    case_dir = _resolve_case_dir(case_id)
    try:
        summary = extract_results_summary(case_dir, case_id=case_id)
    except ResultsExtractError as exc:
        msg = str(exc)
        if "icoFoam hasn't run" in msg:
            raise HTTPException(
                status_code=409,
                detail=ResultsRejection(
                    failing_check="solve_not_run",
                    detail=msg,
                ).model_dump(),
            ) from exc
        raise HTTPException(
            status_code=500,
            detail=ResultsRejection(
                failing_check="results_malformed",
                detail=msg,
            ).model_dump(),
        ) from exc

    return ResultsSummaryWire(
        case_id=summary.case_id,
        final_time=summary.final_time,
        cell_count=summary.cell_count,
        u_magnitude_min=summary.u_magnitude_min,
        u_magnitude_max=summary.u_magnitude_max,
        u_magnitude_mean=summary.u_magnitude_mean,
        u_x_mean=summary.u_x_mean,
        u_x_min=summary.u_x_min,
        u_x_max=summary.u_x_max,
        is_recirculating=summary.is_recirculating,
    )
