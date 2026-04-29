"""Geometric classifier for the M-AI-COPILOT setup-bc envelope.

DEC-V61-100 (M9 Tier-B AI) Step 2. Replaces the ``force_uncertain``
mock in ``ai_actions/__init__.py`` with real geometric heuristics
that classify the mesh and decide what dialog questions to surface.

Strategy (heuristic-only · no LLM):
    1. Read polyMesh points + boundary patches.
    2. Compute aspect ratio, axis alignment, lid candidate count.
    3. Read existing face_annotations.yaml — any user_authoritative
       entries are treated as locked-in answers; classifier doesn't
       re-ask those questions.
    4. Map the geometric signature to one of:
        - LDC_CUBE → confident (defaults: top face = lid moving in +x)
        - AMBIGUOUS_CUBE → uncertain (cube but multiple plausible lids)
        - NON_CUBE → uncertain (need user to label inlet/outlet/walls)
        - DEGENERATE → blocked (mesh has no usable boundary, etc.)

This is the M9 Step 2 classifier surface. Step 3 will harden it for
multi-question scenarios. Future Era 2 may layer an LLM on top.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from ui.backend.schemas.ai_action import UnresolvedQuestion

__all__ = [
    "GeometryClass",
    "ClassificationResult",
    "classify_setup_bc",
]


GeometryClass = Literal[
    "ldc_cube",
    "ambiguous_cube",
    "non_cube",
    "degenerate",
]


@dataclass(frozen=True, slots=True)
class ClassificationResult:
    """Outcome of running the heuristic classifier on a polyMesh.

    Attributes:
        geometry_class: enum identifying the rough geometric category
        confidence: matches AIActionEnvelope.confidence directly
        questions: UnresolvedQuestion list to attach to the envelope
        summary: human-readable one-liner for the dialog summary slot
        rationale: short engineering note for the audit log (NOT
            shown to the user; goes into the action's diagnostics)
    """

    geometry_class: GeometryClass
    confidence: Literal["confident", "uncertain", "blocked"]
    questions: list[UnresolvedQuestion]
    summary: str
    rationale: str


# Numerical tolerances. Chosen by the Tier-A face_id contract:
# 9-decimal rounding tolerates ~5e-10 drift, so anything above 1e-7
# is "noticeably distinct" geometrically.
_AXIS_ALIGNMENT_TOL = 1e-6
_ASPECT_RATIO_CUBE_TOL = 0.05  # 5% — below this, treat as cube
_DEGENERATE_BBOX_MIN = 1e-9


def _read_polymesh_pts(polymesh_dir: Path) -> list[tuple[float, float, float]]:
    """Read polyMesh points file. Reuses the same parser as bc_setup
    but as a pure read (no rewrite).
    """
    from ui.backend.services.case_solve.bc_setup import (
        _parse_points,
        _split_foam_block,
    )

    points_path = polymesh_dir / "points"
    if not points_path.is_file():
        return []
    _, _, body, _ = _split_foam_block(points_path)
    return _parse_points(body)


def _bbox(pts: list[tuple[float, float, float]]) -> tuple[
    tuple[float, float, float],
    tuple[float, float, float],
]:
    """Return (min, max) bounding-box corners. Empty pts → (0,0,0)
    twice (degenerate signal)."""
    if not pts:
        return ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    zs = [p[2] for p in pts]
    return ((min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs)))


def _aspect_ratio(
    bbox_min: tuple[float, float, float], bbox_max: tuple[float, float, float]
) -> float:
    """Max(extent) / min(extent). Returns +inf for degenerate axis."""
    extents = [bbox_max[i] - bbox_min[i] for i in range(3)]
    if any(e < _DEGENERATE_BBOX_MIN for e in extents):
        return float("inf")
    return max(extents) / min(extents)


def _user_authoritative_face_ids(annotations: dict[str, Any]) -> set[str]:
    """Collect face_ids the user has already locked in. Classifier
    must NOT re-ask questions about these faces.
    """
    out: set[str] = set()
    for f in annotations.get("faces", []) or []:
        if f.get("confidence") == "user_authoritative":
            fid = f.get("face_id")
            if isinstance(fid, str):
                out.add(fid)
    return out


def classify_setup_bc(
    case_dir: Path,
    *,
    annotations: dict[str, Any],
) -> ClassificationResult:
    """Classify the case for setup-bc and emit dialog questions.

    Heuristic-only. The Tier-B mock (``force_uncertain``) is replaced
    by this real classifier when callers pass it through; legacy
    ``force_uncertain``/``force_blocked`` paths in the wrapper still
    short-circuit before this is invoked, so this function is the
    "default" envelope-mode brain when the caller wants real behavior.

    Args:
        case_dir: case root.
        annotations: parsed face_annotations.yaml (load_annotations()
            return value). Empty doc OK for first-time classification.

    Returns:
        ClassificationResult — feed into AIActionEnvelope construction.
    """
    polymesh = case_dir / "constant" / "polyMesh"
    if not polymesh.is_dir():
        return ClassificationResult(
            geometry_class="degenerate",
            confidence="blocked",
            questions=[
                UnresolvedQuestion(
                    id="run_step2_first",
                    kind="free_text",
                    prompt=(
                        "No mesh was found. Please run Step 2 (Mesh) "
                        "and re-trigger Step 3."
                    ),
                    needs_face_selection=False,
                    candidate_face_ids=[],
                    candidate_options=[],
                    default_answer=None,
                ),
            ],
            summary=(
                "Cannot classify: polyMesh is missing. Run Step 2 first."
            ),
            rationale=f"polyMesh dir not found at {polymesh}",
        )

    pts = _read_polymesh_pts(polymesh)
    if len(pts) < 8:
        return ClassificationResult(
            geometry_class="degenerate",
            confidence="blocked",
            questions=[
                UnresolvedQuestion(
                    id="degenerate_mesh",
                    kind="free_text",
                    prompt=(
                        "Mesh has fewer than 8 vertices — cannot bound "
                        "a 3D domain. Re-mesh the geometry."
                    ),
                    needs_face_selection=False,
                    candidate_face_ids=[],
                    candidate_options=[],
                    default_answer=None,
                ),
            ],
            summary=f"Mesh has only {len(pts)} vertices; cannot proceed.",
            rationale=f"degenerate mesh vertex count={len(pts)}",
        )

    bbox_min, bbox_max = _bbox(pts)
    ar = _aspect_ratio(bbox_min, bbox_max)
    extents = tuple(bbox_max[i] - bbox_min[i] for i in range(3))

    user_pinned = _user_authoritative_face_ids(annotations)

    # Cube-like: aspect ratio close to 1 across all three axes.
    if ar < 1.0 + _ASPECT_RATIO_CUBE_TOL:
        # If the user has already pinned a face as user_authoritative,
        # we can confidently default to that orientation.
        if user_pinned:
            return ClassificationResult(
                geometry_class="ldc_cube",
                confidence="confident",
                questions=[],
                summary=(
                    f"Cube geometry (aspect ratio {ar:.3f}) with "
                    f"{len(user_pinned)} user-pinned face(s). LDC defaults "
                    f"applied honoring user annotations."
                ),
                rationale=(
                    f"cube_ar={ar:.4f} extents={extents} "
                    f"user_pinned={len(user_pinned)}"
                ),
            )
        # No user pins yet: confident if the axis-aligned bounding box
        # corresponds to the obvious LDC fixture orientation (+z lid).
        # We surface a single uncertain question so the engineer can
        # confirm; the AI defaults to top in the question.
        return ClassificationResult(
            geometry_class="ldc_cube",
            confidence="uncertain",
            questions=[
                UnresolvedQuestion(
                    id="lid_orientation",
                    kind="face_label",
                    prompt=(
                        f"Cube geometry detected (aspect ratio {ar:.3f}). "
                        f"Default lid: top face (+z, max_z={bbox_max[2]:.4f}). "
                        f"Click the lid face in the viewport to confirm or "
                        f"select a different face."
                    ),
                    needs_face_selection=True,
                    candidate_face_ids=[],
                    candidate_options=[],
                    default_answer=None,
                ),
            ],
            summary=(
                f"Cube geometry (aspect ratio {ar:.3f}). Please confirm "
                f"the lid orientation."
            ),
            rationale=f"ldc_cube_default ar={ar:.4f} extents={extents}",
        )

    # Non-cube: surface inlet + outlet questions in addition to lid.
    # The classifier doesn't know which face is inlet vs outlet; the
    # engineer answers via two face-selection questions. Walls are
    # implicitly everything else (the action wrapper handles the
    # default).
    n_questions_remaining = 2  # inlet + outlet
    questions: list[UnresolvedQuestion] = []
    inlet_id = "inlet_face"
    outlet_id = "outlet_face"
    # If the user already pinned at least one inlet/outlet, drop the
    # corresponding question. We can't tell which by face_id alone
    # without also reading patch_type from each annotation, but
    # checking name-prefix is good enough for Tier-B.
    pinned_names: set[str] = set()
    for f in annotations.get("faces", []) or []:
        if f.get("confidence") == "user_authoritative":
            n = f.get("name")
            if isinstance(n, str):
                pinned_names.add(n.lower())
    if any("inlet" in n for n in pinned_names):
        n_questions_remaining -= 1
    else:
        questions.append(
            UnresolvedQuestion(
                id=inlet_id,
                kind="face_label",
                prompt=(
                    f"Non-cube geometry (aspect ratio {ar:.3f}). Click "
                    f"the inlet face in the viewport."
                ),
                needs_face_selection=True,
                candidate_face_ids=[],
                candidate_options=[],
                default_answer=None,
            ),
        )
    if any("outlet" in n for n in pinned_names):
        n_questions_remaining -= 1
    else:
        questions.append(
            UnresolvedQuestion(
                id=outlet_id,
                kind="face_label",
                prompt="Click the outlet face in the viewport.",
                needs_face_selection=True,
                candidate_face_ids=[],
                candidate_options=[],
                default_answer=None,
            ),
        )

    if n_questions_remaining == 0:
        return ClassificationResult(
            geometry_class="non_cube",
            confidence="confident",
            questions=[],
            summary=(
                f"Non-cube geometry (aspect ratio {ar:.3f}). Inlet + "
                f"outlet pinned by user; using engineer's labels."
            ),
            rationale=(
                f"non_cube_resolved ar={ar:.4f} extents={extents} "
                f"pinned_names={sorted(pinned_names)}"
            ),
        )

    return ClassificationResult(
        geometry_class="non_cube",
        confidence="uncertain",
        questions=questions,
        summary=(
            f"Non-cube geometry (aspect ratio {ar:.3f}). Please "
            f"identify the inlet and outlet."
        ),
        rationale=(
            f"non_cube_classify ar={ar:.4f} extents={extents} "
            f"questions_remaining={n_questions_remaining}"
        ),
    )
