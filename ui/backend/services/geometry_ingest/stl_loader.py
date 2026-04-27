"""trimesh-based STL parser. Accepts ASCII or binary STL bytes."""
from __future__ import annotations

import io
import re
from typing import Union

import trimesh


LoadedSTL = Union[trimesh.Trimesh, trimesh.Scene]


def load_stl_from_bytes(data: bytes) -> tuple[LoadedSTL | None, list[str]]:
    """Parse STL bytes. Returns ``(mesh_or_scene, errors)``.

    trimesh dispatches on file content: ASCII STL with multiple ``solid``
    blocks → ``trimesh.Scene`` (one geometry per solid name); binary STL or
    single-solid ASCII → ``trimesh.Trimesh``.

    On parse failure, ``mesh_or_scene`` is ``None`` and ``errors`` describes
    the failing reason (used as the ``failing_check`` route response field).
    """
    if not data:
        return None, ["empty STL payload"]
    try:
        loaded = trimesh.load(io.BytesIO(data), file_type="stl")
    except Exception as exc:  # noqa: BLE001 — trimesh raises a wide variety
        return None, [f"STL parse failed: {exc}"]

    # trimesh does NOT raise on garbage input — it returns an empty Scene.
    # Treat that as a parse failure so the route returns failing_check=stl_parse,
    # not the misleading downstream watertight-derived classification.
    if isinstance(loaded, trimesh.Scene) and len(loaded.geometry) == 0:
        return None, ["STL parse produced no geometry (likely not a valid STL)"]
    if isinstance(loaded, trimesh.Trimesh) and loaded.faces.shape[0] == 0:
        return None, ["STL parse produced an empty mesh"]
    if isinstance(loaded, (trimesh.Trimesh, trimesh.Scene)):
        return loaded, []
    return None, [f"unexpected trimesh load type: {type(loaded).__name__}"]


def combine(loaded: LoadedSTL) -> trimesh.Trimesh | None:
    """Reduce a Scene (or Trimesh) to a single Trimesh for downstream use.

    Returns ``None`` for an empty Scene. Patch identity is NOT lost — the
    caller still has ``loaded.geometry`` for per-solid name extraction.
    """
    if isinstance(loaded, trimesh.Scene):
        meshes = list(loaded.geometry.values())
        if not meshes:
            return None
        return trimesh.util.concatenate(meshes) if len(meshes) > 1 else meshes[0]
    return loaded


def solid_count(loaded: LoadedSTL) -> int:
    if isinstance(loaded, trimesh.Scene):
        return len(loaded.geometry)
    return 1


_SOLID_HEADER_RE = re.compile(rb"^\s*solid\b[^\n]*", re.MULTILINE)
_ENDSOLID_HEADER_RE = re.compile(rb"^\s*endsolid\b[^\n]*", re.MULTILINE)


def _ascii_with_solid_name(mesh: trimesh.Trimesh, name: str) -> bytes:
    """Export ``mesh`` as ASCII STL with the ``solid <name>`` / ``endsolid <name>``
    headers rewritten to match the requested patch name. trimesh's own
    ASCII export uses a generic placeholder ("solid"), which would defeat
    the round-trip detect_patches → solid-name → sHM stub mapping.
    """
    raw = mesh.export(file_type="stl_ascii")
    if isinstance(raw, str):
        raw = raw.encode("utf-8")
    encoded_name = name.encode("ascii", errors="replace")
    raw = _SOLID_HEADER_RE.sub(b"solid " + encoded_name, raw, count=1)
    raw = _ENDSOLID_HEADER_RE.sub(b"endsolid " + encoded_name, raw, count=1)
    if not raw.endswith(b"\n"):
        raw += b"\n"
    return raw


def canonical_stl_bytes(
    mesh_or_loaded: LoadedSTL,
    patch_names: list[str] | None = None,
) -> bytes:
    """Re-serialize STL for storage in ``triSurface/``.

    Behavior:

    * ``Trimesh`` (or single-geometry ``Scene``) → binary STL. ``patch_names``
      is ignored.
    * Multi-geometry ``Scene`` + ``patch_names`` aligned to insertion order
      → ASCII multi-solid STL whose ``solid <name>`` headers match the
      sanitized names returned by :func:`detect_patches`. This is what the
      ``snappyHexMeshDict.stub`` references — the names MUST agree or the
      sHM regions stage at M7 has nothing to bind to.
    * Multi-geometry ``Scene`` without ``patch_names`` → concatenate to a
      single mesh + binary STL (legacy fallback).
    """
    if isinstance(mesh_or_loaded, trimesh.Scene):
        geoms = list(mesh_or_loaded.geometry.values())
        if not geoms:
            return b""
        if len(geoms) == 1:
            return geoms[0].export(file_type="stl")
        if patch_names and len(patch_names) == len(geoms):
            chunks: list[bytes] = []
            for name, mesh in zip(patch_names, geoms):
                chunks.append(_ascii_with_solid_name(mesh, name))
            return b"".join(chunks)
        # Fallback: concat + binary. Loses solid-name identity — acceptable
        # only when caller has no patch_names contract to honor.
        return trimesh.util.concatenate(geoms).export(file_type="stl")
    return mesh_or_loaded.export(file_type="stl")
