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


class TestFieldAliases:
    """Actual-side alias expansion — see CANONICAL_ALIASES.

    Motivation: knowledge/corrections/ shows 14+ COMPARATOR_SCHEMA_MISMATCH
    events where the solver emitted a valid result but under a different field
    name than the gold standard declared. Each test below mirrors a real
    historical failure.
    """

    def test_friction_factor_resolved_via_f_alias(self):
        """Pipe flow: gold=friction_factor, solver emits 'f' (4 real corrections)."""
        cmp = ResultComparator()
        gold = {
            "quantity": "friction_factor",
            "reference_values": [{"value": 0.0211}],
            "tolerance": 0.08,
        }
        # Solver emits under "f" (OpenFOAM shorthand)
        result = make_result(f=0.0211)
        cr = cmp.compare(result, gold)
        assert cr.passed, f"expected pass via alias, summary={cr.summary}"

    def test_friction_factor_resolved_via_fDarcy_alias(self):
        """Pipe flow: solver emits under 'fDarcy'."""
        cmp = ResultComparator()
        gold = {"quantity": "friction_factor", "reference_values": [{"value": 0.0211}], "tolerance": 0.08}
        result = make_result(fDarcy=0.0211)
        cr = cmp.compare(result, gold)
        assert cr.passed

    def test_pressure_coefficient_resolved_via_Cp_alias_with_companion_axis(self):
        """NACA 0012: gold=pressure_coefficient, solver emits Cp + Cp_x arrays.

        Critically: after alias resolution, the companion-axis lookup must
        find "Cp_x" (not "pressure_coefficient_x") — this was the regression
        path where alias worked but axis resolution re-broke.
        """
        cmp = ResultComparator()
        gold = {
            "quantity": "pressure_coefficient",
            "reference_values": [
                {"x_over_c": 0.0, "Cp": 1.0},
                {"x_over_c": 0.5, "Cp": 0.0},
                {"x_over_c": 1.0, "Cp": 0.15},
            ],
            "tolerance": 0.10,
        }
        result = make_result(
            Cp=[1.0, 0.0, 0.15],
            Cp_x=[0.0, 0.5, 1.0],
        )
        cr = cmp.compare(result, gold)
        assert cr.passed, f"axis resolution failed after alias: summary={cr.summary}"

    def test_nusselt_resolved_via_Nu_avg_alias(self):
        """Impinging jet / cavity: gold=nusselt_number, solver emits Nu_avg."""
        cmp = ResultComparator()
        gold = {"quantity": "nusselt_number", "reference_values": [{"Nu": 25.0}], "tolerance": 0.15}
        result = make_result(Nu_avg=24.5)
        cr = cmp.compare(result, gold)
        assert cr.passed

    def test_canonical_wins_over_alias_when_both_present(self):
        """If a solver output contains both canonical and alias keys,
        canonical takes priority — this prevents silent downgrades when
        the adapter is upgraded to emit both during a transition."""
        cmp = ResultComparator()
        gold = {"quantity": "friction_factor", "reference_values": [{"value": 0.0211}], "tolerance": 0.08}
        result = make_result(friction_factor=0.0211, f=0.999)  # canonical correct, alias deliberately wrong
        cr = cmp.compare(result, gold)
        assert cr.passed

    def test_alias_miss_produces_diagnostic_summary(self):
        """When neither canonical nor any alias is present, the failure
        summary must name the tried aliases and available keys — so the
        operator debugging a correction file knows what to look for."""
        cmp = ResultComparator()
        gold = {"quantity": "friction_factor", "reference_values": [{"value": 0.02}], "tolerance": 0.05}
        result = make_result(weird_unknown_field=0.02, Re=50000)
        cr = cmp.compare(result, gold)
        assert not cr.passed
        assert "friction_factor" in cr.summary
        # tried aliases surfaced
        assert "fDarcy" in cr.summary or "darcy_f" in cr.summary
        # available keys surfaced
        assert "Re" in cr.summary or "weird_unknown_field" in cr.summary

    def test_unknown_canonical_has_no_aliases(self):
        """A canonical quantity not in the alias table must still fail cleanly,
        not raise — this guards against future schemas breaking the lookup."""
        cmp = ResultComparator()
        gold = {"quantity": "bogus_novel_quantity", "reference_values": [{"value": 1.0}], "tolerance": 0.05}
        result = make_result(some_field=1.0)
        cr = cmp.compare(result, gold)
        assert not cr.passed
        assert "bogus_novel_quantity" in cr.summary

    def test_u_centerline_via_uCenterline_legacy_alias(self):
        """Backstop for LDC cases bypassing the adapter's explicit rename."""
        cmp = ResultComparator()
        gold = {
            "quantity": "u_centerline",
            "reference_values": [
                {"y": 0.0, "u": 0.0},
                {"y": 0.5, "u": -0.06205},
                {"y": 1.0, "u": 1.0},
            ],
            "tolerance": 0.05,
        }
        # No adapter rename; raw sampleDict key
        result = make_result(
            uCenterline=[0.0, -0.06205, 1.0],
            uCenterline_y=[0.0, 0.5, 1.0],
        )
        cr = cmp.compare(result, gold)
        assert cr.passed, f"legacy LDC alias failed: {cr.summary}"
