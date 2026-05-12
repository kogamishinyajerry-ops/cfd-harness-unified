"""Health checks on a loaded STL: watertight, bbox, unit-guess, shell count.

Honest categorization:
    - Watertight FAIL → ``errors`` (route rejects 4xx)
    - All-defaultFaces (no named solids) → ``warnings`` (UI inline help, user confirms)
    - Single-shell FAIL (multi-body STL) → ``warnings`` (M7 may need cell-zone setup)
    - Unit-guess UNKNOWN → ``warnings`` (user picks unit in editor)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import trimesh

from .unit_detector import GeometricUnit, detect_unit


UnitGuess = Literal["m", "mm", "in", "unknown"]

_UNIT_TO_GUESS: dict[GeometricUnit, UnitGuess] = {
    GeometricUnit.MM: "mm",
    GeometricUnit.M: "m",
    GeometricUnit.INCH: "in",
}


@dataclass(frozen=True, slots=True)
class PatchInfo:
    name: str
    face_count: int


@dataclass(frozen=True, slots=True)
class BodyAABB:
    """Axis-aligned bounding box of one named-solid body."""

    name: str
    min_xyz: tuple[float, float, float]
    max_xyz: tuple[float, float, float]

    @property
    def volume(self) -> float:
        dx = max(0.0, self.max_xyz[0] - self.min_xyz[0])
        dy = max(0.0, self.max_xyz[1] - self.min_xyz[1])
        dz = max(0.0, self.max_xyz[2] - self.min_xyz[2])
        return dx * dy * dz


@dataclass(frozen=True, slots=True)
class BodyPairOverlap:
    """One pair of named-solid bodies whose AABBs intersect with non-zero volume.

    Classification (session 11, F-NEW-26 defensive layer):
      - ``containment``: one AABB strictly contains the other (cavity /
        nested-obstacle pattern; valid for interior-obstacle CFD cases)
      - ``edge_overlap``: slice-shaped or partial intersection
        (classic F-NEW-26 thick-plate-at-face signature)
      - ``significant``: intersection volume ≥ 25% of smaller body's
        AABB volume (substantial overlap; mesh will almost certainly
        fail with PLC self-intersection)
    """

    name_a: str
    name_b: str
    intersection_min: tuple[float, float, float]
    intersection_max: tuple[float, float, float]
    classification: Literal["containment", "edge_overlap", "significant"]

    @property
    def volume(self) -> float:
        dx = max(0.0, self.intersection_max[0] - self.intersection_min[0])
        dy = max(0.0, self.intersection_max[1] - self.intersection_min[1])
        dz = max(0.0, self.intersection_max[2] - self.intersection_min[2])
        return dx * dy * dz


def _aabb_strictly_contains(outer: BodyAABB, inner: BodyAABB) -> bool:
    """Strict containment: outer's AABB encloses inner's on every axis."""
    return all(
        outer.min_xyz[i] <= inner.min_xyz[i] and inner.max_xyz[i] <= outer.max_xyz[i]
        for i in range(3)
    )


def detect_body_pair_overlaps(body_aabbs: list[BodyAABB]) -> list[BodyPairOverlap]:
    """Return all named-solid body pairs whose AABBs have non-zero intersection.

    F-NEW-26 defensive layer (session 11). The cross-repo ticket
    ``.planning/cross_repo_tickets/2026-05-12_case_003_build_cad_farfield_overlap.md``
    documents the upstream class-wide CAD construction bug this detects:
    Codex's `build_domain_patches` creates thick-plate boundary boxes
    at the 6 faces of a CFD domain cuboid, which necessarily overlap at
    the 12 edges + 8 corners. Without this check, the only feedback
    is an unhelpful HXT PLC error during M6 mesh generation, minutes
    after import.

    O(N²) AABB-intersection sweep. N ≤ ~20 in practice (industrial CAD
    has < 20 named bodies per case).
    """
    overlaps: list[BodyPairOverlap] = []
    n = len(body_aabbs)
    for i in range(n):
        for j in range(i + 1, n):
            a, b = body_aabbs[i], body_aabbs[j]
            int_min = tuple(max(a.min_xyz[k], b.min_xyz[k]) for k in range(3))
            int_max = tuple(min(a.max_xyz[k], b.max_xyz[k]) for k in range(3))
            if any(int_max[k] <= int_min[k] for k in range(3)):
                continue  # no AABB intersection
            int_vol = (
                (int_max[0] - int_min[0])
                * (int_max[1] - int_min[1])
                * (int_max[2] - int_min[2])
            )
            smaller_vol = min(a.volume, b.volume)
            if _aabb_strictly_contains(a, b) or _aabb_strictly_contains(b, a):
                clf: Literal["containment", "edge_overlap", "significant"] = "containment"
            elif smaller_vol > 0 and int_vol / smaller_vol >= 0.25:
                clf = "significant"
            else:
                clf = "edge_overlap"
            overlaps.append(
                BodyPairOverlap(
                    name_a=a.name,
                    name_b=b.name,
                    intersection_min=int_min,
                    intersection_max=int_max,
                    classification=clf,
                )
            )
    return overlaps


@dataclass(frozen=True, slots=True)
class IngestReport:
    is_watertight: bool
    bbox_min: tuple[float, float, float]
    bbox_max: tuple[float, float, float]
    bbox_extent: tuple[float, float, float]
    unit_guess: UnitGuess
    solid_count: int
    face_count: int
    is_single_shell: bool
    patches: list[PatchInfo] = field(default_factory=list)
    all_default_faces: bool = False
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @classmethod
    def from_parse_failure(cls, errors: list[str]) -> "IngestReport":
        zero3 = (0.0, 0.0, 0.0)
        return cls(
            is_watertight=False,
            bbox_min=zero3,
            bbox_max=zero3,
            bbox_extent=zero3,
            unit_guess="unknown",
            solid_count=0,
            face_count=0,
            is_single_shell=False,
            patches=[],
            all_default_faces=False,
            warnings=[],
            errors=list(errors),
        )


def _decision_to_guess(decision: GeometricUnit) -> UnitGuess:
    """Map ``unit_detector.GeometricUnit`` → ``UnitGuess`` API literal.

    ``CM`` and ``UNKNOWN`` collapse to ``"unknown"``: the API contract
    surfaces only mm/m/in to the workbench UI and falls back to manual
    pick otherwise.
    """
    return _UNIT_TO_GUESS.get(decision, "unknown")


def _legacy_bbox_band(max_extent: float) -> UnitGuess:
    """Single-band fallback when :func:`detect_unit` returns UNKNOWN with no
    body-class signal. Preserves naca0012 / ldc_box / cylinder UX where the
    bbox is ambiguous under multiple unit interpretations but the band
    heuristic picks a sensible default. Used ONLY when ``body_extents_raw``
    is absent (single-class load) — multi-class loads defer to
    :func:`detect_unit`'s "engineer must confirm" verdict.
    """
    if max_extent <= 0:
        return "unknown"
    if 1e-3 <= max_extent <= 10:
        return "m"
    if 10 < max_extent <= 250:
        return "in"
    if 250 < max_extent <= 1e5:
        return "mm"
    return "unknown"


def run_health_checks(
    *,
    combined: trimesh.Trimesh,
    solid_count: int,
    patches: list[PatchInfo],
    all_default_faces: bool,
    body_extents_raw: list[float] | None = None,
    body_aabbs: list[BodyAABB] | None = None,
) -> IngestReport:
    """Aggregate per-criterion checks into an ``IngestReport``.

    Caller (route or :func:`ingest_stl`) is responsible for combining a
    Scene to a single Trimesh via :func:`stl_loader.combine` and counting
    solids via :func:`stl_loader.solid_count` — done once per upload so
    the concat work isn't repeated by ``canonical_stl_bytes``.

    ``body_extents_raw`` (optional) is the list of per-body max bbox
    extents (raw STL units), used by :func:`detect_unit` to filter out
    CFD-domain bodies before deciding on a unit (F-NEW-12 fix wired
    through the route, V198 session 4). Omitting falls back to
    overall-bbox unit detection (legacy behavior, still correct on
    single-class payloads like APU bay).
    """
    bounds = combined.bounds
    bbox_min = (float(bounds[0][0]), float(bounds[0][1]), float(bounds[0][2]))
    bbox_max = (float(bounds[1][0]), float(bounds[1][1]), float(bounds[1][2]))
    bbox_extent = (
        bbox_max[0] - bbox_min[0],
        bbox_max[1] - bbox_min[1],
        bbox_max[2] - bbox_min[2],
    )
    is_watertight = bool(combined.is_watertight)
    is_single_shell = int(combined.body_count) == 1
    face_count = int(combined.faces.shape[0])
    unit_decision = detect_unit(
        bbox_max_extent_raw=max(bbox_extent),
        body_extents_raw=body_extents_raw,
    )
    unit_guess = _decision_to_guess(unit_decision.decision)
    # Fallback: single-class loads (no body_extents_raw) often have bbox
    # plausible under multiple units → detect_unit returns UNKNOWN. The
    # legacy band heuristic picks a sensible default in that regime so we
    # don't regress naca0012/cylinder/ldc_box UX. Multi-class loads always
    # defer to detect_unit (engineer-confirms is correct UX there).
    if unit_guess == "unknown" and not body_extents_raw:
        unit_guess = _legacy_bbox_band(max(bbox_extent))

    errors: list[str] = []
    warnings: list[str] = []

    if not is_watertight:
        errors.append(
            "STL is not watertight — open edges or non-manifold faces present. "
            "Heal the geometry in the source CAD before re-uploading."
        )
    if all_default_faces:
        warnings.append(
            "STL has no named solids; all faces will land on a single "
            "'defaultFaces' patch. Re-export with named solids per "
            "inlet/outlet/wall to enable per-patch boundary conditions."
        )
    if not is_single_shell:
        warnings.append(
            f"STL contains {int(combined.body_count)} disconnected bodies; "
            "M7 mesh generation may need explicit cell-zone setup."
        )
    if unit_guess == "unknown":
        warnings.append(
            f"Unit could not be guessed from bbox extent {max(bbox_extent):.4g}; "
            "set the unit explicitly in the case editor."
        )

    # F-NEW-26 defensive layer (session 11): detect overlapping named-solid
    # AABBs at import time. Without this, case_003-style source-CAD overlap
    # only surfaces as an unhelpful HXT PLC error during M6 mesh generation.
    # See cross-repo ticket: .planning/cross_repo_tickets/2026-05-12_case_003_build_cad_farfield_overlap.md
    if body_aabbs and len(body_aabbs) >= 2:
        overlap_pairs = detect_body_pair_overlaps(body_aabbs)
        edge_overlaps = [o for o in overlap_pairs if o.classification == "edge_overlap"]
        significant_overlaps = [
            o for o in overlap_pairs if o.classification == "significant"
        ]
        # Containment is the cavity / interior-obstacle pattern — valid;
        # surfaces silently to preserve LDC / cylinder-in-channel UX.

        if significant_overlaps:
            pairs_str = "; ".join(
                f"{o.name_a} ∩ {o.name_b}" for o in significant_overlaps
            )
            errors.append(
                f"Named-solid bodies have substantial AABB overlap "
                f"(≥25% of smaller body's volume): {pairs_str}. This is a "
                f"source-CAD construction defect — bodies must not overlap. "
                f"See .planning/cross_repo_tickets/"
                f"2026-05-12_case_003_build_cad_farfield_overlap.md for the "
                f"class-wide diagnosis and fix options."
            )
        elif len(edge_overlaps) >= 3:
            # Three or more edge overlaps = systematic CAD bug (F-NEW-26
            # case_003 had 13). One or two could be coincidental (shared
            # corner during legitimate assembly), so we only hard-reject
            # at the systematic threshold.
            pairs_str = "; ".join(
                f"{o.name_a} ∩ {o.name_b}" for o in edge_overlaps[:5]
            )
            more = (
                f" (+{len(edge_overlaps) - 5} more)"
                if len(edge_overlaps) > 5
                else ""
            )
            errors.append(
                f"Named-solid bodies have {len(edge_overlaps)} edge AABB "
                f"overlaps (≥3 = F-NEW-26 systematic CAD bug signature): "
                f"{pairs_str}{more}. M6 mesh generation will fail with PLC "
                f"self-intersection errors. See .planning/cross_repo_tickets/"
                f"2026-05-12_case_003_build_cad_farfield_overlap.md."
            )
        elif edge_overlaps:
            pairs_str = "; ".join(
                f"{o.name_a} ∩ {o.name_b}" for o in edge_overlaps
            )
            warnings.append(
                f"Named-solid bodies have edge AABB overlap: {pairs_str}. "
                f"This may produce PLC self-intersection errors during M6 "
                f"mesh generation if the overlap is geometric (not just "
                f"AABB-level shared corner)."
            )

    return IngestReport(
        is_watertight=is_watertight,
        bbox_min=bbox_min,
        bbox_max=bbox_max,
        bbox_extent=bbox_extent,
        unit_guess=unit_guess,
        solid_count=solid_count,
        face_count=face_count,
        is_single_shell=is_single_shell,
        patches=list(patches),
        all_default_faces=all_default_faces,
        warnings=warnings,
        errors=errors,
    )
