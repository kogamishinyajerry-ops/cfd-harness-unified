"""Pre-meshing thin-wall patch loss advisor (Pillar 2 falsification).

Surfaced by industrial-case run-and-correct loop (DEC-V61-198):
case_002a V10 (sHM ate 6 Frame patches + beam_3 in level [1,2] on a
50 mm thick beam) and case_002b CHT inherits the same loss without
the original engineer noticing — V10 is a real, repeated trap, not
a one-off.

This advisor runs **before** snappyHexMesh: given per-patch geometry
+ per-patch refinement levels + the background cell size, it warns
when a patch's effective cell size at its assigned refinement level
is coarser than the patch's thinnest dimension. sHM merging both
opposing surfaces into the same cell is the root cause of patch
loss; warning before meshing prevents the day-long "why is my BC
patch missing" debugging cycle.

Companion to the post-meshing `mesh_quality.advisor` — that one
reads the checkMesh log; this one reads only `case.yaml` + STL bbox
and runs in seconds.

Heuristic (v1):
  - Thinness estimator = smallest dimension of axis-aligned bounding
    box (works for plate / beam / frame; approximate for curved
    shells where bbox-min may overestimate thickness).
  - Effective cell size = background_cell_size / 2^level_max.
  - Warn when effective_cell_size > thickness / min_cells_per_thickness.
  - Recommended level = ceil(log2(background_cell_size / target_cell_size))
    where target_cell_size = thickness / min_cells_per_thickness.

Output is **read-only metadata** — the advisor returns warnings as
data; no mutating route is invoked (V130 advisory-only / V132
contract). The engineer reads the warning and decides whether to
bump the refinement level in `case.yaml.mesh.refinement`.

Reference: V10 finding in `industrial_case_solver_findings.md`.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping, Sequence


@dataclass(frozen=True)
class PatchGeometry:
    """One patch's geometry slice for thinness analysis.

    ``name`` matches the patch name in the multi-solid STL and in
    ``case.yaml.mesh.refinement.<name>`` and
    ``case.yaml.bc_values.<name>``.

    ``bbox_dimensions`` is a 3-tuple of axis-aligned bounding-box
    extents in **mesh-native units** (m if the case is in m, mm if
    in mm — the advisor is unit-agnostic; ``background_cell_size``
    must use the same unit).
    """

    name: str
    bbox_dimensions: tuple[float, float, float]


@dataclass(frozen=True)
class ThinWallWarning:
    """One advisor finding for a patch at risk of sHM loss.

    Fields are intended for direct rendering: ``message`` is the
    engineer-readable summary; the structured fields are present so
    UI / CLI / RAG corpus loaders can format consistently.
    """

    patch_name: str
    estimated_thickness: float
    effective_cell_size: float
    cells_per_thickness: float
    assigned_level: tuple[int, int]
    recommended_level_max: int
    severity: str
    message: str


# Heuristic constants. min_cells_per_thickness < 2 is too aggressive
# (sHM frequently merges); > 4 is excessive (most thin walls are not
# load-bearing for the global flow). 2 is the sane default.
_DEFAULT_MIN_CELLS_PER_THICKNESS = 2

# Severity thresholds (relative to min_cells_per_thickness target):
#   - critical: cells_per_thickness < 1.0 (wall WILL be lost)
#   - warning : cells_per_thickness < min_cells_per_thickness (wall AT RISK)
#   - info    : cells_per_thickness < min_cells_per_thickness * 1.5 (marginal)
_SEVERITY_CRITICAL_RATIO = 1.0
_SEVERITY_INFO_RATIO_MULTIPLIER = 1.5


def detect_thin_wall_patches_at_risk(
    patches: Sequence[PatchGeometry],
    refinement_levels: Mapping[str, tuple[int, int]],
    background_cell_size: float,
    *,
    min_cells_per_thickness: int = _DEFAULT_MIN_CELLS_PER_THICKNESS,
) -> list[ThinWallWarning]:
    """Return warnings for patches likely to be eaten by sHM.

    Args:
        patches: list of :class:`PatchGeometry`. A patch missing
            from ``refinement_levels`` is silently skipped (caller
            owns assignment).
        refinement_levels: ``patch_name -> (level_min, level_max)``
            from ``case.yaml.mesh.refinement.<patch>``.
        background_cell_size: ``case.yaml.domain.background_cell_size``
            in the same units as ``patches[*].bbox_dimensions``.
        min_cells_per_thickness: minimum cells across the wall's
            thinnest dimension to consider it preserved. Default 2;
            increase to 3-4 for cases where wall heat conduction is
            load-bearing.

    Returns:
        Warnings sorted by ascending ``cells_per_thickness`` (most
        at-risk patches first). Empty list when no patch is at risk.

    Notes:
        Uses bounding-box-min as thickness estimator. This is exact
        for axis-aligned plate / beam geometry and a lower bound for
        curved shells (bbox of a curved shell can be much larger than
        its actual thickness, so the advisor will MISS some thin
        curved shells — false negative). It will NOT produce false
        positives in the bbox-min direction.
    """
    if background_cell_size <= 0 or not math.isfinite(background_cell_size):
        raise ValueError(
            f"background_cell_size must be positive finite; "
            f"got {background_cell_size!r}"
        )
    if min_cells_per_thickness < 1:
        raise ValueError(
            f"min_cells_per_thickness must be ≥ 1; "
            f"got {min_cells_per_thickness!r}"
        )

    warnings: list[ThinWallWarning] = []
    info_threshold_ratio = (
        min_cells_per_thickness * _SEVERITY_INFO_RATIO_MULTIPLIER
    )

    for patch in patches:
        levels = refinement_levels.get(patch.name)
        if levels is None:
            continue
        level_max = levels[1]
        if level_max < 0:
            continue

        thickness = min(patch.bbox_dimensions)
        if thickness <= 0 or not math.isfinite(thickness):
            continue

        effective_cell_size = background_cell_size / (2 ** level_max)
        cells_per_thickness = thickness / effective_cell_size

        if cells_per_thickness >= info_threshold_ratio:
            continue

        target_cell_size = thickness / min_cells_per_thickness
        recommended_level_max = max(
            level_max,
            math.ceil(math.log2(background_cell_size / target_cell_size)),
        )

        if cells_per_thickness < _SEVERITY_CRITICAL_RATIO:
            severity = "critical"
            verb = "WILL be merged by sHM"
        elif cells_per_thickness < min_cells_per_thickness:
            severity = "warning"
            verb = "is AT RISK of sHM merge"
        else:
            severity = "info"
            verb = "is marginal for sHM resolution"

        message = (
            f"patch {patch.name!r}: thickness ≈ {thickness:.4g} (bbox-min); "
            f"effective cell size at level {level_max} = "
            f"{effective_cell_size:.4g} → "
            f"{cells_per_thickness:.2f} cells per thickness → {verb}. "
            f"Recommended: bump refinement to level "
            f"{recommended_level_max} (≈{background_cell_size / 2**recommended_level_max:.4g} "
            f"cell size = {thickness / (background_cell_size / 2**recommended_level_max):.2f} "
            f"cells per thickness)."
        )

        warnings.append(
            ThinWallWarning(
                patch_name=patch.name,
                estimated_thickness=thickness,
                effective_cell_size=effective_cell_size,
                cells_per_thickness=cells_per_thickness,
                assigned_level=levels,
                recommended_level_max=recommended_level_max,
                severity=severity,
                message=message,
            )
        )

    warnings.sort(key=lambda w: w.cells_per_thickness)
    return warnings


__all__ = [
    "PatchGeometry",
    "ThinWallWarning",
    "detect_thin_wall_patches_at_risk",
]
