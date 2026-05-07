"""DEC-V61-158/159 (N6.2/N6.3) · AI advisor routes.

Endpoints:
  * ``GET /api/cases/{case_id}/ai-review`` — case review advisor (N6.2)
  * ``GET /api/cases/{case_id}/ai-diagnose`` — failure-mode advisor (N6.3)

Both are read-only by V130/V132 contract. Returns structured
responses with citation-grounded findings/hypotheses.

V132 contract:
  * Routes NOT registered in MUTATING_ROUTES (GET; idempotent)
  * Module path appears in ``_AI_DISPATCH_MODULES`` so Layer-C AST
    scan asserts no KNOWN_MUTATION_FUNCTIONS symbol is imported
  * Layer-A patches every mutation symbol with a sentinel; both
    routes exercised across LLM + offline branches; sentinel must
    record zero invocations
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, get_args

from fastapi import APIRouter, HTTPException, Query, Request

from ui.backend.routes._loopback_guard import require_loopback
from ui.backend.schemas.ai_advisor import (
    DiagnoseResponse,
    FailureMode,
    ReviewResponse,
)
from ui.backend.services.ai_advisor.diagnose import diagnose_case
from ui.backend.services.ai_advisor.review import review_case
from ui.backend.services.case_drafts import is_safe_case_id
from ui.backend.services.case_scaffold import IMPORTED_DIR

router = APIRouter()


# Whitelist for ?problem= query param. Sourced from the FailureMode
# literal so the route + schema stay in sync (Codex-aware: literal
# tampering would fail Pydantic validation downstream anyway, but
# rejecting at the route boundary is cleaner + clearer 400).
_VALID_FAILURE_MODES: frozenset[str] = frozenset(get_args(FailureMode))


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
async def get_ai_review(
    case_id: str,
    request: Request,
) -> ReviewResponse:
    """Compose a citation-grounded case review.

    Loopback-only by default (Codex N6.2 R0 P1): the LLM call path
    is the same blast radius as ``/api/ai-chat`` + ``/api/ai-coach``;
    require_loopback shares their guard so off-box callers cannot
    spend the operator's LLM quota or pull case-derived advisor
    output. Operators who deploy behind a trusted reverse proxy +
    auth set ``AI_CHAT_ALLOW_NON_LOOPBACK=1`` to opt in.

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
    require_loopback(request, route_label="/api/cases/{case_id}/ai-review")
    case_dir = _resolve_case_dir(case_id)
    return await review_case(case_dir)


@router.get(
    "/cases/{case_id}/ai-diagnose",
    response_model=DiagnoseResponse,
    tags=["ai-advisor"],
)
async def get_ai_diagnose(
    case_id: str,
    request: Request,
    problem: Optional[str] = Query(
        default=None,
        description=(
            "Optional failure-mode hint the engineer suspects. One of: "
            "stalled_residuals, diverging_residuals, mesh_quality_critical, "
            "bc_or_physics_setup, unknown."
        ),
    ),
) -> DiagnoseResponse:
    """Compose a citation-grounded failure-mode diagnosis.

    Loopback-only by default (same blast radius as ``/api/ai-review``):
    operator behind a trusted reverse proxy + auth sets
    ``AI_CHAT_ALLOW_NON_LOOPBACK=1`` to opt in.

    Read-only:
      * Reads N5.2 IssueList + bounded log tail (last 200 lines, 256
        KiB cap). Log path is contained under ``case_dir`` — symlink
        escapes are rejected.
      * Retrieves corpus chunks via N6.1 loader.
      * Calls LLM provider; falls through to rule-based on provider
        failure or mock provider.

    The ``problem`` query param is validated against the FailureMode
    literal before reaching the service; unknown values → 400.
    """
    require_loopback(
        request, route_label="/api/cases/{case_id}/ai-diagnose"
    )
    case_dir = _resolve_case_dir(case_id)

    problem_hint: Optional[FailureMode] = None
    if problem is not None:
        if problem not in _VALID_FAILURE_MODES:
            raise HTTPException(
                status_code=400,
                detail={
                    "failing_check": "bad_problem_hint",
                    "value": problem,
                    "allowed": sorted(_VALID_FAILURE_MODES),
                },
            )
        problem_hint = problem  # type: ignore[assignment]

    return await diagnose_case(case_dir, problem_hint=problem_hint)
