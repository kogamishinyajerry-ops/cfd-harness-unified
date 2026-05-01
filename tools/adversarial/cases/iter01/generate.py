from __future__ import annotations

from pathlib import Path
import re

import numpy as np
import trimesh


CASE_CLASS = "thin_features"
PATCH_ORDER = ("inlet", "outlet", "walls", "blade")

PARAMS = {
    "outer_length": 0.24,
    "outer_height": 0.08,
    "outer_depth": 0.04,
    "blade_thickness": 0.002,
    "blade_height": 0.072,
    "blade_depth": 0.032,
    "blade_center_x": 0.02,
}

_SOLID_HEADER_RE = re.compile(rb"^\s*solid\b[^\n]*", re.MULTILINE)
_ENDSOLID_HEADER_RE = re.compile(rb"^\s*endsolid\b[^\n]*", re.MULTILINE)


def _patch_from_faces(mesh: trimesh.Trimesh, mask: np.ndarray) -> trimesh.Trimesh:
    face_index = np.flatnonzero(mask)
    if face_index.size == 0:
        raise ValueError("face selection produced an empty patch")
    patch = mesh.submesh([face_index], append=True, repair=False)
    if patch.faces.size == 0:
        raise ValueError("submesh export produced an empty patch")
    return patch


def build_case() -> dict[str, trimesh.Trimesh]:
    outer = trimesh.creation.box(
        extents=[
            PARAMS["outer_length"],
            PARAMS["outer_height"],
            PARAMS["outer_depth"],
        ]
    )
    normals = outer.face_normals
    inlet_mask = np.isclose(normals[:, 0], -1.0)
    outlet_mask = np.isclose(normals[:, 0], 1.0)
    walls_mask = ~(inlet_mask | outlet_mask)

    blade = trimesh.creation.box(
        extents=[
            PARAMS["blade_thickness"],
            PARAMS["blade_height"],
            PARAMS["blade_depth"],
        ],
        transform=trimesh.transformations.translation_matrix(
            [PARAMS["blade_center_x"], 0.0, 0.0]
        ),
    )

    return {
        "inlet": _patch_from_faces(outer, inlet_mask),
        "outlet": _patch_from_faces(outer, outlet_mask),
        "walls": _patch_from_faces(outer, walls_mask),
        "blade": blade,
    }


def verify_watertight_union(patches: dict[str, trimesh.Trimesh]) -> np.ndarray:
    combined = trimesh.util.concatenate([patches[name] for name in PATCH_ORDER]).copy()
    # Each patch is an open surface by design; weld coincident seam vertices
    # before checking the stitched cavity shell + internal blade obstacle.
    combined.merge_vertices()
    if not combined.is_watertight:
        raise ValueError("patch union is not watertight after seam welding")
    if not combined.is_winding_consistent:
        raise ValueError("patch union has inconsistent winding")
    return combined.extents


def _ascii_with_name(mesh: trimesh.Trimesh, name: str) -> bytes:
    raw = mesh.export(file_type="stl_ascii")
    if isinstance(raw, str):
        raw = raw.encode("ascii")
    encoded = name.encode("ascii")
    raw = _SOLID_HEADER_RE.sub(b"solid " + encoded, raw, count=1)
    raw = _ENDSOLID_HEADER_RE.sub(b"endsolid " + encoded, raw, count=1)
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
    patches = build_case()
    extent = verify_watertight_union(patches)
    write_ascii_multisolid(output, patches)
    print(f"OK | {CASE_CLASS} | {len(PATCH_ORDER)} patches | bbox={format_extent(extent)}")


if __name__ == "__main__":
    main()
