"""DEC-V61-036 G1 tests: missing-target-quantity hard gate.

Tests assert that cases whose audit_real_run fixture has
`extraction_source: key_quantities_fallback` (i.e., the silent-substitution
bug fired) are now hard-FAILed with a MISSING_TARGET_QUANTITY concern,
and that cases with `extraction_source: comparator_deviation` retain
their pre-G1 verdicts.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from ui.backend.main import app


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


# The 4 cases whose audit_real_run fixtures carry the PASS-washing marker.
# Verified empirically via scripts/phase5_audit_run.py pre-DEC-V61-036:
# BFS emitted U_residual_magnitude against gold reattachment_length,
# cylinder emitted a scalar mis-keyed, duct emitted hydraulic_diameter
# against friction_factor, plane_channel emitted U_max_approx against
# u_mean_profile.
PASS_WASHING_CASES = [
    "backward_facing_step",
    "circular_cylinder_wake",
    "duct_flow",
    "plane_channel_flow",
]


@pytest.mark.parametrize("case_id", PASS_WASHING_CASES)
def test_g1_pass_washing_cases_fail_with_missing_target_quantity(
    client: TestClient, case_id: str
) -> None:
    """Each pre-DEC-036 PASS-washing case must now FAIL with a
    MISSING_TARGET_QUANTITY audit concern on the audit_real_run default."""
    response = client.get(f"/api/validation-report/{case_id}?run_id=audit_real_run")
    assert response.status_code == 200, f"{case_id}: {response.text}"
    body = response.json()
    assert body["contract_status"] == "FAIL", (
        f"{case_id}: expected FAIL (G1 gate), got {body['contract_status']}. "
        "Either the fixture was regenerated with a real extractor (good — "
        "remove from PASS_WASHING_CASES) or the G1 trigger missed."
    )
    concern_types = {c["concern_type"] for c in body["audit_concerns"]}
    assert "MISSING_TARGET_QUANTITY" in concern_types, (
        f"{case_id}: expected MISSING_TARGET_QUANTITY concern, got {concern_types}"
    )


def test_g1_honest_cases_preserve_pre_g1_verdict(client: TestClient) -> None:
    """DHC audit_real_run has extraction_source=comparator_deviation — the
    comparator DID find the gold's nusselt_number. G1 must NOT force FAIL
    on it. Pre-G1 behaviour preserved."""
    response = client.get(
        "/api/validation-report/differential_heated_cavity?run_id=audit_real_run"
    )
    assert response.status_code == 200
    body = response.json()
    concern_types = {c["concern_type"] for c in body["audit_concerns"]}
    # Comparator correctly extracted the gold quantity — MISSING_TARGET_QUANTITY
    # must NOT fire here (would be a false positive).
    assert "MISSING_TARGET_QUANTITY" not in concern_types, (
        f"DHC comparator_deviation fixture should NOT trigger G1; concerns: {concern_types}"
    )


def test_g1_ldc_reference_pass_unchanged(client: TestClient) -> None:
    """LDC reference_pass is a curated PASS run that passed comparator pre-G1.
    Extraction source is comparator_deviation (or direct). G1 must not
    break this PASS narrative."""
    response = client.get(
        "/api/validation-report/lid_driven_cavity?run_id=reference_pass"
    )
    assert response.status_code == 200
    body = response.json()
    concern_types = {c["concern_type"] for c in body["audit_concerns"]}
    assert "MISSING_TARGET_QUANTITY" not in concern_types


def test_g1_value_none_forces_fail(client: TestClient) -> None:
    """Synthetic contract: when measurement.value is None, _derive_contract_status
    must return FAIL with deviation_pct=None and within_tolerance=None."""
    # Build via direct service call — avoids needing a new fixture on disk.
    from ui.backend.schemas.validation import (
        AuditConcern,
        GoldStandardReference,
        MeasuredValue,
    )
    from ui.backend.services.validation_report import _derive_contract_status

    gs = GoldStandardReference(
        quantity="friction_factor",
        ref_value=0.0185,
        unit="dimensionless",
        tolerance_pct=0.10,
        citation="Colebrook 1939",
    )
    m = MeasuredValue(
        value=None,
        source="fixture",
        quantity="friction_factor",
        extraction_source="no_numeric_quantity",
    )
    concerns = [
        AuditConcern(
            concern_type="MISSING_TARGET_QUANTITY",
            summary="synthetic",
        )
    ]
    status, deviation, within, lower, upper = _derive_contract_status(
        gs, m, preconditions=[], audit_concerns=concerns
    )
    assert status == "FAIL"
    assert deviation is None
    assert within is None


def test_g1_profile_quantity_bracketed_deviation_is_honest() -> None:
    """DEC-V61-036 G1 round 2 (Codex BLOCKER B1): when the gold's quantity
    is a profile (e.g., `u_centerline`), the comparator emits deviations
    named `u_centerline[y=0.3750]`, not `u_centerline`. The driver must
    match the bracketed form as an honest extraction, NOT falsely fall
    through to `no_numeric_quantity` and hard-FAIL the case.
    """
    import types

    from scripts.phase5_audit_run import _primary_scalar

    # Fake ComparisonResult with a profile deviation.
    fake_dev = types.SimpleNamespace(
        quantity="u_centerline[y=0.3750]", actual=0.12345, expected=0.16486
    )
    fake_comp = types.SimpleNamespace(deviations=[fake_dev], passed=False, summary="")
    fake_exec = types.SimpleNamespace(key_quantities={"u_centerline": [0.1, 0.2, 0.3]})
    fake_report = types.SimpleNamespace(
        comparison_result=fake_comp, execution_result=fake_exec
    )
    quantity, value, src = _primary_scalar(fake_report, expected_quantity="u_centerline")
    assert quantity == "u_centerline[y=0.3750]"
    assert value == pytest.approx(0.12345)
    assert src == "comparator_deviation"


def test_g1_profile_quantity_list_value_accepted_when_no_deviations() -> None:
    """When the comparator produced NO deviations (profile fully within
    tolerance) but key_quantities has a list for the gold's quantity, the
    driver must accept it as an honest extraction and record a
    `key_quantities_profile_sample` source — NOT hard-FAIL."""
    import types

    from scripts.phase5_audit_run import _primary_scalar

    fake_comp = types.SimpleNamespace(deviations=[], passed=True, summary="")
    fake_exec = types.SimpleNamespace(
        key_quantities={"u_centerline": [0.111, 0.222, 0.333]}
    )
    fake_report = types.SimpleNamespace(
        comparison_result=fake_comp, execution_result=fake_exec
    )
    quantity, value, src = _primary_scalar(fake_report, expected_quantity="u_centerline")
    assert quantity == "u_centerline[0]"
    assert value == pytest.approx(0.111)
    assert src == "key_quantities_profile_sample"


def test_g1_measurement_quantity_field_propagates(client: TestClient) -> None:
    """DEC-V61-036 added MeasuredValue.quantity + extraction_source fields.
    Verify they surface in the API response for downstream UI use."""
    response = client.get(
        "/api/validation-report/backward_facing_step?run_id=audit_real_run"
    )
    body = response.json()
    m = body.get("measurement") or {}
    # Field must be present in the payload (may be null or a string).
    assert "quantity" in m
    assert "extraction_source" in m
