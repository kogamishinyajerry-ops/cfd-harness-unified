"""DEC-V61-147 (N4.2) · solver dict override schema + diff tests.

Coverage:
  * Schema field validators (positivity, charset, bounds)
  * Empty override produces empty diff
  * Single-field overrides produce one diff entry each
  * Multiple overrides produce stable-sorted diff
  * Field-name-not-in-tier mapping yields baseline=None
  * residualControl per-field threshold positivity
  * div_scheme_default literal enforcement
  * Stable sort by path
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from ui.backend.schemas.solver_dicts import (
    LinearSolverOverride,
    SolverDictsOverride,
)
from ui.backend.services.case_solve.dict_diff import (
    DiffEntry,
    diff_against_defaults,
)
from ui.backend.services.physics import get_tolerance_template


_ENG = get_tolerance_template("engineering")
_LAB = get_tolerance_template("lab_quality")


def _empty_override() -> SolverDictsOverride:
    return SolverDictsOverride(authored_at="2026-05-07T12:00:00Z")


# ────────── LinearSolverOverride validators ──────────


def test_lso_tolerance_positive():
    LinearSolverOverride(tolerance=1e-6)
    with pytest.raises(ValidationError):
        LinearSolverOverride(tolerance=0.0)
    with pytest.raises(ValidationError):
        LinearSolverOverride(tolerance=-1e-6)


def test_lso_rel_tol_in_zero_one():
    LinearSolverOverride(rel_tol=0.0)
    LinearSolverOverride(rel_tol=0.99)
    with pytest.raises(ValidationError):
        LinearSolverOverride(rel_tol=1.0)
    with pytest.raises(ValidationError):
        LinearSolverOverride(rel_tol=-0.1)


def test_lso_family_must_be_known_literal():
    with pytest.raises(ValidationError):
        LinearSolverOverride(family="MagicNewSolver")  # type: ignore[arg-type]


def test_lso_extra_keys_forbidden():
    with pytest.raises(ValidationError):
        LinearSolverOverride(tolerance=1e-6, mystery="oops")


# ────────── SolverDictsOverride validators ──────────


def test_override_n_non_ortho_bounds():
    SolverDictsOverride(
        n_non_orthogonal_correctors=0, authored_at="2026-05-07T12:00:00Z",
    )
    SolverDictsOverride(
        n_non_orthogonal_correctors=5, authored_at="2026-05-07T12:00:00Z",
    )
    with pytest.raises(ValidationError):
        SolverDictsOverride(
            n_non_orthogonal_correctors=-1, authored_at="2026-05-07T12:00:00Z",
        )
    with pytest.raises(ValidationError):
        SolverDictsOverride(
            n_non_orthogonal_correctors=6, authored_at="2026-05-07T12:00:00Z",
        )


def test_override_div_scheme_must_be_known_literal():
    with pytest.raises(ValidationError):
        SolverDictsOverride(
            div_scheme_default="MagicNewScheme",  # type: ignore[arg-type]
            authored_at="2026-05-07T12:00:00Z",
        )


def test_override_residual_control_thresholds_positive():
    SolverDictsOverride(
        residual_control={"U": 1e-5, "p": 1e-5},
        authored_at="2026-05-07T12:00:00Z",
    )
    with pytest.raises(ValidationError):
        SolverDictsOverride(
            residual_control={"U": 0.0},
            authored_at="2026-05-07T12:00:00Z",
        )
    with pytest.raises(ValidationError):
        SolverDictsOverride(
            residual_control={"U": -1e-5},
            authored_at="2026-05-07T12:00:00Z",
        )


def test_override_linear_solver_field_names_alnum():
    with pytest.raises(ValidationError):
        SolverDictsOverride(
            linear_solvers={"my field": LinearSolverOverride(tolerance=1e-6)},
            authored_at="2026-05-07T12:00:00Z",
        )
    SolverDictsOverride(
        linear_solvers={
            "U": LinearSolverOverride(tolerance=1e-6),
            "pFinal": LinearSolverOverride(tolerance=1e-7),
        },
        authored_at="2026-05-07T12:00:00Z",
    )


def test_override_extra_keys_forbidden():
    with pytest.raises(ValidationError):
        SolverDictsOverride(
            authored_at="2026-05-07T12:00:00Z", mystery="oops",
        )


# ────────── diff_against_defaults ──────────


def test_diff_empty_override_produces_empty_list():
    entries = diff_against_defaults(
        solver="simpleFoam",
        regime="RANS-kOmegaSST",
        tolerance_template=_ENG,
        override=_empty_override(),
    )
    assert entries == []


def test_diff_n_non_ortho_override():
    override = SolverDictsOverride(
        n_non_orthogonal_correctors=3,
        authored_at="2026-05-07T12:00:00Z",
    )
    entries = diff_against_defaults(
        solver="simpleFoam",
        regime="RANS-kOmegaSST",
        tolerance_template=_ENG,
        override=override,
    )
    assert len(entries) == 1
    e = entries[0]
    assert e.path == "n_non_orthogonal_correctors"
    assert e.baseline == 0  # SIMPLE family default per _default_n_non_ortho
    assert e.override == 3
    assert "non-orthogonal" in e.reason


def test_diff_n_non_ortho_for_icoFoam_baseline_is_2():
    override = SolverDictsOverride(
        n_non_orthogonal_correctors=4,
        authored_at="2026-05-07T12:00:00Z",
    )
    entries = diff_against_defaults(
        solver="icoFoam",
        regime="laminar",
        tolerance_template=_ENG,
        override=override,
    )
    assert entries[0].baseline == 2


def test_diff_div_scheme_default_override():
    override = SolverDictsOverride(
        div_scheme_default="upwind",
        authored_at="2026-05-07T12:00:00Z",
    )
    entries = diff_against_defaults(
        solver="simpleFoam",
        regime="RANS-kOmegaSST",
        tolerance_template=_ENG,
        override=override,
    )
    assert len(entries) == 1
    e = entries[0]
    assert e.path == "div_scheme_default"
    assert e.baseline == "limitedLinear"
    assert e.override == "upwind"


def test_diff_div_scheme_baseline_for_icoFoam():
    override = SolverDictsOverride(
        div_scheme_default="limitedLinear",
        authored_at="2026-05-07T12:00:00Z",
    )
    entries = diff_against_defaults(
        solver="icoFoam",
        regime="laminar",
        tolerance_template=_ENG,
        override=override,
    )
    assert entries[0].baseline == "linearUpwind"


def test_diff_linear_solver_tolerance():
    override = SolverDictsOverride(
        linear_solvers={
            "U": LinearSolverOverride(tolerance=1e-7),
        },
        authored_at="2026-05-07T12:00:00Z",
    )
    entries = diff_against_defaults(
        solver="simpleFoam",
        regime="RANS-kOmegaSST",
        tolerance_template=_ENG,
        override=override,
    )
    assert len(entries) == 1
    e = entries[0]
    assert e.path == "linear_solvers.U.tolerance"
    assert e.baseline == _ENG.momentum  # 1e-5
    assert e.override == 1e-7


def test_diff_linear_solver_family_and_rel_tol():
    override = SolverDictsOverride(
        linear_solvers={
            "p": LinearSolverOverride(family="GAMG", rel_tol=0.01),
        },
        authored_at="2026-05-07T12:00:00Z",
    )
    entries = diff_against_defaults(
        solver="simpleFoam",
        regime="RANS-kOmegaSST",
        tolerance_template=_ENG,
        override=override,
    )
    assert len(entries) == 2
    paths = {e.path for e in entries}
    assert "linear_solvers.p.family" in paths
    assert "linear_solvers.p.rel_tol" in paths


def test_diff_linear_solver_unknown_field_baseline_none():
    """When the field name is exotic (not in the standard tier
    mapping), the baseline tolerance is None."""
    override = SolverDictsOverride(
        linear_solvers={
            "exoticTransport": LinearSolverOverride(tolerance=1e-6),
        },
        authored_at="2026-05-07T12:00:00Z",
    )
    entries = diff_against_defaults(
        solver="pimpleFoam",
        regime="RANS-kOmegaSST",
        tolerance_template=_ENG,
        override=override,
    )
    e = next(e for e in entries if e.path.endswith(".tolerance"))
    assert e.baseline is None


def test_diff_residual_control_per_field():
    override = SolverDictsOverride(
        residual_control={"U": 1e-7, "p": 1e-7},
        authored_at="2026-05-07T12:00:00Z",
    )
    entries = diff_against_defaults(
        solver="simpleFoam",
        regime="RANS-kOmegaSST",
        tolerance_template=_ENG,
        override=override,
    )
    assert len(entries) == 2
    paths = sorted(e.path for e in entries)
    assert paths == ["residual_control.U", "residual_control.p"]


def test_diff_combined_overrides_stable_sort():
    override = SolverDictsOverride(
        n_non_orthogonal_correctors=3,
        div_scheme_default="upwind",
        linear_solvers={
            "U": LinearSolverOverride(tolerance=1e-7),
            "p": LinearSolverOverride(family="GAMG"),
        },
        residual_control={"U": 1e-6},
        authored_at="2026-05-07T12:00:00Z",
    )
    entries = diff_against_defaults(
        solver="simpleFoam",
        regime="RANS-kOmegaSST",
        tolerance_template=_LAB,
        override=override,
    )
    paths = [e.path for e in entries]
    # Stable alphabetic sort.
    assert paths == sorted(paths)
    # All overrides accounted for.
    assert "div_scheme_default" in paths
    assert "n_non_orthogonal_correctors" in paths
    assert "linear_solvers.U.tolerance" in paths
    assert "linear_solvers.p.family" in paths
    assert "residual_control.U" in paths


def test_diff_baseline_uses_tolerance_template_tier():
    """Switching template tier changes the baseline tolerance the
    diff reports against — same override, different baseline."""
    override = SolverDictsOverride(
        linear_solvers={"U": LinearSolverOverride(tolerance=1e-7)},
        authored_at="2026-05-07T12:00:00Z",
    )
    eng_entries = diff_against_defaults(
        solver="simpleFoam",
        regime="RANS-kOmegaSST",
        tolerance_template=_ENG,  # 1e-5
        override=override,
    )
    lab_entries = diff_against_defaults(
        solver="simpleFoam",
        regime="RANS-kOmegaSST",
        tolerance_template=_LAB,  # 1e-7
        override=override,
    )
    assert eng_entries[0].baseline == 1e-5
    assert lab_entries[0].baseline == 1e-7


# ────────── DiffEntry shape ──────────


def test_diff_entry_is_frozen_dataclass():
    """DiffEntry is immutable so renders can hold references safely."""
    e = DiffEntry(path="x", baseline=1, override=2, reason="why")
    with pytest.raises(Exception):  # FrozenInstanceError
        e.path = "y"  # type: ignore[misc]
