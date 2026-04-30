"""DEC-V61-102 Phase 1.3 · case_inspect route.

Single endpoint: ``GET /api/cases/{id}/state-preview``. Powers the
frontend "Inspect before AI 处理" modal.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from ui.backend.services.case_drafts import is_safe_case_id
from ui.backend.services.case_inspect import build_state_preview
from ui.backend.services.case_scaffold import IMPORTED_DIR

router = APIRouter()


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
            detail={"failing_check": "case_not_found", "case_id": case_id},
        )
    return case_dir


@router.get(
    "/cases/{case_id}/state-preview",
    tags=["case-inspect"],
)
def get_state_preview(
    case_id: str,
    next_action: str = Query(
        default="",
        description=(
            "Optional next-action hint. When set to one of "
            "'setup_ldc_bc' / 'setup_channel_bc' / 'switch_solver', the "
            "response includes a list of paths that action would clobber "
            "if the user confirms. Omit to get just the current state."
        ),
    ),
) -> dict:
    """Snapshot the case directory state for the inspect-before-act UI."""
    case_dir = _resolve_case_dir(case_id)
    preview = build_state_preview(case_dir, next_action=next_action)  # type: ignore[arg-type]
    return preview.to_wire()
