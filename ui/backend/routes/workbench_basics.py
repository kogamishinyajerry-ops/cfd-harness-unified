"""Workbench-basics route · Stage 2 MVP.

GET /api/cases/{case_id}/workbench-basics

Loads structured first-screen data from
`knowledge/workbench_basics/<case_id>.yaml`, validates against the
`WorkbenchBasics` Pydantic schema, and surfaces patch-id drift as a
soft warning rather than a 500 (per Stage 2 risk note: better an amber
banner than a broken page while authors are still populating cases).

Source authority: physics_contract.geometry_assumption from
`knowledge/gold_standards/<case_id>.yaml`. Per Codex industrial-workbench
meeting 2026-04-25, this endpoint backs the `<CaseFrame>` SVG primitive
shown above the existing tab bar in /learn/cases/<id>.
"""
from __future__ import annotations

from pathlib import Path

import yaml
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from ui.backend.schemas.workbench_basics import (
    WorkbenchBasics,
    validate_patch_consistency,
)
from ui.backend.services.run_ids import _validate_segment

router = APIRouter()

REPO_ROOT = Path(__file__).resolve().parents[3]
BASICS_DIR = REPO_ROOT / "knowledge" / "workbench_basics"


@router.get(
    "/cases/{case_id}/workbench-basics",
    tags=["workbench-basics"],
)
def get_workbench_basics(case_id: str) -> JSONResponse:
    _validate_segment(case_id, "case_id")
    yaml_path = BASICS_DIR / f"{case_id}.yaml"
    if not yaml_path.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                f"workbench-basics not yet authored for {case_id!r}; "
                "Stage 2 MVP rollout is in progress (close trigger: "
                "≥8 of 10 cases populated)."
            ),
        )
    try:
        payload = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        raise HTTPException(
            status_code=500,
            detail=f"workbench_basics YAML parse error for {case_id}: {e}",
        )
    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=500,
            detail=f"workbench_basics YAML for {case_id} did not parse to a mapping",
        )

    drift = validate_patch_consistency(payload)
    if drift:
        payload["schema_drift_warning"] = drift

    try:
        model = WorkbenchBasics(**payload)
    except ValidationError as e:
        raise HTTPException(
            status_code=500,
            detail=f"workbench_basics schema validation failed for {case_id}: {e.errors()}",
        )
    return JSONResponse(model.model_dump(exclude_none=True))
