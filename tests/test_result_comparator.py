"""tests/test_result_comparator.py — ResultComparator 单元测试"""

import pytest
from src.result_comparator import ResultComparator
from src.models import ExecutionResult


def make_result(**kq):
    return ExecutionResult(success=True, is_mock=True, key_quantities=kq)


GOLD_SCALAR = {
    "quantity": "strouhal_number",
    "reference_values": [{"value": 0.165}],
    "tolerance": 0.05,
}

GOLD_VECTOR = {
    "quantity": "u_centerline",
    "reference_values": [
        {"y": 0.0625, "u": -0.037},
        {"y": 0.5, "u": 0.025},
        {"y": 1.0, "u": 1.0},
    ],
    "tolerance": 0.05,
}

GOLD_VECTOR_X = {
    "quantity": "pressure_coefficient",
    "reference_values": [
        {"x_over_c": 0.0, "Cp": 1.0},
        {"x_over_c": 0.5, "Cp": 0.0},
        {"x_over_c": 1.0, "Cp": 0.2},
    ],
    "tolerance": 0.05,
}


class TestScalarComparison:
    def test_pass_exact(self):
        cmp = ResultComparator()
        result = make_result(strouhal_number=0.165)
        cr = cmp.compare(result, GOLD_SCALAR)
        assert cr.passed

    def test_pass_within_tolerance(self):
        cmp = ResultComparator()
        result = make_result(strouhal_number=0.165 * 1.04)  # 4% deviation
        cr = cmp.compare(result, GOLD_SCALAR)
        assert cr.passed

    def test_fail_exceeds_tolerance(self):
        cmp = ResultComparator()
        result = make_result(strouhal_number=0.165 * 1.10)  # 10% deviation
        cr = cmp.compare(result, GOLD_SCALAR)
        assert not cr.passed
        assert len(cr.deviations) == 1
        assert cr.deviations[0].quantity == "strouhal_number"

    def test_custom_threshold(self):
        cmp = ResultComparator(threshold=0.20)
        # gold without explicit tolerance → comparator uses constructor threshold (20%)
        gold_no_tol = {"quantity": "strouhal_number", "reference_values": [{"value": 0.165}]}
        result = make_result(strouhal_number=0.165 * 1.15)  # 15% deviation, within 20%
        cr = cmp.compare(result, gold_no_tol)
        assert cr.passed


class TestVectorComparison:
    def test_pass_vector(self):
        cmp = ResultComparator()
        result = make_result(u_centerline=[-0.037, 0.025, 1.0])
        cr = cmp.compare(result, GOLD_VECTOR)
        assert cr.passed

    def test_fail_vector_one_point(self):
        cmp = ResultComparator()
        result = make_result(u_centerline=[-0.037, 0.10, 1.0])  # second point off
        cr = cmp.compare(result, GOLD_VECTOR)
        assert not cr.passed

    def test_vector_shorter_than_reference(self):
        cmp = ResultComparator()
        result = make_result(u_centerline=[-0.037])
        cr = cmp.compare(result, GOLD_VECTOR)
        assert cr.passed  # 只比较重叠部分（1个点，精确匹配）

    def test_pass_vector_with_x_axis_alignment(self):
        cmp = ResultComparator()
        result = make_result(
            pressure_coefficient=[99.0, 1.0, 0.0, 0.2],
            pressure_coefficient_x=[-0.5, 0.0, 0.5, 1.0],
        )
        cr = cmp.compare(result, GOLD_VECTOR_X)
        assert cr.passed

    def test_fail_vector_with_x_axis_alignment(self):
        cmp = ResultComparator()
        result = make_result(
            pressure_coefficient=[99.0, 1.0, -0.4, 0.2],
            pressure_coefficient_x=[-0.5, 0.0, 0.5, 1.0],
        )
        cr = cmp.compare(result, GOLD_VECTOR_X)
        assert not cr.passed
        assert cr.deviations[0].quantity == "pressure_coefficient[x_over_c=0.5000]"


class TestEdgeCases:
    def test_missing_quantity_key(self):
        cmp = ResultComparator()
        result = make_result()  # 没有 strouhal_number
        cr = cmp.compare(result, GOLD_SCALAR)
        assert not cr.passed
        assert "strouhal_number" in cr.summary

    def test_gold_without_quantity(self):
        cmp = ResultComparator()
        result = make_result(x=1.0)
        cr = cmp.compare(result, {"reference_values": [{"value": 1.0}]})
        assert cr.passed  # 没有 quantity key → 视为通过

    def test_summary_contains_quantity(self):
        cmp = ResultComparator()
        result = make_result(strouhal_number=0.165)
        cr = cmp.compare(result, GOLD_SCALAR)
        assert "strouhal_number" in cr.summary
