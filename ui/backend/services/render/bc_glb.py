"""polyMesh boundary patches → multi-primitive glb (Phase-1A · DEC-V61-097).

The Step 3 (Setup BC) viewport replaces the static bc-overlay.png with
an interactive 3D scene: same vtk.js orbit controls as Step 1, but
with each polyMesh boundary patch rendered as its own colored TRIANGLES
primitive. The user sees the cube with the lid in red, walls in gray,
and the frontAndBack patch in muted blue — and can rotate, zoom, pan
to inspect any face.

Output is a binary glTF 2.0 file. Each boundary patch becomes a
``primitive`` inside a single ``mesh`` with its own indices accessor
and its own material (``baseColorFactor`` per patch). vtk.js
GLTFImporter consumes these materials natively.

We share one POSITION buffer (the full polyMesh points array) across
all primitives, then per-primitive INDICES select that patch's faces
triangulated into a fan from the first vertex. This keeps the file
small even on dense meshes.
"""
from __future__ import annotations

import json
import os
import re
import secrets
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np

from ui.backend.services.case_drafts import is_safe_case_id
from ui.backend.services.case_scaffold import template_clone
from ui.backend.services.render.polymesh_parser import (
    PolyMeshParseError,
    parse_faces,
    parse_points,
    validate_face_indices,
)


_GLB_MAGIC = 0x46546C67          # 'glTF'
_JSON_CHUNK_TYPE = 0x4E4F534A    # 'JSON'
_BIN_CHUNK_TYPE = 0x004E4942     # 'BIN\0'

_COMPONENT_FLOAT = 5126           # FLOAT
_COMPONENT_UNSIGNED_INT = 5125    # UNSIGNED_INT

_TARGET_ARRAY_BUFFER = 34962
_TARGET_ELEMENT_ARRAY_BUFFER = 34963

_MODE_TRIANGLES = 4

# Patch-name → RGBA baseColorFactor. Lid is red (the moving boundary),
# fixedWalls gray (no-slip), and any third patch falls back to muted
# slate. Alpha is high but not 1.0 so a hidden patch is still visible
# through occluders.
_PATCH_COLORS: dict[str, tuple[float, float, float, float]] = {
    "lid": (0.96, 0.39, 0.39, 0.95),         # rose-400
    "fixedWalls": (0.55, 0.57, 0.63, 0.85),  # slate-400
    "frontAndBack": (0.42, 0.49, 0.65, 0.55),  # blue-gray, low alpha to "see through"
    "walls": (0.55, 0.57, 0.63, 0.85),
}
_FALLBACK_COLOR = (0.55, 0.57, 0.63, 0.80)


CacheStatus = Literal["hit", "miss", "rebuild"]


@dataclass(frozen=True, slots=True)
class BcGlbBuildResult:
    cache_path: Path
    status: CacheStatus


@dataclass(frozen=True, slots=True)
class BcRenderError(Exception):
    """Raised on any failure path the route maps to a 4xx response."""
    failing_check: Literal[
        "case_not_found", "no_polymesh", "no_boundary", "parse_error", "transcode_error"
    ]
    message: str

    def __str__(self) -> str:
        return f"{self.failing_check}: {self.message}"


def _imported_case_dir(case_id: str) -> Path:
    return template_clone.IMPORTED_DIR / case_id


def _read_boundary_patches(polymesh: Path) -> dict[str, tuple[int, int]]:
    """Parse ``constant/polyMesh/boundary`` → ``{patch: (startFace, nFaces)}``.

    Mirrors bc_overlay._read_boundary_patches but kept local so this
    module is self-contained.
    """
    boundary = polymesh / "boundary"
    if not boundary.is_file():
        raise BcRenderError(
            failing_check="no_boundary",
            message=f"no boundary file at {boundary}",
        )
    text = boundary.read_text()
    pattern = re.compile(
        r"(\w+)\s*\{[^}]*nFaces\s+(\d+)[^}]*startFace\s+(\d+)[^}]*\}",
        re.DOTALL,
    )
    patches: dict[str, tuple[int, int]] = {}
    for m in pattern.finditer(text):
        name = m.group(1)
        if name == "FoamFile":
            continue
        n_faces = int(m.group(2))
        start_face = int(m.group(3))
        patches[name] = (start_face, n_faces)
    if not patches:
        raise BcRenderError(
            failing_check="no_boundary",
            message=f"boundary file at {boundary} contains no patches",
        )
    return patches


def _triangulate_face(face: list[int]) -> list[tuple[int, int, int]]:
    """Fan-triangulate a polygon. Quads → 2 triangles, generally
    n-gons → n-2 triangles.
    """
    if len(face) < 3:
        return []
    v0 = face[0]
    return [(v0, face[i], face[i + 1]) for i in range(1, len(face) - 1)]


def _pad_to_4(payload: bytes, fill: bytes) -> bytes:
    rem = (4 - (len(payload) % 4)) % 4
    return payload + fill * rem if rem else payload


def _build_bc_glb_bytes(case_dir: Path) -> bytes:
    polymesh = case_dir / "constant" / "polyMesh"
    if not polymesh.is_dir():
        raise BcRenderError(
            failing_check="no_polymesh",
            message=f"no polyMesh at {polymesh}",
        )
    points_path = polymesh / "points"
    faces_path = polymesh / "faces"
    if not points_path.is_file() or not faces_path.is_file():
        raise BcRenderError(
            failing_check="no_polymesh",
            message=f"polyMesh at {polymesh} missing points or faces",
        )

    try:
        points = parse_points(points_path)
        faces = parse_faces(faces_path)
        validate_face_indices(faces, len(points))
    except PolyMeshParseError as exc:
        raise BcRenderError(failing_check="parse_error", message=str(exc))

    patches = _read_boundary_patches(polymesh)
    # Deterministic ordering: lid first (most visually important), then
    # fixedWalls, then everything else alphabetically.
    def patch_sort_key(name: str) -> tuple[int, str]:
        priority = {"lid": 0, "fixedWalls": 1}
        return (priority.get(name, 2), name)

    ordered_patches = sorted(patches.keys(), key=patch_sort_key)

    # Build per-patch index arrays.
    primitive_indices: list[np.ndarray] = []
    primitive_names: list[str] = []
    for name in ordered_patches:
        start_face, n_faces = patches[name]
        if n_faces <= 0:
            continue
        triangles: list[tuple[int, int, int]] = []
        for face_idx in range(start_face, start_face + n_faces):
            if face_idx >= len(faces):
                continue
            triangles.extend(_triangulate_face(faces[face_idx]))
        if not triangles:
            continue
        primitive_indices.append(
            np.asarray(triangles, dtype=np.uint32).reshape(-1)
        )
        primitive_names.append(name)

    if not primitive_indices:
        raise BcRenderError(
            failing_check="parse_error",
            message="no boundary triangles could be assembled (empty patches?)",
        )

    points32 = np.ascontiguousarray(points, dtype=np.float32)
    points_bytes = points32.tobytes()
    p_min = points32.min(axis=0).tolist()
    p_max = points32.max(axis=0).tolist()

    # Layout: positions buffer view first, then each patch's index
    # buffer view back-to-back. All 4-byte aligned (uint32 + float32
    # are naturally aligned at 4 bytes).
    buffer_chunks: list[bytes] = [points_bytes]
    offsets = [0]
    cursor = len(points_bytes)
    if cursor % 4 != 0:
        pad = (4 - (cursor % 4)) % 4
        buffer_chunks.append(b"\x00" * pad)
        cursor += pad

    index_offsets: list[int] = []
    index_lengths: list[int] = []
    index_counts: list[int] = []
    for idx_array in primitive_indices:
        idx_bytes = idx_array.tobytes()
        index_offsets.append(cursor)
        index_lengths.append(len(idx_bytes))
        index_counts.append(int(idx_array.size))
        buffer_chunks.append(idx_bytes)
        cursor += len(idx_bytes)
        if cursor % 4 != 0:
            pad = (4 - (cursor % 4)) % 4
            buffer_chunks.append(b"\x00" * pad)
            cursor += pad

    buffer_payload = b"".join(buffer_chunks)
    total_buffer_len = len(buffer_payload)

    buffer_views: list[dict] = [
        {
            "buffer": 0,
            "byteOffset": offsets[0],
            "byteLength": len(points_bytes),
            "target": _TARGET_ARRAY_BUFFER,
        }
    ]
    for i, (off, length) in enumerate(zip(index_offsets, index_lengths)):
        buffer_views.append({
            "buffer": 0,
            "byteOffset": off,
            "byteLength": length,
            "target": _TARGET_ELEMENT_ARRAY_BUFFER,
        })

    accessors: list[dict] = [
        {
            "bufferView": 0,
            "componentType": _COMPONENT_FLOAT,
            "count": int(len(points32)),
            "type": "VEC3",
            "min": p_min,
            "max": p_max,
        }
    ]
    for i, count in enumerate(index_counts):
        accessors.append({
            "bufferView": 1 + i,
            "componentType": _COMPONENT_UNSIGNED_INT,
            "count": count,
            "type": "SCALAR",
        })

    materials: list[dict] = []
    for name in primitive_names:
        color = _PATCH_COLORS.get(name, _FALLBACK_COLOR)
        materials.append({
            "name": name,
            "pbrMetallicRoughness": {
                "baseColorFactor": list(color),
                "metallicFactor": 0.0,
                "roughnessFactor": 0.85,
            },
            "doubleSided": True,
            # Alpha < 1.0 → BLEND so the back patch is see-through.
            **(
                {"alphaMode": "BLEND"} if color[3] < 0.99 else {}
            ),
        })

    primitives: list[dict] = []
    for i, name in enumerate(primitive_names):
        primitives.append({
            "attributes": {"POSITION": 0},
            "indices": 1 + i,
            "material": i,
            "mode": _MODE_TRIANGLES,
        })

    gltf_json: dict = {
        "asset": {"version": "2.0", "generator": "cfd-harness M-PANELS bc-render"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, "name": "boundary_patches"}],
        "meshes": [{"name": "polyMesh_boundary", "primitives": primitives}],
        "buffers": [{"byteLength": total_buffer_len}],
        "bufferViews": buffer_views,
        "accessors": accessors,
        "materials": materials,
    }

    json_bytes = json.dumps(
        gltf_json, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
    json_chunk = _pad_to_4(json_bytes, b" ")
    bin_chunk = _pad_to_4(buffer_payload, b"\x00")

    json_chunk_header = struct.pack("<II", len(json_chunk), _JSON_CHUNK_TYPE)
    bin_chunk_header = struct.pack("<II", len(bin_chunk), _BIN_CHUNK_TYPE)

    total_length = (
        12  # GLB header
        + 8 + len(json_chunk)
        + 8 + len(bin_chunk)
    )
    glb_header = struct.pack("<III", _GLB_MAGIC, 2, total_length)

    return (
        glb_header
        + json_chunk_header + json_chunk
        + bin_chunk_header + bin_chunk
    )


def _cache_target(case_dir: Path) -> Path:
    return case_dir / ".render_cache" / "bc_overlay.glb"


def _is_cache_fresh(cache: Path, *sources: Path) -> bool:
    if not cache.exists():
        return False
    try:
        cache_mtime = cache.stat().st_mtime
        return all(s.stat().st_mtime <= cache_mtime for s in sources if s.exists())
    except FileNotFoundError:
        return False


def _atomic_write(target: Path, payload: bytes) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(
        f".tmp.{secrets.token_hex(4)}{target.suffix}"
    )
    tmp.write_bytes(payload)
    os.replace(tmp, target)


def build_bc_render_glb(case_id: str) -> BcGlbBuildResult:
    """Public entrypoint. Build (or fetch from cache) the BC-overlay glb."""
    if not is_safe_case_id(case_id):
        raise BcRenderError(
            failing_check="case_not_found",
            message=f"unsafe case_id: {case_id!r}",
        )
    case_dir = _imported_case_dir(case_id)
    if not case_dir.is_dir():
        raise BcRenderError(
            failing_check="case_not_found",
            message=f"imported case dir missing: {case_dir}",
        )

    polymesh = case_dir / "constant" / "polyMesh"
    points_path = polymesh / "points"
    faces_path = polymesh / "faces"
    boundary_path = polymesh / "boundary"

    cache = _cache_target(case_dir)
    if _is_cache_fresh(cache, points_path, faces_path, boundary_path):
        return BcGlbBuildResult(cache_path=cache, status="hit")

    glb_bytes = _build_bc_glb_bytes(case_dir)
    status: CacheStatus = "rebuild" if cache.exists() else "miss"
    _atomic_write(cache, glb_bytes)
    return BcGlbBuildResult(cache_path=cache, status=status)
