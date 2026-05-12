"""Geometry surgery for industrial STL pre-meshing.

Codifies the APU bay v14 pattern (artifact A3 per DEC-V61-198):
sHM is fragile on industrial CAD output that has (a) over-dense
triangulation from CATIA/NX exports (50k-500k faces per body) and
(b) sub-millimeter gaps between adjacent bodies that should mate.
Two fixes:

1. **Tiered decimation** — different body classes get different
   face-count budgets (an APU compressor body keeps more curvature
   than a flat firewall plate).
2. **Axial stretch** — a thin shell that should seal against
   another part can be linearly stretched along one axis around a
   pivot, closing the gap without distorting other axes.

Public API is two pure functions on ``trimesh.Trimesh``:
:func:`decimate_to_tier` and :func:`axial_stretch`. Plus
:func:`apply_surgery` as a one-shot orchestrator that takes a
per-body tier mapping + per-body stretch spec.

Backend selection for decimation:

- Prefers ``fast_simplification`` (10-100× faster than trimesh
  fallback on 500k-face inputs; what APU bay used).
- Falls back to trimesh's ``simplify_quadric_decimation`` (which
  requires pyfqmr) if fast_simplification isn't available.
- Raises ``DecimationBackendUnavailable`` with install hint if
  neither is present.

I/O (read STL, write STL) is the caller's responsibility — these
functions operate on in-memory meshes.

Reference case: ~/Desktop/apu-bay-ventilation/scripts/01b_optimize_geom.py
V-series: V8 (mesh skewness from over-dense triangulation +
narrow gaps).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import numpy as np
import trimesh


class DecimationBackendUnavailable(RuntimeError):
    """Neither fast_simplification nor trimesh+pyfqmr is importable."""


@dataclass(frozen=True)
class TierSpec:
    """Decimation budget for one body class.

    ``keep_ratio`` is the target face-count ratio; the result is
    clamped to ``[min_faces, max_faces]`` so that very small
    bodies don't get pulverized and very large ones don't keep
    100k+ faces just because their input was huge.

    ``min_to_decimate`` is a skip threshold: bodies smaller than
    this don't get touched (decimation overhead exceeds benefit).
    """

    keep_ratio: float
    min_faces: int
    max_faces: int
    min_to_decimate: int = 8000


@dataclass(frozen=True)
class AxialStretchSpec:
    """Linear stretch along one axis around a pivot.

    ``axis`` is "x", "y", or "z". ``center`` is the pivot
    coordinate in the same units as the mesh vertices (mm if mesh
    is mm, m if mesh is m — the function is unit-agnostic).
    ``factor`` is the multiplicative stretch (1.008 = 0.8% growth).
    """

    axis: str
    center: float
    factor: float


def decimate_to_tier(mesh: trimesh.Trimesh, tier: TierSpec) -> trimesh.Trimesh:
    """Reduce face count per ``tier``. Returns a new mesh.

    Returns the input unchanged if face count is below
    ``tier.min_to_decimate`` or if the computed target is greater
    than the current count.
    """
    n_before = len(mesh.faces)
    if n_before < tier.min_to_decimate:
        return mesh

    target = int(n_before * tier.keep_ratio)
    target = max(tier.min_faces, min(tier.max_faces, target))
    if target >= n_before:
        return mesh

    try:
        import fast_simplification as _fs

        verts_new, faces_new = _fs.simplify(
            mesh.vertices.astype(np.float64),
            mesh.faces.astype(np.int32),
            target_count=target,
            agg=10.0,
        )
        return trimesh.Trimesh(
            vertices=verts_new,
            faces=faces_new,
            process=False,
        )
    except ImportError:
        pass

    try:
        return mesh.simplify_quadric_decimation(target)
    except (ImportError, AttributeError, ValueError) as exc:
        raise DecimationBackendUnavailable(
            "Decimation requires either `fast_simplification` "
            "(`.venv/bin/pip install fast-simplification`) or "
            "`pyfqmr` (`.venv/bin/pip install pyfqmr`); neither "
            "is importable. Original error: " + str(exc)
        ) from exc


def axial_stretch(mesh: trimesh.Trimesh, spec: AxialStretchSpec) -> trimesh.Trimesh:
    """Linearly stretch along one axis around a pivot. Returns new mesh.

    Other two axes are untouched. Faces are unchanged (vertex
    re-indexing only).
    """
    axis_idx = {"x": 0, "y": 1, "z": 2}.get(spec.axis)
    if axis_idx is None:
        raise ValueError(f"axis must be 'x', 'y', or 'z'; got {spec.axis!r}")
    if not np.isfinite(spec.factor) or spec.factor <= 0:
        raise ValueError(f"factor must be positive finite; got {spec.factor!r}")

    verts = mesh.vertices.copy()
    verts[:, axis_idx] = spec.center + (verts[:, axis_idx] - spec.center) * spec.factor
    return trimesh.Trimesh(vertices=verts, faces=mesh.faces, process=False)


def apply_surgery(
    meshes: Mapping[str, trimesh.Trimesh],
    *,
    tiers: Mapping[str, TierSpec],
    stretches: Mapping[str, AxialStretchSpec] | None = None,
) -> dict[str, trimesh.Trimesh]:
    """Apply decimation + optional stretch to each named mesh.

    Args:
        meshes: ``body_name -> trimesh`` mapping. Each input mesh
            is treated read-only; a new ``Trimesh`` is returned per
            entry.
        tiers: ``body_name -> TierSpec`` mapping. A body without an
            entry is passed through unchanged.
        stretches: optional ``body_name -> AxialStretchSpec``;
            applied AFTER decimation if present.

    Returns:
        A new dict mapping the same body names to surgery-applied
        meshes. Missing-tier bodies appear in the result unchanged.
    """
    stretches = stretches or {}
    out: dict[str, trimesh.Trimesh] = {}
    for name, mesh in meshes.items():
        m = mesh
        tier = tiers.get(name)
        if tier is not None:
            m = decimate_to_tier(m, tier)
        stretch = stretches.get(name)
        if stretch is not None:
            m = axial_stretch(m, stretch)
        out[name] = m
    return out


# Reference tier presets matching APU bay v14 (DEC-V61-198 A3 source).
# These are *examples* — production callers should define their own
# tiers based on the case's body taxonomy. Re-exporting them here so
# tests + future callers have a recognized starting point.

TIER_APU_BODY = TierSpec(keep_ratio=0.25, min_faces=1500, max_faces=12000)
"""Curved high-feature bodies (compressor, combustor, exhaust shells)."""

TIER_THIN_SHELL = TierSpec(keep_ratio=0.40, min_faces=2000, max_faces=15000)
"""Thin walls (firewalls, outer shell, inner shell)."""

TIER_STRUCTURE = TierSpec(keep_ratio=0.30, min_faces=1000, max_faces=8000)
"""Structural frames + beams (mostly flat plate-like)."""


__all__ = [
    "AxialStretchSpec",
    "DecimationBackendUnavailable",
    "TierSpec",
    "TIER_APU_BODY",
    "TIER_STRUCTURE",
    "TIER_THIN_SHELL",
    "apply_surgery",
    "axial_stretch",
    "decimate_to_tier",
]
