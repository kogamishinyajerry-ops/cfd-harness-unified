"""trimesh-based STL parser. Accepts ASCII or binary STL bytes."""
from __future__ import annotations

import io
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


def canonical_stl_bytes(combined: trimesh.Trimesh) -> bytes:
    """Re-serialize as binary STL. Caller passes the pre-combined mesh
    from :func:`combine` so the concat work isn't repeated."""
    return combined.export(file_type="stl")
