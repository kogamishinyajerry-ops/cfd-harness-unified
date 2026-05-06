"""AI-action wrappers that return the M-AI-COPILOT envelope shape.

Spec_v2 §A3 of DEC-V61-098. Each AI action in this package:

1. Reads ``face_annotations.yaml`` to learn user-authoritative
   decisions made in prior dialog turns.
2. Performs CLASSIFICATION ONLY (DEC-V61-131 N1.1: envelope
   hard-strip — AI does NOT call BC mutation routines from the
   envelope branch).
3. Returns an ``AIActionEnvelope`` carrying:
   - ``confidence`` ∈ {confident, uncertain, blocked}
   - ``unresolved_questions`` for the dialog panel
   - ``annotations_revision_consumed`` and ``annotations_revision_after``
     for the frontend's stale-run guard.

DEC-V61-131 (N1.1) contract change: confident envelopes describe the
suggested action ("would set up LDC defaults: lid=N faces, walls=M
faces") but do NOT call ``setup_ldc_bc`` / ``setup_channel_bc``. The
engineer applies the suggestion by clicking ``[应用 AI 建议]`` in the UI,
which calls the legacy non-envelope ``POST /setup-bc`` route. This
enforces V130 Principle B at the backend layer (per Kogami P1 #2 close).
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

__all__ = [
    "AIActionError",
    "setup_bc_with_annotations",
]


class AIActionError(Exception):
    """Raised when an AI action's underlying read/classify pipeline
    fails in a way that should propagate to the route as a non-200
    response (i.e., a real infrastructure / input failure, NOT a normal
    blocked/uncertain envelope outcome).
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


def _summarize_ldc_suggestion(cls: ClassificationResult) -> str:
    """Compose the confident-LDC summary message describing what the
    engineer's apply click would do. The classifier already inspected
    the polyMesh boundary; we surface its head-counts but do NOT
    write any dicts.
    """
    # The classifier knows the LDC fixture's geometry but not the
    # exact face counts that would result from setup_ldc_bc — the
    # advisory message stays generic ("LDC defaults") rather than
    # quoting numbers we did not compute.
    return (
        "AI is confident this is an LDC cube. Click [应用 AI 建议] to "
        "set up icoFoam LDC defaults (lid + walls split, "
        "U_lid=1 m/s, Re=100)."
    )


def _summarize_channel_suggestion(cls: ClassificationResult) -> str:
    """Compose the confident-channel summary describing what apply
    would do. Mirrors `_summarize_ldc_suggestion` for the non_cube
    geometry class.
    """
    n_inlet = len(cls.inlet_face_ids)
    n_outlet = len(cls.outlet_face_ids)
    return (
        f"AI is confident this is a channel-style geometry "
        f"(inlet pins: {n_inlet}, outlet pins: {n_outlet}). Click "
        f"[应用 AI 建议] to set up icoFoam laminar BCs."
    )


def setup_bc_with_annotations(
    *,
    case_dir: Path,
    case_id: str,
    force_uncertain: bool = False,
    force_blocked: bool = False,
    use_classifier: bool = True,
) -> AIActionEnvelope:
    """Run setup-bc envelope-mode classification (advisory only).

    DEC-V61-131 N1.1: this function NO LONGER mutates the case. It
    reads annotations + classifier output and returns an envelope
    describing what the engineer's apply click would do; the engineer
    applies via the legacy non-envelope ``POST /setup-bc`` route.

    Two operating modes:

    1. **Force flags** (``force_uncertain`` or ``force_blocked``):
       legacy DEC-V61-098 dogfood path. Returns the canned LDC dialog
       question for engineer practice without running the classifier.
       These flags take precedence over the classifier.
       (N1.1: ``force_uncertain`` no longer wraps a real setup call;
       it just returns the uncertain envelope with the LDC dialog.)

    2. **Real classifier** (``use_classifier=True``, default since
       DEC-V61-100 M9 Step 2 · no force flags set): consults
       :func:`classify_setup_bc` to inspect the polyMesh geometry
       + existing user_authoritative annotations and decides whether
       the answer is confident, uncertain, or blocked. The envelope
       describes the suggestion — no mutation.

    Reads ``face_annotations.yaml`` BEFORE classification so the AI
    can honor any user-authoritative entries from prior dialog turns.

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

    Returns:
        ``AIActionEnvelope`` describing the outcome (advisory only).

    Raises:
        AIActionError: if loading annotations fails for an
            infrastructure reason. NOT raised for blocked/uncertain
            envelope outcomes — those return normally via the envelope.
    """
    try:
        annotations = load_annotations(case_dir, case_id=case_id)
    except AnnotationsIOError as exc:
        raise AIActionError(
            f"could not load annotations: {exc}",
            failing_check=exc.failing_check,
        ) from exc

    revision_before = annotations["revision"]

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

    if force_uncertain:
        # N1.1: force_uncertain previously ran setup_ldc_bc THEN
        # wrapped as uncertain. With the hard-strip, no setup runs;
        # the dialog dogfood path emits the LDC question only.
        return AIActionEnvelope(
            confidence="uncertain",
            summary=(
                "AI suggests LDC defaults but wants confirmation on "
                "the lid orientation."
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

    if use_classifier:
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

        # Confident path: describe the suggestion. No mutation.
        if cls.geometry_class == "non_cube":
            summary = _summarize_channel_suggestion(cls)
        else:
            summary = _summarize_ldc_suggestion(cls)

        return AIActionEnvelope(
            confidence="confident",
            summary=summary,
            annotations_revision_consumed=revision_before,
            annotations_revision_after=revision_before,
            next_step_suggestion=(
                "Click [应用 AI 建议] to apply, or [Skip] to keep current setup."
            ),
        )

    # Tier-A backwards-compat path (use_classifier=False, no force
    # flags). Pre-N1.1 this ran setup_ldc_bc unconditionally. Now it
    # returns a confident advisory envelope describing the LDC default
    # suggestion. Tests that pin the legacy contract should switch to
    # asserting the envelope shape, not the side effect.
    return AIActionEnvelope(
        confidence="confident",
        summary=(
            "AI suggests LDC defaults (legacy classifier-off path). "
            "Click [应用 AI 建议] to apply icoFoam LDC defaults."
        ),
        annotations_revision_consumed=revision_before,
        annotations_revision_after=revision_before,
        next_step_suggestion=(
            "Click [应用 AI 建议] to apply, or [Skip] to keep current setup."
        ),
    )
