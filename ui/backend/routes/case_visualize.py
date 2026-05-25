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
from ui.backend.services.case_visualize.residual_series import (
    build_residual_series,
)
from ui.backend.services.case_visualize.vtk_export import (
    VtkExportError,
    ensure_vtk_output,
)
from ui.backend.services.case_visualize.streamline_export import (
    StreamlineExportError,
    ensure_streamlines,
)
from ui.backend.services.case_drafts import _draft_path  # case_id alphabet


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


@router.get("/cases/{case_id}/residual-series", tags=["case-visualize"])
def get_residual_series(case_id: str) -> dict:
    """R6 · Structured residual history for V4 Post-mode chart.

    Returns the best-available residual time-series as JSON. Source
    selection (best-first): parsed solver log → multi-run final
    residuals → empty. Frontend uses ``source`` to label the x-axis
    and falls back to an empty-state when ``source="empty"``.

    Per V130 advisor-not-driver: GET-only, no mutation surface, no
    LLM in path. Safe to poll.
    """
    if not is_safe_case_id(case_id):
        raise HTTPException(status_code=400, detail=f"unsafe case_id: {case_id!r}")
    payload = build_residual_series(case_id)
    return {
        "case_id": payload.case_id,
        "source": payload.source,
        "series": {
            name: [{"x": p.x, "y": p.y} for p in points]
            for name, points in payload.series.items()
        },
        "sample_count": payload.sample_count,
        "latest_run_id": payload.latest_run_id,
        "target_floor": payload.target_floor,
        "achieved": payload.achieved,
        "note": payload.note,
    }


# ──────────────── B2.5 · Post viewport VTP feeds ────────────────
# Endpoints for the V4 Post-mode 3D viewport's real surface + streamline
# overlay. Both serve XML PolyData (VTP), consumed client-side by vtk.js's
# vtkXMLPolyDataReader. See B2.5 architecture decision 2026-05-19
# (.planning/v4_real_viewport_audit_2026-05-19.md).


def _ensure_vtk_or_http(case_dir: Path):
    """Run ``ensure_vtk_output`` and map ``VtkExportError`` to the HTTP
    status the Post overlay endpoints share (409 no run / 503 container /
    500 otherwise). Extracted so surface.vtp + patches stay in lockstep."""
    try:
        return ensure_vtk_output(case_dir)
    except VtkExportError as exc:
        msg = str(exc)
        if "no time directories" in msg or "solver hasn't run" in msg:
            raise HTTPException(status_code=409, detail=msg) from exc
        if "container" in msg.lower() and "not running" in msg.lower():
            raise HTTPException(status_code=503, detail=msg) from exc
        raise HTTPException(status_code=500, detail=msg) from exc


@router.get("/cases/{case_id}/post/patches", tags=["case-visualize"])
def get_post_patches(case_id: str) -> dict:
    """List the case's real boundary patches for the Post surface overlay.

    DEC-V61-205 (M5 C2) bug #2 fix: the frontend used to hardcode
    ``patch=engine`` (an APU-bay-only name) and 404'd on every other case
    (LDC has ``fixedWalls``/``lid``, backward_step its own). This endpoint
    returns the patches that actually exist for this solved case so the
    client can pick a real one. Each entry carries the on-disk VTP byte
    size as a cheap proxy for "how much surface this patch carries" — the
    client defaults to the largest wall-like patch.

    Errors mirror surface.vtp (409 no run / 503 container / 500).
    """
    case_dir = _resolve(case_id)
    vtk = _ensure_vtk_or_http(case_dir)
    patches = sorted(
        (
            {"name": p.stem, "bytes": p.stat().st_size}
            for p in vtk.boundary_dir.glob("*.vtp")
        ),
        key=lambda d: d["name"],
    )
    return {"patches": patches, "latest_time": vtk.latest_time}


@router.get("/cases/{case_id}/post/surface.vtp", tags=["case-visualize"])
def get_post_surface_vtp(case_id: str, patch: str = "engine") -> Response:
    """Return the named patch's surface as VTP with U/p scalars attached.

    Runs ``foamToVTK -latestTime`` in the cfd-openfoam container the
    first time (cached afterwards · re-runs on solver re-execute).

    The caller should resolve a real patch name via ``/post/patches``
    first; the ``engine`` default is kept only as a legacy fallback for
    the canonical KJ66 + external-aero naming convention.

    Errors:
      - 409 when solver hasn't run yet
      - 404 when patch name doesn't exist in the case's boundary set
      - 503 when the OpenFOAM container isn't running
      - 500 for everything else
    """
    # Safety: patch name traversal guard. Allow alnum + _ - . so dotted
    # patch names (e.g. "domain.0") that /post/patches legitimately
    # advertises round-trip without a 400 (Codex M5-C2 R2 P2). "/" is
    # excluded by the char set and ".." is rejected outright, so no path
    # traversal: the name only ever forms boundary_dir/<patch>.vtp.
    if not all(c.isalnum() or c in ("_", "-", ".") for c in patch) or ".." in patch:
        raise HTTPException(status_code=400, detail=f"unsafe patch: {patch!r}")

    case_dir = _resolve(case_id)
    vtk = _ensure_vtk_or_http(case_dir)

    vtp_path = vtk.boundary_dir / f"{patch}.vtp"
    if not vtp_path.is_file():
        available = sorted(
            p.stem for p in vtk.boundary_dir.glob("*.vtp")
        )
        raise HTTPException(
            status_code=404,
            detail=(
                f"patch {patch!r} not in case · available: "
                f"{', '.join(available) or '(none)'}"
            ),
        )
    return Response(
        content=vtp_path.read_bytes(),
        media_type="application/vnd.kitware.vtk-polydata+xml",
        headers={"Cache-Control": "no-store, max-age=0"},
    )


@router.get("/cases/{case_id}/post/streamlines.vtp", tags=["case-visualize"])
def get_post_streamlines_vtp(case_id: str) -> Response:
    """Return integrated streamlines as VTP, with U/p sampled along
    each track.

    Seeds = 8-point line on the inlet AABB diagonal (auto seeding · per
    B2.5 architecture). Runs OpenFOAM's native ``streamLine`` function
    in the container (cached · re-runs on solver re-execute).

    Errors mirror surface.vtp (409 / 503 / 500).
    """
    case_dir = _resolve(case_id)
    try:
        result = ensure_streamlines(case_dir)
    except StreamlineExportError as exc:
        msg = str(exc)
        if "no time directories" in msg or "solver hasn't run" in msg:
            raise HTTPException(status_code=409, detail=msg) from exc
        if "container" in msg.lower() and "not running" in msg.lower():
            raise HTTPException(status_code=503, detail=msg) from exc
        raise HTTPException(status_code=500, detail=msg) from exc

    return Response(
        content=result.track_vtp.read_bytes(),
        media_type="application/vnd.kitware.vtk-polydata+xml",
        headers={"Cache-Control": "no-store, max-age=0"},
    )


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
