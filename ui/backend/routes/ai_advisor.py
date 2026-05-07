"""DEC-V61-158 (N6.2) · AI 审查 (case review) advisor route.

GET /api/cases/{case_id}/ai-review

Read-only by V130/V132 contract. Returns a structured
:class:`ReviewResponse` with citation-grounded findings.

V132 contract:
  * Route NOT registered in MUTATING_ROUTES (it is a GET; idempotent)
  * Module path appears in ``_AI_DISPATCH_MODULES`` so Layer-C AST
    scan asserts no KNOWN_MUTATION_FUNCTIONS symbol is imported
  * Layer-A patches every mutation symbol with a sentinel; this
    route is exercised across LLM + offline branches; sentinel must
    record zero invocations
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException

from ui.backend.schemas.ai_advisor import ReviewResponse
from ui.backend.services.ai_advisor.review import review_case
from ui.backend.services.case_drafts import is_safe_case_id
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
    "/cases/{case_id}/ai-review",
    response_model=ReviewResponse,
    tags=["ai-advisor"],
)
async def get_ai_review(case_id: str) -> ReviewResponse:
    """Compose a citation-grounded case review.

    Read-only:
      * Loads case state via N5.1 + N5.2 walkers (no writes)
      * Retrieves corpus chunks via N6.1 loader (no writes)
      * Calls LLM provider (read-only HTTP); falls through to
        rule-based on provider failure or mock provider
      * Returns structured ReviewResponse

    Engineer reads the findings, copies recommended_change text by
    hand if applicable. There is no [Apply] surface — the V132
    contract test enforces this at the function-symbol level.
    """
    case_dir = _resolve_case_dir(case_id)
    return await review_case(case_dir)
