"""Tests for the AIActionEnvelope Pydantic schemas (DEC-V61-098 spec_v2 §B.2)."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from ui.backend.schemas.ai_action import (
    AIActionEnvelope,
    UnresolvedQuestion,
)


# ────────── UnresolvedQuestion ──────────


def test_unresolved_question_minimal():
    q = UnresolvedQuestion(
        id="q1",
        kind="face_label",
        prompt="Which face is the inlet?",
        needs_face_selection=True,
    )
    assert q.id == "q1"
    assert q.kind == "face_label"
    assert q.candidate_face_ids == []
    assert q.candidate_options == []
    assert q.default_answer is None


def test_unresolved_question_full():
    q = UnresolvedQuestion(
        id="q2",
        kind="boundary_type",
        prompt="What patch type?",
        needs_face_selection=False,
        candidate_options=["patch", "wall", "symmetry"],
        default_answer="wall",
    )
    assert q.candidate_options == ["patch", "wall", "symmetry"]
    assert q.default_answer == "wall"


def test_unresolved_question_rejects_invalid_kind():
    with pytest.raises(ValidationError):
        UnresolvedQuestion(
            id="q",
            kind="not_a_real_kind",  # type: ignore
            prompt="x",
            needs_face_selection=False,
        )


def test_unresolved_question_rejects_empty_id():
    with pytest.raises(ValidationError):
        UnresolvedQuestion(
            id="",
            kind="face_label",
            prompt="x",
            needs_face_selection=False,
        )


def test_unresolved_question_rejects_empty_prompt():
    with pytest.raises(ValidationError):
        UnresolvedQuestion(
            id="q",
            kind="face_label",
            prompt="",
            needs_face_selection=False,
        )


def test_unresolved_question_rejects_blank_list_items():
    with pytest.raises(ValidationError):
        UnresolvedQuestion(
            id="q",
            kind="face_label",
            prompt="x",
            needs_face_selection=False,
            candidate_face_ids=["fid_abc", "  "],
        )


# ────────── AIActionEnvelope · happy paths ──────────


def test_envelope_confident_no_questions():
    e = AIActionEnvelope(
        confidence="confident",
        summary="Set up LDC defaults.",
        annotations_revision_consumed=0,
        annotations_revision_after=1,
    )
    assert e.confidence == "confident"
    assert e.unresolved_questions == []


def test_envelope_uncertain_with_questions():
    e = AIActionEnvelope(
        confidence="uncertain",
        summary="Defaults applied; please confirm lid.",
        annotations_revision_consumed=0,
        annotations_revision_after=1,
        unresolved_questions=[
            UnresolvedQuestion(
                id="lid",
                kind="face_label",
                prompt="Confirm the moving lid.",
                needs_face_selection=True,
            ),
        ],
    )
    assert e.confidence == "uncertain"
    assert len(e.unresolved_questions) == 1


def test_envelope_blocked_with_questions():
    e = AIActionEnvelope(
        confidence="blocked",
        summary="Cannot proceed; need labels.",
        annotations_revision_consumed=0,
        annotations_revision_after=0,
        unresolved_questions=[
            UnresolvedQuestion(
                id="inlet", kind="face_label", prompt="Inlet?",
                needs_face_selection=True,
            ),
        ],
    )
    assert e.confidence == "blocked"


def test_envelope_blocked_with_error_detail_only():
    """spec §B.2: blocked may have NO questions if error_detail is set."""
    e = AIActionEnvelope(
        confidence="blocked",
        summary="Solver crashed.",
        annotations_revision_consumed=2,
        annotations_revision_after=2,
        error_detail="OpenFOAM: divergence in U at iter 47",
    )
    assert e.error_detail.startswith("OpenFOAM:")


# ────────── AIActionEnvelope · invariants ──────────


def test_envelope_confident_must_have_no_questions():
    """Cross-field invariant: confident → empty unresolved_questions."""
    with pytest.raises(ValidationError) as exc:
        AIActionEnvelope(
            confidence="confident",
            summary="x",
            annotations_revision_consumed=0,
            annotations_revision_after=1,
            unresolved_questions=[
                UnresolvedQuestion(
                    id="q", kind="face_label", prompt="x",
                    needs_face_selection=True,
                ),
            ],
        )
    assert "confident" in str(exc.value)


def test_envelope_blocked_requires_questions_or_error_detail():
    """blocked with no questions and no error_detail must reject."""
    with pytest.raises(ValidationError) as exc:
        AIActionEnvelope(
            confidence="blocked",
            summary="x",
            annotations_revision_consumed=0,
            annotations_revision_after=0,
        )
    assert "blocked" in str(exc.value).lower()


def test_envelope_revision_after_must_not_decrease():
    """Cross-field invariant: revision_after >= revision_consumed.
    revision is monotonic, so an AI action cannot 'go back in time'.
    """
    with pytest.raises(ValidationError) as exc:
        AIActionEnvelope(
            confidence="confident",
            summary="x",
            annotations_revision_consumed=5,
            annotations_revision_after=4,
        )
    assert ">=" in str(exc.value) or "revision" in str(exc.value)


def test_envelope_question_ids_must_be_unique():
    with pytest.raises(ValidationError) as exc:
        AIActionEnvelope(
            confidence="uncertain",
            summary="x",
            annotations_revision_consumed=0,
            annotations_revision_after=0,
            unresolved_questions=[
                UnresolvedQuestion(
                    id="dup", kind="face_label", prompt="a",
                    needs_face_selection=True,
                ),
                UnresolvedQuestion(
                    id="dup", kind="face_label", prompt="b",
                    needs_face_selection=True,
                ),
            ],
        )
    assert "duplicate" in str(exc.value).lower()


def test_envelope_revisions_must_be_non_negative():
    with pytest.raises(ValidationError):
        AIActionEnvelope(
            confidence="confident",
            summary="x",
            annotations_revision_consumed=-1,
            annotations_revision_after=0,
        )


# ────────── round-trip serialization ──────────


def test_envelope_json_round_trip():
    """Envelope serializes to JSON and back without loss — needed for
    SSE event payloads and HTTP responses.
    """
    original = AIActionEnvelope(
        confidence="uncertain",
        summary="ok",
        annotations_revision_consumed=3,
        annotations_revision_after=4,
        unresolved_questions=[
            UnresolvedQuestion(
                id="q1",
                kind="face_label",
                prompt="Inlet?",
                needs_face_selection=True,
                candidate_face_ids=["fid_abc"],
                default_answer="fid_abc",
            ),
        ],
        next_step_suggestion="proceed to Step 4",
    )
    payload = original.model_dump_json()
    rehydrated = AIActionEnvelope.model_validate_json(payload)
    assert rehydrated == original
