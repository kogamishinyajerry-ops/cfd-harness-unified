"""polyMesh → wireframe glTF transcoding with mtime-keyed cache.

M-RENDER-API Tier-A B.2 (DEC-V61-095 spec_v2 §B.2). Mirrors the
geometry_glb cache contract — invalidate on points/faces mtime change,
atomic-rename on write.

Cache layout:

    <imported_case_dir>/.render_cache/mesh.glb

Source paths (in resolution order):

    1. <case_dir>/constant/polyMesh/{points,faces}    (M6.0 sHM output)
    2. <case_dir>/<imported_case_id>/constant/polyMesh/{points,faces}
       — fallback for cases scaffolded under user_drafts/imported/

V4 mesh inspection exports boundary faces plus boundary-face line rings:
engineers should see an opaque surface with grid lines on the visible
faces, not a full-volume line cloud.
"""
from __future__ import annotations

import os
import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from ui.backend.services.case_drafts import is_safe_case_id
from ui.backend.services.case_scaffold import template_clone

from .gltf_lines_builder import build_surface_lines_glb
from .polymesh_parser import (
    PolyMeshParseError,
    extract_unique_edges,
    parse_boundary_patches,
    parse_faces,
    parse_points,
    validate_face_indices,
)


CacheStatus = Literal["hit", "miss", "rebuild"]
_CACHE_VERSION = "surface-lines-v5"


@dataclass(frozen=True, slots=True)
class WireframeBuildResult:
    cache_path: Path
    status: CacheStatus


@dataclass(frozen=True, slots=True)
class MeshRenderError(Exception):
    failing_check: Literal[
        "case_not_found",
        "no_polymesh",
        "polymesh_parse_error",
    ]
    message: str

    def __str__(self) -> str:
        return f"{self.failing_check}: {self.message}"


def _imported_case_dir(case_id: str) -> Path:
    return template_clone.IMPORTED_DIR / case_id


def _resolve_polymesh_dir(case_dir: Path) -> Path:
    """Locate ``constant/polyMesh/`` under the case dir.

    M6.0 writes polyMesh at ``<case_dir>/constant/polyMesh/`` after
    gmshToFoam runs. Returns the dir; raises MeshRenderError if missing.
    """
    candidates = [
        case_dir / "constant" / "polyMesh",
    ]
    for d in candidates:
        if d.is_dir():
            return d
    raise MeshRenderError(
        failing_check="no_polymesh",
        message=f"no polyMesh dir under {case_dir} (looked in: {[str(c) for c in candidates]})",
    )


def _polymesh_source_files(
    polymesh_dir: Path, case_dir: Path
) -> tuple[Path, Path, Path | None]:
    """Return ``(points_path, faces_path)`` or raise no_polymesh.

    Round-2 Finding 1: each chosen path is ``resolve(strict=True)``'d and
    asserted to live under the case dir, so a symlink at
    ``constant/polyMesh/points`` (or faces) cannot redirect us to an
    arbitrary file outside IMPORTED_DIR.
    """
    points = polymesh_dir / "points"
    faces = polymesh_dir / "faces"
    boundary = polymesh_dir / "boundary"
    if not points.is_file():
        raise MeshRenderError(
            failing_check="no_polymesh",
            message=f"missing {points}",
        )
    if not faces.is_file():
        raise MeshRenderError(
            failing_check="no_polymesh",
            message=f"missing {faces}",
        )
    try:
        case_root = case_dir.resolve(strict=True)
        points_resolved = points.resolve(strict=True)
        faces_resolved = faces.resolve(strict=True)
        points_resolved.relative_to(case_root)
        faces_resolved.relative_to(case_root)
        boundary_resolved: Path | None = None
        if boundary.is_file():
            boundary_resolved = boundary.resolve(strict=True)
            boundary_resolved.relative_to(case_root)
    except (FileNotFoundError, OSError, ValueError):
        raise MeshRenderError(
            failing_check="no_polymesh",
            message="polyMesh source resolved outside case dir",
        )
    return points_resolved, faces_resolved, boundary_resolved


def _cache_target(case_dir: Path) -> Path:
    return case_dir / ".render_cache" / "mesh.glb"


def _cache_version_target(cache: Path) -> Path:
    return cache.with_name(f"{cache.name}.version")


def _cache_version_payload(boundary_path: Path | None) -> str:
    boundary_state = "present" if boundary_path is not None else "absent"
    return f"{_CACHE_VERSION}\nboundary={boundary_state}"


def _is_cache_fresh(
    cache: Path,
    boundary_path: Path | None,
    *sources: Path,
) -> bool:
    if not cache.exists():
        return False
    version = _cache_version_target(cache)
    if not version.exists():
        return False
    try:
        if version.read_text(encoding="utf-8").strip() != _cache_version_payload(
            boundary_path
        ):
            return False
    except OSError:
        return False
    try:
        cache_mtime = cache.stat().st_mtime
        return all(cache_mtime >= s.stat().st_mtime for s in sources)
    except FileNotFoundError:
        return False


def _atomic_write_guarded_multi(
    target: Path,
    payload: bytes,
    sources: tuple[Path, ...],
    expected_mtimes_ns: tuple[int, ...],
) -> None:
    """Multi-source variant of the guarded atomic write (Round-4 Finding 3).

    Same contract as field_sample / geometry_glb's single-source
    ``_atomic_write_guarded``, but checks an arbitrary number of
    source files. polyMesh wireframes depend on both ``points`` and
    ``faces`` so either changing during the rebuild must abort.
    """
    if len(sources) != len(expected_mtimes_ns):
        raise ValueError(
            "sources and expected_mtimes_ns must have the same length"
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(
        f".tmp.{secrets.token_hex(4)}{target.suffix}"
    )
    tmp.write_bytes(payload)

    # Round-4 Codex regression: a source.stat() that raised on a
    # vanished file leaked the temp and bypassed the failing_check
    # translator. Treat OSError (incl. FileNotFoundError) for any
    # source as a mtime mismatch — abort + clean up.
    def _current_mtimes() -> tuple[int | None, ...]:
        out: list[int | None] = []
        for s in sources:
            try:
                out.append(s.stat().st_mtime_ns)
            except OSError:
                out.append(None)
        return tuple(out)

    if _current_mtimes() != expected_mtimes_ns:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise RuntimeError(
            "polyMesh source mutated or vanished before atomic replace"
        )
    os.replace(tmp, target)
    if _current_mtimes() != expected_mtimes_ns:
        try:
            target.unlink()
        except OSError:
            pass
        raise RuntimeError(
            "polyMesh source mutated or vanished during atomic replace"
        )


def _select_boundary_faces(
    faces: list[list[int]],
    boundary_path: Path | None,
) -> list[list[int]]:
    if boundary_path is None:
        return faces
    patches = parse_boundary_patches(boundary_path)
    wall_patches = [
        patch
        for patch in patches
        if patch.patch_type == "wall"
        or "wall" in patch.name.lower()
        or "engine" in patch.name.lower()
    ]
    selected_patches = wall_patches or patches
    selected: list[list[int]] = []
    for patch in selected_patches:
        start = patch.start_face
        count = patch.n_faces
        end = start + count
        if start < 0 or end > len(faces):
            raise PolyMeshParseError(
                f"boundary range startFace={start} nFaces={count} exceeds "
                f"{len(faces)} parsed faces"
            )
        selected.extend(faces[start:end])
    if not selected:
        raise PolyMeshParseError("boundary file selected zero faces")
    return selected


def _build_wireframe_bytes(
    points_path: Path,
    faces_path: Path,
    boundary_path: Path | None,
) -> bytes:
    try:
        points = parse_points(points_path)
        faces = parse_faces(faces_path)
        # Round-2 Finding 4: face arity is checked against the count
        # prefix in parse_faces, but vertex IDs were never checked
        # against len(points). An out-of-range index would survive
        # edge extraction and produce an indices accessor pointing past
        # the POSITION buffer. Validate before building the GLB.
        validate_face_indices(faces, n_points=len(points))
        surface_faces = _select_boundary_faces(faces, boundary_path)
        edges = extract_unique_edges(surface_faces)
    except PolyMeshParseError as exc:
        raise MeshRenderError(
            failing_check="polymesh_parse_error",
            message=str(exc),
        )
    return build_surface_lines_glb(points, surface_faces, edges)


def build_mesh_wireframe_glb(case_id: str) -> WireframeBuildResult:
    """Public entrypoint for the route layer.

    Resolves the imported case's polyMesh, parses points + faces,
    extracts unique edges, assembles a binary glTF with a single
    LINES primitive, and caches it under ``.render_cache/mesh.glb``
    keyed on the source-file mtimes.
    """
    if not is_safe_case_id(case_id):
        raise MeshRenderError(
            failing_check="case_not_found",
            message=f"unsafe case_id: {case_id!r}",
        )
    case_dir = _imported_case_dir(case_id)
    if not case_dir.is_dir():
        raise MeshRenderError(
            failing_check="case_not_found",
            message=f"imported case dir missing: {case_dir}",
        )

    polymesh_dir = _resolve_polymesh_dir(case_dir)
    points_path, faces_path, boundary_path = _polymesh_source_files(
        polymesh_dir, case_dir
    )

    cache = _cache_target(case_dir)
    sources = tuple(
        p for p in (points_path, faces_path, boundary_path) if p is not None
    )
    if _is_cache_fresh(cache, boundary_path, *sources):
        return WireframeBuildResult(cache_path=cache, status="hit")

    # Round-3+4 Finding 3 closure: source mtimes (points + faces) are
    # threaded through both the post-build check and the guarded
    # multi-source atomic write. The pre-replace check inside the
    # helper aborts BEFORE os.replace (no stale cache visible to
    # concurrent readers); the post-replace check unlinks if a syscall-
    # window mutation slipped through.
    src_mtimes_before = tuple(s.stat().st_mtime_ns for s in sources)
    glb_bytes = _build_wireframe_bytes(points_path, faces_path, boundary_path)
    src_mtimes_after_build = tuple(s.stat().st_mtime_ns for s in sources)
    if src_mtimes_after_build != src_mtimes_before:
        raise MeshRenderError(
            failing_check="polymesh_parse_error",
            message=(
                "polyMesh source mutated during transcode "
                "(retry the request)"
            ),
        )
    status: CacheStatus = "rebuild" if cache.exists() else "miss"
    try:
        _atomic_write_guarded_multi(
            cache, glb_bytes, sources, src_mtimes_before
        )
    except RuntimeError as exc:
        raise MeshRenderError(
            failing_check="polymesh_parse_error",
            message=f"{exc} (retry the request)",
        )
    _cache_version_target(cache).write_text(
        _cache_version_payload(boundary_path) + "\n",
        encoding="utf-8",
    )
    return WireframeBuildResult(cache_path=cache, status=status)
