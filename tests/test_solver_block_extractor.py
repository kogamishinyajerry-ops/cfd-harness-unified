"""Tests for `ui.backend.services.case_extractors.solver_block_extractor`.

Per DEC-V61-211. Two layers:

  (A) **Cross-case structural sweep** — parametrize over all 26
      `.planning/case_profiles/*_dicts/` directories that ship a
      `system/controlDict`, assert every one yields a non-None snapshot
      whose `solver` field matches a baseline mapping (verified by direct
      grep of `application` keys, 2026-05-28). This is the real
      case-discrimination signal: 5 distinct solvers (4 density-based).

  (B) **Edge-case units** — missing dir, missing key, comment-disguised
      key, malformed deltaT, all OF bool token spellings. Each pins one
      behavior the extractor's docstring promises.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from ui.backend.services.case_extractors import extract_solver_block_snapshot
# Codex R0 P1: do NOT import SolverBlockSnapshot from geometry_ingest at
# module top — that chain pulls trimesh and breaks `.[ui]`-only test
# environments. The local mirror in case_extractors covers shape needs.
from ui.backend.services.case_extractors.solver_block_extractor import (
    SolverBlockSnapshot as _MirroredSnapshot,
    _DENSITY_BASED_AT_RISK_SOLVERS as _LOCAL_AT_RISK,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
PROFILES_DIR = REPO_ROOT / ".planning" / "case_profiles"

# Baseline solver mapping: verified by `grep -E '^\s*application' …/controlDict`
# across all 26 in-repo case_profiles on 2026-05-28. If a future case is
# added with a new solver (e.g. chtMultiRegionFoam) extend this dict.
# Density-based (per `solver_block_advisor._DENSITY_BASED_SOLVERS`):
# rhoSimpleFoam, rhoPimpleFoam, rhoCentralFoam.
_EXPECTED_SOLVER: dict[str, str] = {
    "case_004_v64_blade_cad_fix_dicts": "simpleFoam",
    "case_004_v64_case_spec_fix_dicts": "simpleFoam",
    "case_004_v64_mesh_gen_v2_dicts": "simpleFoam",
    "case_004_v64_val_full_1_dicts": "simpleFoam",
    "case_004_v65_le_te_fix_dicts": "simpleFoam",
    "case_006_v64_thermo_fpe_fix_dicts": "rhoSimpleFoam",
    "case_006_v64_val_full_2_dicts": "rhoSimpleFoam",
    "case_016_v64_thermo_fpe_fix_dicts": "rhoPimpleFoam",
    "case_021_v64_val_full_3_incomp_dicts": "simpleFoam",
    "case_021_v65_tbl_2nd_re_dicts": "simpleFoam",
    "case_022_v64_val_full_5_bfs_dicts": "simpleFoam",
    "case_024_v64_cavity_v2_dicts": "simpleFoam",
    "case_024_v64_val_full_4_cavity_dicts": "simpleFoam",
    "case_025_v64_poiseuille_dicts": "simpleFoam",
    "case_026_v64_couette_dicts": "simpleFoam",
    "case_027_v64_pipe_dicts": "simpleFoam",
    "case_027_v65_pipe_2nd_witness_dicts": "simpleFoam",
    "case_028_apu_bay_ventilation_dicts": "simpleFoam",
    "case_028_v2_apu_bay_ventilation_dicts": "simpleFoam",
    "case_028_v3_apu_bay_ventilation_dicts": "simpleFoam",
    "case_028_v4_apu_bay_ventilation_dicts": "pimpleFoam",
    "case_029_naca_stall_dicts": "simpleFoam",
    "case_030_v65_wedge15ma5_v106_2nd_witness_dicts": "rhoCentralFoam",
    "case_031_v65_naca0012_supersonic_v106_retry_dicts": "rhoPimpleFoam",
    "case_032_v65_flat_plate_2nd_witness_dicts": "simpleFoam",
    "case_035_v65_nasa_tmr_flat_plate_FULL_dicts": "simpleFoam",
}

_DENSITY_BASED = frozenset({"rhoSimpleFoam", "rhoPimpleFoam", "rhoCentralFoam"})


# ---- (A) cross-case structural sweep --------------------------------


@pytest.mark.parametrize("profile", sorted(_EXPECTED_SOLVER.keys()))
def test_extractor_returns_expected_solver_per_profile(profile: str) -> None:
    """Every shipped case_profile yields a non-None snapshot whose
    `solver` matches the verified baseline.

    If this fails on a baseline-listed profile: either the extractor
    regressed, or the profile's controlDict was rewritten (truth-chain
    check — investigate which).
    """
    case_dir = PROFILES_DIR / profile
    if not case_dir.is_dir():
        pytest.skip(f"profile dir missing: {profile}")

    snap = extract_solver_block_snapshot(case_dir)
    assert snap is not None, (
        f"{profile}: extractor returned None, expected snapshot with "
        f"solver={_EXPECTED_SOLVER[profile]!r}"
    )
    assert snap.solver == _EXPECTED_SOLVER[profile], (
        f"{profile}: extracted solver={snap.solver!r}, "
        f"expected {_EXPECTED_SOLVER[profile]!r}"
    )


def test_extractor_covers_all_in_repo_profiles_with_controldict() -> None:
    """Canary: every profile that ships a controlDict is covered by the
    baseline. Catches silent drift if a new profile is added (would
    otherwise pass invisibly because parametrize only iterates the
    baseline).
    """
    if not PROFILES_DIR.is_dir():
        pytest.skip("case_profiles dir missing")
    on_disk = {
        p.parent.parent.name for p in PROFILES_DIR.glob("*/system/controlDict")
    }
    listed = set(_EXPECTED_SOLVER.keys())
    missing = on_disk - listed
    unexpected = listed - on_disk
    assert not missing, (
        f"new case_profiles with controlDict not in baseline: {sorted(missing)} "
        f"— add to _EXPECTED_SOLVER after grep-verifying their `application` key"
    )
    if unexpected:
        # Baseline entries for profiles that disappeared (renamed/removed).
        # Soft note via skip-fail behavior in the parametrized test above;
        # do not fail here — removal is a deliberate ops act, not a bug.
        pass


def test_density_based_subset_is_exactly_5_profiles() -> None:
    """Pin the case-discrimination guarantee that motivated DEC-V61-211.

    If this drops to 4 or rises to 6, the eval's downstream
    "density-based vs incompressible" dispatch differentiation has
    shifted — either a profile gained/lost a density-based solver, or
    a new profile was added without baseline updates. Either is a
    truth-chain alert.

    Derivation: from `_EXPECTED_SOLVER`:
      rhoSimpleFoam  ×2 — case_006_v64_thermo_fpe_fix, case_006_v64_val_full_2
      rhoPimpleFoam  ×2 — case_016_v64_thermo_fpe_fix, case_031_v65_naca0012_…
      rhoCentralFoam ×1 — case_030_v65_wedge15ma5_v106_2nd_witness
    """
    density_count = sum(
        1 for s in _EXPECTED_SOLVER.values() if s in _DENSITY_BASED
    )
    assert density_count == 5, (
        f"density-based profile count = {density_count}, expected 5 "
        f"(see docstring for the line-item derivation). Drift requires "
        f"investigation."
    )


# ---- (B) edge-case units --------------------------------------------


def test_missing_system_dir_returns_none(tmp_path: Path) -> None:
    assert extract_solver_block_snapshot(tmp_path) is None


def test_missing_controldict_returns_none(tmp_path: Path) -> None:
    (tmp_path / "system").mkdir()
    assert extract_solver_block_snapshot(tmp_path) is None


def test_controldict_without_application_returns_none(tmp_path: Path) -> None:
    (tmp_path / "system").mkdir()
    (tmp_path / "system" / "controlDict").write_text(
        "FoamFile { version 2.0; }\n"
        "startTime 0;\n"
        "endTime 100;\n",
        encoding="utf-8",
    )
    # No `application` key → snapshot has no meaning to the advisor → None.
    assert extract_solver_block_snapshot(tmp_path) is None


def test_application_inside_line_comment_does_not_false_match(
    tmp_path: Path,
) -> None:
    """The extractor strips `//` comments before regex.

    Without comment-stripping, the regex would happily pick `simpleFoam`
    out of a documentation comment — fabricating a solver field from
    prose. This pins the no-fabrication behavior.
    """
    (tmp_path / "system").mkdir()
    (tmp_path / "system" / "controlDict").write_text(
        "// previous run used: application simpleFoam;\n"
        "// (commented out for an experiment)\n"
        "FoamFile { version 2.0; }\n",
        encoding="utf-8",
    )
    assert extract_solver_block_snapshot(tmp_path) is None


def test_application_inside_block_comment_does_not_false_match(
    tmp_path: Path,
) -> None:
    (tmp_path / "system").mkdir()
    (tmp_path / "system" / "controlDict").write_text(
        "/* NOTE: do not use\n"
        "   application simpleFoam;\n"
        "   on this case yet */\n"
        "FoamFile { version 2.0; }\n",
        encoding="utf-8",
    )
    assert extract_solver_block_snapshot(tmp_path) is None


def test_real_application_succeeds_even_with_adjacent_comments(
    tmp_path: Path,
) -> None:
    (tmp_path / "system").mkdir()
    (tmp_path / "system" / "controlDict").write_text(
        "// previous run used: application icoFoam;\n"
        "application simpleFoam;\n"
        "// (we switched in v3)\n",
        encoding="utf-8",
    )
    snap = extract_solver_block_snapshot(tmp_path)
    assert snap is not None
    assert snap.solver == "simpleFoam"


@pytest.mark.parametrize(
    "token,expected",
    [
        ("yes", True),
        ("true", True),
        ("on", True),
        ("no", False),
        ("false", False),
        ("off", False),
    ],
)
def test_adjusttimestep_bool_tokens(
    tmp_path: Path, token: str, expected: bool
) -> None:
    (tmp_path / "system").mkdir()
    (tmp_path / "system" / "controlDict").write_text(
        f"application simpleFoam;\nadjustTimeStep {token};\n",
        encoding="utf-8",
    )
    snap = extract_solver_block_snapshot(tmp_path)
    assert snap is not None and snap.adjust_time_step is expected


def test_adjusttimestep_unknown_token_on_non_density_based_yields_none_flag(
    tmp_path: Path,
) -> None:
    """For a NON-density-based solver, an unparseable adjustTimeStep
    yields `adjust_time_step=None` on a still-valid snapshot.

    simpleFoam does NOT route through `check_solver_block`'s V27 dispatch
    (advisor's `_DENSITY_BASED_SYMMETRIC_SOLVERS` is currently just
    rhoCentralFoam), so a `None` here is unambiguous — the downstream
    advisor will not synthesize a false finding from it.
    """
    (tmp_path / "system").mkdir()
    (tmp_path / "system" / "controlDict").write_text(
        "application simpleFoam;\nadjustTimeStep $myMacro;\n",
        encoding="utf-8",
    )
    snap = extract_solver_block_snapshot(tmp_path)
    assert snap is not None
    assert snap.solver == "simpleFoam"
    assert snap.adjust_time_step is None


def test_adjusttimestep_unknown_token_on_density_based_refuses_snapshot(
    tmp_path: Path,
) -> None:
    """Codex DEC-V61-211 R0 P2(#2) fix: for a DENSITY-BASED solver, an
    unparseable adjustTimeStep returns None for the WHOLE SNAPSHOT.

    Rationale: `assemble_stack(solver_block_snapshot=snap)` with
    `snap.adjust_time_step=None` makes the advisor assume the OF default
    `no` and emit `v27_adjusttimestep_required` — a CRITICAL finding.
    If the source key was actually a macro (`$myAdjust;`) that might
    expand to `yes`, that finding is FABRICATED. Truth-chain: honest
    refusal beats false certainty. Caller sees `None` snapshot and
    decides what to do (typically: skip the V27 check for this case
    pending macro resolution).
    """
    (tmp_path / "system").mkdir()
    (tmp_path / "system" / "controlDict").write_text(
        "application rhoCentralFoam;\nadjustTimeStep $myAdjust;\n",
        encoding="utf-8",
    )
    snap = extract_solver_block_snapshot(tmp_path)
    assert snap is None, (
        f"density-based solver with unparseable adjustTimeStep must yield "
        f"None snapshot (Codex R0 P2#2); got snapshot={snap!r}"
    )


def test_density_based_unknown_token_with_other_density_solvers_allows_snapshot(
    tmp_path: Path,
) -> None:
    """Only solvers in `_DENSITY_BASED_AT_RISK_SOLVERS` trigger the
    refusal; other rho-prefix solvers (rhoSimpleFoam / rhoPimpleFoam) do
    NOT route through V27 in today's advisor → unparseable adjust is fine.

    Pins the scope-locking of the refusal — a future expansion of the
    upstream V27 dispatch set (rhoCentralDyMFoam etc.) requires updating
    the local mirror AND this test together.
    """
    (tmp_path / "system").mkdir()
    (tmp_path / "system" / "controlDict").write_text(
        "application rhoPimpleFoam;\nadjustTimeStep $myMacro;\n",
        encoding="utf-8",
    )
    snap = extract_solver_block_snapshot(tmp_path)
    assert snap is not None
    assert snap.solver == "rhoPimpleFoam"
    assert snap.adjust_time_step is None  # benign for non-at-risk solvers


def test_deltat_scientific_notation_parses(tmp_path: Path) -> None:
    (tmp_path / "system").mkdir()
    (tmp_path / "system" / "controlDict").write_text(
        "application rhoCentralFoam;\ndeltaT 1e-6;\n",
        encoding="utf-8",
    )
    snap = extract_solver_block_snapshot(tmp_path)
    assert snap is not None and snap.delta_t == pytest.approx(1e-6)


def test_deltat_calc_expression_yields_none_not_fabrication(
    tmp_path: Path,
) -> None:
    """`#calc "expr"` is documented unsupported (DEC-V61-211 scope-lock).

    The extractor must NOT pretend to parse it — None is the honest
    answer ("we cannot determine deltaT from this source") rather than
    a wrong float.
    """
    (tmp_path / "system").mkdir()
    (tmp_path / "system" / "controlDict").write_text(
        'application simpleFoam;\ndeltaT #calc "1e-3 * 5";\n',
        encoding="utf-8",
    )
    snap = extract_solver_block_snapshot(tmp_path)
    assert snap is not None
    assert snap.solver == "simpleFoam"
    assert snap.delta_t is None


def test_preconditioners_v01_always_empty(tmp_path: Path) -> None:
    """v0.1 does not parse the `fvSolution.solvers` block (DEC-V61-211 §Out).

    Pins the omission so a future caller cannot accidentally rely on
    populated preconditioners from v0.1 output.
    """
    (tmp_path / "system").mkdir()
    (tmp_path / "system" / "controlDict").write_text(
        "application simpleFoam;\n",
        encoding="utf-8",
    )
    (tmp_path / "system" / "fvSolution").write_text(
        'solvers { U { solver PBiCGStab; preconditioner DILU; } }\n',
        encoding="utf-8",
    )
    snap = extract_solver_block_snapshot(tmp_path)
    assert snap is not None
    assert snap.preconditioners == {}


def test_snapshot_is_the_local_mirror_dataclass(tmp_path: Path) -> None:
    """Sanity: extractor returns a `_MirroredSnapshot` (local mirror).

    The advisor's `check_solver_block` accesses fields by name (duck-typed)
    so the mirror works in production; isinstance against the upstream
    class is asserted separately in `test_local_mirror_matches_upstream`
    (skip-if-no-trimesh).
    """
    (tmp_path / "system").mkdir()
    (tmp_path / "system" / "controlDict").write_text(
        "application simpleFoam;\n", encoding="utf-8"
    )
    snap = extract_solver_block_snapshot(tmp_path)
    assert isinstance(snap, _MirroredSnapshot)


def test_local_mirror_matches_upstream() -> None:
    """Codex R0 P1 fix: the local mirror dataclass must have the same
    field set as the upstream `solver_block_advisor.SolverBlockSnapshot`.

    Skipped when trimesh isn't installed (the `.[ui]`-only env that
    motivated the mirror in the first place); strict otherwise. This
    catches the drift mode: upstream adds a field, mirror falls behind,
    extractor silently emits incomplete snapshots in workbench env.
    """
    try:
        from ui.backend.services.geometry_ingest.solver_block_advisor import (
            SolverBlockSnapshot as _Upstream,
        )
    except ImportError as exc:
        pytest.skip(f"upstream unavailable (likely trimesh missing): {exc}")
    import dataclasses
    mirror_fields = {f.name for f in dataclasses.fields(_MirroredSnapshot)}
    upstream_fields = {f.name for f in dataclasses.fields(_Upstream)}
    assert mirror_fields == upstream_fields, (
        f"local mirror field-set drifted from upstream.\n"
        f"  mirror   : {sorted(mirror_fields)}\n"
        f"  upstream : {sorted(upstream_fields)}\n"
        f"  missing  : {sorted(upstream_fields - mirror_fields)}\n"
        f"  extra    : {sorted(mirror_fields - upstream_fields)}"
    )


def test_density_based_at_risk_mirror_parity() -> None:
    """The local `_DENSITY_BASED_AT_RISK_SOLVERS` constant must match the
    upstream advisor's V27 dispatch set.

    Drift mode: upstream adds rhoCentralDyMFoam to its set; mirror stays
    at {rhoCentralFoam} → extractor stops refusing snapshots that would
    cause false-positive V27 findings on the new solver. This canary
    pins the parity.
    """
    try:
        from ui.backend.services.geometry_ingest.solver_block_advisor import (
            _DENSITY_BASED_SYMMETRIC_SOLVERS as _Upstream,
        )
    except ImportError as exc:
        pytest.skip(f"upstream unavailable (likely trimesh missing): {exc}")
    assert _LOCAL_AT_RISK == _Upstream, (
        f"local _DENSITY_BASED_AT_RISK_SOLVERS drifted from upstream.\n"
        f"  local    : {sorted(_LOCAL_AT_RISK)}\n"
        f"  upstream : {sorted(_Upstream)}"
    )


def test_extractor_module_loads_without_trimesh() -> None:
    """Codex R0 P1 fix: the extractor module must import even when
    trimesh is absent (`.[ui]` env without `[workbench]`).

    Pin via subprocess so the test environment's trimesh availability
    doesn't mask a real regression — the subprocess clears trimesh from
    sys.modules and stubs the import so the chain is forced to NOT use
    trimesh, then imports the extractor and checks it works.
    """
    import subprocess
    import sys

    code = (
        "import sys\n"
        # Mark trimesh as unavailable in the importer's view.
        "sys.modules['trimesh'] = None\n"
        "from ui.backend.services.case_extractors import (\n"
        "    extract_solver_block_snapshot,\n"
        ")\n"
        "from ui.backend.services.case_extractors.solver_block_extractor "
        "import SolverBlockSnapshot\n"
        "import dataclasses\n"
        "names = sorted(f.name for f in dataclasses.fields(SolverBlockSnapshot))\n"
        "assert names == ['adjust_time_step', 'delta_t', 'preconditioners', 'solver'], names\n"
        "print('OK')\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        env={**__import__("os").environ, "PYTHONPATH": str(REPO_ROOT)},
        timeout=30,
    )
    assert result.returncode == 0 and result.stdout.strip() == "OK", (
        f"extractor failed to import without trimesh.\n"
        f"  stdout: {result.stdout!r}\n"
        f"  stderr: {result.stderr!r}"
    )
