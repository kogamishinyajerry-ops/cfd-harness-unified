"""GET/PUT /api/cases/{case_id}/face-annotations route.

DEC-V61-098 spec_v2 §A4. The route is the persistence channel for
the M-AI-COPILOT collab dialog: when the engineer answers a question
in the right-rail DialogPanel by clicking a face in the 3D viewport
and naming it, the AnnotationPanel dispatches a PUT to this route
with the new annotation + the ``if_match_revision`` token from the
last fetched envelope.

GET shape:
    200 → ``{schema_version, case_id, revision, last_modified, faces[]}``
    404 → annotations file not yet materialized (UI treats as empty doc)

PUT shape:
    Body: ``{if_match_revision: int, faces: [...]}``
    200 → new state with bumped revision
    404 → case not found
    409 → revision conflict (concurrent edit; refetch + retry)
    422 → schema/parse error
    400 → bad case_id (path traversal etc.)
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ui.backend.services.case_annotations import (
    SCHEMA_VERSION,
    AnnotationsIOError,
    AnnotationsRevisionConflict,
    empty_annotations,
    load_annotations,
    save_annotations,
)
from ui.backend.services.case_drafts import is_safe_case_id
from ui.backend.services.case_scaffold import IMPORTED_DIR

__all__ = ["router"]

router = APIRouter()


class _FacePut(BaseModel):
    """A face entry in the PUT body. Loose schema (most fields are
    optional so the engineer can update one face at a time).
    """

    face_id: str = Field(..., min_length=4, max_length=128)
    name: str | None = None
    patch_type: str | None = None
    bc: dict[str, Any] | None = None
    physics_notes: str | None = None
    confidence: str | None = None


class _AnnotationsPutBody(BaseModel):
    """Body shape for PUT /face-annotations."""

    if_match_revision: int = Field(..., ge=0)
    faces: list[_FacePut] = Field(default_factory=list)
    annotated_by: str = Field(
        default="human",
        description=(
            "Identifier for the writer. 'human' for engineer-driven "
            "edits; 'ai:<source>' for AI writes (e.g., 'ai:rule-based')."
        ),
    )


def _resolve_case_dir(case_id: str) -> Path:
    if not is_safe_case_id(case_id):
        raise HTTPException(
            status_code=400,
            detail={"failing_check": "bad_case_id", "case_id": case_id},
        )
    case_dir = IMPORTED_DIR / case_id
    if not case_dir.is_dir():
        raise HTTPException(
            status_code=404,
            detail={
                "failing_check": "case_not_found",
                "case_id": case_id,
            },
        )
    return case_dir


@router.get(
    "/cases/{case_id}/face-annotations",
    tags=["case-annotations"],
)
def get_face_annotations(case_id: str) -> dict[str, Any]:
    """Load the annotations document for ``case_id``.

    Returns an empty document (revision=0) if the file doesn't exist
    yet — the UI treats this as 'no annotations yet' rather than an
    error, so the dialog flow can start fresh.
    """
    case_dir = _resolve_case_dir(case_id)
    try:
        return load_annotations(case_dir, case_id=case_id)
    except AnnotationsIOError as exc:
        status_map = {
            "case_dir_missing": 404,
            "parse_error": 422,
            "symlink_escape": 422,
            "schema_version_mismatch": 422,
        }
        status = status_map.get(exc.failing_check, 500)
        raise HTTPException(
            status_code=status,
            detail={
                "failing_check": exc.failing_check,
                "detail": str(exc),
            },
        ) from exc


@router.put(
    "/cases/{case_id}/face-annotations",
    tags=["case-annotations"],
)
def put_face_annotations(
    case_id: str, body: _AnnotationsPutBody
) -> dict[str, Any]:
    """Merge the supplied face entries into the annotations doc and
    bump revision.

    Concurrency: ``body.if_match_revision`` MUST match the current
    on-disk revision; otherwise a 409 with both attempted and
    current revisions is returned. The frontend should re-fetch
    via GET and retry.
    """
    case_dir = _resolve_case_dir(case_id)

    # Load current state. If file missing, start from empty doc.
    try:
        current = load_annotations(case_dir, case_id=case_id)
    except AnnotationsIOError as exc:
        status_map = {
            "case_dir_missing": 404,
            "parse_error": 422,
            "symlink_escape": 422,
            "schema_version_mismatch": 422,
        }
        status = status_map.get(exc.failing_check, 500)
        raise HTTPException(
            status_code=status,
            detail={
                "failing_check": exc.failing_check,
                "detail": str(exc),
            },
        ) from exc

    # Merge the supplied faces into the current doc.
    timestamp = datetime.now(timezone.utc).isoformat()
    is_ai_write = body.annotated_by.startswith("ai:")

    for face_put in body.faces:
        face_dict = face_put.model_dump(exclude_none=True)
        existing = next(
            (f for f in current["faces"] if f["face_id"] == face_dict["face_id"]),
            None,
        )
        # Sticky invariant: AI cannot overwrite user_authoritative.
        if (
            existing is not None
            and existing.get("confidence") == "user_authoritative"
            and is_ai_write
        ):
            continue
        merged = {
            **(existing or {}),
            **face_dict,
            "annotated_by": body.annotated_by,
            "annotated_at": timestamp,
        }
        if existing is not None:
            current["faces"] = [
                merged if f["face_id"] == face_dict["face_id"] else f
                for f in current["faces"]
            ]
        else:
            current["faces"].append(merged)

    current["last_modified"] = timestamp

    try:
        return save_annotations(
            case_dir, current, if_match_revision=body.if_match_revision
        )
    except AnnotationsRevisionConflict as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "failing_check": "revision_conflict",
                "attempted_revision": exc.attempted_revision,
                "current_revision": exc.current_revision,
            },
        ) from exc
    except AnnotationsIOError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "failing_check": exc.failing_check,
                "detail": str(exc),
            },
        ) from exc
