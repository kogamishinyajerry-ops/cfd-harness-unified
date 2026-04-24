"""TrustGate reducer tests · P1-T2.

Verifies worst-wins aggregation:
  any FAIL → FAIL; else any WARN → WARN; else PASS (including empty input).

Plus: count_by_status histogram, notes aggregation, summary formatting,
convenience properties (passed / has_failures / has_warnings).
"""

from __future__ import annotations

import pytest

from src.metrics import (
    MetricClass,
    MetricReport,
    MetricStatus,
    TrustGateReport,
    reduce_reports,
)


def _r(name: str, status: MetricStatus, notes: str | None = None) -> MetricReport:
    return MetricReport(
        name=name,
        metric_class=MetricClass.POINTWISE,
        status=status,
        notes=notes,
    )


# ---------------------------------------------------------------------------
# Empty input
# ---------------------------------------------------------------------------


def test_reduce_empty_list_is_vacuous_pass() -> None:
    result = reduce_reports([])
    assert result.overall is MetricStatus.PASS
    assert result.reports == ()
    assert result.count_by_status == {
        MetricStatus.PASS: 0,
        MetricStatus.WARN: 0,
        MetricStatus.FAIL: 0,
    }
    assert result.notes == ()
    assert result.passed is True
    assert result.has_failures is False
    assert result.has_warnings is False


# ---------------------------------------------------------------------------
# Single-status cases
# ---------------------------------------------------------------------------


def test_reduce_single_pass() -> None:
    result = reduce_reports([_r("a", MetricStatus.PASS)])
    assert result.overall is MetricStatus.PASS
    assert result.count_by_status[MetricStatus.PASS] == 1


def test_reduce_single_fail_is_fail() -> None:
    result = reduce_reports([_r("a", MetricStatus.FAIL, "boom")])
    assert result.overall is MetricStatus.FAIL
    assert result.has_failures is True
    assert result.notes == ("a [fail]: boom",)


def test_reduce_single_warn_is_warn() -> None:
    result = reduce_reports([_r("a", MetricStatus.WARN, "shaky")])
    assert result.overall is MetricStatus.WARN
    assert result.has_warnings is True
    assert result.has_failures is False
    assert result.notes == ("a [warn]: shaky",)


def test_reduce_all_pass_no_notes() -> None:
    reports = [_r(f"p{i}", MetricStatus.PASS) for i in range(5)]
    result = reduce_reports(reports)
    assert result.overall is MetricStatus.PASS
    assert result.count_by_status[MetricStatus.PASS] == 5
    assert result.notes == ()


# ---------------------------------------------------------------------------
# Worst-wins aggregation
# ---------------------------------------------------------------------------


def test_single_fail_dominates_many_passes() -> None:
    reports = [
        _r("p1", MetricStatus.PASS),
        _r("p2", MetricStatus.PASS),
        _r("f1", MetricStatus.FAIL, "diverged"),
        _r("p3", MetricStatus.PASS),
    ]
    result = reduce_reports(reports)
    assert result.overall is MetricStatus.FAIL
    assert result.count_by_status[MetricStatus.PASS] == 3
    assert result.count_by_status[MetricStatus.FAIL] == 1
    assert "f1 [fail]: diverged" in result.notes


def test_single_fail_dominates_warns() -> None:
    reports = [
        _r("w1", MetricStatus.WARN, "low-conf"),
        _r("f1", MetricStatus.FAIL, "crash"),
        _r("w2", MetricStatus.WARN, "shaky"),
    ]
    result = reduce_reports(reports)
    assert result.overall is MetricStatus.FAIL
    assert result.count_by_status[MetricStatus.WARN] == 2
    assert result.count_by_status[MetricStatus.FAIL] == 1


def test_warn_dominates_pass_but_not_fail() -> None:
    reports = [
        _r("p1", MetricStatus.PASS),
        _r("w1", MetricStatus.WARN, "ok-ish"),
        _r("p2", MetricStatus.PASS),
    ]
    result = reduce_reports(reports)
    assert result.overall is MetricStatus.WARN
    assert result.has_warnings is True
    assert result.has_failures is False


# ---------------------------------------------------------------------------
# Notes order preserves input order + skips PASS/None
# ---------------------------------------------------------------------------


def test_notes_preserve_input_order_and_skip_pass() -> None:
    reports = [
        _r("f1", MetricStatus.FAIL, "first"),
        _r("p1", MetricStatus.PASS, "this-should-be-skipped"),  # PASS → skip
        _r("w1", MetricStatus.WARN, "second"),
        _r("f2", MetricStatus.FAIL, None),  # None → skip even on FAIL
        _r("w2", MetricStatus.WARN, "third"),
    ]
    result = reduce_reports(reports)
    assert result.notes == (
        "f1 [fail]: first",
        "w1 [warn]: second",
        "w2 [warn]: third",
    )


# ---------------------------------------------------------------------------
# Reports list is a defensive copy
# ---------------------------------------------------------------------------


def test_input_mutation_does_not_affect_trust_gate_report() -> None:
    source = [_r("a", MetricStatus.PASS)]
    result = reduce_reports(source)
    source.append(_r("b", MetricStatus.FAIL, "late-addition"))
    assert len(result.reports) == 1
    assert result.overall is MetricStatus.PASS


# ---------------------------------------------------------------------------
# Summary formatting
# ---------------------------------------------------------------------------


def test_summary_includes_verdict_and_counts() -> None:
    reports = [
        _r("p1", MetricStatus.PASS),
        _r("w1", MetricStatus.WARN),
        _r("w2", MetricStatus.WARN),
        _r("f1", MetricStatus.FAIL),
    ]
    result = reduce_reports(reports)
    s = result.summary()
    assert "FAIL" in s
    assert "PASS=1" in s
    assert "WARN=2" in s
    assert "FAIL=1" in s
    assert "n=4" in s


# ---------------------------------------------------------------------------
# TrustGateReport is immutable (frozen dataclass)
# ---------------------------------------------------------------------------


def test_trust_gate_report_is_frozen() -> None:
    result = reduce_reports([])
    with pytest.raises(Exception):
        result.overall = MetricStatus.FAIL  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Regression: Codex V61-055 R1 APPROVE_WITH_COMMENTS — inner container
# immutability. Pre-fix, caller could mutate reports/count_by_status/notes
# post-reduction, silently invalidating summary() / has_* properties.
# ---------------------------------------------------------------------------


def test_reports_tuple_is_immutable() -> None:
    result = reduce_reports([_r("a", MetricStatus.PASS)])
    with pytest.raises((AttributeError, TypeError)):
        result.reports.append(_r("b", MetricStatus.FAIL))  # type: ignore[attr-defined]


def test_count_by_status_is_mapping_proxy() -> None:
    result = reduce_reports([_r("a", MetricStatus.PASS)])
    with pytest.raises(TypeError):
        result.count_by_status[MetricStatus.FAIL] = 999  # type: ignore[index]


def test_notes_tuple_is_immutable() -> None:
    result = reduce_reports([_r("f1", MetricStatus.FAIL, "boom")])
    with pytest.raises((AttributeError, TypeError)):
        result.notes.append("injected")  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Canonical E2E: load_tolerance_policy → evaluate_all → reduce_reports
# (Codex V61-055 R1 noted this gap; adding explicit test per comment.)
# ---------------------------------------------------------------------------


def test_full_pipeline_policy_then_evaluate_then_reduce(tmp_path) -> None:
    from pathlib import Path

    from src.metrics import (
        MetricsRegistry,
        PointwiseMetric,
        load_tolerance_policy,
    )
    from src.models import ExecutionResult

    # Policy: metric 'a' gets 30% tolerance; 'b' + 'c' fall through.
    (tmp_path / "e2e.yaml").write_text(
        """
case_id: e2e
schema_version: 1
tolerance_policy:
  a:
    tolerance: 0.30
""".strip(),
        encoding="utf-8",
    )
    policy = load_tolerance_policy("e2e", case_profiles_dir=tmp_path)

    r = MetricsRegistry()
    r.register(PointwiseMetric(name="a"))
    r.register(PointwiseMetric(name="b"))
    r.register(PointwiseMetric(name="c"))

    artifacts = ExecutionResult(
        success=True,
        is_mock=False,
        key_quantities={"a": 1.25, "b": 1.25, "c": 1.02},
    )
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
        "c": {
            "quantity": "c",
            "reference_values": [{"value": 1.0}],
            "tolerance": 0.05,
        },
    }
    reports = r.evaluate_all(artifacts, observable_defs, tolerance_policy=policy)
    tg = reduce_reports(reports)

    # a: 25% dev, 30% tol → PASS
    # b: 25% dev, 5% tol  → FAIL
    # c: 2% dev,  5% tol  → PASS
    # overall: FAIL (b fails, dominates)
    assert tg.overall is MetricStatus.FAIL
    assert tg.count_by_status[MetricStatus.PASS] == 2
    assert tg.count_by_status[MetricStatus.FAIL] == 1
    assert any("b [fail]" in n for n in tg.notes)
    # Policy-dispatched tolerances surface in the underlying reports:
    by_name = {rep.name: rep for rep in tg.reports}
    assert by_name["a"].tolerance_applied == pytest.approx(0.30)
    assert by_name["b"].tolerance_applied == pytest.approx(0.05)


# ---------------------------------------------------------------------------
# End-to-end with MetricsRegistry
# ---------------------------------------------------------------------------


def test_reduce_integrates_with_registry_evaluate_all() -> None:
    from src.metrics import MetricsRegistry, PointwiseMetric
    from src.models import ExecutionResult

    r = MetricsRegistry()
    r.register(PointwiseMetric(name="a"))
    r.register(PointwiseMetric(name="b"))
    r.register(PointwiseMetric(name="c"))

    artifacts = ExecutionResult(
        success=True,
        is_mock=False,
        key_quantities={"a": 1.0, "b": 1.5, "c": 2.0},  # b: 50% off, c: 100% off
    )
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
        "c": {
            "quantity": "c",
            "reference_values": [{"value": 1.0}],
            "tolerance": 0.05,
        },
    }
    reports = r.evaluate_all(artifacts, observable_defs)
    tg = reduce_reports(reports)
    assert tg.overall is MetricStatus.FAIL
    assert tg.count_by_status[MetricStatus.PASS] == 1
    assert tg.count_by_status[MetricStatus.FAIL] == 2
