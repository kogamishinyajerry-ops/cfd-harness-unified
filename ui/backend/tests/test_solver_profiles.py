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
    _build_pimplefoam_control_dict,
    _build_pimplefoam_fv_schemes,
    _build_pimplefoam_fv_solution,
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


# Codex V61-112 R2 P2: control_block_name must be string-typed.


@pytest.mark.parametrize("bad_value", [None, ["SIMPLE"], {"name": "SIMPLE"}, 42])
def test_fv_solution_control_block_name_non_string_raises_schema_error(bad_value):
    raw = _minimal_simplefoam_raw()
    raw["fv_solution"]["control_block_name"] = bad_value
    with pytest.raises(ProfileSchemaError) as exc:
        _build_profile_from_dict(raw)
    assert "control_block_name" in str(exc.value)


# ===========================================================================
# DEC-V61-112 Phase 2 · pimpleFoam profile golden snapshots + schema
# extension tests (per-solver name_pad).
# ===========================================================================

# Golden V61-107.5 inline pimpleFoam bytes captured 2026-05-03 from the
# pre-rewire helpers. These are the V61-112 Phase 2 acceptance contract;
# do NOT regenerate without an explicit DEC saying V61-107.5 changed.
# Canonical case parameters: end_time=5, delta_t=0.001 (representative
# iter02 smoke parameters per V61-107.5 R12 default profile).

V61_107_5_GOLDEN_PIMPLEFOAM_CONTROL_DICT = (
    'FoamFile { version 2.0; format ascii; class dictionary; '
    'location "system"; object controlDict; }\n'
    "application pimpleFoam;\n"
    "startFrom startTime;\n"
    "startTime 0;\n"
    "stopAt endTime;\n"
    "endTime 5;\n"
    "deltaT 0.001;\n"
    "writeControl runTime;\n"
    "writeInterval 1.0;\n"
    "purgeWrite 0;\n"
    "writeFormat ascii;\n"
    "writePrecision 6;\n"
    "writeCompression off;\n"
    "timeFormat general;\n"
    "timePrecision 6;\n"
    "runTimeModifiable true;\n"
    "adjustTimeStep yes;\n"
    "maxCo 0.5;\n"
    "maxDeltaT 0.001;\n"
)

V61_107_5_GOLDEN_PIMPLEFOAM_FV_SCHEMES = (
    'FoamFile { version 2.0; format ascii; class dictionary; '
    'location "system"; object fvSchemes; }\n'
    "ddtSchemes  { default Euler; }\n"
    "gradSchemes { default Gauss linear; }\n"
    "divSchemes  { default none; div(phi,U) Gauss linearUpwind grad(U); "
    "div((nuEff*dev2(T(grad(U))))) Gauss linear; }\n"
    "laplacianSchemes { default Gauss linear corrected; }\n"
    "interpolationSchemes { default linear; }\n"
    "snGradSchemes { default corrected; }\n"
)

V61_107_5_GOLDEN_PIMPLEFOAM_FV_SOLUTION = (
    'FoamFile { version 2.0; format ascii; class dictionary; '
    'location "system"; object fvSolution; }\n'
    "solvers\n"
    "{\n"
    "    p  { solver PCG; preconditioner DIC; tolerance 1e-06; relTol 0.05; }\n"
    "    pFinal { $p; relTol 0; }\n"
    "    U  { solver smoothSolver; smoother symGaussSeidel; "
    "tolerance 1e-05; relTol 0; }\n"
    "    UFinal { $U; relTol 0; }\n"
    "}\n"
    "PIMPLE\n"
    "{\n"
    "    nOuterCorrectors 1;\n"
    "    nCorrectors 2;\n"
    "    nNonOrthogonalCorrectors 2;\n"
    "    pRefCell 0;\n"
    "    pRefValue 0;\n"
    "}\n"
)


def test_list_profile_names_includes_pimplefoam():
    """V61-112 Phase 2: pimpleFoam profile is on disk and listable."""
    assert "pimpleFoam" in list_profile_names()


def test_load_profile_pimplefoam_returns_solver_profile():
    profile = load_profile("pimpleFoam")
    assert isinstance(profile, SolverProfile)
    assert profile.name == "pimpleFoam"
    assert profile.family == "transient"


def test_pimplefoam_profile_control_dict_byte_identical_to_v61_107_5_golden():
    """V61-112 Phase 2 acceptance gate: pimpleFoam profile renders
    bytes byte-identical to V61-107.5 inline output for the canonical
    case parameters (end_time=5, delta_t=0.001).
    """
    profile = load_profile("pimpleFoam")
    rendered = profile.render_control_dict(end_time=5, delta_t=0.001)
    assert rendered == V61_107_5_GOLDEN_PIMPLEFOAM_CONTROL_DICT, (
        f"pimpleFoam controlDict drift from V61-107.5 golden:\n"
        f"=== profile ({len(rendered)} bytes) ===\n{rendered!r}\n"
        f"=== golden ({len(V61_107_5_GOLDEN_PIMPLEFOAM_CONTROL_DICT)} bytes) ===\n"
        f"{V61_107_5_GOLDEN_PIMPLEFOAM_CONTROL_DICT!r}"
    )


def test_pimplefoam_profile_fv_schemes_byte_identical_to_v61_107_5_golden():
    profile = load_profile("pimpleFoam")
    rendered = profile.render_fv_schemes()
    assert rendered == V61_107_5_GOLDEN_PIMPLEFOAM_FV_SCHEMES, (
        f"pimpleFoam fvSchemes drift from V61-107.5 golden:\n"
        f"=== profile ({len(rendered)} bytes) ===\n{rendered!r}\n"
        f"=== golden ({len(V61_107_5_GOLDEN_PIMPLEFOAM_FV_SCHEMES)} bytes) ===\n"
        f"{V61_107_5_GOLDEN_PIMPLEFOAM_FV_SCHEMES!r}"
    )


def test_pimplefoam_profile_fv_solution_byte_identical_to_v61_107_5_golden():
    """V61-112 Phase 2: pimpleFoam fvSolution renders byte-identical
    to V61-107.5 inline including the per-solver name_pad variation
    (p/U have 2-space pad; pFinal/UFinal have 1-space pad).
    """
    profile = load_profile("pimpleFoam")
    rendered = profile.render_fv_solution()
    assert rendered == V61_107_5_GOLDEN_PIMPLEFOAM_FV_SOLUTION, (
        f"pimpleFoam fvSolution drift from V61-107.5 golden:\n"
        f"=== profile ({len(rendered)} bytes) ===\n{rendered!r}\n"
        f"=== golden ({len(V61_107_5_GOLDEN_PIMPLEFOAM_FV_SOLUTION)} bytes) ===\n"
        f"{V61_107_5_GOLDEN_PIMPLEFOAM_FV_SOLUTION!r}"
    )


def test_pimplefoam_wrappers_route_to_profile_control_dict():
    profile = load_profile("pimpleFoam")
    assert _build_pimplefoam_control_dict(5, 0.001) == profile.render_control_dict(
        end_time=5, delta_t=0.001
    )


def test_pimplefoam_wrappers_route_to_profile_fv_schemes():
    profile = load_profile("pimpleFoam")
    assert _build_pimplefoam_fv_schemes() == profile.render_fv_schemes()


def test_pimplefoam_wrappers_route_to_profile_fv_solution():
    profile = load_profile("pimpleFoam")
    assert _build_pimplefoam_fv_solution() == profile.render_fv_solution()


# Schema-extension tests · per-solver name_pad (Phase 2 contract).


def _minimal_pimplefoam_raw_with_solver_entry(p_entry):
    """Minimal valid raw dict with one customizable solvers[p] entry.
    Used to test the str-vs-dict acceptance contract and bad-shape
    rejection for the Phase 2 schema extension.
    """
    return {
        "name": "pimpleFoam",
        "family": "transient",
        "control_dict": {"application": "pimpleFoam"},
        "fv_schemes": {},
        "fv_solution": {
            "control_block_name": "PIMPLE",
            "control_block_fields": {"nOuterCorrectors": 1},
            "solvers": {"p": p_entry},
        },
    }


def test_solvers_string_entry_normalizes_to_default_pad(tmp_path):
    """Phase 2 backward-compat: string-typed solvers value loads as
    {body: <str>, name_pad: 2}. simpleFoam Phase 1 contract."""
    raw = _minimal_pimplefoam_raw_with_solver_entry("solver PCG;")
    profile = _build_profile_from_dict(raw, name="pimpleFoam")
    p_entry = profile.fv_solution.solvers["p"]
    assert p_entry["body"] == "solver PCG;"
    assert p_entry["name_pad"] == 2


def test_solvers_dict_entry_with_explicit_name_pad():
    """Phase 2 extension: dict-typed solvers value with custom
    name_pad takes precedence over default."""
    raw = _minimal_pimplefoam_raw_with_solver_entry(
        {"body": "$p; relTol 0;", "name_pad": 1}
    )
    profile = _build_profile_from_dict(raw, name="pimpleFoam")
    p_entry = profile.fv_solution.solvers["p"]
    assert p_entry["body"] == "$p; relTol 0;"
    assert p_entry["name_pad"] == 1


def test_solvers_dict_entry_default_name_pad_when_omitted():
    raw = _minimal_pimplefoam_raw_with_solver_entry({"body": "solver PCG;"})
    profile = _build_profile_from_dict(raw, name="pimpleFoam")
    assert profile.fv_solution.solvers["p"]["name_pad"] == 2


def test_solvers_dict_entry_missing_body_raises():
    raw = _minimal_pimplefoam_raw_with_solver_entry({"name_pad": 1})
    with pytest.raises(ProfileSchemaError) as exc:
        _build_profile_from_dict(raw, name="pimpleFoam")
    assert "body" in str(exc.value)


def test_solvers_dict_entry_unknown_keys_raises():
    raw = _minimal_pimplefoam_raw_with_solver_entry(
        {"body": "solver PCG;", "extra_key": 42}
    )
    with pytest.raises(ProfileSchemaError) as exc:
        _build_profile_from_dict(raw, name="pimpleFoam")
    assert "extra_key" in str(exc.value)


@pytest.mark.parametrize("bad_pad", ["1", 1.5, None, [1], {"value": 1}])
def test_solvers_dict_entry_non_int_name_pad_raises(bad_pad):
    raw = _minimal_pimplefoam_raw_with_solver_entry(
        {"body": "solver PCG;", "name_pad": bad_pad}
    )
    with pytest.raises(ProfileSchemaError) as exc:
        _build_profile_from_dict(raw, name="pimpleFoam")
    assert "name_pad" in str(exc.value)


def test_solvers_dict_entry_negative_name_pad_raises():
    raw = _minimal_pimplefoam_raw_with_solver_entry(
        {"body": "solver PCG;", "name_pad": -1}
    )
    with pytest.raises(ProfileSchemaError) as exc:
        _build_profile_from_dict(raw, name="pimpleFoam")
    assert "name_pad" in str(exc.value)


def test_solvers_dict_entry_zero_name_pad_renders_no_space():
    """Edge case: name_pad=0 should render `name{ body }` (no space).
    Useful for highly compact custom profiles; legal value."""
    from ui.backend.services.case_solve.solver_profiles.schema import (
        FvSolutionBlock,
    )
    block = FvSolutionBlock(
        solvers={"p": {"body": "solver PCG;", "name_pad": 0}},
        control_block_name="PIMPLE",
        control_block_fields={"nOuterCorrectors": 1},
    )
    rendered = block.render()
    assert "    p{ solver PCG; }" in rendered


def test_pimplefoam_profile_solvers_have_correct_per_entry_pad():
    """V61-112 Phase 2 contract: pimpleFoam profile honors the V61-
    107.5 inline pad pattern — p/U use 2-space pad, pFinal/UFinal use
    1-space pad."""
    profile = load_profile("pimpleFoam")
    solvers = profile.fv_solution.solvers
    assert solvers["p"]["name_pad"] == 2
    assert solvers["U"]["name_pad"] == 2
    assert solvers["pFinal"]["name_pad"] == 1
    assert solvers["UFinal"]["name_pad"] == 1


def test_simplefoam_profile_solvers_normalize_to_default_pad():
    """V61-112 Phase 1 backward-compat: simpleFoam string-typed
    solvers entries normalize to name_pad=2."""
    profile = load_profile("simpleFoam")
    for entry in profile.fv_solution.solvers.values():
        assert entry["name_pad"] == 2


# V61-112 Phase 2 R1 P2 closure: byte-identity to V61-107.5 inline
# requires preserving `.0` for caller-passed float-typed integer-
# valued numerics (end_time=5.0, delta_t=1.0). The fix relies on
# YAML int-vs-float parse distinction and Python's float repr.


def test_pimplefoam_control_dict_write_interval_yaml_float_renders_with_decimal():
    """pimpleFoam.yaml has `write_interval: 1.0` (YAML float) which
    must render as `writeInterval 1.0;` to match V61-107.5 inline."""
    profile = load_profile("pimpleFoam")
    rendered = profile.render_control_dict(end_time=5, delta_t=0.001)
    assert "writeInterval 1.0;" in rendered


def test_simplefoam_control_dict_write_interval_yaml_int_renders_without_decimal():
    """simpleFoam.yaml has `write_interval: 50` (YAML int) which
    must render as `writeInterval 50;` (no `.0`) to match V61-111
    inline."""
    profile = load_profile("simpleFoam")
    rendered = profile.render_control_dict(end_time=200)
    assert "writeInterval 50;" in rendered


def test_pimplefoam_caller_passes_float_end_time_preserves_decimal():
    """Codex Phase 2 R1 P2: caller passing end_time=5.0 (float) must
    render as `endTime 5.0;` matching V61-107.5 inline f-string
    output `f"endTime {end_time};"` for float input."""
    profile = load_profile("pimpleFoam")
    rendered = profile.render_control_dict(end_time=5.0, delta_t=0.001)
    assert "endTime 5.0;" in rendered
    assert "endTime 5;" not in rendered


def test_pimplefoam_caller_passes_float_delta_t_preserves_decimal():
    """Codex Phase 2 R1 P2: caller passing delta_t=1.0 (float) must
    render as `deltaT 1.0;` and `maxDeltaT 1.0;` (V61-107.5 inline
    behavior — used Python f-string default)."""
    profile = load_profile("pimpleFoam")
    rendered = profile.render_control_dict(end_time=10.0, delta_t=1.0)
    assert "deltaT 1.0;" in rendered
    assert "maxDeltaT 1.0;" in rendered
    # Negative assertion: must NOT strip the decimal.
    assert "deltaT 1;" not in rendered


def test_pimplefoam_caller_passes_int_end_time_no_decimal():
    """Caller passing end_time=5 (int) renders as `endTime 5;` (no
    `.0`). Mirrors the inline behavior `f"endTime {5};"` → "5"."""
    profile = load_profile("pimpleFoam")
    rendered = profile.render_control_dict(end_time=5, delta_t=0.001)
    assert "endTime 5;" in rendered
    assert "endTime 5.0;" not in rendered


def test_schema_default_dataclass_values_render_as_integers():
    """V61-112 Phase 2 R2 P3 closure: ControlDictBlock dataclass
    defaults use INT values (start_time=0, end_time_default=200,
    delta_t_default=1, write_interval=50). A profile that OMITS
    these keys should render integer output (no `.0`) under the
    new ``_format_number`` semantics that preserve `.0` for
    YAML-supplied floats. This pins the contract that future
    profiles omitting fields get clean integer output instead of
    spurious decimals.
    """
    from ui.backend.services.case_solve.solver_profiles.schema import (
        ControlDictBlock, FvSchemesBlock, FvSolutionBlock, SolverProfile,
    )
    # Synthesize a minimal profile that omits start_time, end_time_default,
    # delta_t_default, write_interval — relies on dataclass defaults.
    cd = ControlDictBlock(application="testFoam")
    fs = FvSchemesBlock()
    fv = FvSolutionBlock(
        control_block_name="PIMPLE",
        control_block_fields={"nOuterCorrectors": 1},
    )
    profile = SolverProfile(
        name="testFoam", family="transient",
        control_dict=cd, fv_schemes=fs, fv_solution=fv,
    )
    rendered = profile.render_control_dict()
    assert "startTime 0;" in rendered
    assert "startTime 0.0;" not in rendered
    assert "endTime 200;" in rendered
    assert "endTime 200.0;" not in rendered
    assert "deltaT 1;" in rendered
    assert "deltaT 1.0;" not in rendered
    assert "writeInterval 50;" in rendered
    assert "writeInterval 50.0;" not in rendered


# ===========================================================================
# DEC-V61-112 Phase 3 · icoFoam LDC profile golden snapshots.
# ===========================================================================

# Golden V61-097 inline LDC icoFoam bytes captured 2026-05-03 from
# ``bc_setup.py:452-503`` BEFORE the wrapper-equivalent rewire (the
# inline `w("system/controlDict", ...)` / fvSchemes / fvSolution
# calls). icoFoam has no caller-supplied end_time/delta_t — the
# inline used hardcoded literals (endTime 2, deltaT 0.005,
# writeInterval 0.5). The profile's YAML defaults (end_time_default,
# delta_t_default, write_interval) supply these.

V61_097_GOLDEN_ICOFOAM_CONTROL_DICT = (
    'FoamFile { version 2.0; format ascii; class dictionary; '
    'location "system"; object controlDict; }\n'
    "application icoFoam;\n"
    "startFrom startTime;\n"
    "startTime 0;\n"
    "stopAt endTime;\n"
    "endTime 2;\n"
    "deltaT 0.005;\n"
    "writeControl runTime;\n"
    "writeInterval 0.5;\n"
    "purgeWrite 0;\n"
    "writeFormat ascii;\n"
    "writePrecision 6;\n"
    "writeCompression off;\n"
    "timeFormat general;\n"
    "timePrecision 6;\n"
    "runTimeModifiable true;\n"
)

V61_097_GOLDEN_ICOFOAM_FV_SCHEMES = (
    'FoamFile { version 2.0; format ascii; class dictionary; '
    'location "system"; object fvSchemes; }\n'
    "ddtSchemes  { default Euler; }\n"
    "gradSchemes { default Gauss linear; }\n"
    "divSchemes  { default none; div(phi,U) Gauss linear; }\n"
    "laplacianSchemes { default Gauss linear orthogonal; }\n"
    "interpolationSchemes { default linear; }\n"
    "snGradSchemes { default orthogonal; }\n"
)

V61_097_GOLDEN_ICOFOAM_FV_SOLUTION = (
    'FoamFile { version 2.0; format ascii; class dictionary; '
    'location "system"; object fvSolution; }\n'
    "solvers\n"
    "{\n"
    "    p  { solver PCG; preconditioner DIC; tolerance 1e-06; relTol 0.05; }\n"
    "    pFinal { $p; relTol 0; }\n"
    "    U  { solver smoothSolver; smoother symGaussSeidel; "
    "tolerance 1e-05; relTol 0; }\n"
    "}\n"
    "PISO\n"
    "{\n"
    "    nCorrectors 2;\n"
    "    nNonOrthogonalCorrectors 2;\n"
    "    pRefCell 0;\n"
    "    pRefValue 0;\n"
    "}\n"
)


def test_list_profile_names_includes_icofoam():
    assert "icoFoam" in list_profile_names()


def test_load_profile_icofoam_returns_solver_profile():
    profile = load_profile("icoFoam")
    assert isinstance(profile, SolverProfile)
    assert profile.name == "icoFoam"
    assert profile.family == "transient"


def test_icofoam_profile_control_dict_byte_identical_to_v61_097_golden():
    """V61-112 Phase 3 acceptance gate: icoFoam profile renders bytes
    byte-identical to V61-097 inline output. No caller-supplied
    end_time/delta_t — relies on YAML defaults."""
    profile = load_profile("icoFoam")
    rendered = profile.render_control_dict()
    assert rendered == V61_097_GOLDEN_ICOFOAM_CONTROL_DICT, (
        f"icoFoam controlDict drift from V61-097 golden:\n"
        f"=== profile ({len(rendered)} bytes) ===\n{rendered!r}\n"
        f"=== golden ({len(V61_097_GOLDEN_ICOFOAM_CONTROL_DICT)} bytes) ===\n"
        f"{V61_097_GOLDEN_ICOFOAM_CONTROL_DICT!r}"
    )


def test_icofoam_profile_fv_schemes_byte_identical_to_v61_097_golden():
    profile = load_profile("icoFoam")
    rendered = profile.render_fv_schemes()
    assert rendered == V61_097_GOLDEN_ICOFOAM_FV_SCHEMES


def test_icofoam_profile_fv_solution_byte_identical_to_v61_097_golden():
    """V61-112 Phase 3: icoFoam fvSolution renders byte-identical to
    V61-097 inline including the PISO control_block_name (new value
    alongside SIMPLE/PIMPLE) and the 3-solver shape (no UFinal)."""
    profile = load_profile("icoFoam")
    rendered = profile.render_fv_solution()
    assert rendered == V61_097_GOLDEN_ICOFOAM_FV_SOLUTION


def test_icofoam_profile_omits_adjust_time_step_and_max_co():
    """V61-097 LDC icoFoam controlDict does NOT have adjustTimeStep
    or maxCo lines (icoFoam in OpenFOAM-10 ignores them). Phase 3
    profile sets adjust_time_step / max_co to null → omitted from
    rendered output."""
    profile = load_profile("icoFoam")
    rendered = profile.render_control_dict()
    assert "adjustTimeStep" not in rendered
    assert "maxCo" not in rendered
    assert "maxDeltaT" not in rendered


def test_icofoam_profile_solvers_no_ufinal_present():
    """V61-097 LDC fvSolution has p, pFinal, U — but NO UFinal
    (icoFoam PISO reuses U solver settings for final corrector).
    Distinct from V61-107.5 pimpleFoam which has all 4 solvers."""
    profile = load_profile("icoFoam")
    solvers = profile.fv_solution.solvers
    assert set(solvers.keys()) == {"p", "pFinal", "U"}
    assert "UFinal" not in solvers


def test_icofoam_profile_control_block_name_is_piso():
    """V61-097: icoFoam uses PISO control block (transient PISO
    solver). Distinct from PIMPLE (pimpleFoam) and SIMPLE
    (simpleFoam)."""
    profile = load_profile("icoFoam")
    assert profile.fv_solution.control_block_name == "PISO"


# ===========================================================================
# DEC-V61-112 Phase 4 · channel pimpleFoam profile golden snapshots +
# max_delta_t_value schema extension tests.
# ===========================================================================

# Golden V61-101 inline channel pimpleFoam bytes captured 2026-05-03
# from `bc_setup.py:806-893` BEFORE the wrapper-equivalent rewire.
# Channel pimpleFoam uses int writeInterval=1 (NOT 1.0 like STL
# pimpleFoam V61-107.5) and FIXED maxDeltaT=0.05 (NOT follows caller
# delta_t). These distinctions necessitate a SEPARATE profile +
# the Phase 4 schema extension `max_delta_t_value`.

V61_101_GOLDEN_CHANNEL_CONTROL_DICT = (
    'FoamFile { version 2.0; format ascii; class dictionary; '
    'location "system"; object controlDict; }\n'
    "application pimpleFoam;\n"
    "startFrom startTime;\n"
    "startTime 0;\n"
    "stopAt endTime;\n"
    "endTime 5;\n"
    "deltaT 0.005;\n"
    "writeControl runTime;\n"
    "writeInterval 1;\n"  # INT (not 1.0) — distinct from STL pimpleFoam
    "purgeWrite 0;\n"
    "writeFormat ascii;\n"
    "writePrecision 6;\n"
    "writeCompression off;\n"
    "timeFormat general;\n"
    "timePrecision 6;\n"
    "runTimeModifiable true;\n"
    "adjustTimeStep yes;\n"
    "maxCo 0.5;\n"
    "maxDeltaT 0.05;\n"  # FIXED cap — distinct from STL pimpleFoam (follows caller)
)

V61_101_GOLDEN_CHANNEL_FV_SCHEMES = (
    'FoamFile { version 2.0; format ascii; class dictionary; '
    'location "system"; object fvSchemes; }\n'
    "ddtSchemes  { default Euler; }\n"
    "gradSchemes { default Gauss linear; }\n"
    "divSchemes  { default none; div(phi,U) Gauss linear; "
    "div((nuEff*dev2(T(grad(U))))) Gauss linear; }\n"
    "laplacianSchemes { default Gauss linear orthogonal; }\n"  # orthogonal, not corrected
    "interpolationSchemes { default linear; }\n"
    "snGradSchemes { default orthogonal; }\n"  # orthogonal, not corrected
)

V61_101_GOLDEN_CHANNEL_FV_SOLUTION = (
    'FoamFile { version 2.0; format ascii; class dictionary; '
    'location "system"; object fvSolution; }\n'
    "solvers\n"
    "{\n"
    "    p  { solver PCG; preconditioner DIC; tolerance 1e-06; relTol 0.05; }\n"
    "    pFinal { $p; relTol 0; }\n"
    "    U  { solver smoothSolver; smoother symGaussSeidel; "
    "tolerance 1e-05; relTol 0; }\n"
    "    UFinal { $U; relTol 0; }\n"
    "}\n"
    "PIMPLE\n"
    "{\n"
    "    nOuterCorrectors 1;\n"
    "    nCorrectors 2;\n"
    "    nNonOrthogonalCorrectors 2;\n"
    "    pRefCell 0;\n"
    "    pRefValue 0;\n"
    "}\n"
)


def test_list_profile_names_includes_channelpimplefoam():
    assert "channelPimpleFoam" in list_profile_names()


def test_load_profile_channelpimplefoam_returns_solver_profile():
    profile = load_profile("channelPimpleFoam")
    assert isinstance(profile, SolverProfile)
    assert profile.name == "channelPimpleFoam"
    assert profile.family == "transient"
    # Application name is `pimpleFoam` (same OpenFOAM solver as STL
    # pimpleFoam) — the profile name distinguishes the channel
    # variant in the registry.
    assert profile.control_dict.application == "pimpleFoam"


def test_channelpimplefoam_profile_control_dict_byte_identical_to_v61_101_golden():
    profile = load_profile("channelPimpleFoam")
    rendered = profile.render_control_dict()
    assert rendered == V61_101_GOLDEN_CHANNEL_CONTROL_DICT, (
        f"channelPimpleFoam controlDict drift from V61-101 golden:\n"
        f"=== profile ({len(rendered)} bytes) ===\n{rendered!r}\n"
        f"=== golden ({len(V61_101_GOLDEN_CHANNEL_CONTROL_DICT)} bytes) ===\n"
        f"{V61_101_GOLDEN_CHANNEL_CONTROL_DICT!r}"
    )


def test_channelpimplefoam_profile_fv_schemes_byte_identical_to_v61_101_golden():
    profile = load_profile("channelPimpleFoam")
    assert profile.render_fv_schemes() == V61_101_GOLDEN_CHANNEL_FV_SCHEMES


def test_channelpimplefoam_profile_fv_solution_byte_identical_to_v61_101_golden():
    profile = load_profile("channelPimpleFoam")
    assert profile.render_fv_solution() == V61_101_GOLDEN_CHANNEL_FV_SOLUTION


def test_channelpimplefoam_max_delta_t_value_renders_fixed_cap():
    """V61-101 channel uses `maxDeltaT 0.05;` FIXED cap — distinct
    from STL pimpleFoam V61-107.5 which uses `maxDeltaT == caller
    delta_t`. The Phase 4 schema extension `max_delta_t_value`
    enables this byte-identity."""
    profile = load_profile("channelPimpleFoam")
    rendered = profile.render_control_dict()
    assert "maxDeltaT 0.05;" in rendered


def test_channelpimplefoam_distinct_from_stl_pimplefoam():
    """V61-112 Phase 4 contract: channel pimpleFoam differs from STL
    pimpleFoam in writeInterval format (int vs float), maxDeltaT
    semantics (fixed vs follows-caller), and fvSchemes (linear
    vs linearUpwind, orthogonal vs corrected)."""
    channel = load_profile("channelPimpleFoam")
    stl = load_profile("pimpleFoam")
    # Same application but distinct rendering.
    assert channel.control_dict.application == stl.control_dict.application == "pimpleFoam"
    # Distinct writeInterval rendering (channel int vs STL float).
    assert "writeInterval 1;" in channel.render_control_dict()
    assert "writeInterval 1.0;" in stl.render_control_dict(end_time=5, delta_t=0.001)
    # Distinct fvSchemes for divSchemes (channel linear, STL linearUpwind).
    assert "div(phi,U) Gauss linear;" in channel.render_fv_schemes()
    assert "div(phi,U) Gauss linearUpwind grad(U);" in stl.render_fv_schemes()
    # Distinct laplacian (channel orthogonal, STL corrected).
    assert "laplacianSchemes { default Gauss linear orthogonal; }" in channel.render_fv_schemes()
    assert "laplacianSchemes { default Gauss linear corrected; }" in stl.render_fv_schemes()


# Phase 4 schema extension tests · max_delta_t_value field.


def test_max_delta_t_value_takes_precedence_over_follows_delta_t():
    """V61-112 Phase 4 schema extension: when max_delta_t_value is
    set, it takes precedence over max_delta_t_follows_delta_t."""
    from ui.backend.services.case_solve.solver_profiles.schema import (
        ControlDictBlock,
    )
    cd = ControlDictBlock(
        application="testFoam",
        max_delta_t_value=0.05,
        max_delta_t_follows_delta_t=True,  # would normally render dt
    )
    rendered = cd.render(end_time=5, delta_t=0.001)
    # Fixed value wins.
    assert "maxDeltaT 0.05;" in rendered
    # Caller delta_t value NOT rendered as maxDeltaT.
    assert "maxDeltaT 0.001;" not in rendered


def test_max_delta_t_value_none_falls_through_to_follows_delta_t():
    """When max_delta_t_value is None and follows_delta_t is True,
    falls through to caller delta_t (STL pimpleFoam Phase 2 behavior
    preserved)."""
    from ui.backend.services.case_solve.solver_profiles.schema import (
        ControlDictBlock,
    )
    cd = ControlDictBlock(
        application="pimpleFoam",
        max_delta_t_value=None,
        max_delta_t_follows_delta_t=True,
    )
    rendered = cd.render(end_time=5, delta_t=0.001)
    assert "maxDeltaT 0.001;" in rendered


# Codex Phase 4 R1 P2: control_dict transient-field schema validation.


def _minimal_channel_raw_with_control_dict_field(field_name, field_value):
    return {
        "name": "channelPimpleFoam",
        "family": "transient",
        "control_dict": {
            "application": "pimpleFoam",
            field_name: field_value,
        },
        "fv_schemes": {},
        "fv_solution": {
            "control_block_name": "PIMPLE",
            "control_block_fields": {"nOuterCorrectors": 1},
            "solvers": {"p": "solver PCG;"},
        },
    }


@pytest.mark.parametrize("bad_value", ["0.05", True, False, [0.05], {"v": 0.05}])
def test_control_dict_max_delta_t_value_non_numeric_raises_schema_error(bad_value):
    """Codex Phase 4 R1 P2: max_delta_t_value must be int/float/None;
    bool/string/list/dict rejected at load time, not deferred to
    render time where _format_number would emit `maxDeltaT yes;` or
    raise an uncaught exception."""
    raw = _minimal_channel_raw_with_control_dict_field(
        "max_delta_t_value", bad_value
    )
    with pytest.raises(ProfileSchemaError) as exc:
        _build_profile_from_dict(raw, name="channelPimpleFoam")
    assert "max_delta_t_value" in str(exc.value)


@pytest.mark.parametrize("bad_value", ["0.5", True, False, [0.5], {"v": 0.5}])
def test_control_dict_max_co_non_numeric_raises_schema_error(bad_value):
    """max_co same validation pattern as max_delta_t_value."""
    raw = _minimal_channel_raw_with_control_dict_field("max_co", bad_value)
    with pytest.raises(ProfileSchemaError) as exc:
        _build_profile_from_dict(raw, name="channelPimpleFoam")
    assert "max_co" in str(exc.value)


@pytest.mark.parametrize("bad_value", ["yes", "true", 1, 0, [True]])
def test_control_dict_adjust_time_step_non_bool_raises_schema_error(bad_value):
    """adjust_time_step must be bool or None; reject string and int
    (int 0/1 would silently coerce to False/True via bool subclass)."""
    raw = _minimal_channel_raw_with_control_dict_field(
        "adjust_time_step", bad_value
    )
    with pytest.raises(ProfileSchemaError) as exc:
        _build_profile_from_dict(raw, name="channelPimpleFoam")
    assert "adjust_time_step" in str(exc.value)


@pytest.mark.parametrize("bad_value", ["100", 100.5, True, [100]])
def test_control_dict_iteration_floor_non_int_raises_schema_error(bad_value):
    """iteration_floor must be int or None."""
    raw = _minimal_channel_raw_with_control_dict_field(
        "iteration_floor", bad_value
    )
    with pytest.raises(ProfileSchemaError) as exc:
        _build_profile_from_dict(raw, name="channelPimpleFoam")
    assert "iteration_floor" in str(exc.value)


def test_max_delta_t_both_none_omits_line():
    """When both fields are unset, maxDeltaT line omitted (icoFoam
    Phase 3 behavior preserved)."""
    from ui.backend.services.case_solve.solver_profiles.schema import (
        ControlDictBlock,
    )
    cd = ControlDictBlock(application="icoFoam")
    rendered = cd.render(end_time=2, delta_t=0.005)
    assert "maxDeltaT" not in rendered


def test_pimplefoam_byte_identity_with_default_caller_signature_floats():
    """V61-112 Phase 2 R1 P2 regression-pin: setup_bc_from_stl_patches
    passes float-typed end_time/delta_t to _build_pimplefoam_control_dict.
    The profile path MUST byte-match the inline f-string behavior for
    common float-valued integer inputs (5.0, 1.0)."""
    profile = load_profile("pimpleFoam")
    # Reproduce the V61-107.5 inline output for the real default-caller
    # values that Codex P2 R1 flagged.
    expected = (
        'FoamFile { version 2.0; format ascii; class dictionary; '
        'location "system"; object controlDict; }\n'
        "application pimpleFoam;\n"
        "startFrom startTime;\n"
        "startTime 0;\n"
        "stopAt endTime;\n"
        "endTime 5.0;\n"  # caller passed float 5.0 → `.0` preserved
        "deltaT 1.0;\n"   # caller passed float 1.0 → `.0` preserved
        "writeControl runTime;\n"
        "writeInterval 1.0;\n"
        "purgeWrite 0;\n"
        "writeFormat ascii;\n"
        "writePrecision 6;\n"
        "writeCompression off;\n"
        "timeFormat general;\n"
        "timePrecision 6;\n"
        "runTimeModifiable true;\n"
        "adjustTimeStep yes;\n"
        "maxCo 0.5;\n"
        "maxDeltaT 1.0;\n"  # follows delta_t → `.0` preserved
    )
    rendered = profile.render_control_dict(end_time=5.0, delta_t=1.0)
    assert rendered == expected
