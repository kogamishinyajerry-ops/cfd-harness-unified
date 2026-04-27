"""POST /api/import/{case_id}/mesh — M6.0 gmsh meshing route.

Consumes the M5.0 imported case scaffold (triSurface + STL on disk),
runs gmsh + gmshToFoam, and writes ``constant/polyMesh/`` so the M6.1
trust-core executor patch can skip ``blockMesh``.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ui.backend.schemas.mesh_imported import (
    MeshRejection,
    MeshRequest,
    MeshSuccessResponse,
    MeshSummary,
)
from ui.backend.services.meshing_gmsh import MeshResult, mesh_imported_case
from ui.backend.services.meshing_gmsh.pipeline import (
    FailingCheck,
    MeshPipelineError,
)


router = APIRouter()


# Map pipeline failing_check enum → HTTP status. case_not_found is the
# only 404; the rest are 4xx user errors (geometry quality / sizing).
_STATUS_FOR_FAILING_CHECK: dict[FailingCheck, int] = {
    "case_not_found": 404,
    "source_not_imported": 400,
    "gmsh_diverged": 422,
    "cell_cap_exceeded": 422,
    "gmshToFoam_failed": 502,  # downstream container-side failure
}


def _result_to_response(result: MeshResult) -> MeshSuccessResponse:
    return MeshSuccessResponse(
        case_id=result.case_id,
        mesh_summary=MeshSummary(
            cell_count=result.cell_count,
            face_count=result.face_count,
            point_count=result.point_count,
            mesh_mode_used=result.mesh_mode,
            polyMesh_path=str(result.polyMesh_path),
            msh_path=str(result.msh_path),
            generation_time_s=result.generation_time_s,
            warning=result.warning,
        ),
    )


@router.post(
    "/import/{case_id}/mesh",
    response_model=MeshSuccessResponse,
)
def mesh_imported_route(
    case_id: str,
    request: MeshRequest,
) -> MeshSuccessResponse:
    # Intentionally synchronous: gmsh + gmshToFoam can take 30-300s on
    # real geometry. An async handler would block the FastAPI event
    # loop for that whole window and starve unrelated routes
    # (/api/health, SSE streams). Synchronous routes run in FastAPI's
    # default threadpool, so a long mesh blocks one worker thread but
    # leaves the event loop free.
    try:
        result = mesh_imported_case(case_id, mesh_mode=request.mesh_mode)
    except MeshPipelineError as exc:
        rejection = MeshRejection(
            reason=str(exc),
            failing_check=exc.failing_check,
        )
        raise HTTPException(
            status_code=_STATUS_FOR_FAILING_CHECK.get(exc.failing_check, 400),
            detail=rejection.model_dump(),
        ) from exc

    return _result_to_response(result)
