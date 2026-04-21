"""Phase 7a — field artifacts route tests.

Runs OFFLINE against the committed fixture at
ui/backend/tests/fixtures/phase7a_sample_fields/ via
set_fields_root_for_testing. Must NOT call the solver.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ui.backend.main import app
from ui.backend.services.field_artifacts import set_fields_root_for_testing

_FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "phase7a_sample_fields"
_RUN_ID = "lid_driven_cavity__audit_real_run"


@pytest.fixture(autouse=True)
def _point_fields_root_at_fixture():
    set_fields_root_for_testing(_FIXTURE_ROOT)
    yield
    set_fields_root_for_testing(None)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# ---------- Manifest endpoint ----------

def test_get_manifest_200(client: TestClient) -> None:
    r = client.get(f"/api/runs/{_RUN_ID}/field-artifacts")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["run_id"] == _RUN_ID
    assert body["case_id"] == "lid_driven_cavity"
    assert body["run_label"] == "audit_real_run"
    assert body["timestamp"] == "20260421T000000Z"


def test_manifest_three_artifacts(client: TestClient) -> None:
    r = client.get(f"/api/runs/{_RUN_ID}/field-artifacts")
    assert r.status_code == 200
    artifacts = r.json()["artifacts"]
    assert len(artifacts) >= 3, artifacts
    kinds = {a["kind"] for a in artifacts}
    assert {"vtk", "csv", "residual_log"}.issubset(kinds), kinds


def test_manifest_ordering(client: TestClient) -> None:
    """User ratification #6: sort by (kind_order, filename), vtk < csv < residual_log."""
    r = client.get(f"/api/runs/{_RUN_ID}/field-artifacts")
    assert r.status_code == 200
    artifacts = r.json()["artifacts"]
    order = {"vtk": 0, "csv": 1, "residual_log": 2}
    keys = [(order[a["kind"]], a["filename"]) for a in artifacts]
    assert keys == sorted(keys), keys


_HEX64 = re.compile(r"^[0-9a-f]{64}$")


def test_sha256_format(client: TestClient) -> None:
    r = client.get(f"/api/runs/{_RUN_ID}/field-artifacts")
    artifacts = r.json()["artifacts"]
    for a in artifacts:
        assert _HEX64.match(a["sha256"]), a


def test_manifest_sizes_positive(client: TestClient) -> None:
    r = client.get(f"/api/runs/{_RUN_ID}/field-artifacts")
    artifacts = r.json()["artifacts"]
    for a in artifacts:
        assert a["size_bytes"] > 0, a


def test_manifest_404_missing_run(client: TestClient) -> None:
    r = client.get("/api/runs/nonexistent_case__no_run/field-artifacts")
    assert r.status_code == 404, r.text


def test_manifest_400_or_404_malformed_run_id(client: TestClient) -> None:
    r = client.get("/api/runs/no_separator_here/field-artifacts")
    # parse_run_id raises 400; some FastAPI versions wrap as 422. Accept 400 or 404.
    assert r.status_code in (400, 404, 422), r.text


# ---------- Download endpoint ----------

def test_download_residuals_csv_200(client: TestClient) -> None:
    r = client.get(f"/api/runs/{_RUN_ID}/field-artifacts/residuals.csv")
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("text/csv")
    fixture = _FIXTURE_ROOT / "lid_driven_cavity" / "20260421T000000Z" / "residuals.csv"
    assert int(r.headers.get("content-length", "-1")) == fixture.stat().st_size


def test_download_vtk_200(client: TestClient) -> None:
    r = client.get(f"/api/runs/{_RUN_ID}/field-artifacts/lid_driven_cavity_2000.vtk")
    assert r.status_code == 200, r.text


def test_download_404_traversal(client: TestClient) -> None:
    r = client.get(f"/api/runs/{_RUN_ID}/field-artifacts/..%2F..%2Fetc%2Fpasswd")
    assert r.status_code == 404, r.text


def test_download_404_missing(client: TestClient) -> None:
    r = client.get(f"/api/runs/{_RUN_ID}/field-artifacts/does_not_exist.csv")
    assert r.status_code == 404, r.text
