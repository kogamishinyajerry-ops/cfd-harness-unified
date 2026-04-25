"""Exports route · Stage 6 ExportPack MVP.

GET /api/cases/{case_id}/runs/{run_id}/export.csv  (per-run, ≥30 cols × 1 row)
GET /api/exports/batch.csv                          (all cases × all runs)
GET /api/exports/manifest                           (schema + row counts as JSON)

CSV chosen over xlsx: stdlib only (no openpyxl dep), audit-friendly
(text grep-able), opens in Excel/Sheets natively. Schema captured in
ui/backend/services/export_csv.py COLUMNS — ≥30 fields cleanly satisfies
Stage 6 close trigger.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, Response

from ui.backend.services.export_csv import (
    export_batch_csv,
    export_manifest,
    export_run_csv,
)
from ui.backend.services.run_ids import _validate_segment

router = APIRouter()


@router.get(
    "/cases/{case_id}/runs/{run_id}/export.csv",
    tags=["exports"],
)
def get_run_export_csv(case_id: str, run_id: str) -> Response:
    _validate_segment(case_id, "case_id")
    _validate_segment(run_id, "run_id")
    body = export_run_csv(case_id, run_id)
    if body is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Cannot build validation report for {case_id!r} / {run_id!r}; "
                "fixture or gold standard missing."
            ),
        )
    filename = f"{case_id}_{run_id}.csv"
    return Response(
        content=body,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )


@router.get("/exports/batch.csv", tags=["exports"])
def get_batch_export_csv() -> Response:
    body = export_batch_csv()
    filename = "cfd-harness_batch_export.csv"
    return Response(
        content=body,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )


@router.get("/exports/manifest", tags=["exports"])
def get_export_manifest() -> JSONResponse:
    return JSONResponse(export_manifest())
