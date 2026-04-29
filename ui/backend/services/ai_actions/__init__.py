"""AI-action wrappers that return the M-AI-COPILOT envelope shape.

Spec_v2 §A3 of DEC-V61-098. Each AI action in this package:

1. Reads ``face_annotations.yaml`` to learn user-authoritative
   decisions made in prior dialog turns.
2. Performs its native action (call into the underlying service —
   e.g., ``setup_ldc_bc`` for ``setup_bc_with_annotations``).
3. Returns an ``AIActionEnvelope`` carrying:
   - ``confidence`` ∈ {confident, uncertain, blocked}
   - ``unresolved_questions`` for the dialog panel
   - ``annotations_revision_consumed`` and ``annotations_revision_after``
     for the frontend's stale-run guard.

Tier-A scope: only ``setup_bc_with_annotations`` is implemented. The
LDC fixture path (``setup_ldc_bc``) is the only concrete action; the
``force_uncertain`` / ``force_blocked`` flags allow the frontend to
dogfood the dialog flow without requiring a real arbitrary-STL AI
classifier (deferred to M9 Tier-B AI per the long-horizon roadmap).
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from ui.backend.schemas.ai_action import AIActionEnvelope, UnresolvedQuestion
from ui.backend.services.ai_actions.classifier import (
    ClassificationResult,
    classify_setup_bc,
)
from ui.backend.services.case_annotations import (
    AnnotationsIOError,
    load_annotations,
)
from ui.backend.services.case_solve.bc_setup import (
    BCSetupError,
    BCSetupResult,
    setup_ldc_bc,
)

__all__ = [
    "AIActionError",
    "setup_bc_with_annotations",
]


class AIActionError(Exception):
    """Raised when an AI action's underlying service fails in a way
    that should propagate to the route as a non-200 response (i.e., a
    real infrastructure / input failure, NOT a normal blocked/uncertain
    envelope outcome).
    """

    def __init__(self, message: str, *, failing_check: str) -> None:
        super().__init__(message)
        self.failing_check = failing_check


def _ldc_dialog_questions(
    *, force_blocked: bool, force_uncertain: bool
) -> list[UnresolvedQuestion]:
    """The Tier-A demo dialog questions for forced LDC scenarios.

    Dogfooding scenario (per spec_v2 §D): user clicks `[AI 处理]` on
    Step 3 with ``?force_uncertain=1``; backend returns 'uncertain'
    with one face_label question so the engineer can practice the
    dialog flow without needing real arbitrary-STL ambiguity.
    """
    if not (force_blocked or force_uncertain):
        return []
    return [
        UnresolvedQuestion(
            id="lid_orientation",
            kind="face_label",
            prompt=(
                "Confirm which face is the moving lid (default: top, +z). "
                "Click the lid face in the 3D viewport to confirm or "
                "select a different face."
            ),
            needs_face_selection=True,
            default_answer=None,
        ),
    ]


def setup_bc_with_annotations(
    *,
    case_dir: Path,
    case_id: str,
    force_uncertain: bool = False,
    force_blocked: bool = False,
    use_classifier: bool = True,
) -> AIActionEnvelope:
    """Run setup-bc with annotation-aware envelope return.

    Two operating modes:

    1. **Force flags** (``force_uncertain`` or ``force_blocked``):
       legacy DEC-V61-098 dogfood path. Returns the canned LDC dialog
       question for engineer practice without running the classifier.
       These flags take precedence over the classifier.

    2. **Real classifier** (``use_classifier=True``, default since
       DEC-V61-100 M9 Step 2 · no force flags set): consults
       :func:`classify_setup_bc` to inspect the polyMesh geometry
       + existing user_authoritative annotations and decides whether
       the answer is confident, uncertain, or blocked. If confident,
       runs the underlying ``setup_ldc_bc``; if not, returns the
       classifier's questions immediately.

    Reads ``face_annotations.yaml`` BEFORE the action so the AI can
    honor any user-authoritative entries from prior dialog turns —
    M9 Step 2 makes that loop close: the classifier reads the
    annotations and skips re-asking questions about pinned faces.

    Args:
        case_dir: the host case directory.
        case_id: the case identifier.
        force_uncertain: if true, return ``confidence='uncertain'``
            with one mock dialog question (DEC-V61-098 dogfood path).
        force_blocked: if true, return ``confidence='blocked'`` with
            one mock dialog question (DEC-V61-098 dogfood path).
            Mutually exclusive with ``force_uncertain``;
            ``force_blocked`` wins if both are passed.
        use_classifier: when true (default since DEC-V61-100), the
            geometric classifier is invoked when no force flag is set.
            Passing ``False`` reverts to the Tier-A confident-only
            behavior — used by tests that need the legacy contract,
            and by the LDC dogfood path that doesn't want classifier
            second-guessing.

    Returns:
        ``AIActionEnvelope`` describing the outcome.

    Raises:
        AIActionError: if the underlying ``setup_ldc_bc`` failed
            for an infrastructure reason (the route maps these to
            HTTP 4xx/5xx). NOT raised for blocked/uncertain envelope
            outcomes — those return normally via the envelope.
    """
    # Read the current annotations to populate revision tracking.
    # Annotations file may not exist on first call; load_annotations
    # returns an empty doc with revision=0 in that case.
    try:
        annotations = load_annotations(case_dir, case_id=case_id)
    except AnnotationsIOError as exc:
        raise AIActionError(
            f"could not load annotations: {exc}",
            failing_check=exc.failing_check,
        ) from exc

    revision_before = annotations["revision"]

    # If forced into a non-confident state for dogfood, short-circuit
    # BEFORE running the underlying setup OR the classifier.
    if force_blocked:
        return AIActionEnvelope(
            confidence="blocked",
            summary=(
                "AI cannot proceed without your confirmation. Please "
                "answer the questions below."
            ),
            annotations_revision_consumed=revision_before,
            annotations_revision_after=revision_before,
            unresolved_questions=_ldc_dialog_questions(
                force_blocked=True, force_uncertain=False
            ),
        )

    # M9 Step 2: consult the geometric classifier BEFORE running the
    # underlying setup. If it returns blocked/uncertain, surface that
    # immediately and don't write any dicts — the engineer answers
    # the question(s) via the dialog, the resume PUTs annotations, and
    # the next envelope call will (ideally) be confident.
    if use_classifier and not force_uncertain:
        cls: ClassificationResult = classify_setup_bc(
            case_dir, annotations=annotations
        )
        if cls.confidence != "confident":
            return AIActionEnvelope(
                confidence=cls.confidence,
                summary=cls.summary,
                annotations_revision_consumed=revision_before,
                annotations_revision_after=revision_before,
                unresolved_questions=cls.questions,
                next_step_suggestion=(
                    "Click [继续 AI 处理] after answering the question(s)."
                    if cls.confidence == "uncertain"
                    else None
                ),
            )

    # Run the underlying setup-bc.
    try:
        result: BCSetupResult = setup_ldc_bc(case_dir, case_id=case_id)
    except BCSetupError as exc:
        raise AIActionError(
            str(exc), failing_check="setup_bc_failed"
        ) from exc

    if force_uncertain:
        return AIActionEnvelope(
            confidence="uncertain",
            summary=(
                f"Set up LDC defaults: lid={result.n_lid_faces} faces, "
                f"walls={result.n_wall_faces} faces. Please confirm "
                f"the lid orientation."
            ),
            annotations_revision_consumed=revision_before,
            annotations_revision_after=revision_before,
            unresolved_questions=_ldc_dialog_questions(
                force_blocked=False, force_uncertain=True
            ),
            next_step_suggestion=(
                "After confirming, click [继续 AI 处理] to re-run."
            ),
        )

    # Confident path.
    return AIActionEnvelope(
        confidence="confident",
        summary=(
            f"Set up LDC defaults: lid={result.n_lid_faces} faces, "
            f"walls={result.n_wall_faces} faces. Reynolds={result.reynolds}."
        ),
        annotations_revision_consumed=revision_before,
        annotations_revision_after=revision_before,
        next_step_suggestion="Proceed to Step 4 (Solve).",
    )
