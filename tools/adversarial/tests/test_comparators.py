"""Unit tests for ``tools.adversarial.comparators`` (DEC-V61-106).

Pure-logic — no backend, no gmsh, no real solver output. Exercises:
  - Each op (>=, <=, ==, !=, >, <) on float and bool measures
  - Pass / fail outcomes
  - Type mismatch detection (bool measure with float threshold and v.v.)
  - Unknown measure
  - NaN actual value (solver-divergence canary)
  - Empty / missing comparator block (structural error)
  - Aggregate all_passed correctness across multi-comparator suites
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

# Make tools/adversarial/ importable.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.adversarial.comparators import (  # noqa: E402
    ComparatorSuiteResult,
    evaluate_comparator_suite,
    format_suite_summary,
)


_GOOD_SUMMARY = {
    "final_time": 250.0,
    "cell_count": 7159,
    "u_magnitude_min": 0.0,
    "u_magnitude_max": 1.6,
    "u_magnitude_mean": 0.4,
    "u_x_mean": 0.05,
    "u_x_min": -0.3,
    "u_x_max": 1.4,
    "is_recirculating": True,
}


# ===== happy path =====

def test_single_float_ge_passes():
    suite = evaluate_comparator_suite(
        [{"measure": "u_magnitude_max", "op": ">=", "value": 1.0}],
        _GOOD_SUMMARY,
    )
    assert suite.all_passed is True
    assert suite.individual_results[0].passed is True
    assert suite.individual_results[0].failure_reason is None


def test_single_bool_eq_passes():
    suite = evaluate_comparator_suite(
        [{"measure": "is_recirculating", "op": "==", "value": True}],
        _GOOD_SUMMARY,
    )
    assert suite.all_passed is True


def test_multi_comparator_all_pass():
    suite = evaluate_comparator_suite(
        [
            {"measure": "u_magnitude_max", "op": ">=", "value": 1.0},
            {"measure": "u_x_min", "op": "<", "value": 0.0},
            {"measure": "is_recirculating", "op": "==", "value": True},
        ],
        _GOOD_SUMMARY,
    )
    assert suite.all_passed is True
    assert len(suite.individual_results) == 3
    assert all(r.passed for r in suite.individual_results)


def test_all_six_ops_on_float():
    cases = [
        ("u_magnitude_max", ">=", 1.6, True),
        ("u_magnitude_max", ">=", 1.7, False),
        ("u_magnitude_max", "<=", 1.6, True),
        ("u_magnitude_max", "<=", 1.5, False),
        ("u_magnitude_max", ">", 1.5, True),
        ("u_magnitude_max", ">", 1.6, False),
        ("u_magnitude_max", "<", 1.7, True),
        ("u_magnitude_max", "<", 1.6, False),
        ("cell_count", "==", 7159, True),
        ("cell_count", "==", 7158, False),
        ("cell_count", "!=", 0, True),
        ("cell_count", "!=", 7159, False),
    ]
    for measure, op, value, expected in cases:
        suite = evaluate_comparator_suite(
            [{"measure": measure, "op": op, "value": value}],
            _GOOD_SUMMARY,
        )
        assert suite.all_passed is expected, (
            f"{measure} {op} {value} expected {expected}, got {suite.individual_results[0]}"
        )


# ===== fail paths =====

def test_one_failing_comparator_fails_suite():
    suite = evaluate_comparator_suite(
        [
            {"measure": "u_magnitude_max", "op": ">=", "value": 1.0},  # passes
            {"measure": "u_magnitude_max", "op": ">=", "value": 100.0},  # fails
        ],
        _GOOD_SUMMARY,
    )
    assert suite.all_passed is False
    assert suite.individual_results[0].passed is True
    assert suite.individual_results[1].passed is False
    assert "comparator_failed" in suite.individual_results[1].failure_reason


# ===== structural errors =====

def test_unknown_measure_fails_with_clear_reason():
    suite = evaluate_comparator_suite(
        [{"measure": "u_magnitude_zomega", "op": ">=", "value": 1.0}],
        _GOOD_SUMMARY,
    )
    assert suite.all_passed is False
    assert "unknown_measure" in suite.individual_results[0].failure_reason


def test_invalid_op_fails():
    suite = evaluate_comparator_suite(
        [{"measure": "u_magnitude_max", "op": "~~", "value": 1.0}],
        _GOOD_SUMMARY,
    )
    assert suite.all_passed is False
    assert "invalid_op" in suite.individual_results[0].failure_reason


def test_empty_comparator_list_is_structural_error():
    suite = evaluate_comparator_suite([], _GOOD_SUMMARY)
    assert suite.all_passed is False
    assert suite.structural_error == "empty_or_missing_comparators"


def test_missing_comparator_list_is_structural_error():
    suite = evaluate_comparator_suite(None, _GOOD_SUMMARY)
    assert suite.all_passed is False
    assert suite.structural_error == "empty_or_missing_comparators"


def test_missing_summary_is_structural_error():
    suite = evaluate_comparator_suite(
        [{"measure": "u_magnitude_max", "op": ">=", "value": 1.0}], None,
    )
    assert suite.all_passed is False
    assert suite.structural_error == "extractor_summary_missing_or_invalid"


# ===== type-safety =====

def test_bool_measure_with_float_threshold_fails_clearly():
    suite = evaluate_comparator_suite(
        [{"measure": "is_recirculating", "op": "==", "value": 1.0}],
        _GOOD_SUMMARY,
    )
    assert suite.all_passed is False
    assert "value_type_mismatch" in suite.individual_results[0].failure_reason


def test_float_measure_with_bool_threshold_fails_clearly():
    suite = evaluate_comparator_suite(
        [{"measure": "u_magnitude_max", "op": ">=", "value": True}],
        _GOOD_SUMMARY,
    )
    assert suite.all_passed is False
    assert "value_type_mismatch" in suite.individual_results[0].failure_reason


def test_bool_measure_with_lt_op_fails():
    suite = evaluate_comparator_suite(
        [{"measure": "is_recirculating", "op": "<", "value": True}],
        _GOOD_SUMMARY,
    )
    assert suite.all_passed is False
    assert "invalid_op_for_bool" in suite.individual_results[0].failure_reason


def test_summary_missing_measure_fails_with_clear_reason():
    summary_missing = dict(_GOOD_SUMMARY)
    del summary_missing["u_magnitude_max"]
    suite = evaluate_comparator_suite(
        [{"measure": "u_magnitude_max", "op": ">=", "value": 1.0}],
        summary_missing,
    )
    assert suite.all_passed is False
    assert "measure_not_in_summary" in suite.individual_results[0].failure_reason


def test_nan_actual_value_short_circuits_to_fail():
    summary_nan = dict(_GOOD_SUMMARY)
    summary_nan["u_magnitude_max"] = math.nan
    suite = evaluate_comparator_suite(
        [{"measure": "u_magnitude_max", "op": ">=", "value": 1.0}],
        summary_nan,
    )
    assert suite.all_passed is False
    assert "measure_nan" in suite.individual_results[0].failure_reason


def test_inf_actual_value_short_circuits_to_fail():
    """Codex R10: +inf would otherwise pass `u_magnitude_max >= 1.0`
    silently, masking solver divergence the framework exists to
    expose."""
    summary_inf = dict(_GOOD_SUMMARY)
    summary_inf["u_magnitude_max"] = math.inf
    suite = evaluate_comparator_suite(
        [{"measure": "u_magnitude_max", "op": ">=", "value": 1.0}],
        summary_inf,
    )
    assert suite.all_passed is False
    assert "measure_inf" in suite.individual_results[0].failure_reason


def test_negative_inf_actual_value_also_short_circuits():
    summary_neg_inf = dict(_GOOD_SUMMARY)
    summary_neg_inf["u_x_min"] = -math.inf
    suite = evaluate_comparator_suite(
        [{"measure": "u_x_min", "op": "<", "value": 0.0}],
        summary_neg_inf,
    )
    assert suite.all_passed is False
    assert "measure_inf" in suite.individual_results[0].failure_reason


def test_bool_actual_for_float_measure_rejected():
    """Codex R10: ``isinstance(True, (int, float))`` is True because
    bool subclasses int. Without an explicit bool guard a corrupted
    summary with True/False for u_magnitude_max would pass numeric
    comparators."""
    summary_bool = dict(_GOOD_SUMMARY)
    summary_bool["u_magnitude_max"] = True
    suite = evaluate_comparator_suite(
        [{"measure": "u_magnitude_max", "op": ">=", "value": 1.0}],
        summary_bool,
    )
    assert suite.all_passed is False
    assert "measure_type_mismatch" in suite.individual_results[0].failure_reason
    assert "bool" in suite.individual_results[0].failure_reason


def test_summary_with_string_for_float_measure_fails():
    summary_bad = dict(_GOOD_SUMMARY)
    summary_bad["u_magnitude_max"] = "1.6"
    suite = evaluate_comparator_suite(
        [{"measure": "u_magnitude_max", "op": ">=", "value": 1.0}],
        summary_bad,
    )
    assert suite.all_passed is False
    assert "measure_type_mismatch" in suite.individual_results[0].failure_reason


def test_non_dict_comparator_fails():
    suite = evaluate_comparator_suite(["not-a-dict"], _GOOD_SUMMARY)
    assert suite.all_passed is False
    assert "comparator_must_be_object" in suite.individual_results[0].failure_reason


# ===== formatting =====

def test_format_summary_renders_pass_path():
    suite = evaluate_comparator_suite(
        [{"measure": "u_magnitude_max", "op": ">=", "value": 1.0}],
        _GOOD_SUMMARY,
    )
    text = format_suite_summary(suite)
    assert "all comparators passed" in text
    assert "u_magnitude_max" in text


def test_format_summary_renders_fail_path():
    suite = evaluate_comparator_suite(
        [{"measure": "u_magnitude_max", "op": ">=", "value": 100.0}],
        _GOOD_SUMMARY,
    )
    text = format_suite_summary(suite)
    assert "comparator(s) failed" in text


def test_format_summary_structural_error_is_explicit():
    suite = evaluate_comparator_suite([], _GOOD_SUMMARY)
    text = format_suite_summary(suite)
    assert "comparator_suite_error" in text
    assert "empty_or_missing_comparators" in text
