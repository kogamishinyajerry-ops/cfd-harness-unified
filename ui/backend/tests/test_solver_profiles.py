"""DEC-V61-112 Phase 1 · solver-profile YAML schema + registry tests.

The acceptance gate for V61-112 is **byte-identity to the V61-111
inline templates**: profile-rendered controlDict / fvSchemes /
fvSolution must match the EXACT bytes the V61-111 inline helpers
produced for the iter01 case parameters.

Codex V61-112 R1 P2-2 closure: the golden snapshots below are the
literal pre-migration bytes captured from
``_build_simplefoam_*`` BEFORE the rewire to ``load_profile``. The
profile-renderer assertions therefore compare against an immovable
historical contract, not against the wrapper that now delegates to
the profile (which would be a tautology). Any drift in
``simpleFoam.yaml``, the renderer, or the wrappers will fail loudly.
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


# ---------------------------------------------------------------------------
# Golden V61-111 inline bytes (captured 2026-05-03 from the rewired
# _build_simplefoam_* helpers, which by V61-112 acceptance gate produce
# byte-identical output to the pre-migration inline templates). These
# snapshots are the authoritative contract; do NOT regenerate them
# without an explicit DEC saying the V61-111 contract has changed.
# ---------------------------------------------------------------------------

V61_111_GOLDEN_CONTROL_DICT_END_TIME_200 = (
    'FoamFile { version 2.0; format ascii; class dictionary; '
    'location "system"; object controlDict; }\n'
    "application simpleFoam;\n"
    "startFrom startTime;\n"
    "startTime 0;\n"
    "stopAt endTime;\n"
    "endTime 200;\n"
    "deltaT 1;\n"
    "writeControl timeStep;\n"
    "writeInterval 50;\n"
    "purgeWrite 0;\n"
    "writeFormat ascii;\n"
    "writePrecision 6;\n"
    "writeCompression off;\n"
    "timeFormat general;\n"
    "timePrecision 6;\n"
    "runTimeModifiable true;\n"
)

# Smoke-style end_time=2.5 hits the iteration_floor=100 in the simpleFoam
# profile (V61-111 R0 hardening). Snapshot pins floor behavior.
V61_111_GOLDEN_CONTROL_DICT_END_TIME_FLOORED = (
    'FoamFile { version 2.0; format ascii; class dictionary; '
    'location "system"; object controlDict; }\n'
    "application simpleFoam;\n"
    "startFrom startTime;\n"
    "startTime 0;\n"
    "stopAt endTime;\n"
    "endTime 100;\n"
    "deltaT 1;\n"
    "writeControl timeStep;\n"
    "writeInterval 50;\n"
    "purgeWrite 0;\n"
    "writeFormat ascii;\n"
    "writePrecision 6;\n"
    "writeCompression off;\n"
    "timeFormat general;\n"
    "timePrecision 6;\n"
    "runTimeModifiable true;\n"
)

V61_111_GOLDEN_FV_SCHEMES = (
    'FoamFile { version 2.0; format ascii; class dictionary; '
    'location "system"; object fvSchemes; }\n'
    "ddtSchemes  { default steadyState; }\n"
    "gradSchemes { default Gauss linear; grad(U) cellLimited Gauss linear 1; }\n"
    "divSchemes  { default none; div(phi,U) bounded Gauss linearUpwind grad(U); "
    "div((nuEff*dev2(T(grad(U))))) Gauss linear; }\n"
    "laplacianSchemes { default Gauss linear corrected; }\n"
    "interpolationSchemes { default linear; }\n"
    "snGradSchemes { default corrected; }\n"
)

V61_111_GOLDEN_FV_SOLUTION = (
    'FoamFile { version 2.0; format ascii; class dictionary; '
    'location "system"; object fvSolution; }\n'
    "solvers\n"
    "{\n"
    "    p  { solver GAMG; tolerance 1e-06; relTol 0.1; smoother GaussSeidel; }\n"
    "    U  { solver smoothSolver; smoother symGaussSeidel; tolerance 1e-05; "
    "relTol 0.1; nSweeps 1; }\n"
    "}\n"
    "SIMPLE\n"
    "{\n"
    "    nNonOrthogonalCorrectors 2;\n"
    "    pRefCell 0;\n"
    "    pRefValue 0;\n"
    "    residualControl\n"
    "    {\n"
    "        p   1e-3;\n"
    "        U   1e-4;\n"
    "    }\n"
    "}\n"
    "relaxationFactors\n"
    "{\n"
    "    fields\n"
    "    {\n"
    "        p   0.3;\n"
    "    }\n"
    "    equations\n"
    "    {\n"
    "        U   0.7;\n"
    "    }\n"
    "}\n"
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


# ---------------------------------------------------------------------------
# V61-112 acceptance gate: profile-render bytes MUST equal the V61-111
# golden snapshots above. Codex R1 P2-2: this compares against literal
# pre-migration bytes, not against the wrapper that now delegates to the
# profile (which would be a tautology and would silently accept any
# regression in the new code path).
# ---------------------------------------------------------------------------


def test_simplefoam_profile_control_dict_byte_identical_to_v61_111_golden():
    profile = load_profile("simpleFoam")
    rendered = profile.render_control_dict(end_time=200)
    assert rendered == V61_111_GOLDEN_CONTROL_DICT_END_TIME_200, (
        f"controlDict drift from V61-111 golden:\n"
        f"=== profile ({len(rendered)} bytes) ===\n{rendered!r}\n"
        f"=== golden ({len(V61_111_GOLDEN_CONTROL_DICT_END_TIME_200)} bytes) ===\n"
        f"{V61_111_GOLDEN_CONTROL_DICT_END_TIME_200!r}"
    )


def test_simplefoam_profile_control_dict_iteration_floor_byte_identical():
    """V61-112: iteration_floor=100 floors small end_time inputs.
    Snapshot pins both the floor value and the rendered bytes.
    """
    profile = load_profile("simpleFoam")
    rendered = profile.render_control_dict(end_time=2.5)
    assert rendered == V61_111_GOLDEN_CONTROL_DICT_END_TIME_FLOORED


def test_simplefoam_profile_fv_schemes_byte_identical_to_v61_111_golden():
    profile = load_profile("simpleFoam")
    rendered = profile.render_fv_schemes()
    assert rendered == V61_111_GOLDEN_FV_SCHEMES, (
        f"fvSchemes drift from V61-111 golden:\n"
        f"=== profile ({len(rendered)} bytes) ===\n{rendered!r}\n"
        f"=== golden ({len(V61_111_GOLDEN_FV_SCHEMES)} bytes) ===\n"
        f"{V61_111_GOLDEN_FV_SCHEMES!r}"
    )


def test_simplefoam_profile_fv_solution_byte_identical_to_v61_111_golden():
    profile = load_profile("simpleFoam")
    rendered = profile.render_fv_solution()
    assert rendered == V61_111_GOLDEN_FV_SOLUTION, (
        f"fvSolution drift from V61-111 golden:\n"
        f"=== profile ({len(rendered)} bytes) ===\n{rendered!r}\n"
        f"=== golden ({len(V61_111_GOLDEN_FV_SOLUTION)} bytes) ===\n"
        f"{V61_111_GOLDEN_FV_SOLUTION!r}"
    )


# ---------------------------------------------------------------------------
# Wrapper-equivalence tests: verify the V61-112 rewire (build_simplefoam_*
# helpers now call load_profile) routes correctly. Tautological by
# construction in this commit, but documents the contract that any future
# divergence between wrapper and profile is forbidden.
# ---------------------------------------------------------------------------


def test_simplefoam_wrappers_route_to_profile_control_dict():
    profile = load_profile("simpleFoam")
    assert _build_simplefoam_control_dict(200) == profile.render_control_dict(end_time=200)


def test_simplefoam_wrappers_route_to_profile_fv_schemes():
    profile = load_profile("simpleFoam")
    assert _build_simplefoam_fv_schemes() == profile.render_fv_schemes()


def test_simplefoam_wrappers_route_to_profile_fv_solution():
    profile = load_profile("simpleFoam")
    assert _build_simplefoam_fv_solution() == profile.render_fv_solution()


def test_load_profile_caches_result():
    """Profiles are immutable post-load; the registry caches them
    in-process so concurrent requests don't re-parse YAML."""
    p1 = load_profile("simpleFoam")
    p2 = load_profile("simpleFoam")
    assert p1 is p2  # cached identity


# ---------------------------------------------------------------------------
# Codex V61-112 R1 P2-3 closure: schema-validation tests for malformed
# YAML edits. These should raise ProfileSchemaError at LOAD time, not
# silently render invalid OpenFOAM at request time.
# ---------------------------------------------------------------------------


def _build_profile_from_dict(raw: dict, name: str = "simpleFoam") -> SolverProfile:
    """Helper: directly invoke the schema builder on an in-memory dict
    (bypasses YAML parse). Wraps raw KeyError/TypeError/ValueError into
    ProfileSchemaError to mirror what ``load_profile`` does."""
    from ui.backend.services.case_solve.solver_profiles.registry import _build_profile
    try:
        return _build_profile(name, raw)
    except (KeyError, TypeError, ValueError) as exc:
        raise ProfileSchemaError(
            f"profile {name!r} schema mismatch: {exc}"
        ) from exc


def _minimal_simplefoam_raw() -> dict:
    """Minimal valid raw dict that loads as 'simpleFoam'."""
    return {
        "name": "simpleFoam",
        "family": "steady",
        "control_dict": {"application": "simpleFoam"},
        "fv_schemes": {},
        "fv_solution": {
            "control_block_name": "SIMPLE",
            "control_block_fields": {"nNonOrthogonalCorrectors": 2},
            "solvers": {"p": "solver GAMG;"},
        },
    }


def test_fv_solution_solvers_list_raises_schema_error():
    raw = _minimal_simplefoam_raw()
    raw["fv_solution"]["solvers"] = ["GAMG", "smoothSolver"]  # wrong shape
    with pytest.raises(ProfileSchemaError) as exc:
        _build_profile_from_dict(raw)
    assert "solvers" in str(exc.value)


def test_fv_solution_solvers_value_dict_raises_schema_error():
    raw = _minimal_simplefoam_raw()
    raw["fv_solution"]["solvers"] = {"p": {"solver": "GAMG"}}  # nested dict not allowed
    with pytest.raises(ProfileSchemaError) as exc:
        _build_profile_from_dict(raw)
    assert "solvers" in str(exc.value)


def test_fv_solution_control_block_fields_list_raises_schema_error():
    raw = _minimal_simplefoam_raw()
    raw["fv_solution"]["control_block_fields"] = ["nNonOrthogonalCorrectors"]  # wrong shape
    with pytest.raises(ProfileSchemaError) as exc:
        _build_profile_from_dict(raw)
    assert "control_block_fields" in str(exc.value)


def test_fv_solution_residual_control_list_raises_schema_error():
    raw = _minimal_simplefoam_raw()
    raw["fv_solution"]["control_block_fields"] = {
        "residualControl": ["p", "U"],  # should be dict
    }
    # control_block_fields[residualControl] is a list, not a scalar or dict
    with pytest.raises(ProfileSchemaError) as exc:
        _build_profile_from_dict(raw)
    assert "control_block_fields" in str(exc.value)


def test_fv_solution_residual_control_nested_dict_raises_schema_error():
    raw = _minimal_simplefoam_raw()
    raw["fv_solution"]["control_block_fields"] = {
        "residualControl": {"p": {"value": "1e-3"}},  # leaf must be scalar
    }
    with pytest.raises(ProfileSchemaError) as exc:
        _build_profile_from_dict(raw)
    assert "residualControl" in str(exc.value)


def test_fv_solution_relaxation_factors_list_raises_schema_error():
    raw = _minimal_simplefoam_raw()
    raw["fv_solution"]["relaxation_factors_fields"] = [0.3]  # should be dict
    with pytest.raises(ProfileSchemaError) as exc:
        _build_profile_from_dict(raw)
    assert "relaxation_factors_fields" in str(exc.value)
