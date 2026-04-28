"""STL → glTF binary (.glb) transcoding with mtime-keyed cache.

M-RENDER-API Tier-A B.1 (DEC-V61-095 spec_v2 §B.1). The Viewport's
glb consumer (M-PANELS / M-VIZ.mesh follow-ups) calls
GET /api/cases/<id>/geometry/render which delegates here.

Cache layout:

    <imported_case_dir>/.render_cache/geometry.glb

Cache invalidation: source-mtime comparison. If any *.stl under
``triSurface/`` is newer than the cached glb, the cache is rebuilt.

Atomic write: the new glb lands in a tempfile next to the cache
target, then ``os.replace`` moves it into place. Concurrent readers
either see the old bytes (pre-replace) or the new bytes (post-replace)
— never a half-written file.
"""
from __future__ import annotations

import os
import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import trimesh

from ui.backend.services.case_drafts import is_safe_case_id
from ui.backend.services.case_scaffold import template_clone


CacheStatus = Literal["hit", "miss", "rebuild"]


@dataclass(frozen=True, slots=True)
class GlbBuildResult:
    """Return value carrying the resolved cache path + which path it took.

    ``status`` is informational — the route does not branch on it, but
    tests assert it to confirm the cache invalidation contract.
    """
    cache_path: Path
    status: CacheStatus


@dataclass(frozen=True, slots=True)
class GeometryRenderError(Exception):
    """Raised on any failure path the route maps to a 4xx response.

    ``failing_check`` is the route's HTTP-status discriminator:

        case_not_found  → 404
        no_source_stl   → 422
        transcode_error → 422
    """
    failing_check: Literal["case_not_found", "no_source_stl", "transcode_error"]
    message: str

    def __str__(self) -> str:
        return f"{self.failing_check}: {self.message}"


def _imported_case_dir(case_id: str) -> Path:
    return template_clone.IMPORTED_DIR / case_id


def _resolve_source_stl(case_dir: Path) -> Path:
    """Pick the canonical STL under ``case_dir/triSurface/``.

    Mirrors the case-insensitive match in ``routes/geometry_render.py``
    (Codex round-1 P2 #1 fix on M-VIZ): ``glob("*.stl")`` would miss
    uploads named ``MODEL.STL`` since ``_safe_origin_filename``
    preserves the original casing.

    Round-2 Finding 1: resolves the chosen path strictly and asserts it
    stays under the case dir, so a symlink in ``triSurface/`` cannot
    redirect us to an arbitrary file outside IMPORTED_DIR.
    """
    triSurface = case_dir / "triSurface"
    if not triSurface.is_dir():
        raise GeometryRenderError(
            failing_check="no_source_stl",
            message=f"no triSurface/ under {case_dir}",
        )
    stls = sorted(p for p in triSurface.iterdir() if p.suffix.lower() == ".stl")
    if not stls:
        raise GeometryRenderError(
            failing_check="no_source_stl",
            message=f"no .stl under {triSurface}",
        )
    chosen = stls[0]
    try:
        resolved = chosen.resolve(strict=True)
        case_root = case_dir.resolve(strict=True)
        resolved.relative_to(case_root)
    except (FileNotFoundError, OSError, ValueError):
        raise GeometryRenderError(
            failing_check="no_source_stl",
            message=f"STL {chosen.name} resolved outside case dir",
        )
    return resolved


def _cache_target(case_dir: Path) -> Path:
    return case_dir / ".render_cache" / "geometry.glb"


def _is_cache_fresh(cache: Path, source: Path) -> bool:
    if not cache.exists():
        return False
    try:
        return cache.stat().st_mtime >= source.stat().st_mtime
    except FileNotFoundError:
        return False


def _atomic_write(target: Path, payload: bytes) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(
        f".tmp.{secrets.token_hex(4)}{target.suffix}"
    )
    tmp.write_bytes(payload)
    os.replace(tmp, target)


def _transcode_to_glb(source_stl: Path) -> bytes:
    """Run trimesh's STL→glb pipeline.

    trimesh raises various subclasses on parse failure (ValueError,
    LookupError, …). We collapse them to GeometryRenderError so the
    route layer has a single error class to map.
    """
    try:
        mesh = trimesh.load(source_stl, force="mesh")
    except Exception as exc:
        raise GeometryRenderError(
            failing_check="transcode_error",
            message=f"trimesh.load({source_stl.name}) failed: {exc!r}",
        )
    if mesh is None or getattr(mesh, "is_empty", False):
        raise GeometryRenderError(
            failing_check="transcode_error",
            message=f"trimesh produced empty mesh from {source_stl.name}",
        )
    try:
        glb = mesh.export(file_type="glb")
    except Exception as exc:
        raise GeometryRenderError(
            failing_check="transcode_error",
            message=f"trimesh.export(glb) failed: {exc!r}",
        )
    if not isinstance(glb, (bytes, bytearray)) or len(glb) < 4 or bytes(glb[:4]) != b"glTF":
        raise GeometryRenderError(
            failing_check="transcode_error",
            message="trimesh returned non-glb payload (missing 'glTF' magic)",
        )
    return bytes(glb)


def build_geometry_glb(case_id: str) -> GlbBuildResult:
    """Return the cached glb for ``case_id``, building it on cache miss.

    Public entrypoint for the route layer. Raises
    :class:`GeometryRenderError` on any failure path the route maps to
    4xx; lets unexpected exceptions propagate (route layer falls back
    to FastAPI's default 500 handler).
    """
    if not is_safe_case_id(case_id):
        raise GeometryRenderError(
            failing_check="case_not_found",
            message=f"unsafe case_id: {case_id!r}",
        )
    case_dir = _imported_case_dir(case_id)
    if not case_dir.is_dir():
        raise GeometryRenderError(
            failing_check="case_not_found",
            message=f"imported case dir missing: {case_dir}",
        )

    source_stl = _resolve_source_stl(case_dir)
    cache = _cache_target(case_dir)

    if _is_cache_fresh(cache, source_stl):
        return GlbBuildResult(cache_path=cache, status="hit")

    # Round-2 Finding 3: snapshot source mtime before transcode; if it
    # mutates during the rebuild, abort so the next request can rebuild
    # against the newer source rather than overwrite the cache with a
    # stale-but-fresh-mtimed payload.
    src_mtime_before = source_stl.stat().st_mtime_ns
    glb_bytes = _transcode_to_glb(source_stl)
    src_mtime_after = source_stl.stat().st_mtime_ns
    if src_mtime_after != src_mtime_before:
        raise GeometryRenderError(
            failing_check="transcode_error",
            message=(
                f"source {source_stl.name} mutated during transcode "
                "(retry the request)"
            ),
        )
    status: CacheStatus = "rebuild" if cache.exists() else "miss"
    _atomic_write(cache, glb_bytes)
    return GlbBuildResult(cache_path=cache, status=status)
