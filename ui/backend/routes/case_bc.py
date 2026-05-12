"""DEC-V61-146 (N4.1) · POST /api/cases/{case_id}/bc-contract.

Engineer-driven commit of structured per-patch BC contract. Translates
into 0.orig/{U, p} dict files via the case_bc writer.

V132 contract: NEW MUTATING ROUTE registered in MUTATING_ROUTES. AI
dispatch paths must NEVER call this — V130 Principle B.

Status mapping:
  * 200 → BCContractCommitResponse
  * 400 → bad case_id
  * 404 → case_dir missing
  * 422 → contract validation error (Pydantic) OR pairing inconsistency
  * 502 → disk write failed
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from ui.backend.schemas.bc_contract import BCContract
from ui.backend.services.case_bc.writer import BCWriterError, write_bc_dicts
from ui.backend.services.case_drafts import is_safe_case_id
from ui.backend.services.case_scaffold import IMPORTED_DIR


logger = logging.getLogger(__name__)
router = APIRouter()


class BCContractCommitResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    written_paths: list[str] = Field(default_factory=list)
    dict_texts: dict[str, str] = Field(default_factory=dict)
    committed_at: str
    patch_count: int = Field(
        ...,
        ge=1,
        description=(
            "Number of patches in the committed contract. Useful for "
            "the frontend to surface 'BC fill rate: N of M patches'."
        ),
    )


@router.post(
    "/cases/{case_id}/bc-contract",
    response_model=BCContractCommitResponse,
    tags=["bc-contract"],
)
def commit_bc_contract(
    case_id: str,
    contract: BCContract,
) -> BCContractCommitResponse:
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
        written = write_bc_dicts(case_dir, contract=contract)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "failing_check": "case_not_scaffolded",
                "case_id": case_id,
                "message": str(exc),
            },
        ) from exc
    except BCWriterError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "failing_check": exc.failing_check,
                "case_id": case_id,
                "message": str(exc),
            },
        ) from exc
    except OSError as exc:
        logger.exception(
            "BC contract commit failed for case_id=%r: %s",
            case_id,
            type(exc).__name__,
        )
        raise HTTPException(
            status_code=502,
            detail={
                "failing_check": "bc_write_failed",
                "case_id": case_id,
                "message": f"{type(exc).__name__}: write failed",
            },
        ) from exc

    return BCContractCommitResponse(
        case_id=case_id,
        written_paths=list(written.keys()),
        dict_texts=written,
        committed_at=datetime.now(tz=timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        patch_count=len(contract.patches),
    )
