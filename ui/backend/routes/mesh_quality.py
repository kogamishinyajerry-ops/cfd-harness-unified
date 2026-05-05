"""DEC-V61-122 · GET /api/cases/{case_id}/mesh-quality.

Surfaces the polyMesh-derived MeshQualityReport. Read-only,
idempotent, no side effects.

Status mapping:
  * 200 → MeshQualityReport JSON
  * 400 → bad case_id (path-traversal / unsafe segment)
  * 404 → case_dir missing OR polyMesh missing (case has not been
          meshed yet)
  * 500 → polyMesh files exist but parse failed; structured detail
          carries failing_check enum so operators don't see opaque
          tracebacks
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from ui.backend.services.case_drafts import is_safe_case_id
from ui.backend.services.case_scaffold import IMPORTED_DIR
from ui.backend.services.mesh_quality import (
    CheckMeshError,
    MeshQualityNotAvailableError,
    MeshQualityParseError,
    MeshQualityReport,
    analyze_mesh_quality,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/cases/{case_id}/mesh-quality",
    response_model=MeshQualityReport,
    tags=["mesh-quality"],
)
def get_mesh_quality(
    case_id: str,
    run_checkmesh: bool = False,
) -> MeshQualityReport:
    """Get mesh quality report for a case.

    DEC-V61-126: when ``run_checkmesh=true`` query param is set, the
    response augments the V122 fields with OpenFOAM checkMesh-derived
    metrics (skewness, non-orthogonality, aspect ratio). When the
    container is unavailable, those fields stay None and a warning
    is logged — the V122 fields populate as normal so the engineer
    still gets actionable information.

    Genuine checkMesh failures (parse_error, exit_nonzero, generic
    docker_sdk_error) surface as HTTP 502 with structured detail
    so the operator sees the failing_check enum without opaque
    tracebacks.
    """
    if not is_safe_case_id(case_id):
        raise HTTPException(
            status_code=400,
            detail={"failing_check": "bad_case_id", "case_id": case_id},
        )
    case_dir = IMPORTED_DIR / case_id
    if not case_dir.is_dir():
        raise HTTPException(
            status_code=404,
            detail={"failing_check": "case_not_found", "case_id": case_id},
        )
    try:
        return analyze_mesh_quality(case_dir, run_checkmesh=run_checkmesh)
    except MeshQualityNotAvailableError as exc:
        raise HTTPException(
            status_code=404,
            detail={
                "failing_check": "polymesh_not_ready",
                "case_id": case_id,
                "message": str(exc),
            },
        ) from exc
    except MeshQualityParseError as exc:
        logger.exception(
            "mesh-quality parse failed for case_id=%r failing_check=%s",
            case_id,
            exc.failing_check,
        )
        raise HTTPException(
            status_code=500,
            detail={
                "failing_check": exc.failing_check,
                "case_id": case_id,
                "message": str(exc),
            },
        ) from exc
    except CheckMeshError as exc:
        # V126: real checkMesh failure (parse error, exit_nonzero,
        # docker_sdk_error mid-call). Container-unavailable / not-running
        # paths are graceful-degraded inside analyze_mesh_quality and
        # never reach this handler — anything that surfaces here is a
        # genuine fault the operator needs to see.
        logger.exception(
            "checkMesh failed for case_id=%r failing_check=%s",
            case_id,
            exc.failing_check,
        )
        raise HTTPException(
            status_code=502,
            detail={
                "failing_check": exc.failing_check,
                "case_id": case_id,
                "message": str(exc),
            },
        ) from exc
