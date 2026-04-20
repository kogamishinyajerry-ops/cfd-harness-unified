"""Case Editor routes (Phase 1).

    GET    /api/cases/{case_id}/yaml       → source YAML + origin
    PUT    /api/cases/{case_id}/yaml       → save draft + lint
    POST   /api/cases/{case_id}/yaml/lint  → lint without saving
    DELETE /api/cases/{case_id}/yaml       → revert (delete draft)

Writes land in ``ui/backend/user_drafts/`` — NEVER in
``knowledge/whitelist.yaml`` or ``knowledge/gold_standards/**``
(hard floors #1 / #2 per DEC-V61-002).
"""

from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException

from ui.backend.schemas.editor import (
    CaseYamlLintResult,
    CaseYamlPayload,
    CaseYamlSaveResult,
)
from ui.backend.services.case_drafts import (
    get_case_yaml,
    lint_case_yaml,
    put_case_yaml,
    revert_case_yaml,
)

router = APIRouter()


@router.get("/cases/{case_id}/yaml", response_model=CaseYamlPayload)
def get_case_yaml_route(case_id: str) -> CaseYamlPayload:
    try:
        src = get_case_yaml(case_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if src.origin == "missing":
        raise HTTPException(status_code=404, detail=f"case_id not found: {case_id}")
    return CaseYamlPayload(
        case_id=case_id,
        yaml_text=src.yaml_text,
        origin=src.origin,
        draft_path=src.draft_path,
    )


@router.put("/cases/{case_id}/yaml", response_model=CaseYamlSaveResult)
def put_case_yaml_route(
    case_id: str,
    payload: CaseYamlPayload = Body(...),
) -> CaseYamlSaveResult:
    if payload.case_id != case_id:
        raise HTTPException(
            status_code=400,
            detail=f"payload.case_id ({payload.case_id!r}) != path ({case_id!r})",
        )
    try:
        draft_path, lint = put_case_yaml(case_id, payload.yaml_text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return CaseYamlSaveResult(
        case_id=case_id,
        saved=lint.ok,
        draft_path=draft_path or None,
        lint=CaseYamlLintResult(ok=lint.ok, errors=lint.errors, warnings=lint.warnings),
    )


@router.post("/cases/{case_id}/yaml/lint", response_model=CaseYamlLintResult)
def lint_case_yaml_route(
    case_id: str,
    payload: CaseYamlPayload = Body(...),
) -> CaseYamlLintResult:
    _ = case_id  # case_id is unused for lint but kept for RESTful symmetry
    lint = lint_case_yaml(payload.yaml_text)
    return CaseYamlLintResult(ok=lint.ok, errors=lint.errors, warnings=lint.warnings)


@router.delete("/cases/{case_id}/yaml", response_model=CaseYamlPayload)
def delete_case_yaml_route(case_id: str) -> CaseYamlPayload:
    try:
        src = revert_case_yaml(case_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if src.origin == "missing":
        raise HTTPException(status_code=404, detail=f"case_id not found: {case_id}")
    return CaseYamlPayload(
        case_id=case_id,
        yaml_text=src.yaml_text,
        origin=src.origin,
        draft_path=src.draft_path,
    )
