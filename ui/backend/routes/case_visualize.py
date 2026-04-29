"""Phase-1A visualization routes (DEC-V61-097).

Three GET endpoints, one PNG each:

* ``/api/cases/{case_id}/bc-overlay.png``
* ``/api/cases/{case_id}/residual-history.png``
* ``/api/cases/{case_id}/velocity-slice.png``

Each returns ``image/png`` with no caching headers — callers should
re-fetch when they expect the underlying data has changed (after
setup-bc / solve / etc).
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from ui.backend.services.case_drafts import is_safe_case_id
from ui.backend.services.case_scaffold import IMPORTED_DIR
from ui.backend.services.case_visualize import (
    BcOverlayError,
    ResidualChartError,
    VelocitySliceError,
    render_bc_overlay_png,
    render_residual_chart_png,
    render_velocity_slice_png,
)


router = APIRouter()


def _resolve(case_id: str) -> Path:
    if not is_safe_case_id(case_id):
        raise HTTPException(status_code=400, detail=f"unsafe case_id: {case_id!r}")
    case_dir = IMPORTED_DIR / case_id
    if not case_dir.is_dir():
        raise HTTPException(status_code=404, detail=f"case {case_id!r} not found")
    return case_dir


def _png_response(payload: bytes) -> Response:
    # Cache-Control: no-store so an [AI 处理] re-run lands fresh PNGs
    # without a stale-cache 304. The fields are derived from disk
    # files that mutate per step.
    return Response(
        content=payload,
        media_type="image/png",
        headers={"Cache-Control": "no-store, max-age=0"},
    )


@router.get("/cases/{case_id}/bc-overlay.png", tags=["case-visualize"])
def get_bc_overlay(case_id: str) -> Response:
    """Render the post-setup-bc cube with lid faces in red and walls
    in gray. 409 if BC has not been set up yet.
    """
    case_dir = _resolve(case_id)
    try:
        png = render_bc_overlay_png(case_dir)
    except BcOverlayError as exc:
        msg = str(exc)
        if "lid" in msg or "fixedWalls" in msg or "no polyMesh" in msg:
            raise HTTPException(status_code=409, detail=msg) from exc
        raise HTTPException(status_code=500, detail=msg) from exc
    return _png_response(png)


@router.get("/cases/{case_id}/residual-history.png", tags=["case-visualize"])
def get_residual_history(case_id: str) -> Response:
    """Render the icoFoam residual history. 409 if no log.icoFoam."""
    case_dir = _resolve(case_id)
    try:
        png = render_residual_chart_png(case_dir)
    except ResidualChartError as exc:
        msg = str(exc)
        if "no log" in msg or "no parseable" in msg:
            raise HTTPException(status_code=409, detail=msg) from exc
        raise HTTPException(status_code=500, detail=msg) from exc
    return _png_response(png)


@router.get("/cases/{case_id}/velocity-slice.png", tags=["case-visualize"])
def get_velocity_slice(case_id: str) -> Response:
    """Render |U| on the z=0 midplane. May invoke postProcess in the
    cfd-openfoam container if cell centres aren't yet on disk —
    one-time cost, ~2s.
    """
    case_dir = _resolve(case_id)
    try:
        png = render_velocity_slice_png(case_dir)
    except VelocitySliceError as exc:
        msg = str(exc)
        if "solver hasn't run" in msg or "no time directories" in msg:
            raise HTTPException(status_code=409, detail=msg) from exc
        if "container" in msg.lower() and "not running" in msg.lower():
            raise HTTPException(status_code=503, detail=msg) from exc
        raise HTTPException(status_code=500, detail=msg) from exc
    return _png_response(png)
