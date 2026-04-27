"""Detect named patches (boundary regions) from a loaded STL.

ASCII STL with multiple ``solid <name>`` blocks → ``trimesh.Scene`` whose
``geometry`` dict keys are the solid names → one patch per name. Binary
STL or single-solid ASCII → single patch named ``defaultFaces`` and the
``all_default_faces`` flag set, which the UI surfaces as a WARN (user
should re-export with named solids per inlet/outlet/wall).
"""
from __future__ import annotations

import re

import trimesh

from .health_check import PatchInfo

# OpenFOAM patch / sHM region names must be valid C-identifier-ish tokens
# (letters, digits, underscore; cannot start with a digit). STL `solid <name>`
# headers in the wild contain whitespace, dots, dashes, unicode, etc.
_PATCH_NAME_INVALID = re.compile(r"[^A-Za-z0-9_]")


def _sanitize_patch_name(raw: str) -> str:
    """Coerce a raw STL solid name into an OpenFOAM-safe patch identifier.

    Any non-`[A-Za-z0-9_]` char is replaced with `_`. A leading digit gets
    a `p_` prefix. Empty / fully-stripped names fall back to ``defaultFaces``
    so downstream sHM dict generation always has a usable token.
    """
    if not raw:
        return "defaultFaces"
    cleaned = _PATCH_NAME_INVALID.sub("_", raw).strip("_")
    if not cleaned:
        return "defaultFaces"
    if cleaned[0].isdigit():
        cleaned = f"p_{cleaned}"
    return cleaned


def detect_patches(loaded: trimesh.Trimesh | trimesh.Scene) -> tuple[list[PatchInfo], bool]:
    """Return ``(patches, all_default_faces)``.

    ``all_default_faces`` is ``True`` when the STL has no named solids
    (single binary blob or single-solid ASCII). The route does NOT reject
    on this — the UI shows inline help and lets the user confirm. M7
    mesh generation will fall back to a single ``defaultFaces`` patch in
    ``snappyHexMeshDict``.
    """
    if isinstance(loaded, trimesh.Scene):
        patches: list[PatchInfo] = []
        for name, geom in loaded.geometry.items():
            face_count = int(geom.faces.shape[0]) if hasattr(geom, "faces") else 0
            patches.append(PatchInfo(name=_sanitize_patch_name(name), face_count=face_count))
        # Edge case: trimesh may load a single-solid ASCII into a Scene
        # with a single auto-named geometry. Treat as defaulted if the
        # only key looks like trimesh's auto-name.
        if len(patches) == 1 and patches[0].name.lower() in {"geometry", "geometry_0", ""}:
            return [PatchInfo(name="defaultFaces", face_count=patches[0].face_count)], True
        return patches, False

    # Single Trimesh — no per-solid names available.
    face_count = int(loaded.faces.shape[0])
    return [PatchInfo(name="defaultFaces", face_count=face_count)], True
