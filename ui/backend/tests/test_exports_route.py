"""Stage 6 · exports (CSV) route tests.

Guards Stage 6 close trigger fields:
- ≥30 columns in schema
- ≥30 batch rows produced
- single source of truth (CSV agrees with validation_report on key fields)
- per-run + batch + manifest endpoints all 200
"""
from __future__ import annotations

import csv
import io

from fastapi.testclient import TestClient

from ui.backend.main import app
from ui.backend.services.export_csv import COLUMNS

client = TestClient(app)


def test_schema_has_at_least_30_columns() -> None:
    """Stage 6 close trigger: ≥30 fields per row."""
    assert len(COLUMNS) >= 30
    # Required-by-spec fields:
    required = {
        "case_id",
        "run_id",
        "measurement_value",
        "gold_ref_value",
        "gold_tolerance_pct",
        "deviation_pct",
        "contract_status",
        "exported_at_utc",
    }
    assert required.issubset(set(COLUMNS))


def test_per_run_csv_returns_200_and_proper_content_type() -> None:
    r = client.get(
        "/api/cases/lid_driven_cavity/runs/mesh_80/export.csv"
    )
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers.get("content-disposition", "")
    # Body parses as CSV with the documented header
    reader = csv.DictReader(io.StringIO(r.text))
    rows = list(reader)
    assert reader.fieldnames == COLUMNS
    assert len(rows) == 1
    assert rows[0]["case_id"] == "lid_driven_cavity"
    assert rows[0]["run_id"] == "mesh_80"


def test_per_run_csv_404_on_unknown_run() -> None:
    r = client.get(
        "/api/cases/lid_driven_cavity/runs/never_existed_run/export.csv"
    )
    assert r.status_code == 404


def test_batch_csv_returns_30_plus_rows() -> None:
    """Stage 6 close trigger: ≥30 batch rows."""
    r = client.get("/api/exports/batch.csv")
    assert r.status_code == 200
    reader = csv.DictReader(io.StringIO(r.text))
    rows = list(reader)
    assert len(rows) >= 30
    # All 10 whitelist cases represented
    case_ids = {row["case_id"] for row in rows}
    assert len(case_ids) == 10


def test_manifest_returns_schema_metadata() -> None:
    r = client.get("/api/exports/manifest")
    assert r.status_code == 200
    body = r.json()
    assert body["schema_version"] == "v1"
    assert body["n_columns"] == len(COLUMNS)
    assert body["n_batch_rows"] >= 30
    assert body["columns"] == COLUMNS


def test_csv_verdict_agrees_with_validation_report() -> None:
    """Single-source-of-truth check: CSV contract_status field must
    match the verdict that GET /api/validation-report would return."""
    csv_resp = client.get(
        "/api/cases/lid_driven_cavity/runs/mesh_80/export.csv"
    )
    csv_row = next(csv.DictReader(io.StringIO(csv_resp.text)))
    api_resp = client.get(
        "/api/validation-report/lid_driven_cavity?run_id=mesh_80"
    )
    api_body = api_resp.json()
    assert csv_row["contract_status"] == api_body["contract_status"]
    csv_dev = csv_row["deviation_pct"]
    api_dev = api_body.get("deviation_pct")
    if csv_dev and api_dev is not None:
        assert abs(float(csv_dev) - float(api_dev)) < 1e-3


def test_csv_data_rows_carry_no_unbounded_blanks() -> None:
    """Schema integrity: required fields must never be blank in a row.
    (Optional fields like measurement_commit_sha may be blank.)"""
    r = client.get("/api/exports/batch.csv")
    rows = list(csv.DictReader(io.StringIO(r.text)))
    required_non_empty = {"case_id", "run_id", "contract_status", "exported_at_utc"}
    for row in rows:
        for field in required_non_empty:
            assert row[field], f"row {row['case_id']}/{row['run_id']} has empty {field}"
