"""MetricsRegistry unit tests · P1-T1 MVP.

Verifies registry CRUD + filter_by_class + evaluate_all iteration. Does
NOT exercise concrete metric extraction (per-metric-class DECs are future
work); confirms that evaluate() on an MVP Metric raises NotImplementedError
as documented.
"""

from __future__ import annotations

import pytest

from src.metrics import (
    IntegratedMetric,
    Metric,
    MetricClass,
    MetricReport,
    MetricStatus,
    MetricsRegistry,
    PointwiseMetric,
    ResidualMetric,
    SpectralMetric,
)


def test_registry_empty_at_construction() -> None:
    r = MetricsRegistry()
    assert len(r) == 0
    assert r.names() == []
    assert r.lookup("anything") is None
    assert "anything" not in r


def test_register_and_lookup() -> None:
    r = MetricsRegistry()
    m = PointwiseMetric(name="u_centerline_y0.5", unit="m/s")
    r.register(m)
    assert len(r) == 1
    assert "u_centerline_y0.5" in r
    assert r.lookup("u_centerline_y0.5") is m
    assert r.names() == ["u_centerline_y0.5"]


def test_register_collision_raises() -> None:
    r = MetricsRegistry()
    r.register(PointwiseMetric(name="x"))
    with pytest.raises(KeyError, match="already registered"):
        r.register(IntegratedMetric(name="x"))


def test_unregister_then_reregister_ok() -> None:
    r = MetricsRegistry()
    m1 = PointwiseMetric(name="x")
    r.register(m1)
    removed = r.unregister("x")
    assert removed is m1
    assert "x" not in r
    r.register(IntegratedMetric(name="x"))
    assert isinstance(r.lookup("x"), IntegratedMetric)


def test_unregister_missing_returns_none() -> None:
    r = MetricsRegistry()
    assert r.unregister("nope") is None


def test_filter_by_class() -> None:
    r = MetricsRegistry()
    r.register(PointwiseMetric(name="p1"))
    r.register(PointwiseMetric(name="p2"))
    r.register(IntegratedMetric(name="cd"))
    r.register(SpectralMetric(name="St"))
    r.register(ResidualMetric(name="final_p"))

    pointwise = r.filter_by_class(MetricClass.POINTWISE)
    assert sorted(m.name for m in pointwise) == ["p1", "p2"]

    integrated = r.filter_by_class(MetricClass.INTEGRATED)
    assert [m.name for m in integrated] == ["cd"]

    spectral = r.filter_by_class(MetricClass.SPECTRAL)
    assert [m.name for m in spectral] == ["St"]

    residual = r.filter_by_class(MetricClass.RESIDUAL)
    assert [m.name for m in residual] == ["final_p"]


def test_iteration_returns_all_metrics() -> None:
    r = MetricsRegistry()
    r.register(PointwiseMetric(name="a"))
    r.register(IntegratedMetric(name="b"))
    found_names = {m.name for m in r}
    assert found_names == {"a", "b"}


def test_evaluate_all_skips_missing_observable_def() -> None:
    r = MetricsRegistry()
    r.register(PointwiseMetric(name="has_obs"))
    r.register(PointwiseMetric(name="no_obs"))
    observable_defs = {"has_obs": {"quantity": "u", "tolerance": 0.05}}

    # Both metrics raise NotImplementedError on evaluate() in MVP; the
    # 'no_obs' metric should be skipped (no observable def), so the
    # iteration should hit 'has_obs' first and raise immediately.
    with pytest.raises(NotImplementedError, match="has no evaluate"):
        r.evaluate_all({}, observable_defs)


def test_evaluate_all_empty_when_no_matching_defs() -> None:
    r = MetricsRegistry()
    r.register(PointwiseMetric(name="orphan"))
    # No observable defs at all → iteration skips all metrics → empty list
    reports = r.evaluate_all({}, observable_defs={})
    assert reports == []


def test_concrete_metric_classes_carry_correct_metadata() -> None:
    assert PointwiseMetric.metric_class is MetricClass.POINTWISE
    assert IntegratedMetric.metric_class is MetricClass.INTEGRATED
    assert SpectralMetric.metric_class is MetricClass.SPECTRAL
    assert ResidualMetric.metric_class is MetricClass.RESIDUAL

    # Each subclass declares its delegate module for traceability.
    assert PointwiseMetric.delegate_to_module == "src.result_comparator"
    assert IntegratedMetric.delegate_to_module == "src.result_comparator"
    assert SpectralMetric.delegate_to_module == "src.cylinder_strouhal_fft"
    assert ResidualMetric.delegate_to_module == "src.convergence_attestor"


def test_metric_report_defaults_are_sensible() -> None:
    rep = MetricReport(name="x", metric_class=MetricClass.POINTWISE)
    assert rep.value is None
    assert rep.unit == "dimensionless"
    assert rep.status is MetricStatus.PASS  # default optimistic
    assert rep.provenance == {}
    assert rep.version_metadata == {}
    assert rep.notes is None


def test_metric_repr_includes_class_and_delegate() -> None:
    m = SpectralMetric(name="St")
    s = repr(m)
    assert "SpectralMetric" in s
    assert "St" in s
    assert "spectral" in s
    assert "cylinder_strouhal_fft" in s
