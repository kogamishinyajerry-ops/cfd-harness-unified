"""POST /api/import/{case_id}/mesh/prism-layers — DEC-V61-137 (N2.3).

Engineer-driven boundary-layer prism injection on top of the existing
polyMesh from the gmsh stage. Adds a NEW mutating route that must be
registered in V132 ``MUTATING_ROUTES`` + behavioral contract test.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ui.backend.schemas.mesh_prism_layers import (
    MeshPrismLayersRequest,
    PrismFailingCheck,
    PrismLayersRejection,
    PrismLayersSuccessResponse,
    PrismLayersSummary,
)
from ui.backend.services.meshing_snappy.pipeline import (
    PrismLayersPipelineError,
    PrismLayersResult,
    apply_prism_layers,
)


router = APIRouter()


# Map pipeline failing_check enum → HTTP status. case_not_found is
# 404; polyMesh_not_ready / patch_not_found / snappy_diverged /
# snappy_addlayers_did_not_converge are all 422 (engineer-supplied
# config / state cannot run); snappy_container_failed is 502.
_STATUS_FOR_FAILING_CHECK: dict[PrismFailingCheck, int] = {
    "case_not_found": 404,
    "polyMesh_not_ready": 422,
    "patch_not_found": 422,
    "snappy_diverged": 422,
    "snappy_addlayers_did_not_converge": 422,
    "snappy_container_failed": 502,
}


def _result_to_response(result: PrismLayersResult) -> PrismLayersSuccessResponse:
    return PrismLayersSuccessResponse(
        case_id=result.case_id,
        prism_summary=PrismLayersSummary(
            cell_count=0,  # filled at the route layer if needed; v0
                          # leaves the raw polyMesh introspection to
                          # the V126/V127 mesh-quality endpoint, which
                          # the frontend re-fetches after this run.
            face_count=0,
            layers_added=result.layers_added,
            coverage_fraction=result.coverage_fraction,
            polyMesh_path=str(result.polyMesh_path),
            log_path=str(result.log_path),
            generation_time_s=result.generation_time_s,
        ),
    )


@router.post(
    "/import/{case_id}/mesh/prism-layers",
    response_model=PrismLayersSuccessResponse,
)
def mesh_prism_layers_route(
    case_id: str,
    request: MeshPrismLayersRequest,
) -> PrismLayersSuccessResponse:
    """Apply snappyHexMesh addLayers to the existing polyMesh.

    Synchronous on the FastAPI threadpool — snappyHexMesh runs
    O(seconds-minutes), same threadpool discipline as the gmsh
    route (V096 R5 P3 reference).
    """
    try:
        result = apply_prism_layers(
            case_id,
            patches=list(request.patches),
        )
    except PrismLayersPipelineError as exc:
        rejection = PrismLayersRejection(
            reason=str(exc),
            failing_check=exc.failing_check,
        )
        raise HTTPException(
            status_code=_STATUS_FOR_FAILING_CHECK.get(exc.failing_check, 400),
            detail=rejection.model_dump(),
        ) from exc

    return _result_to_response(result)
