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
