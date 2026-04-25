"""Mesh-metrics schema · Stage 3 MVP per Codex industrial-workbench
meeting 2026-04-25 (transcript:
reports/codex_tool_reports/industrial_workbench_meeting_2026-04-25.md).

Backs the `<MeshQC>` SVG primitive: red/yellow/green color-semantic QC
band over GCI uncertainty + asymptotic-range + Richardson observed
order. Source data is the already-computed
`ui.backend.services.grid_convergence.compute_gci_from_fixtures(case_id)`,
which loads mesh_20/40/80/160_measurement.yaml fixtures.

Stage 3 close trigger: 4 档 mesh 数据 ≥8 case (most cases already have
4 fixtures populated; this endpoint surfaces that).
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


# QC verdict tri-state: drives bar color in <MeshQC>. "gray" = unknown
# (insufficient data, not a failure).
QcVerdict = str  # Literal["green", "yellow", "red", "gray"] kept loose


class MeshDensityPoint(BaseModel):
    """One mesh density's measured observable + nominal cell count."""

    id: str = Field(..., description="Mesh fixture id, e.g. 'mesh_20'")
    n_cells_1d: int = Field(..., description="Cell count along the dominant refinement direction")
    value: Optional[float] = Field(
        None,
        description=(
            "Comparator observable at this density. None if fixture present "
            "but value field empty (rare; flagged via has_value=False)."
        ),
    )
    has_value: bool


class GciSummary(BaseModel):
    """Richardson + GCI summary over the finest 3 meshes (Celik 2008)."""

    p_obs: Optional[float] = Field(None, description="Observed order of accuracy")
    f_extrapolated: Optional[float] = Field(
        None,
        description="Richardson-extrapolated value at h→0",
    )
    e_21: Optional[float] = Field(None, description="Relative change coarse→medium")
    e_32: Optional[float] = Field(None, description="Relative change medium→fine")
    gci_21_pct: Optional[float] = Field(
        None, description="Coarse-mesh GCI uncertainty band (% of f_2)"
    )
    gci_32_pct: Optional[float] = Field(
        None, description="Fine-mesh GCI uncertainty band (% of f_3)"
    )
    asymptotic_range_ok: Optional[bool] = Field(
        None,
        description=(
            "True if GCI_32·r^p ≈ GCI_21 within ~25%; means sweep is in the "
            "asymptotic regime where Richardson extrapolation is meaningful."
        ),
    )
    note: Optional[str] = Field(None, description="Human-readable diagnostic")


class QcBand(BaseModel):
    """Tri-state verdicts shown as red/yellow/green chips in <MeshQC>.

    Threshold conventions:
    - gci_32: green ≤5%, yellow ≤15%, red >15% (Celik 2008 typical bands)
    - asymptotic_range: green=in range, red=out, gray=unknown
    - richardson_p: green if 1.5≤p≤2.5 (matches 2nd-order schemes the
      harness uses), yellow if 1.0≤p<1.5 or 2.5<p≤4.0, red otherwise
    - n_levels: green if ≥4 fixtures populated (full sweep), yellow ≥3
      (just enough for GCI), red <3 (cannot compute Richardson)
    """

    gci_32: QcVerdict
    asymptotic_range: QcVerdict
    richardson_p: QcVerdict
    n_levels: QcVerdict


class MeshMetrics(BaseModel):
    """Top-level response for `/api/cases/{case_id}/mesh-metrics`."""

    case_id: str
    densities: list[MeshDensityPoint]
    gci: Optional[GciSummary] = None
    qc_band: QcBand
    # When fewer than 3 densities are available we can't run Richardson;
    # `gci` is None and qc_band reflects that. Frontend handles the
    # degraded state explicitly.
    diagnostic_note: Optional[str] = None


# Threshold helpers — pure, importable for tests.

def _verdict_gci(gci_pct: Optional[float]) -> QcVerdict:
    if gci_pct is None:
        return "gray"
    if gci_pct <= 5.0:
        return "green"
    if gci_pct <= 15.0:
        return "yellow"
    return "red"


def _verdict_asymptotic(ok: Optional[bool]) -> QcVerdict:
    if ok is None:
        return "gray"
    return "green" if ok else "red"


def _verdict_richardson_p(p: Optional[float]) -> QcVerdict:
    if p is None:
        return "gray"
    if 1.5 <= p <= 2.5:
        return "green"
    if 1.0 <= p <= 4.0:
        return "yellow"
    return "red"


def _verdict_n_levels(n: int) -> QcVerdict:
    if n >= 4:
        return "green"
    if n >= 3:
        return "yellow"
    return "red"


def build_qc_band(
    gci_32_pct: Optional[float],
    asymptotic_range_ok: Optional[bool],
    p_obs: Optional[float],
    n_levels: int,
) -> QcBand:
    return QcBand(
        gci_32=_verdict_gci(gci_32_pct),
        asymptotic_range=_verdict_asymptotic(asymptotic_range_ok),
        richardson_p=_verdict_richardson_p(p_obs),
        n_levels=_verdict_n_levels(n_levels),
    )
