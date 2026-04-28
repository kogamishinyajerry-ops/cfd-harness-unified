"""GET /api/cases/{case_id}/geometry/stl — serve STL bytes for the Viewport.

M-VIZ Tier-A backend deliverable (per DEC-V61-094 + spec_v2 §B.1).
Tiny anticipatory endpoint — full M-RENDER-API surface (multi-format,
glTF, mesh, fields) lands in a later milestone. For M-VIZ this exists
solely so the frontend Viewport.tsx component has something concrete
to fetch when smoke-testing the imported case fixtures.

Source of truth: ``ui/backend/user_drafts/imported/{case_id}/triSurface/*.stl``
(written by ``case_scaffold.scaffold_imported_case`` during M5.0 import).

Path-traversal defense: ``is_safe_case_id`` + post-resolve subpath check
mirroring the comparison_report.get_render_file pattern.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ui.backend.services.case_drafts import is_safe_case_id
from ui.backend.services.case_scaffold import template_clone


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
