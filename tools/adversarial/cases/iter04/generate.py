from __future__ import annotations

from pathlib import Path
import re

import numpy as np
import trimesh


CASE_CLASS = "rotated_extruded_l_bend"
PATCH_ORDER = ("inlet", "outlet", "walls")

PARAMS = {
    "leg_x_m": 0.22,
    "leg_y_m": 0.18,
    "channel_width_m": 0.06,
    "depth_m": 0.07,
    "rotation_deg_xyz": (23.0, -17.0, 31.0),
}

# Boundary edges of the L profile (counter-clockwise):
#   0:(0->1) outer wall
#   1:(1->2) inlet
#   2:(2->3) inner wall
#   3:(3->4) inner wall
#   4:(4->5) outlet
#   5:(5->0) outer wall
EDGE_PATCHES = ("walls", "inlet", "walls", "walls", "outlet", "walls")

# Valid triangulation of the concave L profile in 2D.
CAP_TRIANGLES = np.array(
    [
        [0, 1, 2],
        [0, 2, 3],
        [0, 3, 4],
        [0, 4, 5],
    ],
    dtype=np.int64,
)

_SOLID_HEADER_RE = re.compile(rb"^\s*solid\b[^\n]*", re.MULTILINE)
_ENDSOLID_HEADER_RE = re.compile(rb"^\s*endsolid\b[^\n]*", re.MULTILINE)


def l_profile_vertices() -> np.ndarray:
    leg_x = PARAMS["leg_x_m"]
    leg_y = PARAMS["leg_y_m"]
    width = PARAMS["channel_width_m"]
    return np.array(
        [
            [0.0, 0.0],
            [leg_x, 0.0],
            [leg_x, width],
            [width, width],
            [width, leg_y],
            [0.0, leg_y],
        ],
        dtype=np.float64,
    )


def build_tagged_shell() -> tuple[trimesh.Trimesh, np.ndarray]:
    verts_2d = l_profile_vertices()
    depth = PARAMS["depth_m"]
    n = len(verts_2d)

    z_bottom = -0.5 * depth
    z_top = 0.5 * depth
    bottom = np.column_stack((verts_2d, np.full(n, z_bottom)))
    top = np.column_stack((verts_2d, np.full(n, z_top)))
    vertices = np.vstack((bottom, top))

    faces: list[list[int]] = []
    labels: list[str] = []

    # Top (+z) and bottom (-z) caps are walls.
    for a, b, c in CAP_TRIANGLES:
        faces.append([a + n, b + n, c + n])
        labels.append("walls")
        faces.append([c, b, a])
        labels.append("walls")

    # Side quads split into 2 triangles each.
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

    # Rotate to make all patches non-axis-aligned in global coordinates.
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
