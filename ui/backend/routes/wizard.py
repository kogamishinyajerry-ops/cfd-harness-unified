"""Onboarding-wizard routes · Stage 8a.

    GET  /api/wizard/templates              → 3 starter templates
    POST /api/wizard/draft                  → render YAML + write user draft
    GET  /api/wizard/run/{case_id}/stream   → phase-tagged SSE timeline (8a-2)

Strict additive surface — no shared code with foam_agent_adapter, no
fixture-format changes, no schema collision with line-B branches.
"""
from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import StreamingResponse

from ui.backend.services.wizard_drivers import get_driver

from ui.backend.schemas.wizard import (
    DraftCreateRequest,
    DraftCreateResponse,
    TemplateListResponse,
    WizardPreviewResponse,
)
from ui.backend.services.wizard import (
    create_draft,
    get_unknown_keys,
    list_templates,
    render_yaml,
)


router = APIRouter()


def _validate_case_id(case_id: str) -> None:
    """Mirrors case_drafts._draft_path's safety check upfront so the
    wizard returns a clean 400 instead of a generic ValueError."""
    safe = "".join(c for c in case_id if c.isalnum() or c in ("_", "-"))
    if safe != case_id or not case_id:
        raise HTTPException(
            status_code=400,
            detail=(
                f"case_id {case_id!r} must be non-empty alphanumeric / "
                "underscore / hyphen only."
            ),
        )


@router.get("/wizard/templates", response_model=TemplateListResponse)
def list_templates_route() -> TemplateListResponse:
    return TemplateListResponse(templates=list_templates())


@router.post("/wizard/preview", response_model=WizardPreviewResponse)
def preview_yaml_route(
    payload: DraftCreateRequest = Body(...),
) -> WizardPreviewResponse:
    """Render the same YAML body `POST /api/wizard/draft` would write,
    but without the file-write side effect. Frontend renders this text
    verbatim — closes Opus round-2 Q11 (preview-vs-create drift).

    `case_id` validation runs but is non-fatal: the preview is still
    useful while the user is still typing the id. We surface a 400 only
    when the *template* or *params* are wrong; an in-progress case_id
    just gets echoed back. (The /draft route still rejects unsafe ids.)
    """
    try:
        yaml_text = render_yaml(
            template_id=payload.template_id,
            case_id=payload.case_id or "<your-case-id>",
            name_display=payload.name_display,
            params=payload.params,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return WizardPreviewResponse(
        yaml_text=yaml_text,
        unknown_keys=get_unknown_keys(payload.template_id, payload.params),
    )


@router.post("/wizard/draft", response_model=DraftCreateResponse)
def create_draft_route(
    payload: DraftCreateRequest = Body(...),
) -> DraftCreateResponse:
    _validate_case_id(payload.case_id)
    try:
        return create_draft(
            template_id=payload.template_id,
            case_id=payload.case_id,
            name_display=payload.name_display,
            params=payload.params,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# --- Phase-tagged SSE stream -----------------------------------------------
# The 5-phase walking logic + mock script DATA were extracted into
# services.wizard_drivers (Stage 8b prep / round-3 trajectory). The route
# is now a thin pass-through that picks a driver and streams its output
# unchanged. Stage 8b adds RealSolverDriver as a sibling class in
# wizard_drivers.py — only env-var picks change here, schema unchanged.


@router.get("/wizard/run/{case_id}/stream")
async def wizard_run_stream(case_id: str) -> StreamingResponse:
    _validate_case_id(case_id)
    driver = get_driver()
    return StreamingResponse(
        driver.run(case_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
