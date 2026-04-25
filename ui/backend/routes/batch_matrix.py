"""Batch matrix route · Stage 5 GoldOps MVP.

GET /api/batch-matrix

Returns the 10×4 case × mesh density verdict grid for the
`<BatchMatrix>` SVG primitive on LearnHomePage. Read-only and
idempotent.
"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ui.backend.services.batch_matrix import build_batch_matrix

router = APIRouter()


@router.get("/batch-matrix", tags=["batch-matrix"])
def get_batch_matrix() -> JSONResponse:
    matrix = build_batch_matrix()
    return JSONResponse(matrix.model_dump(exclude_none=True))
