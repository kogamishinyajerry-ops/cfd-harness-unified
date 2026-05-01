"""Iter 06 — half-pipe with symmetry plane.

Stresses two pipeline behaviors not yet covered by iter02..iter05:
  1. Curved (cylindrical) wall surfaces — all prior cases used flat
     polygonal walls, so per-triangle voting was assigning planar
     surfaces. The half-pipe has 24 quad strips along the curved
     wall, each potentially mapped to a different gmsh parametric
     surface.
  2. SYMMETRY BCClass driven end-to-end from the named-patches
     mode. The class has been in `bc_setup_from_stl_patches.py`
     since cacda9f but never executed by an adversarial case —
     iter06 is the first.

Geometry: half-cylinder (radius 0.05 m, length 0.30 m) lying along
+z, half-disk cross-section above the y=0 plane. Four named patches:
  - inlet:    half-disk cap at z=0
  - outlet:   half-disk cap at z=L
  - walls:    curved cylindrical surface (no-slip)
  - symmetry: flat rectangular surface at y=0
"""

from __future__ import annotations

from pathlib import Path
import re

import numpy as np
import trimesh


CASE_CLASS = "half_pipe_with_symmetry_plane"
PATCH_ORDER = ("inlet", "outlet", "walls", "symmetry")

PARAMS = {
    "radius_m": 0.05,
    "length_m": 0.30,
    "n_arc_segments": 24,
}

_SOLID_HEADER_RE = re.compile(rb"^\s*solid\b[^\n]*", re.MULTILINE)
_ENDSOLID_HEADER_RE = re.compile(rb"^\s*endsolid\b[^\n]*", re.MULTILINE)


def build_tagged_shell() -> tuple[trimesh.Trimesh, np.ndarray]:
    r = PARAMS["radius_m"]
    L = PARAMS["length_m"]
    n_seg = PARAMS["n_arc_segments"]

    # Half-disk profile: arc points on upper half + 2 endpoints on x-axis.
    # angles 0..pi from (+r, 0) sweeping to (-r, 0).
    angles = np.linspace(0.0, np.pi, n_seg + 1)
    arc_xy = np.column_stack([r * np.cos(angles), r * np.sin(angles)])
    n_arc = len(arc_xy)

    # Vertex layout:
    #   0..n_arc-1            : bottom arc (z=0)
    #   n_arc                 : bottom center (z=0)
    #   n_arc+1..2*n_arc      : top arc (z=L)
    #   2*n_arc+1             : top center (z=L)
    bot_arc = np.column_stack([arc_xy, np.zeros(n_arc)])
    top_arc = np.column_stack([arc_xy, np.full(n_arc, L)])
    bot_center = np.array([[0.0, 0.0, 0.0]])
    top_center = np.array([[0.0, 0.0, L]])
    vertices = np.vstack([bot_arc, bot_center, top_arc, top_center])

    bc_idx = n_arc
    top_off = n_arc + 1
    tc_idx = 2 * n_arc + 1

    faces: list[list[int]] = []
    labels: list[str] = []

    # Inlet (z=0 cap, half-disk): fan from bot_center. For outward normal
    # along -z (out of fluid which extends in +z), winding should give
    # cross product in -z. Try (bc, i, i+1) for segment i:
    #   v1 = arc[i] - bc = (xi, yi, 0), v2 = arc[i+1] - bc = (xj, yj, 0)
    #   v1 × v2 = (0, 0, xi*yj - xj*yi). For arc points in upper half
    #   sweeping CCW (i=0 at +x, i=n at -x), xi*yj - xj*yi > 0, so
    #   cross is +z. We need -z. Reverse winding: (bc, i+1, i).
    for i in range(n_arc - 1):
        faces.append([bc_idx, i + 1, i])
        labels.append("inlet")

    # Outlet (z=L cap, half-disk): fan from top_center. For outward
    # normal +z, winding (tc, top_off + i, top_off + i+1):
    #   v1 = arc[i] - tc, v2 = arc[i+1] - tc → cross = +z ✓
    for i in range(n_arc - 1):
        faces.append([tc_idx, top_off + i, top_off + i + 1])
        labels.append("outlet")

    # Walls (curved cylindrical surface): quad strips along arc, each
    # split into 2 triangles. Outward normal points radially outward
    # (in +r direction at each angular position). For arc point i with
    # outward radial = (cos(theta_i), sin(theta_i), 0), the quad
    # vertices are bot_i, bot_j, top_j, top_i (going CCW around
    # outward normal). Triangle 1: (bot_i, bot_j, top_j); Triangle 2:
    # (bot_i, top_j, top_i).
    for i in range(n_arc - 1):
        bi, bj = i, i + 1
        ti, tj = top_off + i, top_off + i + 1
        faces.append([bi, bj, tj])
        labels.append("walls")
        faces.append([bi, tj, ti])
        labels.append("walls")

    # Symmetry plane (y=0 flat rectangle): outward normal must point in
    # -y (out of the fluid which lies in y>0). The plane includes 6
    # vertices because both cap fans converge at center vertices that
    # sit ON the diameter edge, and watertight manifold requires those
    # centers to be vertices of the symmetry rectangle too:
    #   a = arc[0]              = (+r, 0, 0)   idx 0
    #   b = bot_center          = (0, 0, 0)    idx n_arc
    #   c = arc[n_arc-1]        = (-r, 0, 0)   idx n_arc-1
    #   d = top_arc[n_arc-1]    = (-r, 0, L)   idx top_off + n_arc - 1
    #   e = top_center          = (0, 0, L)    idx 2*n_arc + 1
    #   f = top_arc[0]          = (+r, 0, L)   idx top_off
    # Triangulated as 4 triangles, all with -y outward normal.
    a, b, c = 0, bc_idx, n_arc - 1
    d, e, f = top_off + n_arc - 1, tc_idx, top_off
    faces.append([a, e, b])
    faces.append([a, f, e])
    faces.append([b, d, c])
    faces.append([b, e, d])
    for _ in range(4):
        labels.append("symmetry")

    shell = trimesh.Trimesh(
        vertices=vertices,
        faces=np.asarray(faces, dtype=np.int64),
        process=False,
    )

    if not shell.is_watertight:
        raise ValueError("generated half-pipe shell is not watertight")
    if shell.body_count != 1:
        raise ValueError("generated half-pipe must be one connected manifold")
    if not shell.is_winding_consistent:
        raise ValueError("generated half-pipe has inconsistent winding")

    return shell, np.asarray(labels, dtype=object)


def _patch_from_faces(
    mesh: trimesh.Trimesh, labels: np.ndarray, patch_name: str
) -> trimesh.Trimesh:
    face_index = np.flatnonzero(labels == patch_name)
    if face_index.size == 0:
        raise ValueError(f"empty patch: {patch_name}")
    patch = mesh.submesh([face_index], append=True, repair=False)
    if patch.faces.size == 0:
        raise ValueError(f"submesh export failed for patch: {patch_name}")
    return patch


def build_patches() -> dict[str, trimesh.Trimesh]:
    shell, labels = build_tagged_shell()
    return {name: _patch_from_faces(shell, labels, name) for name in PATCH_ORDER}


def verify_watertight_union(patches: dict[str, trimesh.Trimesh]) -> np.ndarray:
    combined = trimesh.util.concatenate(
        [patches[name] for name in PATCH_ORDER]
    ).copy()
    combined.merge_vertices()
    if not combined.is_watertight:
        raise ValueError("patch union is not watertight after seam welding")
    if combined.body_count != 1:
        raise ValueError("patch union must be one connected shell")
    if not combined.is_winding_consistent:
        raise ValueError("patch union has inconsistent winding")
    return combined.extents


def _ascii_with_name(mesh: trimesh.Trimesh, name: str) -> bytes:
    raw = mesh.export(file_type="stl_ascii")
    if isinstance(raw, str):
        raw = raw.encode("ascii")
    encoded_name = name.encode("ascii")
    raw = _SOLID_HEADER_RE.sub(b"solid " + encoded_name, raw, count=1)
    raw = _ENDSOLID_HEADER_RE.sub(b"endsolid " + encoded_name, raw, count=1)
    if not raw.endswith(b"\n"):
        raw += b"\n"
    return raw


def write_ascii_multisolid(path: Path, patches: dict[str, trimesh.Trimesh]) -> None:
    chunks = [_ascii_with_name(patches[name], name) for name in PATCH_ORDER]
    path.write_bytes(b"".join(chunks))


def format_extent(extent: np.ndarray) -> str:
    return "(" + ", ".join(f"{value:.4f}" for value in extent) + ")"


def main() -> None:
    here = Path(__file__).resolve().parent
    output = here / "geometry.stl"
    patches = build_patches()
    extent = verify_watertight_union(patches)
    write_ascii_multisolid(output, patches)
    print(
        f"OK | {CASE_CLASS} | {len(PATCH_ORDER)} patches | bbox={format_extent(extent)}"
    )


if __name__ == "__main__":
    main()
