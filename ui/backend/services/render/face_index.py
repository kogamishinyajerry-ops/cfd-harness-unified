"""Cell-id → face_id mapping for the boundary glb.

Per DEC-V61-098 spec_v2 §A6, the frontend Viewport pickMode needs to
resolve a vtkCellPicker hit (per-primitive triangle index) back to the
stable ``face_id`` so the AnnotationPanel can dispatch a PUT against
the right face. This service emits a deterministic mapping in the
same primitive order as :func:`bc_glb._build_bc_glb_bytes` so the
frontend can index it by (primitive_index, triangle_index).

Output shape:

    {
        "case_id": "...",
        "primitives": [
            {
                "patch_name": "lid",
                "face_ids": ["fid_abc...", "fid_abc...", "fid_def...", ...]
            },
            ...
        ]
    }

Each ``face_ids[i]`` is the ``face_id`` for triangle ``i`` within that
primitive (after fan-triangulation: a quad face contributes 2 entries
of the same ``face_id``, an n-gon contributes n-2). The frontend
caches this once per case and looks up on click.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ui.backend.services.case_annotations import face_id as compute_face_id
from ui.backend.services.render.bc_glb import (
    BcRenderError,
    _bc_source_files,
    _read_boundary_patches,
    _triangulate_face,
)
from ui.backend.services.render.polymesh_parser import (
    PolyMeshParseError,
    parse_faces,
    parse_points,
    validate_face_indices,
)

__all__ = ["build_face_index"]


def _patch_sort_key(name: str) -> tuple[int, str]:
    """Mirror :func:`bc_glb._build_bc_glb_bytes`'s patch ordering so the
    primitive index in the response matches the glTF primitive index.
    """
    priority = {"lid": 0, "fixedWalls": 1}
    return (priority.get(name, 2), name)


def build_face_index(case_dir: Path) -> dict[str, Any]:
    """Build the cell→face_id mapping for ``case_dir``'s polyMesh.

    Raises:
        BcRenderError: same failing_check tags as bc_glb so the route
            can map them to identical HTTP statuses.
    """
    polymesh = case_dir / "constant" / "polyMesh"
    if not polymesh.is_dir():
        raise BcRenderError(
            failing_check="no_polymesh",
            message=f"no polyMesh at {polymesh}",
        )

    points_path, faces_path, boundary_path = _bc_source_files(polymesh, case_dir)

    try:
        points = parse_points(points_path)
        faces = parse_faces(faces_path)
        validate_face_indices(faces, len(points))
    except PolyMeshParseError as exc:
        raise BcRenderError(failing_check="parse_error", message=str(exc))

    patches = _read_boundary_patches(boundary_path)
    ordered_patches = sorted(patches.keys(), key=_patch_sort_key)

    primitives: list[dict[str, Any]] = []
    for name in ordered_patches:
        start_face, n_faces = patches[name]
        if n_faces <= 0:
            continue
        face_ids_per_triangle: list[str] = []
        for face_idx in range(start_face, start_face + n_faces):
            if face_idx >= len(faces):
                raise BcRenderError(
                    failing_check="parse_error",
                    message=(
                        f"boundary patch {name!r} references face {face_idx} "
                        f"but faces has length {len(faces)}"
                    ),
                )
            polymesh_face = faces[face_idx]
            triangles = _triangulate_face(polymesh_face)
            if not triangles:
                continue
            # Compute face_id from the polyMesh face's vertex coordinates
            # (NOT the per-triangle vertices — face_id identifies the
            # whole polygon, so all of its triangles share the same id).
            # Convert numpy float64 → Python float so repr() matches the
            # backend face_id() contract (np.float64 repr renders e.g.
            # ``np.float64(0.0)`` which would hash to a different value).
            verts = [
                (float(points[v][0]), float(points[v][1]), float(points[v][2]))
                for v in polymesh_face
            ]
            fid = compute_face_id(verts)
            face_ids_per_triangle.extend([fid] * len(triangles))
        if not face_ids_per_triangle:
            continue
        primitives.append({
            "patch_name": name,
            "face_ids": face_ids_per_triangle,
        })

    if not primitives:
        raise BcRenderError(
            failing_check="parse_error",
            message="no boundary triangles could be assembled (empty patches?)",
        )

    return {
        "case_id": case_dir.name,
        "primitives": primitives,
    }
