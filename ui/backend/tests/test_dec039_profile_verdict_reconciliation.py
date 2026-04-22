"""DEC-V61-039: tests for profile_verdict surfacing alongside contract_status.

The root user-report bug: `comparison-report` said LDC PARTIAL (11/17
profile points within tolerance) while `/validation-report` said LDC
FAIL (audit scalar +370% deviation). Both are HONEST at different
levels — pointwise vs scalar — but the API hid the split-brain.

Fix: ValidationReport now surfaces both. `contract_status` remains the
scalar verdict; new `profile_verdict` + `profile_pass_count` +
`profile_total_count` expose the pointwise view for gold-overlay cases.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from ui.backend.main import app


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


def test_dec039_ldc_audit_real_run_exposes_both_verdicts(client: TestClient) -> None:
    """LDC audit_real_run: scalar FAIL (deviation >300%) but profile 11/17
    PARTIAL. Both must be present in the API response."""
    r = client.get("/api/validation-report/lid_driven_cavity?run_id=audit_real_run")
    assert r.status_code == 200
    body = r.json()
    # Scalar verdict remains FAIL (the wrong profile point was picked as scalar).
    assert body["contract_status"] == "FAIL"
    # Profile-level pointwise verdict surfaces separately.
    assert body["profile_verdict"] == "PARTIAL"
    assert body["profile_pass_count"] == 11
    assert body["profile_total_count"] == 17


def test_dec039_non_gold_overlay_cases_have_null_profile_verdict(
    client: TestClient,
) -> None:
    """Cases that are visual-only (no gold-overlay) must NOT surface a
    profile_verdict — the field stays None. Confirms the DEC doesn't
    accidentally fire for BFS / duct / RBC / etc."""
    for case in ("backward_facing_step", "duct_flow",
                 "rayleigh_benard_convection"):
        r = client.get(f"/api/validation-report/{case}?run_id=audit_real_run")
        assert r.status_code == 200
        body = r.json()
        assert body["profile_verdict"] is None, (
            f"{case}: expected no profile_verdict, got {body['profile_verdict']}"
        )
        assert body["profile_pass_count"] is None
        assert body["profile_total_count"] is None


def test_dec039_schema_fields_present_in_openapi(client: TestClient) -> None:
    """profile_verdict + profile_pass_count + profile_total_count must
    be documented in the OpenAPI schema so frontend/TypeScript clients
    can rely on them."""
    r = client.get("/api/openapi.json")
    assert r.status_code == 200
    spec = r.json()
    vr_schema = spec["components"]["schemas"]["ValidationReport"]
    props = vr_schema["properties"]
    assert "profile_verdict" in props
    assert "profile_pass_count" in props
    assert "profile_total_count" in props
