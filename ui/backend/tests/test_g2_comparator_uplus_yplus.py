"""DEC-V61-036c G2 tests: comparator u+/y+ + dict-profile coverage.

Closes the last schema-level PASS-washing path Codex flagged in DEC-036
round 1 (B2): `_compare_vector` didn't read `u_plus` key and
`_resolve_profile_axis` didn't support `y_plus` axis. The plane_channel
DNS profile (Kim 1987 / Moser 1999) is `{y_plus, u_plus}` tuples, and
the comparator silently picked None for every reference scalar →
returned zero deviations → fake PASS.
"""

from __future__ import annotations

import types

import pytest

from src.result_comparator import ResultComparator


def test_g2_comparator_honestly_fails_plane_channel_u_plus_profile() -> None:
    """A simulation that emits a bad u+ profile vs Kim 1987 DNS gold
    must now produce deviations. Before G2, zero deviations → fake PASS.
    """
    from src.models import ExecutionResult

    # Kim 1987 gold shape (subset).
    ref_values = [
        {"y_plus": 0.0, "u_plus": 0.0},
        {"y_plus": 5.0, "u_plus": 5.4},
        {"y_plus": 30.0, "u_plus": 13.5},
        {"y_plus": 100.0, "u_plus": 22.8},
    ]

    # Simulation emits a completely wrong u+ profile (5x high).
    bad_profile = [0.0, 27.0, 67.5, 114.0]
    y_plus_coords = [0.0, 5.0, 30.0, 100.0]

    result = ExecutionResult(
        success=True,
        is_mock=False,
        key_quantities={
            "u_mean_profile": bad_profile,
            # Axis candidate: `u_mean_profile_y_plus` maps to ref `y_plus`.
            "u_mean_profile_y_plus": y_plus_coords,
        },
    )

    comp = ResultComparator()
    # Construct a gold-standard dict matching the comparator's expected shape.
    gold = types.SimpleNamespace(
        quantity="u_mean_profile",
        reference_values=ref_values,
        tolerance=0.05,
    )
    gold_dict = {
        "quantity": "u_mean_profile",
        "reference_values": ref_values,
        "tolerance": 0.05,
    }
    cmp_result = comp.compare(result, gold_dict)
    # The bad profile is ~5× the gold — expect at least 3 non-trivial deviations
    # (y+=0 is trivially 0.0).
    assert len(cmp_result.deviations) >= 3, (
        f"G2 fix should surface deviations; got {cmp_result.deviations}"
    )
    # Each deviation should be named `u_mean_profile[y_plus=X]`.
    for dev in cmp_result.deviations:
        assert "u_mean_profile[y_plus=" in dev.quantity


def test_g2_comparator_passes_when_u_plus_matches_gold() -> None:
    """Sanity check: when u_plus matches gold, comparator passes."""
    from src.models import ExecutionResult

    ref_values = [
        {"y_plus": 5.0, "u_plus": 5.4},
        {"y_plus": 30.0, "u_plus": 13.5},
    ]
    # Exact match.
    good_profile = [5.4, 13.5]
    result = ExecutionResult(
        success=True, is_mock=False,
        key_quantities={
            "u_mean_profile": good_profile,
            "u_mean_profile_y_plus": [5.0, 30.0],
        },
    )
    comp = ResultComparator()
    gold_dict = {
        "quantity": "u_mean_profile",
        "reference_values": ref_values,
        "tolerance": 0.05,
    }
    cmp_result = comp.compare(result, gold_dict)
    assert cmp_result.passed
    assert cmp_result.deviations == []


def test_g2_driver_accepts_dict_profile_with_Cp_key() -> None:
    """DEC-V61-036c G2 dict-profile sample: NACA sampleDict can emit
    list[dict{x_over_c, Cp}] under the `pressure_coefficient` kq. The
    driver must sample the Cp scalar, not hard-FAIL."""
    from scripts.phase5_audit_run import _primary_scalar

    fake_comp = types.SimpleNamespace(deviations=[], passed=True, summary="")
    fake_exec = types.SimpleNamespace(
        key_quantities={
            "pressure_coefficient": [
                {"x_over_c": 0.0, "Cp": 1.0},
                {"x_over_c": 0.5, "Cp": -0.3},
            ],
        },
    )
    fake_report = types.SimpleNamespace(
        comparison_result=fake_comp, execution_result=fake_exec
    )
    quantity, value, src = _primary_scalar(fake_report, expected_quantity="pressure_coefficient")
    assert quantity == "pressure_coefficient[0]"
    assert value == pytest.approx(1.0)
    assert src == "key_quantities_profile_sample_dict:Cp"


def test_g2_driver_accepts_dict_profile_with_u_plus_key() -> None:
    """Plane-channel DNS gold is list[dict{y_plus, u_plus}]; if someone
    loads that shape into key_quantities, the driver must sample u_plus."""
    from scripts.phase5_audit_run import _primary_scalar

    fake_comp = types.SimpleNamespace(deviations=[], passed=True, summary="")
    fake_exec = types.SimpleNamespace(
        key_quantities={
            "u_mean_profile": [
                {"y_plus": 5.0, "u_plus": 5.4},
                {"y_plus": 30.0, "u_plus": 13.5},
            ],
        },
    )
    fake_report = types.SimpleNamespace(
        comparison_result=fake_comp, execution_result=fake_exec
    )
    quantity, value, src = _primary_scalar(fake_report, expected_quantity="u_mean_profile")
    assert quantity == "u_mean_profile[0]"
    assert value == pytest.approx(5.4)
    assert src == "key_quantities_profile_sample_dict:u_plus"
