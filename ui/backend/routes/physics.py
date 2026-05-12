"""DEC-V61-142 (N3.3) · POST /api/cases/{case_id}/physics.

Engineer-driven commit of MaterialContract + RegimeContract. Translates
both into the case's `constant/physicalProperties` +
`constant/momentumTransport` dicts.

V132 contract: this is a NEW MUTATING ROUTE registered in
``services/ai_actions/mutating_routes.py``. AI dispatch paths must
NEVER call this — V130 Principle B (engineer applies, AI advises).

Status mapping:
  * 200 → PhysicsCommitResponse (dict text + paths echoed)
  * 400 → bad case_id (path-traversal / unsafe segment)
  * 404 → case_dir missing
  * 422 → contract validation error (FastAPI default Pydantic 422),
          OR case is missing the constant/ directory (case not yet
          scaffolded by Step 1 import)
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from ui.backend.schemas.material_contract import MaterialContract
from ui.backend.schemas.regime_contract import RegimeContract
from ui.backend.services.case_drafts import is_safe_case_id
from ui.backend.services.case_scaffold import IMPORTED_DIR
from ui.backend.services.physics.writer import write_physics_dicts


logger = logging.getLogger(__name__)
router = APIRouter()


class PhysicsCommitRequest(BaseModel):
    """Body of POST /api/cases/{case_id}/physics. Carries both
    contracts in one round-trip so we don't have a partial-commit
    window where physicalProperties is updated but momentumTransport
    is stale (or vice versa)."""

    model_config = ConfigDict(extra="forbid")

    material: MaterialContract = Field(...)
    regime: RegimeContract = Field(...)


class PhysicsStateResponse(BaseModel):
    """GET /api/cases/{case_id}/physics — current committed state.

    Engineer mental model is query-before-mutate: this paired GET
    surfaces the dict text already written by an earlier POST so the
    persona / UI can compare against intended changes. Both fields
    are nullable: a freshly scaffolded case (Step 1 only) has neither
    file on disk yet — the route returns null rather than 404 because
    "nothing committed" is a valid Step 3 state.

    Added by DEC-V61-168 / B.5.2 to address DOGFOOD_REPORT_LIVE F3.
    """

    model_config = ConfigDict(extra="forbid")

    case_id: str
    material_dict_text: str | None = Field(
        default=None,
        description=(
            "Raw text of `constant/physicalProperties` if the file "
            "exists; null otherwise."
        ),
    )
    regime_dict_text: str | None = Field(
        default=None,
        description=(
            "Raw text of `constant/momentumTransport` if the file "
            "exists; null otherwise."
        ),
    )


class PhysicsCommitResponse(BaseModel):
    """Echo what was written. Lets the engineer verify the dict text
    in the UI without re-fetching from disk. Path strings are
    repository-relative (the case_dir convention used elsewhere)."""

    model_config = ConfigDict(extra="forbid")

    case_id: str
    written_paths: list[str] = Field(
        default_factory=list,
        description=(
            "Repository-relative dict paths that were written. "
            "Useful for the frontend to show 'wrote N files' confirmation."
        ),
    )
    dict_texts: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Map from rel-path → raw OpenFOAM dict text just written. "
            "Frontend can render in a 'show diff' panel."
        ),
    )
    committed_at: str = Field(
        ...,
        description="ISO 8601 UTC timestamp the commit completed.",
    )


@router.get(
    "/cases/{case_id}/physics",
    response_model=PhysicsStateResponse,
    tags=["physics"],
)
def get_physics_state(case_id: str) -> PhysicsStateResponse:
    """Return current `constant/physicalProperties` + `constant/momentumTransport`
    text for an imported case.

    Both fields are null when the case has been scaffolded but not yet
    physics-committed. Added per DEC-V61-168 / B.5.2 (DOGFOOD_REPORT_LIVE F3).
    """
    if not is_safe_case_id(case_id):
        raise HTTPException(
            status_code=400,
            detail={"failing_check": "bad_case_id", "case_id": case_id},
        )
    case_dir: Path = IMPORTED_DIR / case_id
    if not case_dir.is_dir():
        raise HTTPException(
            status_code=404,
            detail={"failing_check": "case_not_found", "case_id": case_id},
        )
    constant_dir = case_dir / "constant"
    material_path = constant_dir / "physicalProperties"
    regime_path = constant_dir / "momentumTransport"
    return PhysicsStateResponse(
        case_id=case_id,
        material_dict_text=(
            material_path.read_text(encoding="utf-8")
            if material_path.is_file() else None
        ),
        regime_dict_text=(
            regime_path.read_text(encoding="utf-8")
            if regime_path.is_file() else None
        ),
    )


@router.post(
    "/cases/{case_id}/physics",
    response_model=PhysicsCommitResponse,
    tags=["physics"],
)
def commit_physics(
    case_id: str,
    request: PhysicsCommitRequest,
) -> PhysicsCommitResponse:
    """Commit MaterialContract + RegimeContract to the case's
    constant/ dicts."""
    if not is_safe_case_id(case_id):
        raise HTTPException(
            status_code=400,
            detail={"failing_check": "bad_case_id", "case_id": case_id},
        )
    case_dir: Path = IMPORTED_DIR / case_id
    if not case_dir.is_dir():
        raise HTTPException(
            status_code=404,
            detail={"failing_check": "case_not_found", "case_id": case_id},
        )
    try:
        written = write_physics_dicts(
            case_dir,
            material=request.material,
            regime=request.regime,
        )
    except FileNotFoundError as exc:
        # constant/ missing — case scaffold incomplete.
        raise HTTPException(
            status_code=422,
            detail={
                "failing_check": "case_not_scaffolded",
                "case_id": case_id,
                "message": str(exc),
            },
        ) from exc
    except OSError as exc:
        # Disk-full / permission — surface structured 502.
        logger.exception(
            "physics commit failed for case_id=%r: %s",
            case_id,
            type(exc).__name__,
        )
        raise HTTPException(
            status_code=502,
            detail={
                "failing_check": "physics_write_failed",
                "case_id": case_id,
                "message": f"{type(exc).__name__}: write failed",
            },
        ) from exc

    return PhysicsCommitResponse(
        case_id=case_id,
        written_paths=list(written.keys()),
        dict_texts=written,
        committed_at=datetime.now(tz=timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
    )
