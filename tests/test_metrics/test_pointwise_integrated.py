"""PointwiseMetric + IntegratedMetric extractor-wrap tests · P1-T1ab.

Covers the shared `_comparator_wrap.evaluate_via_result_comparator` path:
scalar happy-path, missing quantity, tolerance-policy override, integrated
metric class label + delegate traceability, dict-artifact coercion.

The underlying `src.result_comparator` is exercised in its own test file;
here we only verify the wrapper correctly maps ComparisonResult → MetricReport.
"""

from __future__ import annotations

import pytest

from src.metrics import (
    IntegratedMetric,
    MetricClass,
    MetricStatus,
    PointwiseMetric,
)
from src.models import ExecutionResult


def _exec(**kq) -> ExecutionResult:
    return ExecutionResult(success=True, is_mock=False, key_quantities=dict(kq))


# ---------------------------------------------------------------------------
# Pointwise happy path
# ---------------------------------------------------------------------------


def test_pointwise_scalar_pass_within_tolerance() -> None:
    m = PointwiseMetric(name="u_centerline_y0.5", unit="m/s")
    report = m.evaluate(
        artifacts=_exec(u_centerline_y0_5=0.98),
        observable_def={
            "quantity": "u_centerline_y0_5",
            "reference_values": [{"value": 1.0}],
            "tolerance": 0.05,
        },
    )
    assert report.status is MetricStatus.PASS
    assert report.value == pytest.approx(0.98)
    assert report.reference_value == pytest.approx(1.0)
    assert report.deviation == pytest.approx(0.02, rel=1e-6)
    assert report.tolerance_applied == pytest.approx(0.05)
    assert report.metric_class is MetricClass.POINTWISE
    assert report.provenance["delegate_module"] == "src.result_comparator"
    assert report.provenance["tolerance_source"] == "observable_def"
    assert report.notes is None


def test_pointwise_scalar_fails_when_exceeds_tolerance() -> None:
    m = PointwiseMetric(name="cp_x03")
    report = m.evaluate(
        artifacts=_exec(cp_x03=0.5),
        observable_def={
            "quantity": "cp_x03",
            "reference_values": [{"Cp": 1.0}],  # ref-scalar via alias key
            "tolerance": 0.05,
        },
    )
    assert report.status is MetricStatus.FAIL
    assert report.deviation is not None and report.deviation > 0.05
    assert report.notes is not None
    assert "cp_x03" in report.notes


def test_pointwise_missing_quantity_fails_with_helpful_note() -> None:
    m = PointwiseMetric(name="u_centerline")
    report = m.evaluate(
        artifacts=_exec(other_quantity=1.0),
        observable_def={
            "quantity": "u_centerline",
            "reference_values": [{"value": 1.0}],
        },
    )
    assert report.status is MetricStatus.FAIL
    assert report.value is None
    assert report.notes is not None
    assert "u_centerline" in report.notes
    assert "not found" in report.notes.lower()


# ---------------------------------------------------------------------------
# Tolerance-policy override (VCP §8.2 dispatch)
# ---------------------------------------------------------------------------


def test_tolerance_policy_override_wins_over_observable_def() -> None:
    m = PointwiseMetric(name="Nu_wall")
    # Value deviates 8%. With observable_def tolerance 5% it would FAIL.
    # tolerance_policy=0.10 overrides → PASS.
    report = m.evaluate(
        artifacts=_exec(Nu_wall=1.08),
        observable_def={
            "quantity": "Nu_wall",
            "reference_values": [{"Nu": 1.0}],
            "tolerance": 0.05,
        },
        tolerance_policy={"tolerance": 0.10},
    )
    assert report.status is MetricStatus.PASS
    assert report.tolerance_applied == pytest.approx(0.10)
    assert report.provenance["tolerance_source"] == "tolerance_policy"


def test_tolerance_policy_without_tolerance_key_is_ignored() -> None:
    # Only recognized key is "tolerance"; other metadata should not be
    # interpreted as an override.
    m = PointwiseMetric(name="x")
    report = m.evaluate(
        artifacts=_exec(x=1.0),
        observable_def={
            "quantity": "x",
            "reference_values": [{"value": 1.0}],
            "tolerance": 0.05,
        },
        tolerance_policy={"rule": "per-metric-class-default"},
    )
    assert report.status is MetricStatus.PASS
    assert report.tolerance_applied == pytest.approx(0.05)
    assert report.provenance["tolerance_source"] == "observable_def"


# ---------------------------------------------------------------------------
# IntegratedMetric — same wrapper, different metric_class label
# ---------------------------------------------------------------------------


def test_integrated_cd_mean_pass() -> None:
    m = IntegratedMetric(name="cd_mean")
    report = m.evaluate(
        artifacts=_exec(cd_mean=1.2),
        observable_def={
            "quantity": "cd_mean",
            "reference_values": [{"value": 1.25}],
            "tolerance": 0.10,
        },
    )
    assert report.status is MetricStatus.PASS
    assert report.metric_class is MetricClass.INTEGRATED
    assert report.provenance["delegate_module"] == "src.result_comparator"


def test_integrated_fails_when_reference_zero_and_value_large() -> None:
    # Near-zero reference uses absolute-error fallback per
    # result_comparator._compare_scalar. Keep the wrapper consistent.
    m = IntegratedMetric(name="reattachment_length_xr")
    report = m.evaluate(
        artifacts=_exec(reattachment_length_xr=0.5),
        observable_def={
            "quantity": "reattachment_length_xr",
            "reference_values": [{"value": 0.0}],
            "tolerance": 0.1,
        },
    )
    assert report.status is MetricStatus.FAIL


# ---------------------------------------------------------------------------
# Artifact coercion: dict with key_quantities vs raw dict vs ExecutionResult
# ---------------------------------------------------------------------------


def test_dict_artifacts_with_key_quantities_key() -> None:
    m = PointwiseMetric(name="u")
    report = m.evaluate(
        artifacts={"key_quantities": {"u": 1.0}},
        observable_def={
            "quantity": "u",
            "reference_values": [{"value": 1.0}],
            "tolerance": 0.01,
        },
    )
    assert report.status is MetricStatus.PASS
    assert report.value == pytest.approx(1.0)


def test_dict_artifacts_as_bare_kq_dict() -> None:
    m = PointwiseMetric(name="u")
    report = m.evaluate(
        artifacts={"u": 1.0},
        observable_def={
            "quantity": "u",
            "reference_values": [{"value": 1.0}],
            "tolerance": 0.01,
        },
    )
    assert report.status is MetricStatus.PASS


def test_artifacts_type_error_on_non_dict_non_exec_result() -> None:
    m = PointwiseMetric(name="u")
    with pytest.raises(TypeError, match="ExecutionResult or dict-like"):
        m.evaluate(
            artifacts="not a dict",
            observable_def={
                "quantity": "u",
                "reference_values": [{"value": 1.0}],
            },
        )


# ---------------------------------------------------------------------------
# Alias resolution — canonical quantity name + alias lookup
# ---------------------------------------------------------------------------


def test_canonical_alias_resolution_via_comparator() -> None:
    # Gold declares canonical "friction_factor" but solver emitted "f".
    # result_comparator's CANONICAL_ALIASES handles this — wrapper inherits it.
    m = IntegratedMetric(name="friction_factor")
    report = m.evaluate(
        artifacts=_exec(f=0.031),
        observable_def={
            "quantity": "friction_factor",
            "reference_values": [{"f": 0.030}],
            "tolerance": 0.10,
        },
    )
    # value comes from key_quantities lookup at canonical name; alias
    # match happens inside comparator, so value field may be None while
    # status is still PASS.
    assert report.status is MetricStatus.PASS


# ---------------------------------------------------------------------------
# Registry integration
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Regression: Codex DEC-V61-054 R1 finding #1 — wrapper PASS→FAIL false-fail
# when reference_values is heterogeneous and entry[0] has a key the
# comparator skips. Wrapper must mirror comparator's iteration order + key set.
# ---------------------------------------------------------------------------


def test_wrapper_and_comparator_agree_on_heterogeneous_reference_values() -> None:
    # Codex repro: reference_values = [{'u': 2.0}, {'value': 1.0}], actual=1.0.
    # Pre-fix: wrapper picked entry[0]["u"]=2.0 → deviation 0.5 → FALSE FAIL.
    # Post-fix: comparator-canonical order walks entries; "u" is now in the
    # shared REF_SCALAR_KEYS, so wrapper picks entry[0]["u"]=2.0 and FAILs
    # consistently — OR comparator was updated to see "u" too, also FAILing
    # consistently. Either way wrapper + comparator must agree.
    m = PointwiseMetric(name="x")
    report = m.evaluate(
        artifacts=_exec(x=1.0),
        observable_def={
            "quantity": "x",
            "reference_values": [{"u": 2.0}, {"value": 1.0}],
            "tolerance": 0.1,
        },
    )
    # With REF_SCALAR_KEYS = (value, u, u_plus, Nu, Cp, Cf, f, St),
    # comparator picks entry[0]["u"]=2.0 first → abs_err=1.0 → FAIL.
    # Wrapper picks the same. They agree.
    assert report.status is MetricStatus.FAIL
    assert report.reference_value == pytest.approx(2.0)


def test_wrapper_empty_first_entry_walks_to_next() -> None:
    # reference_values = [{unrecognized key}, {'value': 1.0}]. Wrapper
    # should skip entry[0] (no scalar-keyed value) and pick entry[1]["value"].
    m = PointwiseMetric(name="x")
    report = m.evaluate(
        artifacts=_exec(x=1.0),
        observable_def={
            "quantity": "x",
            "reference_values": [{"unknown_key": 99.0}, {"value": 1.0}],
            "tolerance": 0.05,
        },
    )
    assert report.status is MetricStatus.PASS
    assert report.reference_value == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Regression: Codex DEC-V61-054 R1 finding #2 — tolerance_policy top-level
# leak into unrelated metrics. Per-metric dispatch must NOT fall back to
# whole-dict when per-name entry is absent.
# ---------------------------------------------------------------------------


def test_tolerance_policy_top_level_does_not_leak_into_unrelated_metrics() -> None:
    from src.metrics import MetricsRegistry

    r = MetricsRegistry()
    r.register(PointwiseMetric(name="a"))
    r.register(PointwiseMetric(name="b"))
    artifacts = _exec(a=1.25, b=1.25)  # both 25% off
    observable_defs = {
        "a": {
            "quantity": "a",
            "reference_values": [{"value": 1.0}],
            "tolerance": 0.05,
        },
        "b": {
            "quantity": "b",
            "reference_values": [{"value": 1.0}],
            "tolerance": 0.05,
        },
    }
    # Policy only addresses metric `a` explicitly. The top-level "tolerance"
    # must NOT be inherited by metric `b`.
    tolerance_policy = {"tolerance": 0.5, "a": {"tolerance": 0.3}}

    reports = r.evaluate_all(artifacts, observable_defs, tolerance_policy)
    by_name = {rep.name: rep for rep in reports}

    # `a` got its named 0.3 override → 25% < 30% → PASS
    assert by_name["a"].status is MetricStatus.PASS
    assert by_name["a"].tolerance_applied == pytest.approx(0.3)

    # `b` had no named override → falls back to observable_def 0.05
    # → 25% > 5% → FAIL. Crucially NOT 0.5 from the outer dict.
    assert by_name["b"].status is MetricStatus.FAIL
    assert by_name["b"].tolerance_applied == pytest.approx(0.05)


def test_registry_evaluate_all_exercises_wrapper() -> None:
    from src.metrics import MetricsRegistry

    r = MetricsRegistry()
    r.register(PointwiseMetric(name="a"))
    r.register(IntegratedMetric(name="b"))
    artifacts = _exec(a=1.0, b=2.0)
    observable_defs = {
        "a": {
            "quantity": "a",
            "reference_values": [{"value": 1.0}],
            "tolerance": 0.01,
        },
        "b": {
            "quantity": "b",
            "reference_values": [{"value": 2.0}],
            "tolerance": 0.01,
        },
    }
    reports = r.evaluate_all(artifacts, observable_defs)
    assert {rep.name for rep in reports} == {"a", "b"}
    assert all(rep.status is MetricStatus.PASS for rep in reports)
