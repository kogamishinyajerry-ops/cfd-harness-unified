"""Pydantic schemas for the M-AI-COPILOT envelope contract.

Spec_v2 §B.2 of DEC-V61-098. The ``AIActionEnvelope`` is the response
shape for every AI action that opts into the collab-first dialog flow
(currently only ``setup-bc`` under the ``?envelope=1`` query parameter).

The envelope wraps the AI's outcome with structured uncertainty:

- ``confident``: AI completed the step. ``unresolved_questions`` is empty.
- ``uncertain``: AI completed a partial / fallback action; user can ratify.
- ``blocked``: AI cannot proceed. ``unresolved_questions`` populated;
  ``error_detail`` may carry a short reason.

Frontend consumers MUST honor ``annotations_revision_consumed`` /
``annotations_revision_after`` to reject stale envelopes (mirrors the
V61-097 ``genRef`` pattern in ``SolveStreamContext``).
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

__all__ = [
    "AIActionConfidence",
    "AIActionEnvelope",
    "QuestionKind",
    "UnresolvedQuestion",
]


AIActionConfidence = Literal["confident", "uncertain", "blocked"]
QuestionKind = Literal[
    "face_label",
    "physics_value",
    "boundary_type",
    "free_text",
]


class UnresolvedQuestion(BaseModel):
    """A single unresolved question the AI surfaces to the engineer.

    Each question is paired with the dialog-panel UI: ``face_label``
    questions expect a face-pick, ``boundary_type`` questions expect a
    dropdown, ``physics_value`` expects a typed value, ``free_text``
    expects free-form input.
    """

    id: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description=(
            "Stable across retries. Deterministic from face_ids + "
            "question kind so the dialog-panel state survives a re-run "
            "of the same AI action."
        ),
    )
    kind: QuestionKind
    prompt: str = Field(
        ...,
        min_length=1,
        max_length=1024,
        description="Human-readable prompt rendered in the dialog panel.",
    )
    needs_face_selection: bool = Field(
        False,
        description=(
            "When true, the dialog panel arms the 3D viewport's "
            "pick mode; the user must click a face to answer."
        ),
    )
    candidate_face_ids: list[str] = Field(
        default_factory=list,
        description=(
            "If the AI has narrowed the candidates to a subset of "
            "faces, this list lets the dialog highlight only those "
            "faces in the viewport. Empty = all faces are candidates."
        ),
    )
    candidate_options: list[str] = Field(
        default_factory=list,
        description=(
            "For boundary_type / patch_type picks, the enumerated "
            "options the user can choose from."
        ),
    )
    default_answer: Optional[str] = Field(
        default=None,
        description="AI's best guess if forced to pick. May be None.",
    )

    @field_validator("candidate_face_ids", "candidate_options")
    @classmethod
    def _items_nonempty(cls, v: list[str]) -> list[str]:
        for item in v:
            if not item or not item.strip():
                raise ValueError("list items must be non-empty strings")
        return v


class AIActionEnvelope(BaseModel):
    """The standard return shape for every AI action under M-AI-COPILOT.

    HTTP 200 + this envelope when the action ran (regardless of
    confidence). True 4xx still happens on input validation; transport
    errors still happen on infrastructure failure.
    """

    confidence: AIActionConfidence
    summary: str = Field(
        ...,
        min_length=1,
        max_length=512,
        description="One-sentence what-happened.",
    )
    annotations_revision_consumed: int = Field(
        ...,
        ge=0,
        description=(
            "Which face_annotations.yaml revision the AI ran against. "
            "Frontend uses this to detect stale runs (the annotations "
            "have been edited since the AI started)."
        ),
    )
    annotations_revision_after: int = Field(
        ...,
        ge=0,
        description=(
            "The revision after the AI's writes. Equals "
            "annotations_revision_consumed if the AI didn't write."
        ),
    )
    unresolved_questions: list[UnresolvedQuestion] = Field(
        default_factory=list,
        description=(
            "Empty when confidence == 'confident'. Populated when "
            "confidence is 'uncertain' or 'blocked'. The frontend "
            "renders these inline in the right-rail dialog panel."
        ),
    )
    next_step_suggestion: Optional[str] = Field(
        default=None,
        description=(
            "Optional hint for the next step (e.g. 'proceed to Step 4 "
            "(Solve)'). Frontend may surface in the status strip."
        ),
    )
    error_detail: Optional[str] = Field(
        default=None,
        description=(
            "Populated only when confidence == 'blocked'. A short "
            "human-readable reason (e.g. 'no inlet face identified')."
        ),
    )

    @field_validator("unresolved_questions")
    @classmethod
    def _question_ids_unique(
        cls, v: list[UnresolvedQuestion]
    ) -> list[UnresolvedQuestion]:
        seen: set[str] = set()
        for q in v:
            if q.id in seen:
                raise ValueError(
                    f"duplicate UnresolvedQuestion.id: {q.id!r}"
                )
            seen.add(q.id)
        return v

    def model_post_init(self, __context: object, /) -> None:
        # Cross-field invariants:
        # 1. annotations_revision_after >= annotations_revision_consumed
        if self.annotations_revision_after < self.annotations_revision_consumed:
            raise ValueError(
                f"annotations_revision_after "
                f"({self.annotations_revision_after}) must be >= "
                f"annotations_revision_consumed "
                f"({self.annotations_revision_consumed})"
            )
        # 2. confidence='confident' → unresolved_questions empty
        if self.confidence == "confident" and self.unresolved_questions:
            raise ValueError(
                "confidence='confident' requires "
                "unresolved_questions to be empty"
            )
        # 3. confidence='blocked' → at least one question OR error_detail
        if self.confidence == "blocked" and not (
            self.unresolved_questions or self.error_detail
        ):
            raise ValueError(
                "confidence='blocked' requires either "
                "unresolved_questions to be non-empty OR "
                "error_detail to be set"
            )
