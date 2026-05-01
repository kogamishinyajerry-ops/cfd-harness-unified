from __future__ import annotations

from pathlib import Path
import re

import numpy as np
import trimesh


CASE_CLASS = "rotated_t_junction_two_inlets_one_outlet"
PATCH_ORDER = ("inlet_1", "inlet_2", "outlet_1", "walls")

PARAMS = {
    "half_span_x_m": 0.17,
    "stem_length_m": 0.14,
    "channel_width_m": 0.06,
    "depth_m": 0.08,
    "rotation_deg_xyz": (21.0, -28.0, 17.0),
}

# CCW boundary edges of the 2D T profile:
#   0:(0->1) walls
#   1:(1->2) walls
#   2:(2->3) outlet_1
#   3:(3->4) walls
#   4:(4->5) walls
#   5:(5->6) inlet_2
#   6:(6->7) walls
#   7:(7->0) inlet_1
EDGE_PATCHES = (
    "walls",
    "walls",
    "outlet_1",
    "walls",
    "walls",
    "inlet_2",
    "walls",
    "inlet_1",
)

# Valid triangulation for the concave T profile cap.
CAP_TRIANGLES = np.array(
    [
        [7, 0, 1],
        [1, 2, 3],
        [1, 3, 4],
        [7, 1, 4],
        [7, 4, 5],
        [5, 6, 7],
    ],
    dtype=np.int64,
)

_SOLID_HEADER_RE = re.compile(rb"^\s*solid\b[^\n]*", re.MULTILINE)
_ENDSOLID_HEADER_RE = re.compile(rb"^\s*endsolid\b[^\n]*", re.MULTILINE)


def t_profile_vertices() -> np.ndarray:
    half = PARAMS["half_span_x_m"]
    stem = PARAMS["stem_length_m"]
    width = PARAMS["channel_width_m"]
    hw = 0.5 * width
    return np.array(
        [
            [-half, 0.0],
            [-hw, 0.0],
            [-hw, -stem],
            [hw, -stem],
            [hw, 0.0],
            [half, 0.0],
            [half, width],
            [-half, width],
        ],
        dtype=np.float64,
    )


def _signed_area_2d(vertices: np.ndarray) -> float:
    x = vertices[:, 0]
    y = vertices[:, 1]
    return 0.5 * np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y)


def _tri_area_2d(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    return 0.5 * abs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1]))


def _verify_cap_triangulation(vertices_2d: np.ndarray) -> None:
    poly_area = abs(_signed_area_2d(vertices_2d))
    tri_area = 0.0
    for i, j, k in CAP_TRIANGLES:
        tri_area += _tri_area_2d(vertices_2d[i], vertices_2d[j], vertices_2d[k])
    if not np.isclose(tri_area, poly_area, rtol=1e-9, atol=1e-12):
        raise ValueError(
            f"cap triangulation area mismatch: tri_area={tri_area:.12g}, poly_area={poly_area:.12g}"
        )


def build_tagged_shell() -> tuple[trimesh.Trimesh, np.ndarray]:
    verts_2d = t_profile_vertices()
    _verify_cap_triangulation(verts_2d)

    if _signed_area_2d(verts_2d) <= 0.0:
        raise ValueError("profile vertices must be CCW")

    depth = PARAMS["depth_m"]
    n = len(verts_2d)
    z_bottom = -0.5 * depth
    z_top = 0.5 * depth

    bottom = np.column_stack((verts_2d, np.full(n, z_bottom)))
    top = np.column_stack((verts_2d, np.full(n, z_top)))
    vertices = np.vstack((bottom, top))

    faces: list[list[int]] = []
    labels: list[str] = []

    # Caps are all walls.
    for a, b, c in CAP_TRIANGLES:
        faces.append([a + n, b + n, c + n])
        labels.append("walls")
        faces.append([c, b, a])
        labels.append("walls")

    # Boundary edges extruded into side quads (2 triangles per edge).
    for i, patch_name in enumerate(EDGE_PATCHES):
        j = (i + 1) % n
        bi, bj = i, j
        ti, tj = i + n, j + n
        faces.append([bi, bj, tj])
        labels.append(patch_name)
        faces.append([bi, tj, ti])
        labels.append(patch_name)

    shell = trimesh.Trimesh(
        vertices=vertices,
        faces=np.asarray(faces, dtype=np.int64),
        process=False,
    )

    # Rotate in 3D so patch normals are non-axis-aligned in world coordinates.
    ax, ay, az = np.deg2rad(PARAMS["rotation_deg_xyz"])
    transform = trimesh.transformations.euler_matrix(ax, ay, az, axes="sxyz")
    shell.apply_transform(transform)

    if not shell.is_watertight:
        raise ValueError("generated shell is not watertight")
    if shell.body_count != 1:
        raise ValueError("generated shell must be one connected manifold")
    if not shell.is_winding_consistent:
        raise ValueError("generated shell has inconsistent winding")

    return shell, np.asarray(labels, dtype=object)


def _patch_from_faces(mesh: trimesh.Trimesh, labels: np.ndarray, patch_name: str) -> trimesh.Trimesh:
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
    combined = trimesh.util.concatenate([patches[name] for name in PATCH_ORDER]).copy()
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
    print(f"OK | {CASE_CLASS} | {len(PATCH_ORDER)} patches | bbox={format_extent(extent)}")


if __name__ == "__main__":
    main()
