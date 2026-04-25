"""Batch matrix service · Stage 5 GoldOps MVP.

Composes 10×4 (case × density) verdicts by calling build_validation_report
per pair. Each call is cached via the validation report's own internal
caches (gold YAML loader, fixture loader), so the per-cell cost is
mostly comparator math — fast enough for a single homepage render.

Whitelist source: knowledge/whitelist.yaml (10 cases). Density columns:
hardcoded mesh_20/40/80/160 to match GRID_CONVERGENCE_CASES on the
frontend; new densities slot in additively.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml

from ui.backend.schemas.batch_matrix import (
    BatchMatrix,
    MatrixCell,
    MatrixRow,
    VerdictCounts,
)
from ui.backend.services.validation_report import build_validation_report

_REPO_ROOT = Path(__file__).resolve().parents[3]
_WHITELIST_PATH = _REPO_ROOT / "knowledge" / "whitelist.yaml"
_BASICS_DIR = _REPO_ROOT / "knowledge" / "workbench_basics"

DENSITY_COLUMNS: tuple[str, ...] = ("mesh_20", "mesh_40", "mesh_80", "mesh_160")


def _load_whitelist_rows() -> list[dict]:
    if not _WHITELIST_PATH.is_file():
        return []
    try:
        doc = yaml.safe_load(_WHITELIST_PATH.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        return []
    rows = (doc or {}).get("cases") or []
    return [r for r in rows if isinstance(r, dict) and r.get("id")]


def _row_for_case(case_row: dict) -> Optional[MatrixRow]:
    case_id = case_row["id"]
    cells: list[MatrixCell] = []

    for density_id in DENSITY_COLUMNS:
        n_cells_1d = int(density_id.split("_")[-1])
        report = build_validation_report(case_id, run_id=density_id)
        if report is None:
            cells.append(
                MatrixCell(
                    density_id=density_id,
                    n_cells_1d=n_cells_1d,
                    verdict="UNKNOWN",
                    deviation_pct=None,
                    measurement_value=None,
                )
            )
            continue
        meas_value = (
            report.measurement.value if report.measurement is not None else None
        )
        cells.append(
            MatrixCell(
                density_id=density_id,
                n_cells_1d=n_cells_1d,
                verdict=report.contract_status,
                deviation_pct=report.deviation_pct,
                measurement_value=meas_value,
            )
        )

    has_basics = (_BASICS_DIR / f"{case_id}.yaml").is_file()

    return MatrixRow(
        case_id=case_id,
        display_name=case_row.get("name", case_id),
        display_name_zh=case_row.get("display_name_zh"),
        canonical_ref=case_row.get("reference"),
        cells=cells,
        has_workbench_basics=has_basics,
    )


def build_batch_matrix() -> BatchMatrix:
    rows: list[MatrixRow] = []
    counts = VerdictCounts()
    for case_row in _load_whitelist_rows():
        row = _row_for_case(case_row)
        if row is None:
            continue
        rows.append(row)
        for c in row.cells:
            if c.verdict == "PASS":
                counts.PASS += 1
            elif c.verdict == "HAZARD":
                counts.HAZARD += 1
            elif c.verdict == "FAIL":
                counts.FAIL += 1
            else:
                counts.UNKNOWN += 1
            counts.total += 1

    return BatchMatrix(
        rows=rows,
        densities=list(DENSITY_COLUMNS),
        counts=counts,
        n_cases=len(rows),
        n_densities=len(DENSITY_COLUMNS),
    )
