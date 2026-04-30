"""Geometry-render routes — STL pass-through (M-VIZ) + glb transcode (M-RENDER-API).

  GET /api/cases/{case_id}/geometry/stl     — M-VIZ Tier-A · raw STL bytes
  GET /api/cases/{case_id}/geometry/render  — M-RENDER-API B.1 · transcoded glb

Both routes share path-traversal defense (``is_safe_case_id`` + post-
resolve subpath check) and source-of-truth path
(``user_drafts/imported/{case_id}/triSurface/*.stl``). The /render
endpoint additionally caches the transcoded glb under
``<case_dir>/.render_cache/`` keyed on source mtime.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ui.backend.services.case_drafts import is_safe_case_id
from ui.backend.services.case_scaffold import template_clone
from ui.backend.services.render import (
    BcRenderError,
    FieldSampleError,
    GeometryRenderError,
    MeshRenderError,
    build_bc_render_glb,
    build_field_payload,
    build_geometry_glb,
    build_mesh_wireframe_glb,
)


router = APIRouter()


@router.get("/cases/{case_id}/geometry/stl", tags=["geometry-render"])
def get_case_stl(case_id: str) -> FileResponse:
    """Return the imported case's STL as raw binary.

    Returns 404 if the case_id is unsafe, the imported case directory is
    missing, the triSurface subdir is missing, or no .stl is on disk.

    Content-Type ``model/stl`` per spec_v2 §B.1. ``application/octet-stream``
    would also work for browser-side fetch consumers, but ``model/stl`` is
    more accurate and vtk.js doesn't care about the MIME type when reading
    via ``parseAsArrayBuffer``.
    """
    if not is_safe_case_id(case_id):
        raise HTTPException(status_code=404, detail="case not found")

    imported_root = template_clone.IMPORTED_DIR / case_id
    triSurface_dir = imported_root / "triSurface"
    if not triSurface_dir.is_dir():
        raise HTTPException(status_code=404, detail="case not found")

    # Case-insensitive .stl match · _safe_origin_filename preserves the
    # uploader's original extension casing (model.STL stays as model.STL),
    # so glob("*.stl") would miss uploads on case-sensitive filesystems.
    # Mirrors meshing_gmsh/pipeline.py:82.
    stl_files = sorted(
        p for p in triSurface_dir.iterdir() if p.suffix.lower() == ".stl"
    )
    if not stl_files:
        raise HTTPException(status_code=404, detail="no STL on disk for this case")

    target = stl_files[0]
    try:
        resolved = target.resolve(strict=True)
        resolved.relative_to(template_clone.IMPORTED_DIR.resolve())
    except (ValueError, OSError, FileNotFoundError):
        raise HTTPException(status_code=404, detail="case not found")

    return FileResponse(
        resolved,
        media_type="model/stl",
        filename=resolved.name,
    )


_RENDER_FAILING_CHECK_TO_STATUS: dict[str, int] = {
    "case_not_found": 404,
    "no_source_stl": 422,
    "transcode_error": 422,
}


@router.get("/cases/{case_id}/geometry/render", tags=["geometry-render"])
def get_case_geometry_glb(case_id: str) -> FileResponse:
    """Return the imported case's geometry as binary glTF (.glb).

    Caches the transcoded glb under ``<case_dir>/.render_cache/geometry.glb``
    keyed on the source STL mtime. Concurrent readers either see the
    pre-replace or post-replace bytes — never a half-written file.
    """
    try:
        result = build_geometry_glb(case_id)
    except GeometryRenderError as exc:
        status = _RENDER_FAILING_CHECK_TO_STATUS.get(exc.failing_check, 422)
        raise HTTPException(status_code=status, detail=str(exc))

    try:
        resolved = result.cache_path.resolve(strict=True)
        resolved.relative_to(template_clone.IMPORTED_DIR.resolve())
    except (ValueError, OSError, FileNotFoundError):
        raise HTTPException(status_code=404, detail="case not found")

    return FileResponse(
        resolved,
        media_type="model/gltf-binary",
        filename="geometry.glb",
    )


_MESH_FAILING_CHECK_TO_STATUS: dict[str, int] = {
    "case_not_found": 404,
    "no_polymesh": 404,
    "polymesh_parse_error": 422,
}


@router.api_route(
    "/cases/{case_id}/mesh/render",
    methods=["GET", "HEAD"],
    tags=["geometry-render"],
)
def get_case_mesh_wireframe_glb(case_id: str) -> FileResponse:
    """Return the imported case's polyMesh as a wireframe binary glTF.

    Reads ``<case_dir>/constant/polyMesh/{points,faces}`` (M6.0 sHM
    output), extracts unique edges across all faces, and emits a glTF
    with a single ``mode: LINES`` primitive. Cached at
    ``<case_dir>/.render_cache/mesh.glb`` keyed on points + faces mtimes.

    HEAD is supported (Codex round-19 dogfood smoke 2026-04-30) so the
    StepPanelShell mesh-existence probe can confirm Step 2 completion
    on case-switch without downloading the full glb body. FastAPI's
    @router.get does not auto-register HEAD; users hitting HEAD on a
    GET-only route get a 405 and the probe falls through to "no
    mesh", regating Step 3's viewport even when artifacts exist.
    Starlette's FileResponse handles HEAD (strips body) automatically.
    """
    try:
        result = build_mesh_wireframe_glb(case_id)
    except MeshRenderError as exc:
        status = _MESH_FAILING_CHECK_TO_STATUS.get(exc.failing_check, 422)
        raise HTTPException(status_code=status, detail=str(exc))

    try:
        resolved = result.cache_path.resolve(strict=True)
        resolved.relative_to(template_clone.IMPORTED_DIR.resolve())
    except (ValueError, OSError, FileNotFoundError):
        raise HTTPException(status_code=404, detail="case not found")

    return FileResponse(
        resolved,
        media_type="model/gltf-binary",
        filename="mesh.glb",
    )


_BC_FAILING_CHECK_TO_STATUS: dict[str, int] = {
    "case_not_found": 404,
    "no_polymesh": 404,
    "no_boundary": 409,  # polyMesh exists but boundary not yet split (pre-setup-bc)
    "parse_error": 422,
    "transcode_error": 422,
}


@router.get("/cases/{case_id}/bc/render", tags=["geometry-render"])
def get_case_bc_render_glb(case_id: str) -> FileResponse:
    """Return the post-setup-bc polyMesh boundary patches as a colored glb.

    Phase-1A (DEC-V61-097). Replaces the static
    ``/cases/{id}/bc-overlay.png`` endpoint for Step 3 of M-PANELS.
    Each polyMesh boundary patch becomes its own TRIANGLES primitive
    with a distinct PBR baseColorFactor — vtk.js renders them in the
    standard orbit viewport so the user can rotate/zoom/pan.

    Cached at ``<case_dir>/.render_cache/bc_overlay.glb`` keyed on
    points + faces + boundary mtimes; rebuilds whenever any of the
    three is touched (e.g., re-running setup-bc to relabel patches).
    """
    try:
        result = build_bc_render_glb(case_id)
    except BcRenderError as exc:
        status = _BC_FAILING_CHECK_TO_STATUS.get(exc.failing_check, 422)
        raise HTTPException(status_code=status, detail=str(exc))

    try:
        resolved = result.cache_path.resolve(strict=True)
        resolved.relative_to(template_clone.IMPORTED_DIR.resolve())
    except (ValueError, OSError, FileNotFoundError):
        raise HTTPException(status_code=404, detail="case not found")

    return FileResponse(
        resolved,
        media_type="model/gltf-binary",
        filename="bc_overlay.glb",
    )


_FIELD_FAILING_CHECK_TO_STATUS: dict[str, int] = {
    "case_not_found": 404,
    "run_not_found": 404,
    "field_not_found": 404,
    "field_unsupported": 422,
    "field_parse_error": 422,
}


@router.get(
    "/cases/{case_id}/results/{run_id}/field/{name}",
    tags=["geometry-render"],
)
def get_case_field_sample(
    case_id: str, run_id: str, name: str
) -> FileResponse:
    """Return the case+run+field as a binary float32 stream.

    Tier-A fallback per spec_v2 §B.3: ``application/octet-stream``
    carrying the internalField scalar values packed as little-endian
    float32. Frontend handles colormap mapping. M-VIZ.results upgrades
    to baked-color glTF.

    The result has Content-Length = 4 × point_count.
    """
    try:
        result = build_field_payload(case_id, run_id, name)
    except FieldSampleError as exc:
        status = _FIELD_FAILING_CHECK_TO_STATUS.get(exc.failing_check, 422)
        raise HTTPException(status_code=status, detail=str(exc))

    try:
        resolved = result.cache_path.resolve(strict=True)
        resolved.relative_to(template_clone.IMPORTED_DIR.resolve())
    except (ValueError, OSError, FileNotFoundError):
        raise HTTPException(status_code=404, detail="case not found")

    return FileResponse(
        resolved,
        media_type="application/octet-stream",
        filename=f"field-{run_id}-{name}.bin",
        headers={"X-Field-Point-Count": str(result.point_count)},
    )
