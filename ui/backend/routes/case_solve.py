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

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse

from ui.backend.schemas.ai_action import AIActionEnvelope
from ui.backend.schemas.case_solve import (
    ResultsRejection,
    ResultsSummaryWire,
    SetupBcRejection,
    SetupBcSummary,
    SolveRejection,
    SolveSummary,
)
from ui.backend.services.ai_actions import (
    AIActionError,
    setup_bc_with_annotations,
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
    stream_icofoam,
)
from ui.backend.services.case_solve.bc_setup_from_stl_patches import (
    StlPatchBCError,
    setup_bc_from_stl_patches,
)
from ui.backend.services.case_solve.solver_streamer import (
    SolveAlreadyRunning,
    _prepare_stream_icofoam,
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


def _setup_bc_failure_to_http(exc: BCSetupError) -> HTTPException:
    """Map a ``BCSetupError`` to the appropriate HTTPException, shared
    by the legacy ``setup_bc`` route and the envelope-mode wrapper.
    """
    msg = str(exc)
    if "axis-aligned cube" in msg or "no boundary faces match" in msg:
        return HTTPException(
            status_code=400,
            detail=SetupBcRejection(
                failing_check="not_an_ldc_cube", detail=msg
            ).model_dump(),
        )
    # DEC-V61-101: channel executor user-actionable failures. Stale
    # pins after classifier verification (mesh regen mid-flight) and
    # missing pin matches both come back as the engineer's problem to
    # solve by re-picking, so they're 422 (semantic — request shape
    # OK, content rejected) rather than 500 (server-side fault).
    if (
        "stale pins after classifier verification" in msg
        or "no boundary face matched any" in msg
        or "all boundary faces classified as inlet/outlet" in msg
        or "classifier contract violated" in msg
    ):
        return HTTPException(
            status_code=422,
            detail=SetupBcRejection(
                failing_check="channel_pin_mismatch", detail=msg
            ).model_dump(),
        )
    if "no constant/polyMesh" in msg or "boundary file" in msg:
        return HTTPException(
            status_code=409,
            detail=SetupBcRejection(
                failing_check="mesh_missing", detail=msg
            ).model_dump(),
        )
    return HTTPException(
        status_code=500,
        detail=SetupBcRejection(
            failing_check="write_failed", detail=msg
        ).model_dump(),
    )


@router.post(
    "/import/{case_id}/setup-bc",
    tags=["case-solve"],
)
def setup_bc(
    case_id: str,
    envelope: int = Query(
        default=0,
        ge=0,
        le=1,
        description=(
            "When 1, return AIActionEnvelope (M-AI-COPILOT collab "
            "shape) instead of legacy SetupBcSummary. Backward-compat: "
            "default 0 preserves V61-097 callers."
        ),
    ),
    force_uncertain: int = Query(
        default=0,
        ge=0,
        le=1,
        description=(
            "(envelope=1 only) When 1, force confidence='uncertain' "
            "with one mock dialog question. Tier-A LDC dogfood path "
            "for the dialog flow without needing real arbitrary-STL "
            "AI ambiguity."
        ),
    ),
    force_blocked: int = Query(
        default=0,
        ge=0,
        le=1,
        description=(
            "(envelope=1 only) When 1, force confidence='blocked' "
            "with one mock dialog question. Mutually exclusive with "
            "force_uncertain; if both are passed, force_blocked wins."
        ),
    ),
    from_stl_patches: int = Query(
        default=0,
        ge=0,
        le=1,
        description=(
            "DEC-V61-103: when 1, drive BC dict authoring from named "
            "polyMesh patches (multi-patch CAD imports) instead of "
            "the LDC lid/fixedWalls split. Mutually exclusive with "
            "envelope; if both are passed, from_stl_patches wins."
        ),
    ),
):
    """Author OpenFOAM dicts for the case in one of three modes.

    * Default (V61-097): split single patch into ``lid``/``fixedWalls``
      and author icoFoam Re=100 — LDC demo path.
    * ``?envelope=1`` (V61-098): wrap legacy outcome with
      ``AIActionEnvelope`` for the M-AI-COPILOT dialog flow.
    * ``?from_stl_patches=1`` (V61-103): read named patches from
      ``constant/polyMesh/boundary`` (preserved through gmsh by
      DEC-V61-102's defect-2a fix), map each to a default BC class
      via the project table (inlet/outlet/walls/symmetry/...), author
      the 7 icoFoam dicts referencing the actual patch names. The
      engineer can then fine-tune any field via the V61-102 raw-dict
      editor without re-running setup-bc.

    All three modes are idempotent.
    """
    case_dir = _resolve_case_dir(case_id)

    if from_stl_patches:
        try:
            result = setup_bc_from_stl_patches(case_dir, case_id=case_id)
        except StlPatchBCError as exc:
            status = {
                "mesh_not_setup": 409,
                "no_named_patches": 409,
                "write_failed": 500,
                "case_lock_failed": 409,
            }.get(exc.failing_check, 400)
            raise HTTPException(
                status_code=status,
                detail=SetupBcRejection(
                    failing_check=exc.failing_check,
                    detail=str(exc),
                ).model_dump(),
            ) from exc
        return JSONResponse(
            content={
                "case_id": result.case_id,
                "patches": [
                    {"name": name, "bc_class": cls.value}
                    for name, cls in result.patches
                ],
                "inlet_speed": result.inlet_speed,
                "inlet_velocities": [
                    {"name": name, "U": list(u)}
                    for name, u in result.inlet_velocities
                ],
                "nu": result.nu,
                "delta_t": result.delta_t,
                "end_time": result.end_time,
                "written_files": list(result.written_files),
                "skipped_user_overrides": list(result.skipped_user_overrides),
                "warnings": list(result.warnings),
            },
            status_code=200,
        )

    if envelope:
        try:
            env = setup_bc_with_annotations(
                case_dir=case_dir,
                case_id=case_id,
                force_uncertain=bool(force_uncertain),
                force_blocked=bool(force_blocked),
            )
        except AIActionError as exc:
            # AIActionError wraps either a BCSetupError (LDC or channel
            # executor) or an AnnotationsIOError. Map BC failures to
            # the same HTTP shape as the legacy route; surface other
            # tags as 422 with the failing_check.
            #
            # Codex DEC-V61-101 R1 MED closure: setup_channel_bc_failed
            # was previously falling through to the 422 branch, losing
            # the BCSetupError → 4xx/5xx contract that the LDC path has.
            failing = getattr(exc, "failing_check", "ai_action_failed")
            if failing in ("setup_bc_failed", "setup_channel_bc_failed"):
                raise _setup_bc_failure_to_http(BCSetupError(str(exc))) from exc
            raise HTTPException(
                status_code=422,
                detail=SetupBcRejection(
                    failing_check=failing,
                    detail=str(exc),
                ).model_dump(),
            ) from exc
        return JSONResponse(
            content=env.model_dump(),
            status_code=200,
        )

    # Legacy V61-097 path.
    try:
        result = setup_ldc_bc(case_dir, case_id=case_id)
    except BCSetupError as exc:
        raise _setup_bc_failure_to_http(exc) from exc

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
    "/import/{case_id}/solve-stream",
    tags=["case-solve"],
)
def solve_stream(case_id: str) -> StreamingResponse:
    """Run icoFoam with **live** SSE streaming so the UI can update a
    residual chart in real time.

    Setup failures (case missing, bc not setup, container down) raise
    HTTPException BEFORE the first byte is yielded — those become
    HTTP 4xx/5xx with the same shape as the blocking ``/solve`` route.
    Failures DURING the run land as in-stream ``error`` events; the
    HTTP status stays 200 because the stream has already started.
    """
    case_dir = _resolve_case_dir(case_id)

    # Validate eagerly so we can return a real HTTP error code instead
    # of a 200-with-error-event. The streamer also checks these but
    # raising here gives the route a chance to attach the structured
    # SolveRejection contract.
    if not (case_dir / "system" / "controlDict").is_file():
        raise HTTPException(
            status_code=409,
            detail=SolveRejection(
                failing_check="bc_not_setup",
                detail=f"no system/controlDict at {case_dir}",
            ).model_dump(),
        )

    # Codex round-1 HIGH-1: preflight must run BEFORE we hand a
    # generator to StreamingResponse. ``_prepare_stream_icofoam`` is a
    # plain function (not a generator), so any SolverRunError raised
    # here surfaces as an HTTPException synchronously — instead of as
    # a 200 response with a torn iterator.
    try:
        prepared = _prepare_stream_icofoam(case_host_dir=case_dir)
    except SolveAlreadyRunning as exc:
        # HIGH-2: a prior run for this case is still active. Reject
        # with 409 so the client can wait + retry.
        raise HTTPException(
            status_code=409,
            detail=SolveRejection(
                failing_check="solve_already_running",
                detail=str(exc),
            ).model_dump(),
        ) from exc
    except SolverRunError as exc:
        msg = str(exc)
        if "container" in msg.lower() and (
            "not running" in msg.lower() or "not found" in msg.lower()
        ):
            status = 503
            failing = "container_unavailable"
        else:
            status = 502
            failing = "post_stage_failed"
        raise HTTPException(
            status_code=status,
            detail=SolveRejection(
                failing_check=failing,
                detail=msg,
            ).model_dump(),
        ) from exc

    return StreamingResponse(
        stream_icofoam(prepared=prepared),
        media_type="text/event-stream",
        headers={
            # SSE wants no buffering by intermediaries; declare
            # explicitly so reverse proxies (nginx etc) flush each
            # event instead of accumulating.
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
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
