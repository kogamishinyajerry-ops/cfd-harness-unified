"""Mesh-metrics route · Stage 3 MVP.

GET /api/cases/{case_id}/mesh-metrics

Surfaces existing GCI computation
(`ui.backend.services.grid_convergence.compute_gci_from_fixtures`) as a
JSON QC band suitable for the `<MeshQC>` SVG primitive in MeshTab.
This is read-only and idempotent — cheap to call.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from ui.backend.schemas.mesh_metrics import (
    GciSummary,
    MeshDensityPoint,
    MeshMetrics,
    build_qc_band,
)
from ui.backend.services.grid_convergence import (
    compute_gci_from_fixtures,
    load_mesh_solutions_from_fixtures,
)
from ui.backend.services.run_ids import _validate_segment

router = APIRouter()


@router.get(
    "/cases/{case_id}/mesh-metrics",
    tags=["mesh-metrics"],
)
def get_mesh_metrics(case_id: str) -> JSONResponse:
    _validate_segment(case_id, "case_id")

    sols = load_mesh_solutions_from_fixtures(case_id)
    if not sols:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No mesh density fixtures for {case_id!r}; check "
                f"ui/backend/tests/fixtures/runs/{case_id}/mesh_*_measurement.yaml"
            ),
        )

    densities: list[MeshDensityPoint] = []
    for s in sorted(sols, key=lambda x: x.n_cells_1d):
        densities.append(
            MeshDensityPoint(
                id=s.label,
                n_cells_1d=s.n_cells_1d,
                value=s.value,
                has_value=s.value is not None,
            )
        )

    gci_obj = compute_gci_from_fixtures(case_id) if len(sols) >= 3 else None
    gci_payload: GciSummary | None = None
    diagnostic_note: str | None = None

    if gci_obj is not None:
        # Convert dimensionless GCI to percent (multiply by 100). Source
        # values are already "Fs * eps / (r^p - 1)" which is a fractional
        # uncertainty bound.
        gci_21_pct = (
            gci_obj.gci_21 * 100.0 if gci_obj.gci_21 is not None else None
        )
        gci_32_pct = (
            gci_obj.gci_32 * 100.0 if gci_obj.gci_32 is not None else None
        )
        e_21_pct = gci_obj.e_21 * 100.0
        e_32_pct = gci_obj.e_32 * 100.0
        gci_payload = GciSummary(
            p_obs=gci_obj.p_obs,
            f_extrapolated=gci_obj.f_extrapolated,
            e_21=e_21_pct,
            e_32=e_32_pct,
            gci_21_pct=gci_21_pct,
            gci_32_pct=gci_32_pct,
            asymptotic_range_ok=gci_obj.asymptotic_range_ok,
            note=gci_obj.note,
        )
    else:
        diagnostic_note = (
            f"Insufficient fixtures for Richardson/GCI: have {len(sols)}, need ≥3."
        )

    qc_band = build_qc_band(
        gci_32_pct=gci_payload.gci_32_pct if gci_payload else None,
        asymptotic_range_ok=gci_payload.asymptotic_range_ok if gci_payload else None,
        p_obs=gci_payload.p_obs if gci_payload else None,
        n_levels=len(sols),
    )

    model = MeshMetrics(
        case_id=case_id,
        densities=densities,
        gci=gci_payload,
        qc_band=qc_band,
        diagnostic_note=diagnostic_note,
    )
    return JSONResponse(model.model_dump(exclude_none=True))
