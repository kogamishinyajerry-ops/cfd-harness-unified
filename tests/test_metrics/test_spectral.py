"""SpectralMetric tests · P1-T1c.

SpectralMetric consumes pre-extracted Strouhal scalars from
`ExecutionResult.key_quantities` (the FFT pipeline runs upstream in
Execution Plane; Evaluation Plane reads, not runs — ADR-001 Contract 2).

Status matrix:
  - value within tolerance + low_confidence=False → PASS
  - value within tolerance + low_confidence=True  → WARN (demotion)
  - value outside tolerance (regardless of low_confidence) → FAIL
  - quantity missing from key_quantities → FAIL (inherited from comparator)

The FFT extractor itself (cylinder_strouhal_fft.emit_strouhal) is
tested independently in test_cylinder_strouhal_fft.py.
"""

from __future__ import annotations

import pytest

from src.metrics import MetricClass, MetricStatus, SpectralMetric
from src.models import ExecutionResult


def _exec(**kq) -> ExecutionResult:
    return ExecutionResult(success=True, is_mock=False, key_quantities=dict(kq))


# ---------------------------------------------------------------------------
# Happy path — value within tolerance + high confidence → PASS
# ---------------------------------------------------------------------------


def test_spectral_pass_high_confidence_within_tolerance() -> None:
    m = SpectralMetric(name="cylinder_wake_strouhal")
    report = m.evaluate(
        artifacts=_exec(
            cylinder_wake_strouhal=0.163,
            strouhal_low_confidence=False,
        ),
        observable_def={
            "quantity": "cylinder_wake_strouhal",
            "reference_values": [{"St": 0.164}],
            "tolerance": 0.05,
        },
    )
    assert report.status is MetricStatus.PASS
    assert report.value == pytest.approx(0.163)
    assert report.reference_value == pytest.approx(0.164)
    assert report.metric_class is MetricClass.SPECTRAL
    assert report.provenance["delegate_module"] == "src.cylinder_strouhal_fft"
    assert report.provenance["low_confidence"] is False
    assert report.notes is None


# ---------------------------------------------------------------------------
# Low-confidence demotion — PASS → WARN
# ---------------------------------------------------------------------------


def test_spectral_warn_when_low_confidence_demotes_pass() -> None:
    m = SpectralMetric(name="strouhal_number")
    report = m.evaluate(
        artifacts=_exec(
            strouhal_number=0.163,
            strouhal_low_confidence=True,
        ),
        observable_def={
            "quantity": "strouhal_number",
            "reference_values": [{"St": 0.164}],
            "tolerance": 0.05,
        },
    )
    assert report.status is MetricStatus.WARN
    assert report.provenance["low_confidence"] is True
    assert "low_confidence" in report.notes


def test_spectral_low_confidence_via_quantity_prefixed_key() -> None:
    # Custom observable: `my_spectral_x` with companion `my_spectral_x_low_confidence`
    m = SpectralMetric(name="my_spectral_x")
    report = m.evaluate(
        artifacts=_exec(
            my_spectral_x=1.0,
            my_spectral_x_low_confidence=True,
        ),
        observable_def={
            "quantity": "my_spectral_x",
            "reference_values": [{"value": 1.0}],
            "tolerance": 0.05,
        },
    )
    assert report.status is MetricStatus.WARN
    assert report.provenance["low_confidence"] is True


def test_spectral_low_confidence_via_explicit_key_override() -> None:
    m = SpectralMetric(
        name="strouhal_number", low_confidence_key="custom_lc_flag"
    )
    report = m.evaluate(
        artifacts=_exec(
            strouhal_number=0.163,
            custom_lc_flag=True,
        ),
        observable_def={
            "quantity": "strouhal_number",
            "reference_values": [{"St": 0.164}],
            "tolerance": 0.05,
        },
    )
    assert report.status is MetricStatus.WARN


# ---------------------------------------------------------------------------
# Low-confidence does NOT upgrade FAIL → WARN
# ---------------------------------------------------------------------------


def test_spectral_low_confidence_does_not_upgrade_fail() -> None:
    m = SpectralMetric(name="strouhal_number")
    # Value 0.10 vs ref 0.164 → ~39% deviation → FAIL regardless of confidence.
    report = m.evaluate(
        artifacts=_exec(
            strouhal_number=0.10,
            strouhal_low_confidence=True,
        ),
        observable_def={
            "quantity": "strouhal_number",
            "reference_values": [{"St": 0.164}],
            "tolerance": 0.05,
        },
    )
    assert report.status is MetricStatus.FAIL
    assert report.provenance["low_confidence"] is True


# ---------------------------------------------------------------------------
# FAIL paths — quantity missing, reference deviation
# ---------------------------------------------------------------------------


def test_spectral_fail_quantity_missing() -> None:
    m = SpectralMetric(name="strouhal_number")
    report = m.evaluate(
        artifacts=_exec(cd_mean=1.33),  # no strouhal_number
        observable_def={
            "quantity": "strouhal_number",
            "reference_values": [{"St": 0.164}],
            "tolerance": 0.05,
        },
    )
    assert report.status is MetricStatus.FAIL
    assert report.value is None
    assert "strouhal_number" in report.notes


def test_spectral_fail_outside_tolerance_high_confidence() -> None:
    m = SpectralMetric(name="strouhal_number")
    report = m.evaluate(
        artifacts=_exec(
            strouhal_number=0.20,
            strouhal_low_confidence=False,
        ),
        observable_def={
            "quantity": "strouhal_number",
            "reference_values": [{"St": 0.164}],
            "tolerance": 0.05,
        },
    )
    assert report.status is MetricStatus.FAIL
    assert report.deviation is not None and report.deviation > 0.05


# ---------------------------------------------------------------------------
# Tolerance policy override
# ---------------------------------------------------------------------------


def test_spectral_tolerance_policy_loosens_bound() -> None:
    # 0.15 vs 0.164 → ~8.5% deviation. Tight 5% FAIL; loose 15% PASS.
    m = SpectralMetric(name="strouhal_number")
    report = m.evaluate(
        artifacts=_exec(strouhal_number=0.15, strouhal_low_confidence=False),
        observable_def={
            "quantity": "strouhal_number",
            "reference_values": [{"St": 0.164}],
            "tolerance": 0.05,
        },
        tolerance_policy={"tolerance": 0.15},
    )
    assert report.status is MetricStatus.PASS
    assert report.tolerance_applied == pytest.approx(0.15)
    assert report.provenance["tolerance_source"] == "tolerance_policy"


# ---------------------------------------------------------------------------
# Absent low-confidence flag → treat as confident (no demotion)
# ---------------------------------------------------------------------------


def test_spectral_absent_low_confidence_flag_is_confident() -> None:
    m = SpectralMetric(name="strouhal_number")
    report = m.evaluate(
        artifacts=_exec(strouhal_number=0.163),  # no _low_confidence key at all
        observable_def={
            "quantity": "strouhal_number",
            "reference_values": [{"St": 0.164}],
            "tolerance": 0.05,
        },
    )
    assert report.status is MetricStatus.PASS
    assert report.provenance["low_confidence"] is False
