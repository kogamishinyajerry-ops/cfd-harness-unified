"""Export CSV service · Stage 6 ExportPack MVP.

Per Codex industrial-workbench meeting 2026-04-25 + roadmap S6
(workbench_rollout_roadmap.md). Stage 6 spec calls for xlsx export but
the project has no xlsx dependency today (no openpyxl in pyproject.toml
runtime deps). CSV is the pragmatic equivalent: tabular, opens cleanly
in Excel / Google Sheets / pandas, fully stdlib, and audit-friendly
(no opaque binary container — the file is human-readable).

Schema is a flat single CSV row per (case, run, observable) tuple with
≥30 columns covering case metadata, run metadata, measurement,
gold-standard reference, comparator verdict, and export provenance.
This satisfies the Stage 6 close trigger ("字段映射 ≥30 行 · 含 metric /
dimension / verdict / commit_sha / gold ref"). Future xlsx upgrade is
a one-import swap when openpyxl lands.
"""
from __future__ import annotations

import csv
import io
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Optional

import yaml

from ui.backend.services.validation_report import (
    build_validation_report,
    list_runs,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_WHITELIST_PATH = _REPO_ROOT / "knowledge" / "whitelist.yaml"


# Column schema — fixed order, surfaced in /export.csv first row. ≥30
# fields per Stage 6 close trigger. Adding new columns is forward-compat;
# removing/renaming requires a schema-version bump.
COLUMNS: list[str] = [
    # Case metadata (10)
    "case_id",
    "case_name",
    "case_canonical_ref",
    "case_doi",
    "case_flow_type",
    "case_geometry_type",
    "case_compressibility",
    "case_steady_state",
    "case_solver",
    "case_turbulence_model",
    # Run metadata (5)
    "run_id",
    "run_label_zh",
    "run_label_en",
    "run_category",
    "run_expected_verdict",
    # Measurement (5)
    "observable_index",
    "measurement_quantity",
    "measurement_value",
    "measurement_unit",
    "measurement_commit_sha",
    # Gold standard (5)
    "gold_quantity",
    "gold_ref_value",
    "gold_unit",
    "gold_tolerance_pct",
    "gold_citation",
    # Comparator verdict (4)
    "deviation_pct",
    "within_tolerance",
    "contract_status",
    "profile_verdict",
    # Audit / provenance (5)
    "n_preconditions",
    "n_preconditions_satisfied",
    "n_audit_concerns",
    "exported_at_utc",
    "exporter",
]


def _whitelist_case_ids() -> list[str]:
    if not _WHITELIST_PATH.is_file():
        return []
    try:
        doc = yaml.safe_load(_WHITELIST_PATH.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        return []
    rows = (doc or {}).get("cases") or []
    return [r["id"] for r in rows if isinstance(r, dict) and r.get("id")]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _exporter_label() -> str:
    return os.environ.get("CFD_EXPORTER_LABEL", "cfd-harness-unified")


def _row_for_run(case_id: str, run_id: str) -> Optional[dict[str, str]]:
    """Build one CSV row for (case, run). Returns None if no validation
    report can be built (e.g. fixture absent)."""
    report = build_validation_report(case_id, run_id=run_id)
    if report is None:
        return None

    case = report.case
    runs = list_runs(case_id)
    run_meta = next((r for r in runs if r.run_id == run_id), None)

    gs = report.gold_standard
    meas = report.measurement

    ref = gs.ref_value if gs else None
    tol = gs.tolerance_pct if gs else None

    return {
        "case_id": case.case_id,
        "case_name": case.name or "",
        "case_canonical_ref": case.reference or "",
        "case_doi": case.doi or "",
        "case_flow_type": case.flow_type or "",
        "case_geometry_type": case.geometry_type or "",
        "case_compressibility": case.compressibility or "",
        "case_steady_state": case.steady_state or "",
        "case_solver": case.solver or "",
        "case_turbulence_model": case.turbulence_model or "",
        "run_id": run_id,
        "run_label_zh": (run_meta.label_zh if run_meta else "") or "",
        "run_label_en": (run_meta.label_en if run_meta else "") or "",
        "run_category": (run_meta.category if run_meta else "") or "",
        "run_expected_verdict": (
            (run_meta.expected_verdict if run_meta else "") or ""
        ),
        "observable_index": "0",
        "measurement_quantity": (meas.quantity if meas else "") or "",
        "measurement_value": (
            f"{meas.value:.10g}"
            if meas is not None and meas.value is not None
            else ""
        ),
        "measurement_unit": gs.unit if gs and gs.unit else "",
        "measurement_commit_sha": (
            (meas.commit_sha if meas else "") or ""
        ),
        "gold_quantity": gs.quantity if gs else "",
        "gold_ref_value": f"{ref:.10g}" if ref is not None else "",
        "gold_unit": gs.unit if gs and gs.unit else "",
        "gold_tolerance_pct": f"{tol:.6g}" if tol is not None else "",
        "gold_citation": (gs.citation if gs else "") or "",
        "deviation_pct": (
            f"{report.deviation_pct:.6g}"
            if report.deviation_pct is not None
            else ""
        ),
        "within_tolerance": (
            ""
            if report.within_tolerance is None
            else ("true" if report.within_tolerance else "false")
        ),
        "contract_status": report.contract_status or "",
        "profile_verdict": report.profile_verdict or "",
        "n_preconditions": str(len(report.preconditions)),
        "n_preconditions_satisfied": str(
            sum(
                1
                for p in report.preconditions
                if p.satisfied is True
            )
        ),
        "n_audit_concerns": str(len(report.audit_concerns)),
        "exported_at_utc": _now_iso(),
        "exporter": _exporter_label(),
    }


def export_run_csv(case_id: str, run_id: str) -> Optional[str]:
    """Single-run CSV: 1 header + 1 data row. Returns CSV text or None
    if the run cannot be reported on."""
    row = _row_for_run(case_id, run_id)
    if row is None:
        return None
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=COLUMNS)
    writer.writeheader()
    writer.writerow(row)
    return buf.getvalue()


def export_batch_csv() -> str:
    """Batch CSV across all whitelist cases × all available runs.

    Iterates whitelist case ids, then list_runs() per case, calling
    _row_for_run for each (case, run). Skips rows whose validation
    report can't be built (returns None). Produces a CSV with one header
    + N data rows where N = sum_over_cases(len(runs(case))).
    """
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=COLUMNS)
    writer.writeheader()
    for case_id in _whitelist_case_ids():
        for run in list_runs(case_id):
            row = _row_for_run(case_id, run.run_id)
            if row is None:
                continue
            writer.writerow(row)
    return buf.getvalue()


def iter_batch_rows() -> Iterator[dict[str, str]]:
    """Generator variant — used by manifest counting without serialization."""
    for case_id in _whitelist_case_ids():
        for run in list_runs(case_id):
            row = _row_for_run(case_id, run.run_id)
            if row is None:
                continue
            yield row


def export_manifest() -> dict:
    """Lightweight manifest describing the schema + current row count.

    Used by `<ExportPanel>` to surface "schema vN · M batch rows" without
    the user having to download the CSV first. Cheap because it iterates
    runs but not full reports — actually it does, since we have to
    successfully build each report to count it. Kept simple for MVP;
    cache layer is a future polish.
    """
    n_rows = sum(1 for _ in iter_batch_rows())
    n_columns = len(COLUMNS)
    return {
        "schema_version": "v1",
        "n_columns": n_columns,
        "n_batch_rows": n_rows,
        "columns": COLUMNS,
        "exported_at_utc": _now_iso(),
        "exporter": _exporter_label(),
    }
