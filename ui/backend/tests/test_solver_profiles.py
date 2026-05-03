"""DEC-V61-112 Phase 1 · solver-profile YAML schema + registry tests.

The acceptance gate for V61-112 is **byte-identity**: profile-
rendered controlDict / fvSchemes / fvSolution must match the V61-111
inline output verbatim for the iter01 case parameters. This test
file pins that contract — any drift between the YAML profile and
the V61-111 inline templates fails loudly in CI.
"""
from __future__ import annotations

import pytest

from ui.backend.services.case_solve.solver_profiles import (
    ProfileNotFoundError,
    ProfileSchemaError,
    SolverProfile,
    list_profile_names,
    load_profile,
)
from ui.backend.services.case_solve.bc_setup_from_stl_patches import (
    _build_simplefoam_control_dict,
    _build_simplefoam_fv_schemes,
    _build_simplefoam_fv_solution,
)


def test_list_profile_names_includes_simplefoam():
    names = list_profile_names()
    assert "simpleFoam" in names


def test_load_profile_simplefoam_returns_solver_profile():
    profile = load_profile("simpleFoam")
    assert isinstance(profile, SolverProfile)
    assert profile.name == "simpleFoam"
    assert profile.family == "steady"


def test_load_profile_unknown_raises_profile_not_found():
    with pytest.raises(ProfileNotFoundError) as exc:
        load_profile("nonExistentSolver")
    err = str(exc.value)
    assert "nonExistentSolver" in err


def test_simplefoam_profile_control_dict_byte_identical_to_v61_111_inline():
    """V61-112 acceptance gate: simpleFoam profile renders the
    SAME bytes as the V61-111 inline ``_build_simplefoam_control_dict``
    helper for the canonical iter01 end_time=200 case.
    """
    profile = load_profile("simpleFoam")
    rendered = profile.render_control_dict(end_time=200)
    inline = _build_simplefoam_control_dict(200)
    assert rendered == inline, (
        f"controlDict byte mismatch:\n"
        f"=== profile ({len(rendered)} bytes) ===\n{rendered!r}\n"
        f"=== inline ({len(inline)} bytes) ===\n{inline!r}"
    )


def test_simplefoam_profile_control_dict_iteration_floor_matches():
    """V61-112: when caller passes a small end_time (transient-style),
    the schema's iteration_floor=100 must apply identically to the
    V61-111 inline floor."""
    profile = load_profile("simpleFoam")
    rendered = profile.render_control_dict(end_time=2.5)
    inline = _build_simplefoam_control_dict(2.5)
    assert rendered == inline


def test_simplefoam_profile_fv_schemes_byte_identical_to_v61_111_inline():
    """V61-112 acceptance gate for fvSchemes."""
    profile = load_profile("simpleFoam")
    rendered = profile.render_fv_schemes()
    inline = _build_simplefoam_fv_schemes()
    assert rendered == inline, (
        f"fvSchemes byte mismatch:\n"
        f"=== profile ({len(rendered)} bytes) ===\n{rendered!r}\n"
        f"=== inline ({len(inline)} bytes) ===\n{inline!r}"
    )


def test_simplefoam_profile_fv_solution_byte_identical_to_v61_111_inline():
    """V61-112 acceptance gate for fvSolution."""
    profile = load_profile("simpleFoam")
    rendered = profile.render_fv_solution()
    inline = _build_simplefoam_fv_solution()
    assert rendered == inline, (
        f"fvSolution byte mismatch:\n"
        f"=== profile ({len(rendered)} bytes) ===\n{rendered!r}\n"
        f"=== inline ({len(inline)} bytes) ===\n{inline!r}"
    )


def test_load_profile_caches_result():
    """Profiles are immutable post-load; the registry caches them
    in-process so concurrent requests don't re-parse YAML."""
    p1 = load_profile("simpleFoam")
    p2 = load_profile("simpleFoam")
    assert p1 is p2  # cached identity
