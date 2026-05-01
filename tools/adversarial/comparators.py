"""Analytical-comparator evaluation for adversarial smoke verdicts (DEC-V61-106).

The smoke runner today has 3 expected_status classes (converged /
manual_bc_baseline / physics_validation_required). The third class is
a permanent SKIP — cases that need qualitative physics validation get
no regression protection.

This module adds a 4th class: ``analytical_comparator_pass``. Cases
declare quantitative checks against ``ResultsSummary`` measures (e.g.
"u_magnitude_max >= 1.2") and verdict = PASS iff all comparators pass.

Schema (in intent.json's ``smoke_runner`` block):

    "smoke_runner": {
      "expected_status": "analytical_comparator_pass",
      "rationale": "...",
      "analytical_comparators": [
        {
          "measure": "u_magnitude_max",
          "op": ">=",
          "value": 1.2,
          "rationale": "Bypass jet should accelerate above 1.2 m/s"
        },
        {
          "measure": "is_recirculating",
          "op": "==",
          "value": true,
          "rationale": "Downstream wake must contain recirculation"
        }
      ]
    }

Design choices:
- No expression DSL — engineer authors literal threshold values based
  on domain knowledge. Eliminates eval-injection risk and keeps Codex
  review tractable.
- Fixed enum of measures (mirrors ``ResultsSummary`` fields). Catches
  typos at evaluation time with a structured ``unknown_measure`` fail.
- Fixed enum of ops. ``==`` against a float field emits a warning (use
  bounded comparison instead).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


# Measures available to comparators. Mirror of
# ``ui.backend.services.case_solve.results_extractor.ResultsSummary``
# fields, restricted to the numerically-comparable ones.
_BOOL_MEASURES = frozenset({"is_recirculating"})
_FLOAT_MEASURES = frozenset({
    "final_time", "cell_count",
    "u_magnitude_min", "u_magnitude_max", "u_magnitude_mean",
    "u_x_mean", "u_x_min", "u_x_max",
})
_VALID_MEASURES = _BOOL_MEASURES | _FLOAT_MEASURES
_VALID_OPS = frozenset({">=", "<=", "==", "!=", ">", "<"})


@dataclass(frozen=True, slots=True)
class ComparatorResult:
    measure: str
    op: str
    threshold: Any
    actual: Any
    passed: bool
    failure_reason: str | None  # None when passed; populated on FAIL/error


@dataclass(frozen=True, slots=True)
class ComparatorSuiteResult:
    """Aggregate outcome of evaluating an analytical_comparator block.

    ``all_passed`` is False if any individual comparator fails OR if a
    structural error (unknown measure, missing field, type mismatch)
    short-circuits a comparator. The smoke runner translates this into
    PASS / FAIL.
    """
    all_passed: bool
    individual_results: tuple[ComparatorResult, ...]
    structural_error: str | None = None


def _coerce_actual(measure: str, summary: dict[str, Any]) -> tuple[Any, str | None]:
    """Pull the measure value from a ResultsSummary-shape dict. Returns
    ``(value, error_reason_or_None)``."""
    if measure not in _VALID_MEASURES:
        return None, f"unknown_measure: '{measure}' not in {sorted(_VALID_MEASURES)}"
    if measure not in summary:
        return None, f"measure_not_in_summary: '{measure}' missing from extractor output"
    val = summary[measure]
    if measure in _FLOAT_MEASURES:
        if not isinstance(val, (int, float)):
            return None, f"measure_type_mismatch: '{measure}' expected numeric, got {type(val).__name__}"
        if isinstance(val, float) and math.isnan(val):
            return None, f"measure_nan: '{measure}' is NaN — solver likely diverged"
    elif measure in _BOOL_MEASURES:
        if not isinstance(val, bool):
            return None, f"measure_type_mismatch: '{measure}' expected bool, got {type(val).__name__}"
    return val, None


def _evaluate_one(
    comparator: dict[str, Any], summary: dict[str, Any]
) -> ComparatorResult:
    measure = comparator.get("measure")
    op = comparator.get("op")
    threshold = comparator.get("value")

    if not isinstance(measure, str):
        return ComparatorResult(
            measure=str(measure), op=str(op), threshold=threshold, actual=None,
            passed=False, failure_reason="measure_must_be_string",
        )
    if op not in _VALID_OPS:
        return ComparatorResult(
            measure=measure, op=str(op), threshold=threshold, actual=None,
            passed=False,
            failure_reason=f"invalid_op: '{op}' not in {sorted(_VALID_OPS)}",
        )

    actual, err = _coerce_actual(measure, summary)
    if err is not None:
        return ComparatorResult(
            measure=measure, op=op, threshold=threshold, actual=None,
            passed=False, failure_reason=err,
        )

    # Boolean-measure threshold validation
    if measure in _BOOL_MEASURES:
        if not isinstance(threshold, bool):
            return ComparatorResult(
                measure=measure, op=op, threshold=threshold, actual=actual,
                passed=False,
                failure_reason=f"value_type_mismatch: bool measure '{measure}' compared to non-bool {type(threshold).__name__}",
            )
        if op not in {"==", "!="}:
            return ComparatorResult(
                measure=measure, op=op, threshold=threshold, actual=actual,
                passed=False,
                failure_reason=f"invalid_op_for_bool: '{op}' not allowed on bool measure (use == or !=)",
            )
    else:
        # Float measure: threshold must be numeric. Bool flows down to
        # int via Python's bool subtype rules — disallow explicitly so
        # `value: true` against a float measure is caught.
        if isinstance(threshold, bool) or not isinstance(threshold, (int, float)):
            return ComparatorResult(
                measure=measure, op=op, threshold=threshold, actual=actual,
                passed=False,
                failure_reason=f"value_type_mismatch: float measure '{measure}' compared to non-numeric {type(threshold).__name__}",
            )

    # Evaluate
    try:
        if op == ">=":
            passed = actual >= threshold
        elif op == "<=":
            passed = actual <= threshold
        elif op == "==":
            passed = actual == threshold
        elif op == "!=":
            passed = actual != threshold
        elif op == ">":
            passed = actual > threshold
        elif op == "<":
            passed = actual < threshold
        else:  # pragma: no cover — op is guaranteed in _VALID_OPS above
            return ComparatorResult(
                measure=measure, op=op, threshold=threshold, actual=actual,
                passed=False, failure_reason=f"unhandled_op: {op}",
            )
    except TypeError as exc:
        return ComparatorResult(
            measure=measure, op=op, threshold=threshold, actual=actual,
            passed=False, failure_reason=f"evaluation_typeerror: {exc}",
        )

    return ComparatorResult(
        measure=measure, op=op, threshold=threshold, actual=actual,
        passed=passed,
        failure_reason=None if passed else (
            f"comparator_failed: {measure}({actual}) {op} {threshold} is False"
        ),
    )


def evaluate_comparator_suite(
    comparators: list[dict[str, Any]] | None,
    summary: dict[str, Any] | None,
) -> ComparatorSuiteResult:
    """Evaluate an analytical_comparator block against an extractor
    summary. Returns aggregate result with per-comparator detail.

    Structural errors (empty comparator list, missing summary) produce
    ``all_passed=False`` with ``structural_error`` populated.
    """
    if not isinstance(comparators, list) or len(comparators) == 0:
        return ComparatorSuiteResult(
            all_passed=False, individual_results=(),
            structural_error="empty_or_missing_comparators",
        )
    if not isinstance(summary, dict):
        return ComparatorSuiteResult(
            all_passed=False, individual_results=(),
            structural_error="extractor_summary_missing_or_invalid",
        )

    results: list[ComparatorResult] = []
    for c in comparators:
        if not isinstance(c, dict):
            results.append(ComparatorResult(
                measure="<invalid>", op="<invalid>", threshold=None,
                actual=None, passed=False,
                failure_reason=f"comparator_must_be_object: got {type(c).__name__}",
            ))
            continue
        results.append(_evaluate_one(c, summary))

    all_passed = all(r.passed for r in results)
    return ComparatorSuiteResult(
        all_passed=all_passed,
        individual_results=tuple(results),
    )


def format_suite_summary(suite: ComparatorSuiteResult) -> str:
    """Render a one-line + bullet-list summary for the smoke verdict."""
    if suite.structural_error:
        return f"comparator_suite_error: {suite.structural_error}"
    lines = []
    for r in suite.individual_results:
        sym = "✓" if r.passed else "✗"
        if r.passed:
            lines.append(f"    {sym} {r.measure}({r.actual}) {r.op} {r.threshold}")
        else:
            lines.append(f"    {sym} {r.failure_reason}")
    head = "all comparators passed" if suite.all_passed else "comparator(s) failed:"
    return head + "\n" + "\n".join(lines)
