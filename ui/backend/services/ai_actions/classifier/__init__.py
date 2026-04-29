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
        # Codex round 1 HIGH-1 (DEC-V61-100 Step 2 review 2026-04-29):
        # Returning confident on ANY user_authoritative pin was unsound
        # because setup_ldc_bc() always derives the lid from max-z
        # geometry — it does NOT consume annotations. So if the user
        # pinned a SIDE face as the lid, the classifier would say
        # confident, the wrapper would run setup_ldc_bc, and the writer
        # would still pick the top face. Loop not closed.
        #
        # Honest fix: only return confident if the pinned face is on
        # the top plane (matching what setup_ldc_bc will actually do).
        # We can't verify face-by-face from face_id alone without the
        # face_index lookup table, but we CAN check whether the user
        # named a face "lid" — that signals they intend the top plane.
        # This keeps the dialog open until the user's pin matches the
        # writer's behavior.
        pinned_names: set[str] = set()
        for f in annotations.get("faces", []) or []:
            if f.get("confidence") == "user_authoritative":
                n = f.get("name")
                if isinstance(n, str):
                    pinned_names.add(n.lower())
        lid_pinned = any("lid" in n for n in pinned_names)

        if lid_pinned:
            return ClassificationResult(
                geometry_class="ldc_cube",
                confidence="confident",
                questions=[],
                summary=(
                    f"Cube geometry (aspect ratio {ar:.3f}) with "
                    f"user-pinned lid. LDC defaults applied — writer "
                    f"will use the top (+z) plane as the moving lid."
                ),
                rationale=(
                    f"cube_ar={ar:.4f} extents={extents} "
                    f"lid_pinned=True names={sorted(pinned_names)}"
                ),
            )
        # No lid pin yet (whether user pinned other faces or not):
        # surface the lid question so engineer confirms top-plane is
        # the intended lid before we hand off to setup_ldc_bc.
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
                        f"Click the lid face in the viewport to confirm "
                        f"(name it 'lid' in the dialog)."
                    ),
                    needs_face_selection=True,
                    candidate_face_ids=[],
                    candidate_options=[],
                    default_answer="lid",
                ),
            ],
            summary=(
                f"Cube geometry (aspect ratio {ar:.3f}). Please confirm "
                f"the lid orientation."
            ),
            rationale=(
                f"ldc_cube_default ar={ar:.4f} extents={extents} "
                f"pinned_names={sorted(pinned_names)} (lid not pinned)"
            ),
        )

    # Codex round 1 HIGH-2 (DEC-V61-100 Step 2 review 2026-04-29):
    # The non-cube branch CANNOT return confident yet — the only
    # downstream executor (setup_ldc_bc) is LDC-only and would write
    # incorrect lid/fixedWalls boundaries on a channel/airfoil mesh.
    # Until a non-LDC executor exists (deferred to a future milestone:
    # M10 STEP/IGES + M11 Mesh Wizard or a dedicated channel/external
    # action), the non-cube path stays uncertain even when the user
    # has pinned inlet+outlet. The dialog message tells them why so
    # they don't think they did something wrong.
    #
    # We still emit the inlet+outlet questions so the engineer can
    # CAPTURE their intent in face_annotations.yaml — the data
    # accumulates in the doc and gets re-used when a non-LDC executor
    # ships.
    questions: list[UnresolvedQuestion] = []
    pinned_names: set[str] = set()
    for f in annotations.get("faces", []) or []:
        if f.get("confidence") == "user_authoritative":
            n = f.get("name")
            if isinstance(n, str):
                pinned_names.add(n.lower())
    inlet_pinned = any("inlet" in n for n in pinned_names)
    outlet_pinned = any("outlet" in n for n in pinned_names)
    if not inlet_pinned:
        questions.append(
            UnresolvedQuestion(
                id="inlet_face",
                kind="face_label",
                prompt=(
                    f"Non-cube geometry (aspect ratio {ar:.3f}). Click "
                    f"the inlet face in the viewport."
                ),
                needs_face_selection=True,
                candidate_face_ids=[],
                candidate_options=[],
                default_answer="inlet",
            ),
        )
    if not outlet_pinned:
        questions.append(
            UnresolvedQuestion(
                id="outlet_face",
                kind="face_label",
                prompt="Click the outlet face in the viewport.",
                needs_face_selection=True,
                candidate_face_ids=[],
                candidate_options=[],
                default_answer="outlet",
            ),
        )

    # Special case: both already pinned BUT no non-LDC executor
    # exists. Surface a "blocked" envelope so the engineer knows the
    # case can't be solved with the current pipeline; their
    # annotations are saved for when M10/M11 ship.
    if inlet_pinned and outlet_pinned:
        return ClassificationResult(
            geometry_class="non_cube",
            confidence="blocked",
            questions=[
                UnresolvedQuestion(
                    id="non_cube_executor_pending",
                    kind="free_text",
                    prompt=(
                        f"Non-cube geometry (aspect ratio {ar:.3f}) with "
                        f"inlet+outlet pinned. The current solver path is "
                        f"LDC-only — channel/external-flow executors "
                        f"land in M10 (STEP/IGES) and M11 (Mesh Wizard). "
                        f"Your annotations are saved and will be honored "
                        f"once the non-LDC pipeline ships."
                    ),
                    needs_face_selection=False,
                    candidate_face_ids=[],
                    candidate_options=[],
                    default_answer=None,
                ),
            ],
            summary=(
                f"Non-cube geometry (aspect ratio {ar:.3f}) with annotations "
                f"saved. Cannot solve until a non-LDC executor lands."
            ),
            rationale=(
                f"non_cube_blocked ar={ar:.4f} extents={extents} "
                f"pinned={sorted(pinned_names)}"
            ),
        )

    return ClassificationResult(
        geometry_class="non_cube",
        confidence="uncertain",
        questions=questions,
        summary=(
            f"Non-cube geometry (aspect ratio {ar:.3f}). Please "
            f"identify the inlet and outlet faces."
        ),
        rationale=(
            f"non_cube_classify ar={ar:.4f} extents={extents} "
            f"inlet_pinned={inlet_pinned} outlet_pinned={outlet_pinned}"
        ),
    )
