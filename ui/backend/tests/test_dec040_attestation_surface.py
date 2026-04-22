"""DEC-V61-040: tests for attestor verdict surfacing via ValidationReport.

DEC-V61-038 writes the A1..A6 attestor verdict onto the fixture at audit
time; DEC-V61-040 threads that verdict through the API so the UI can
render a DualVerdictBadge (scalar contract + attestor) and an AttestorPanel
with the per-check breakdown.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from ui.backend.main import app


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


def test_dec040_ldc_audit_real_run_exposes_attestation(client: TestClient) -> None:
    """LDC audit_real_run: scalar FAIL but attestor ATTEST_PASS (clean
    convergence, just wrong scalar point picked). Both must be in the API
    response as independent verdicts."""
    r = client.get("/api/validation-report/lid_driven_cavity?run_id=audit_real_run")
    assert r.status_code == 200
    body = r.json()
    assert body["contract_status"] == "FAIL"
    attestation = body["attestation"]
    assert attestation is not None, "LDC audit fixture was backfilled with attestation"
    assert attestation["overall"] == "ATTEST_PASS"
    # All 6 checks present.
    check_ids = [c["check_id"] for c in attestation["checks"]]
    assert check_ids == ["A1", "A2", "A3", "A4", "A5", "A6"]
    # Every check PASS for the clean LDC run.
    assert all(c["verdict"] == "PASS" for c in attestation["checks"])


def test_dec040_reference_run_has_null_attestation(client: TestClient) -> None:
    """reference_pass is a curated literature-anchored fixture with no
    solver log, so it should carry no attestation block → API returns null."""
    r = client.get("/api/validation-report/lid_driven_cavity?run_id=reference_pass")
    assert r.status_code == 200
    body = r.json()
    assert body["attestation"] is None, (
        "reference runs have no solver log; attestation must be null"
    )


def test_dec040_schema_fields_present_in_openapi(client: TestClient) -> None:
    """attestation + AttestorVerdict + AttestorCheck must be documented in
    the OpenAPI schema so TypeScript clients can rely on them."""
    r = client.get("/api/openapi.json")
    assert r.status_code == 200
    spec = r.json()
    schemas = spec["components"]["schemas"]
    assert "AttestorVerdict" in schemas
    assert "AttestorCheck" in schemas
    vr = schemas["ValidationReport"]
    assert "attestation" in vr["properties"]
    av = schemas["AttestorVerdict"]
    props = av["properties"]
    assert "overall" in props
    assert "checks" in props
