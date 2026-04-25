"""Batch matrix schema · Stage 5 GoldOps MVP per Codex industrial-workbench
meeting 2026-04-25.

Backs `<BatchMatrix>`: a 10-case × 4-density grid showing pass/fail/
hazard/unknown verdict per cell. Sits on LearnHomePage as a system-pulse
view between the buyer hero and the catalog grid.

Stage 5 close trigger: batch matrix renders all 10 cases. We hit that
trivially since the data composes from existing validation_report
service per (case, density) pair.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from ui.backend.schemas.validation import ContractStatus


class MatrixCell(BaseModel):
    """One cell in the 10×4 batch matrix."""

    density_id: str = Field(..., description="e.g. 'mesh_20'")
    n_cells_1d: int
    verdict: ContractStatus = Field(
        ...,
        description="PASS / HAZARD / FAIL / UNKNOWN — same enum as validation report",
    )
    deviation_pct: Optional[float] = Field(
        None,
        description="Relative deviation vs gold; None if measurement absent or non-finite",
    )
    measurement_value: Optional[float] = Field(
        None, description="Raw observable at this density"
    )
    verdict_reason: Optional[str] = Field(
        None,
        description=(
            "Short human-readable reason when verdict is HAZARD/FAIL/UNKNOWN. "
            "PASS leaves it null. Surfaces precondition gaps and hard-fail concerns "
            "so users don't see '0.19% HAZARD' without an explanation (Opus 4.7 "
            "review 2026-04-25 LDC tolerance probe — the symptom was 'tolerance "
            "looks over-strict' but the real issue was unexplained verdict)."
        ),
    )


class MatrixRow(BaseModel):
    """One case row across all sweep densities."""

    case_id: str
    display_name: str
    display_name_zh: Optional[str] = None
    canonical_ref: Optional[str] = None
    cells: list[MatrixCell]
    has_workbench_basics: bool = Field(
        ...,
        description=(
            "Whether knowledge/workbench_basics/<case_id>.yaml is authored; "
            "used by frontend to gray out rows whose CaseFrame would 404."
        ),
    )


class VerdictCounts(BaseModel):
    """Roll-up counters across all matrix cells."""

    PASS: int = 0
    HAZARD: int = 0
    FAIL: int = 0
    UNKNOWN: int = 0
    total: int = 0


class BatchMatrix(BaseModel):
    """Top-level response for `/api/batch-matrix`."""

    rows: list[MatrixRow]
    densities: list[str] = Field(
        ...,
        description=(
            "The fixed density column order, e.g. ['mesh_20', 'mesh_40', "
            "'mesh_80', 'mesh_160']. Frontend uses this to align cells."
        ),
    )
    counts: VerdictCounts
    n_cases: int
    n_densities: int
    diagnostic_note: Optional[str] = None
