"""CaseProfile tolerance_policy loader tests · P1-T3."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.metrics import (
    CaseProfileError,
    MetricClass,
    MetricStatus,
    MetricsRegistry,
    PointwiseMetric,
    load_case_profile,
    load_tolerance_policy,
)
from src.models import ExecutionResult


# ---------------------------------------------------------------------------
# Missing file / empty file paths
# ---------------------------------------------------------------------------


def test_missing_case_returns_empty_policy(tmp_path: Path) -> None:
    assert load_tolerance_policy("does_not_exist", case_profiles_dir=tmp_path) == {}


def test_missing_case_profile_returns_none(tmp_path: Path) -> None:
    assert load_case_profile("does_not_exist", case_profiles_dir=tmp_path) is None


def test_empty_yaml_file_treated_as_no_policy(tmp_path: Path) -> None:
    (tmp_path / "empty.yaml").write_text("", encoding="utf-8")
    assert load_tolerance_policy("empty", case_profiles_dir=tmp_path) == {}


def test_profile_without_tolerance_policy_returns_empty(tmp_path: Path) -> None:
    (tmp_path / "no_policy.yaml").write_text(
        "case_id: no_policy\nschema_version: 1\n", encoding="utf-8"
    )
    assert load_tolerance_policy("no_policy", case_profiles_dir=tmp_path) == {}


# ---------------------------------------------------------------------------
# Happy path — well-formed tolerance_policy
# ---------------------------------------------------------------------------


def test_well_formed_policy_parses_to_registry_shape(tmp_path: Path) -> None:
    (tmp_path / "x.yaml").write_text(
        """
case_id: x
schema_version: 1
tolerance_policy:
  u_centerline:
    tolerance: 0.05
  cp_at_x:
    tolerance: 0.10
""".strip(),
        encoding="utf-8",
    )
    policy = load_tolerance_policy("x", case_profiles_dir=tmp_path)
    assert policy == {
        "u_centerline": {"tolerance": 0.05},
        "cp_at_x": {"tolerance": 0.10},
    }


def test_policy_is_defensively_copied(tmp_path: Path) -> None:
    (tmp_path / "x.yaml").write_text(
        """
case_id: x
schema_version: 1
tolerance_policy:
  a:
    tolerance: 0.05
""".strip(),
        encoding="utf-8",
    )
    policy1 = load_tolerance_policy("x", case_profiles_dir=tmp_path)
    policy1["a"]["tolerance"] = 999  # mutate
    policy2 = load_tolerance_policy("x", case_profiles_dir=tmp_path)
    assert policy2["a"]["tolerance"] == 0.05  # fresh read not affected


# ---------------------------------------------------------------------------
# Malformed YAML / schema violations
# ---------------------------------------------------------------------------


def test_malformed_yaml_raises_case_profile_error(tmp_path: Path) -> None:
    (tmp_path / "bad.yaml").write_text(
        "case_id: bad\ntolerance_policy: {unclosed",
        encoding="utf-8",
    )
    with pytest.raises(CaseProfileError, match="malformed"):
        load_tolerance_policy("bad", case_profiles_dir=tmp_path)


def test_tolerance_policy_not_dict_raises(tmp_path: Path) -> None:
    (tmp_path / "x.yaml").write_text(
        "case_id: x\ntolerance_policy: not-a-dict\n",
        encoding="utf-8",
    )
    with pytest.raises(CaseProfileError, match="must be a mapping"):
        load_tolerance_policy("x", case_profiles_dir=tmp_path)


def test_observable_entry_not_dict_raises(tmp_path: Path) -> None:
    (tmp_path / "x.yaml").write_text(
        """
case_id: x
tolerance_policy:
  my_obs: 0.05
""".strip(),
        encoding="utf-8",
    )
    with pytest.raises(CaseProfileError, match="must be a mapping"):
        load_tolerance_policy("x", case_profiles_dir=tmp_path)


def test_non_numeric_tolerance_raises(tmp_path: Path) -> None:
    (tmp_path / "x.yaml").write_text(
        """
case_id: x
tolerance_policy:
  my_obs:
    tolerance: "five percent"
""".strip(),
        encoding="utf-8",
    )
    with pytest.raises(CaseProfileError, match="must be a number"):
        load_tolerance_policy("x", case_profiles_dir=tmp_path)


def test_boolean_tolerance_rejected(tmp_path: Path) -> None:
    # Python treats bool as int — explicit guard needed.
    (tmp_path / "x.yaml").write_text(
        """
case_id: x
tolerance_policy:
  my_obs:
    tolerance: true
""".strip(),
        encoding="utf-8",
    )
    with pytest.raises(CaseProfileError, match="must be a number"):
        load_tolerance_policy("x", case_profiles_dir=tmp_path)


def test_nan_tolerance_rejected(tmp_path: Path) -> None:
    (tmp_path / "x.yaml").write_text(
        """
case_id: x
tolerance_policy:
  my_obs:
    tolerance: .nan
""".strip(),
        encoding="utf-8",
    )
    with pytest.raises(CaseProfileError, match="NaN"):
        load_tolerance_policy("x", case_profiles_dir=tmp_path)


def test_null_tolerance_passes_through(tmp_path: Path) -> None:
    # Residual metrics have `tolerance: null` — loader must accept this.
    (tmp_path / "x.yaml").write_text(
        """
case_id: x
tolerance_policy:
  convergence_attestation:
    tolerance: null
""".strip(),
        encoding="utf-8",
    )
    policy = load_tolerance_policy("x", case_profiles_dir=tmp_path)
    assert policy == {"convergence_attestation": {"tolerance": None}}


# ---------------------------------------------------------------------------
# Real repo case profiles (P1-T3 concrete examples)
# ---------------------------------------------------------------------------


def test_lid_driven_cavity_policy_loads_from_repo() -> None:
    # No override → loader walks up from module to find .planning/case_profiles/
    policy = load_tolerance_policy("lid_driven_cavity")
    assert "u_centerline" in policy
    assert policy["u_centerline"]["tolerance"] == pytest.approx(0.05)
    assert "primary_vortex_location_x" in policy
    assert policy["primary_vortex_location_x"]["tolerance"] == pytest.approx(0.03)


def test_circular_cylinder_wake_policy_loads_from_repo() -> None:
    policy = load_tolerance_policy("circular_cylinder_wake")
    assert policy["strouhal_number"]["tolerance"] == pytest.approx(0.25)
    assert policy["cd_mean"]["tolerance"] == pytest.approx(0.05)


# ---------------------------------------------------------------------------
# End-to-end integration with MetricsRegistry
# ---------------------------------------------------------------------------


def test_end_to_end_loader_feeds_registry_dispatch(tmp_path: Path) -> None:
    # Observable `a` has 25% deviation. With default 5% tolerance → FAIL.
    # With tolerance_policy-loaded 30% → PASS.
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
    artifacts = ExecutionResult(
        success=True,
        is_mock=False,
        key_quantities={"a": 1.25, "b": 1.25},
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
    }
    reports = r.evaluate_all(artifacts, observable_defs, tolerance_policy=policy)
    by_name = {rep.name: rep for rep in reports}

    # `a` gets the 30% policy override → PASS
    assert by_name["a"].status is MetricStatus.PASS
    assert by_name["a"].tolerance_applied == pytest.approx(0.30)

    # `b` absent from policy → falls through to observable_def 5% → FAIL
    assert by_name["b"].status is MetricStatus.FAIL
    assert by_name["b"].tolerance_applied == pytest.approx(0.05)
