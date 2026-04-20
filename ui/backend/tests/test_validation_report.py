"""Phase 0 acceptance tests: 3 real cases render a Validation Report.

Fixtures live in ui/backend/tests/fixtures/{case_id}_measurement.yaml
and are committed alongside the backend. The authoritative
knowledge/gold_standards/*.yaml files are read read-only.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from ui.backend.main import app


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


def test_cases_index_contains_ten_entries(client: TestClient) -> None:
    response = client.get("/api/cases")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 10, f"expected 10 whitelist cases, got {len(body)}"
    ids = {entry["case_id"] for entry in body}
    # Phase 0 gate: canonical three that drive Screen 4.
    assert "differential_heated_cavity" in ids
    assert "circular_cylinder_wake" in ids
    assert "turbulent_flat_plate" in ids


def test_case_detail_differential_heated_cavity(client: TestClient) -> None:
    response = client.get("/api/cases/differential_heated_cavity")
    assert response.status_code == 200
    body = response.json()
    assert body["case_id"] == "differential_heated_cavity"
    assert body["gold_standard"]["quantity"] == "nusselt_number"
    assert body["gold_standard"]["ref_value"] == pytest.approx(30.0)
    # Ampofo/Karayiannis 2003 is the canonical citation per whitelist.yaml.
    assert body["reference"]
    # Preconditions must be non-empty with at least one unsatisfied
    # (BL under-resolution per DEC-ADWM-004).
    assert any(p["satisfied"] is False for p in body["preconditions"])


def test_validation_report_dhc_is_fail_with_hazard(client: TestClient) -> None:
    response = client.get("/api/validation-report/differential_heated_cavity")
    assert response.status_code == 200
    body = response.json()
    assert body["measurement"]["value"] == pytest.approx(77.82)
    assert body["gold_standard"]["ref_value"] == pytest.approx(30.0)
    # 77.82 >> upper tolerance bound (30 * 1.15 = 34.5).
    assert body["contract_status"] == "FAIL"
    assert body["within_tolerance"] is False
    assert body["deviation_pct"] > 100.0
    # Audit concern surface must include both contract-status narrative
    # and the two measurement-level concerns from the fixture.
    types = {c["concern_type"] for c in body["audit_concerns"]}
    assert "COMPATIBLE_WITH_SILENT_PASS_HAZARD" in types
    assert "DEVIATION" in types
    # Decisions trail threads DEC-ADWM-002 + DEC-ADWM-004.
    trail_ids = {d["decision_id"] for d in body["decisions_trail"]}
    assert {"DEC-ADWM-002", "DEC-ADWM-004"}.issubset(trail_ids)


def test_validation_report_cylinder_wake_is_hazard(client: TestClient) -> None:
    response = client.get("/api/validation-report/circular_cylinder_wake")
    assert response.status_code == 200
    body = response.json()
    assert body["measurement"]["value"] == pytest.approx(0.165)
    # Measurement equals ref_value → inside tolerance → HAZARD (not PASS)
    # because the canonical-band shortcut is an armed silent-pass hazard.
    assert body["contract_status"] == "HAZARD"
    assert body["within_tolerance"] is True
    types = {c["concern_type"] for c in body["audit_concerns"]}
    assert "COMPATIBLE_WITH_SILENT_PASS_HAZARD" in types


def test_validation_report_turbulent_flat_plate_hazard(client: TestClient) -> None:
    response = client.get("/api/validation-report/turbulent_flat_plate")
    assert response.status_code == 200
    body = response.json()
    # Spalding fallback measurement Cf=0.0070 is within ±10% of 0.0076.
    assert body["measurement"]["value"] == pytest.approx(0.0070)
    assert body["contract_status"] in ("HAZARD", "PASS")
    # Audit concern must include the Spalding fallback hazard regardless.
    types = {c["concern_type"] for c in body["audit_concerns"]}
    assert "COMPATIBLE_WITH_SILENT_PASS_HAZARD" in types


def test_unknown_case_returns_404(client: TestClient) -> None:
    response = client.get("/api/validation-report/not_a_real_case")
    assert response.status_code == 404
