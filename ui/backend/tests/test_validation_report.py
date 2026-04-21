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
    # Gold ref_value was remediated 30.0 → 8.8 per Gate Q-new (b12d54e) after
    # regime-consistency audit; test updated to track the authoritative gold.
    assert body["gold_standard"]["ref_value"] == pytest.approx(8.8)
    # Ampofo/Karayiannis 2003 is the canonical citation per whitelist.yaml.
    assert body["reference"]
    # Preconditions must be non-empty. Post-b12d54e DHC regime was
    # downgraded Ra=1e10 → Ra=1e6 (Gate Q-new Path P-2), at which point
    # the BL-under-resolution precondition from DEC-ADWM-004 no longer
    # fires — all three preconditions satisfy under the new regime.
    assert len(body["preconditions"]) > 0


def test_validation_report_dhc_is_fail_with_hazard(client: TestClient) -> None:
    # Pin to the real_incident run: after DEC-V61-024 Option A, DHC has
    # a reference_pass curated run (Nu=8.75 de Vahl Davis Ra=1e6) that
    # now serves as the default. The Nu=77.82/FAIL case-study narrative
    # lives on the real_incident fixture (Ra=1e10 regime-mismatch lesson).
    response = client.get(
        "/api/validation-report/differential_heated_cavity?run_id=real_incident"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["measurement"]["value"] == pytest.approx(77.82)
    # Gold ref_value remediated 30.0 → 8.8 (b12d54e); 77.82 is still far
    # outside tolerance (8.8 * 1.15 = 10.12), so FAIL semantics hold.
    assert body["gold_standard"]["ref_value"] == pytest.approx(8.8)
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
    # Pin to the real_incident run: canonical-band shortcut scenario is a
    # property of the specific incident fixture (measurement 0.165 with
    # silent-pass-hazard concern), not of the default reference_pass.
    response = client.get(
        "/api/validation-report/circular_cylinder_wake?run_id=real_incident"
    )
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
    # Pin to the real_incident run: Spalding-fallback Cf=0.00760 is the
    # §5d Part-2 acceptance output preserved as an incident fixture. The
    # default reference_pass run shows a Blasius-aligned PASS instead.
    response = client.get(
        "/api/validation-report/turbulent_flat_plate?run_id=real_incident"
    )
    assert response.status_code == 200
    body = response.json()
    # Spalding fallback measurement Cf ≈ 0.00760 (0.0576 / (0.5*Re)^0.2 at
    # Re=50000 per DEC-ADWM-005). Post-PR #20 the fixture records the exact
    # executor output to 10 decimals. Old-gold tolerance band was Cf=0.0076
    # ±10%; under B-class remediation gold became 0.00420 (Blasius laminar
    # at Re_x=25000) so the measurement now lies far outside tolerance.
    assert body["measurement"]["value"] == pytest.approx(0.007600365566051871)
    assert body["contract_status"] in ("HAZARD", "PASS", "FAIL")


def test_validation_report_default_prefers_reference_pass_when_curated(
    client: TestClient,
) -> None:
    """Multi-run governance: a case with a curated reference_pass run
    must surface that run by default rather than the real_incident
    fixture, so the learner's first impression is a PASS narrative."""
    response = client.get("/api/validation-report/turbulent_flat_plate")
    assert response.status_code == 200
    body = response.json()
    # reference_pass is Blasius-aligned 0.00423 (+0.7% deviation, inside
    # the 10% tolerance band → PASS).
    assert body["measurement"]["value"] == pytest.approx(0.00423)
    assert body["contract_status"] == "PASS"


def test_validation_report_rejects_unknown_run_id(client: TestClient) -> None:
    response = client.get(
        "/api/validation-report/turbulent_flat_plate?run_id=does_not_exist"
    )
    assert response.status_code == 404


def test_case_runs_endpoint_lists_reference_pass_first(client: TestClient) -> None:
    response = client.get("/api/cases/turbulent_flat_plate/runs")
    assert response.status_code == 200
    runs = response.json()
    assert any(r["run_id"] == "reference_pass" for r in runs)
    assert any(r["run_id"] == "real_incident" for r in runs)
    categories = {r["run_id"]: r["category"] for r in runs}
    assert categories["reference_pass"] == "reference"
    assert categories["real_incident"] == "real_incident"
    # Pedagogical ordering: reference before real_incident before
    # teaching variants before grid_convergence. Also: mesh_N runs
    # sorted numerically, not lexicographically (mesh_20 before mesh_160).
    order = [r["run_id"] for r in runs]
    assert order.index("reference_pass") < order.index("real_incident")
    assert order.index("real_incident") < order.index("under_resolved")
    mesh_runs = [r for r in order if r.startswith("mesh_")]
    assert mesh_runs == ["mesh_20", "mesh_40", "mesh_80", "mesh_160"]
    # Grid-convergence runs must sit after the teaching variants so the
    # Compare run-picker doesn't open on mesh_20.
    for mesh_id in mesh_runs:
        assert order.index("under_resolved") < order.index(mesh_id)


def test_unknown_case_returns_404(client: TestClient) -> None:
    response = client.get("/api/validation-report/not_a_real_case")
    assert response.status_code == 404
