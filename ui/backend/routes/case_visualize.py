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
    ARTIFACT_NAMES,
    BcOverlayError,
    ReportBundleError,
    ResidualChartError,
    VelocitySliceError,
    build_report_bundle,
    read_report_artifact,
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


# 2026-04-30 dogfood feedback: the original Step 5 viewport was a single
# midplane PNG which the user rejected as far below the line-B pipeline's
# multi-data reports. The bundle endpoint computes |U|+streamlines,
# pressure, vorticity, and centreline profiles in one matplotlib pass
# and exposes them as four separate PNG URLs the frontend lays out as
# a grid. See ui/backend/services/case_visualize/report_bundle.py.

def _report_bundle_error_to_http(exc: ReportBundleError) -> HTTPException:
    msg = str(exc)
    if "solver hasn't run" in msg or "no time directories" in msg:
        return HTTPException(status_code=409, detail=msg)
    if "container" in msg.lower() and "not running" in msg.lower():
        return HTTPException(status_code=503, detail=msg)
    return HTTPException(status_code=500, detail=msg)


@router.get("/cases/{case_id}/report-bundle", tags=["case-visualize"])
def get_report_bundle(case_id: str) -> dict:
    """Render (or read from cache) the four research-grade post-
    processing figures and return their URLs + summary stats.
    """
    case_dir = _resolve(case_id)
    try:
        bundle = build_report_bundle(case_dir)
    except ReportBundleError as exc:
        raise _report_bundle_error_to_http(exc) from exc

    base = f"/api/cases/{case_id}"
    # Codex round-1 P2 + round-2 P1 (2026-04-30): the URL `?v=` token
    # uses ReportBundle.cache_version, which combines final_time with
    # the U field's mtime. final_time alone failed for in-place
    # re-solves (icoFoam can overwrite the same time directory, leaving
    # final_time unchanged); including the U mtime makes the version
    # actually move on every re-render. React's <img src=...> changes,
    # browser refetches, grid updates.
    return {
        "final_time": bundle.final_time,
        "cell_count": bundle.cell_count,
        "slab_cell_count": bundle.slab_cell_count,
        "plane_axes": list(bundle.plane_axes),
        "summary_text": bundle.summary_text,
        "cache_version": bundle.cache_version,
        "case_kind": bundle.case_kind,
        "artifacts": {
            name: f"{base}/report/{name}.png?v={bundle.cache_version}"
            for name in ARTIFACT_NAMES
        },
    }


@router.api_route(
    "/cases/{case_id}/report/{artifact}.png",
    methods=["GET", "HEAD"],
    tags=["case-visualize"],
)
def get_report_artifact(
    case_id: str,
    artifact: str,
    v: str | None = None,
) -> Response:
    """Serve one of the cached report PNGs. ``artifact`` must be one of
    ``ARTIFACT_NAMES``; anything else returns 404.

    ``v`` is the optional cache_version token from /report-bundle's
    artifact URLs. When provided and the case has been re-solved
    between metadata fetch and PNG fetch (Codex round-3 P2), the
    bundle's current cache_version no longer matches ``v`` — return
    410 Gone so the client knows to re-fetch /report-bundle. When
    omitted, serve the current bundle (backward compatibility for
    callers that don't pass the version, e.g. direct curl).

    HEAD support (Codex round-19 dogfood smoke 2026-04-30): the
    Step5ResultsGrid FigureCard's onError → fetch(HEAD) probe needs
    the 410 status to detect a stale artifact and drop the bundle
    cache. A 405 here would silently strand the broken-image state
    until the user manually re-clicks [AI 处理].
    """
    if artifact not in ARTIFACT_NAMES:
        raise HTTPException(
            status_code=404,
            detail=f"unknown artifact: {artifact!r}",
        )
    case_dir = _resolve(case_id)
    # Codex round-5 P2: previously this route built the report
    # bundle to validate ``v`` AND read_report_artifact rebuilt it
    # again to read the file — 2 builds per PNG, 8 builds per Step 5
    # render. build_report_bundle parses U/C/p unconditionally before
    # checking the disk cache, so this was wasteful. Now we build
    # once, then read the file path directly off the bundle.
    try:
        from ui.backend.services.case_visualize import build_report_bundle
        bundle = build_report_bundle(case_dir)
        if v is not None and v != bundle.cache_version:
            raise HTTPException(
                status_code=410,
                detail=(
                    f"artifact version {v!r} is stale; current is "
                    f"{bundle.cache_version!r}. Re-fetch /report-bundle."
                ),
            )
        # bundle.artifacts maps logical name → URL fragment of the
        # form "reports/<dir>/<name>.png?v=...". Strip the query
        # string to get the on-disk relative path.
        rel = bundle.artifacts[artifact].split("?", 1)[0]
        on_disk = case_dir / rel
        if not on_disk.is_file():
            raise ReportBundleError(
                f"artifact {artifact!r} not on disk at {on_disk}"
            )
        png = on_disk.read_bytes()
    except ReportBundleError as exc:
        raise _report_bundle_error_to_http(exc) from exc
    return _png_response(png)
