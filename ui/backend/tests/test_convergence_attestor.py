"""DEC-V61-038 tests: convergence attestor A1..A6.

Coverage: each check's PASS/HAZARD/FAIL branch + LDC/BFS integration
(real audit logs at reports/phase5_fields/*).

Ground truth from Codex round-1 physics audit (DEC-036):
  LDC    → ATTEST_PASS (all 6 checks PASS or N/A)
  BFS    → ATTEST_FAIL via A2 (sum_local=5.25e+18) + A3 HAZARD + A5 HAZARD
  DHC    → ATTEST_PASS (converged, Nu off gold but physics OK)
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from src import convergence_attestor as ca
from src.convergence_attestor import Thresholds, load_thresholds


def _write_log(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "log.simpleFoam"
    p.write_text(content, encoding="utf-8")
    return p


def _make_audit_fixture_report(tmp_path: Path, log_content: str) -> SimpleNamespace:
    from src.models import ComparisonResult, DeviationDetail

    log = _write_log(tmp_path, log_content)
    execution_result = SimpleNamespace(
        success=True,
        exit_code=0,
        raw_output_path=str(tmp_path),
        key_quantities={"u_centerline": [-0.0415]},
    )
    comparison_result = ComparisonResult(
        passed=True,
        deviations=[
            DeviationDetail(
                quantity="u_centerline[y=0.0625]",
                expected=-0.04192,
                actual=-0.0415,
                relative_error=0.0100,
                tolerance=0.05,
            )
        ],
        summary="within tolerance",
    )
    return SimpleNamespace(
        comparison_result=comparison_result,
        execution_result=execution_result,
        task_spec=None,
        attestation=ca.attest(
            log,
            execution_result=execution_result,
            case_id="lid_driven_cavity",
        ),
    )


# ---------------------------------------------------------------------------
# A1 solver_exit_clean
# ---------------------------------------------------------------------------

def test_a1_passes_on_clean_log(tmp_path: Path) -> None:
    log = _write_log(tmp_path, "Time = 1\nExecutionTime = 1 s\nEnd\n")
    result = ca.attest(log)
    a1 = next(c for c in result.checks if c.check_id == "A1")
    assert a1.verdict == "PASS"


def test_a1_fails_on_foam_fatal(tmp_path: Path) -> None:
    content = "Time = 1\nFOAM FATAL IO ERROR: missing dict\nExiting\n"
    log = _write_log(tmp_path, content)
    result = ca.attest(log)
    a1 = next(c for c in result.checks if c.check_id == "A1")
    assert a1.verdict == "FAIL"
    assert result.overall == "ATTEST_FAIL"


def test_a1_ignores_sigfpe_startup_banner(tmp_path: Path) -> None:
    """DEC-036b Codex nit: 'floating point exception trapping' is a
    startup banner, not an actual exception. Must NOT fire A1."""
    content = (
        "sigFpe : Enabling floating point exception trapping (FOAM_SIGFPE).\n"
        "Time = 1\nEnd\n"
    )
    log = _write_log(tmp_path, content)
    result = ca.attest(log)
    a1 = next(c for c in result.checks if c.check_id == "A1")
    assert a1.verdict == "PASS"


# ---------------------------------------------------------------------------
# A2 continuity_floor
# ---------------------------------------------------------------------------

def test_a2_passes_on_clean_continuity(tmp_path: Path) -> None:
    content = (
        "time step continuity errors : "
        "sum local = 1e-07, global = 1e-09, cumulative = 1e-12\n"
    )
    log = _write_log(tmp_path, content)
    result = ca.attest(log)
    a2 = next(c for c in result.checks if c.check_id == "A2")
    assert a2.verdict == "PASS"


def test_a2_hazard_between_floors(tmp_path: Path) -> None:
    """sum_local between A2 floor (1e-4) and G5 floor (1e-2) → HAZARD."""
    content = (
        "time step continuity errors : "
        "sum local = 1e-03, global = 1e-05, cumulative = 0.001\n"
    )
    log = _write_log(tmp_path, content)
    result = ca.attest(log)
    a2 = next(c for c in result.checks if c.check_id == "A2")
    assert a2.verdict == "HAZARD"


def test_a2_hazard_above_g5_floor_after_split_brain_fix(tmp_path: Path) -> None:
    """Codex DEC-038 round-1 A2/G5 split-brain fix: A2 no longer returns
    FAIL even for sum_local > 1e-2. That FAIL call belongs to G5 at the
    gate layer. A2 stays strictly HAZARD-tier."""
    content = (
        "time step continuity errors : "
        "sum local = 0.5, global = 0.01, cumulative = 0.1\n"
    )
    log = _write_log(tmp_path, content)
    result = ca.attest(log)
    a2 = next(c for c in result.checks if c.check_id == "A2")
    assert a2.verdict == "HAZARD"  # was FAIL pre-fix


# ---------------------------------------------------------------------------
# A3 residual_floor
# ---------------------------------------------------------------------------

def test_a3_passes_when_all_residuals_below_floor(tmp_path: Path) -> None:
    content = (
        "smoothSolver:  Solving for Ux, Initial residual = 1e-06, "
        "Final residual = 1e-07, No Iterations 2\n"
    )
    log = _write_log(tmp_path, content)
    result = ca.attest(log)
    a3 = next(c for c in result.checks if c.check_id == "A3")
    assert a3.verdict == "PASS"


def test_a3_hazard_when_final_residual_above_floor(tmp_path: Path) -> None:
    content = (
        "smoothSolver:  Solving for Ux, Initial residual = 0.05, "
        "Final residual = 0.001, No Iterations 20\n"
    )
    log = _write_log(tmp_path, content)
    result = ca.attest(log)
    a3 = next(c for c in result.checks if c.check_id == "A3")
    assert a3.verdict == "HAZARD"
    assert "Ux" in a3.evidence["offenders"]


# ---------------------------------------------------------------------------
# A4 solver_iteration_cap
# ---------------------------------------------------------------------------

def test_a4_fails_on_consecutive_cap_hits(tmp_path: Path) -> None:
    """5 consecutive Time= blocks each with a capped GAMG p solve → FAIL.

    Codex round-1 BLOCKER 2: measurement unit changed from consecutive
    lines to consecutive TIME STEPS. Each `Time =` divider opens a new
    block, so this test now needs Time= dividers.
    """
    content = "".join(
        f"Time = {i}\nGAMG:  Solving for p, Initial residual = 0.9, "
        "Final residual = 0.5, No Iterations 1000\n"
        for i in range(5)
    )
    log = _write_log(tmp_path, content)
    result = ca.attest(log)
    a4 = next(c for c in result.checks if c.check_id == "A4")
    assert a4.verdict == "FAIL"
    assert a4.evidence["consecutive_cap_blocks"] >= 3


def test_a4_fails_on_p_rgh_buoyant_log(tmp_path: Path) -> None:
    """Codex DEC-038 round-1 BLOCKER 1: impinging_jet stuck solver is
    `GAMG: Solving for p_rgh` in log.buoyantFoam — A4 regex must match
    p_rgh (not just `p,`) to catch the real impinging_jet case.
    """
    content = "\n".join(
        [f"Time = {i}s\nGAMG:  Solving for p_rgh, Initial residual = 0.7, "
         "Final residual = 0.5, No Iterations 1000"
         for i in range(5)]
    )
    log = _write_log(tmp_path, content)
    result = ca.attest(log)
    a4 = next(c for c in result.checks if c.check_id == "A4")
    assert a4.verdict == "FAIL", f"got {a4.verdict}: {a4.summary}"


def test_a4_fails_on_dicpcg_p_rgh(tmp_path: Path) -> None:
    """DHC uses DICPCG: Solving for p_rgh. Same regex coverage requirement."""
    content = "\n".join(
        [f"Time = {i*0.5}s\nDICPCG:  Solving for p_rgh, Initial residual = 0.8, "
         "Final residual = 0.6, No Iterations 1000"
         for i in range(1, 6)]
    )
    log = _write_log(tmp_path, content)
    result = ca.attest(log)
    a4 = next(c for c in result.checks if c.check_id == "A4")
    assert a4.verdict == "FAIL"


def test_a4_multi_corrector_pimple_counts_blocks_not_lines(tmp_path: Path) -> None:
    """Codex DEC-038 round-1 BLOCKER 2: PIMPLE emits multiple pressure
    solves per Time= block. A4 must count BLOCKS, not LINES — 2 cap-hits
    within the same block should count as 1 toward consecutive threshold,
    not 2. Here 2 blocks × 2 cap-hits = 4 lines but only 2 blocks, so
    consecutive=2 < 3 → PASS. A 3rd capped block is needed to FAIL.
    """
    # 2 capped blocks — should NOT fire (need 3 consecutive blocks).
    content = (
        "Time = 1s\n"
        "GAMG:  Solving for p_rgh, Initial residual = 0.7, Final residual = 0.5, No Iterations 1000\n"
        "GAMG:  Solving for p_rgh, Initial residual = 0.7, Final residual = 0.5, No Iterations 1000\n"
        "Time = 2s\n"
        "GAMG:  Solving for p_rgh, Initial residual = 0.7, Final residual = 0.5, No Iterations 1000\n"
        "GAMG:  Solving for p_rgh, Initial residual = 0.7, Final residual = 0.5, No Iterations 1000\n"
    )
    log = _write_log(tmp_path, content)
    result = ca.attest(log)
    a4 = next(c for c in result.checks if c.check_id == "A4")
    assert a4.verdict == "PASS", f"2 blocks should not fire A4 (threshold=3); got {a4.verdict}"


def test_a4_fires_after_three_consecutive_blocks(tmp_path: Path) -> None:
    """3 consecutive capped blocks → FAIL, regardless of per-block count."""
    content = "".join(
        f"Time = {i}s\n"
        "GAMG:  Solving for p_rgh, Initial residual = 0.7, Final residual = 0.5, No Iterations 1000\n"
        "GAMG:  Solving for p_rgh, Initial residual = 0.7, Final residual = 0.5, No Iterations 1000\n"
        for i in range(1, 4)
    )
    log = _write_log(tmp_path, content)
    result = ca.attest(log)
    a4 = next(c for c in result.checks if c.check_id == "A4")
    assert a4.verdict == "FAIL"
    assert a4.evidence["consecutive_cap_blocks"] == 3


def test_attestor_not_applicable_when_log_missing(tmp_path: Path) -> None:
    """Codex DEC-038 round-1 comment C: missing log → ATTEST_NOT_APPLICABLE,
    distinct from ATTEST_PASS. DEC-V61-040 UI tiers will surface this
    explicitly for reference/visual_only runs that have no solver log.
    """
    result = ca.attest(None)
    assert result.overall == "ATTEST_NOT_APPLICABLE"
    result = ca.attest(tmp_path / "missing.log")
    assert result.overall == "ATTEST_NOT_APPLICABLE"


def test_a2_never_returns_fail_only_hazard(tmp_path: Path) -> None:
    """Codex DEC-038 round-1 comment A7: A2 stays HAZARD-tier to avoid
    split-brain with G5. Even sum_local=0.5 returns HAZARD from A2 (G5
    is responsible for the FAIL call at the gate layer)."""
    content = (
        "time step continuity errors : "
        "sum local = 0.5, global = 0.01, cumulative = 0.1\n"
    )
    log = _write_log(tmp_path, content)
    result = ca.attest(log)
    a2 = next(c for c in result.checks if c.check_id == "A2")
    assert a2.verdict == "HAZARD"  # was FAIL pre-fix


def test_attest_and_verdict_integration_continuity_hazard(tmp_path: Path) -> None:
    from ui.backend.schemas.validation import (
        AuditConcern,
        GoldStandardReference,
        MeasuredValue,
    )
    from ui.backend.services.validation_report import _derive_contract_status

    log = _write_log(
        tmp_path,
        (
            "Time = 1\n"
            "time step continuity errors : sum local = 5e-04, global = 1e-06, cumulative = 1e-06\n"
            "smoothSolver:  Solving for Ux, Initial residual = 1e-06, Final residual = 1e-07, No Iterations 2\n"
            "ExecutionTime = 1 s\n"
            "End\n"
        ),
    )
    attestation = ca.attest(log, case_id="lid_driven_cavity")

    assert attestation.overall == "ATTEST_HAZARD"
    a2 = next(c for c in attestation.checks if c.check_id == "A2")
    assert a2.verdict == "HAZARD"

    concerns = [
        AuditConcern(
            concern_type=concern.concern_type,
            summary=concern.summary,
            detail=concern.detail,
            decision_refs=["DEC-V61-038"],
        )
        for concern in attestation.concerns
    ]
    status, _, within_tolerance, _, _ = _derive_contract_status(
        GoldStandardReference(
            quantity="u_centerline",
            ref_value=-0.2058,
            unit="dimensionless",
            tolerance_pct=0.05,
            citation="Ghia 1982",
        ),
        MeasuredValue(
            value=-0.2050,
            source="fixture",
            quantity="u_centerline",
        ),
        [],
        concerns,
    )

    assert status == "HAZARD"
    assert within_tolerance is None


def test_load_thresholds_defaults() -> None:
    thresholds = load_thresholds()
    assert isinstance(thresholds, Thresholds)
    assert thresholds.continuity_floor == pytest.approx(1e-4)
    assert thresholds.residual_floor == pytest.approx(1e-3)
    assert thresholds.residual_floor_per_field["p_rgh"] == pytest.approx(1e-2)


def test_load_thresholds_per_case_impinging_jet() -> None:
    thresholds = load_thresholds("impinging_jet")
    assert isinstance(thresholds, Thresholds)
    assert thresholds.residual_floor_per_field["p_rgh"] == pytest.approx(5e-3)
    assert thresholds.residual_floor_per_field["Ux"] == pytest.approx(1e-3)


def test_load_thresholds_per_case_rayleigh_benard() -> None:
    thresholds = load_thresholds("rayleigh_benard_convection")
    assert thresholds.residual_floor_per_field["h"] == pytest.approx(2e-3)
    assert thresholds.no_progress_decade_frac == pytest.approx(0.3)


def test_load_thresholds_unknown_case_falls_back() -> None:
    defaults = load_thresholds()
    unknown = load_thresholds("nonexistent_xyz_12345")
    assert unknown.continuity_floor == defaults.continuity_floor
    assert unknown.residual_floor == defaults.residual_floor
    assert unknown.residual_floor_per_field == defaults.residual_floor_per_field
    assert unknown.no_progress_decade_frac == defaults.no_progress_decade_frac


def test_load_thresholds_missing_yaml_uses_hardcoded(tmp_path: Path) -> None:
    bad_path = tmp_path / "nonexistent.yaml"
    thresholds = load_thresholds(yaml_path=bad_path)
    assert isinstance(thresholds, Thresholds)
    assert thresholds.continuity_floor == ca.A2_CONTINUITY_FLOOR
    assert thresholds.residual_floor == ca.A3_RESIDUAL_FLOOR


def test_a4_passes_on_sparse_cap_hits(tmp_path: Path) -> None:
    """Single-iteration cap is not pathological — solver typically hits
    high counts in transient but recovers."""
    content = (
        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, "
        "No Iterations 1000\n"
        "GAMG:  Solving for p, Initial residual = 0.5, Final residual = 0.01, "
        "No Iterations 50\n"
    )
    log = _write_log(tmp_path, content)
    result = ca.attest(log)
    a4 = next(c for c in result.checks if c.check_id == "A4")
    assert a4.verdict == "PASS"


def test_a1_exit_code_false_forces_fail(tmp_path: Path) -> None:
    log = _write_log(tmp_path, "Time = 1\nExecutionTime = 1 s\nEnd\n")
    result = ca._check_a1_solver_crash(
        log,
        execution_result=SimpleNamespace(success=False, exit_code=139),
    )
    assert result.verdict == "FAIL"
    assert result.evidence["exit_code"] == 139


def test_a1_log_fatal_fires_even_with_success_exit(tmp_path: Path) -> None:
    log = _write_log(tmp_path, "Time = 1\nmiddle\nFloating exception\nEnd\n")
    result = ca._check_a1_solver_crash(
        log,
        execution_result=SimpleNamespace(success=True, exit_code=0),
    )
    assert result.verdict == "FAIL"


def test_a1_sigFpe_banner_not_false_positive(tmp_path: Path) -> None:
    log = _write_log(
        tmp_path,
        "sigFpe : Enabling floating point exception trapping (FOAM_SIGFPE).\n"
        "Time = 1\nEnd\n",
    )
    result = ca._check_a1_solver_crash(
        log,
        execution_result=SimpleNamespace(success=True, exit_code=0),
    )
    assert result.verdict == "PASS"


def test_a3_per_field_threshold_impinging_jet_p_rgh(tmp_path: Path) -> None:
    """Override guard: 6e-3 trips impinging_jet p_rgh (5e-3) but not YAML default (1e-2)."""
    log = _write_log(
        tmp_path,
        "DILUPBiCGStab:  Solving for p_rgh, Initial residual = 6e-3, "
        "Final residual = 1e-5, No Iterations 2\n",
    )
    impinging = ca._check_a3_residual_floor(log, thresholds=load_thresholds("impinging_jet"))
    default = ca._check_a3_residual_floor(log, thresholds=load_thresholds())
    assert impinging.verdict == "HAZARD"
    assert impinging.evidence["thresholds_by_field"]["p_rgh"] == pytest.approx(5e-3)
    assert default.verdict == "PASS"


def test_audit_fixture_doc_recomputes_expected_verdict_to_hazard(tmp_path: Path) -> None:
    from scripts.phase5_audit_run import _audit_fixture_doc

    report = _make_audit_fixture_report(
        tmp_path,
        (
            "Time = 1\n"
            "time step continuity errors : "
            "sum local = 5e-04, global = 1e-06, cumulative = 1e-06\n"
            "ExecutionTime = 1 s\n"
            "End\n"
        ),
    )

    doc = _audit_fixture_doc("lid_driven_cavity", report, commit_sha="deadbee")

    assert doc["run_metadata"]["expected_verdict"] == "HAZARD"
    assert doc["run_metadata"]["actual_verdict"] == "HAZARD"


def test_audit_fixture_doc_recomputes_to_fail_on_hard_concern(tmp_path: Path) -> None:
    from scripts.phase5_audit_run import _audit_fixture_doc

    report = _make_audit_fixture_report(
        tmp_path,
        "Time = 1\nFOAM FATAL ERROR: missing dict\nExiting\n",
    )

    doc = _audit_fixture_doc("lid_driven_cavity", report, commit_sha="deadbee")

    assert doc["run_metadata"]["expected_verdict"] == "FAIL"
    assert doc["run_metadata"]["actual_verdict"] == "FAIL"


def test_audit_fixture_doc_clean_run_stays_pass_regression(tmp_path: Path) -> None:
    from scripts.phase5_audit_run import _audit_fixture_doc

    report = _make_audit_fixture_report(
        tmp_path,
        "Time = 1\nExecutionTime = 1 s\nEnd\n",
    )

    doc = _audit_fixture_doc("lid_driven_cavity", report, commit_sha="deadbee")

    assert doc["run_metadata"]["expected_verdict"] == "PASS"
    assert doc["run_metadata"]["actual_verdict"] == "PASS"


# ---------------------------------------------------------------------------
# A5 bounding_recurrence
# ---------------------------------------------------------------------------

def test_a5_hazard_on_recurrent_bounding(tmp_path: Path) -> None:
    """≥30% of last 50 iterations with `bounding k` → HAZARD."""
    blocks = []
    for i in range(60):
        blocks.append(f"Time = {i}")
        if i >= 20:  # last 40 iterations all bound k
            blocks.append("bounding k, min: -1e-3 max: 1.0 average: 0.5")
    log = _write_log(tmp_path, "\n".join(blocks) + "\n")
    result = ca.attest(log)
    a5 = next(c for c in result.checks if c.check_id == "A5")
    assert a5.verdict == "HAZARD"
    assert a5.evidence["per_field_fraction"]["k"] >= 0.30


def test_a5_passes_on_early_bounding_only(tmp_path: Path) -> None:
    """Bounding in early transient but not in final window → PASS."""
    blocks = []
    for i in range(60):
        blocks.append(f"Time = {i}")
        if i < 5:  # only first 5 iterations bound
            blocks.append("bounding k, min: -1e-3 max: 1.0 average: 0.5")
    log = _write_log(tmp_path, "\n".join(blocks) + "\n")
    result = ca.attest(log)
    a5 = next(c for c in result.checks if c.check_id == "A5")
    assert a5.verdict == "PASS"


# ---------------------------------------------------------------------------
# A6 no_residual_progress
# ---------------------------------------------------------------------------

def test_a6_hazard_on_high_plateau(tmp_path: Path) -> None:
    """Ux stuck at 0.4 ± 0.02 for 60 iterations → HAZARD (high and flat)."""
    lines = []
    for _ in range(60):
        lines.append(
            "smoothSolver:  Solving for Ux, Initial residual = 0.4, "
            "Final residual = 0.3, No Iterations 20"
        )
    log = _write_log(tmp_path, "\n".join(lines) + "\n")
    result = ca.attest(log)
    a6 = next(c for c in result.checks if c.check_id == "A6")
    assert a6.verdict == "HAZARD"


def test_a6_ignores_converged_plateau(tmp_path: Path) -> None:
    """Ux stuck at 1e-5 (below A3 floor) is converged, not stuck → PASS.

    Codex nit: A6 should not false-positive on fully converged cases
    where residuals hit machine-noise and oscillate in the floor."""
    lines = []
    for _ in range(60):
        lines.append(
            "smoothSolver:  Solving for Ux, Initial residual = 1e-05, "
            "Final residual = 1e-06, No Iterations 2"
        )
    log = _write_log(tmp_path, "\n".join(lines) + "\n")
    result = ca.attest(log)
    a6 = next(c for c in result.checks if c.check_id == "A6")
    assert a6.verdict == "PASS"


def test_a6_decade_range_exactly_1_fires_fail(tmp_path: Path) -> None:
    """Boundary guard: exactly 1.0 decade must fire A6, which stays HAZARD-tier."""
    lines = []
    for i in range(50):
        initial = "1.0" if i % 2 == 0 else "10.0"
        lines.append(
            f"smoothSolver:  Solving for Ux, Initial residual = {initial}, "
            "Final residual = 0.5, No Iterations 2"
        )
    log = _write_log(tmp_path, "\n".join(lines) + "\n")
    result = ca._check_a6_no_progress(log, thresholds=load_thresholds())
    assert result.verdict == "HAZARD"
    assert result.evidence["offenders"]["Ux"]["decades"] == pytest.approx(1.0)


def test_a4_gap_blocks_reset_consecutive(tmp_path: Path) -> None:
    log = _write_log(
        tmp_path,
        "Time = 1\n"
        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n"
        "Time = 2\n"
        "smoothSolver:  Solving for Ux, Initial residual = 0.1, Final residual = 0.01, No Iterations 2\n"
        "Time = 3\n"
        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n"
        "Time = 4\n"
        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n",
    )
    result = ca._check_a4_iteration_cap(log, thresholds=load_thresholds())
    assert result.verdict == "PASS"


def test_a4_three_consecutive_caps_fail(tmp_path: Path) -> None:
    log = _write_log(
        tmp_path,
        "Time = 1\n"
        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n"
        "Time = 2\n"
        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n"
        "Time = 3\n"
        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n",
    )
    result = ca._check_a4_iteration_cap(log, thresholds=load_thresholds())
    assert result.verdict == "FAIL"
    assert result.evidence["consecutive_cap_blocks"] == 3


def test_attest_with_execution_result_failure(tmp_path: Path) -> None:
    log = _write_log(tmp_path, "Time = 1\nExecutionTime = 1 s\nEnd\n")
    result = ca.attest(log, execution_result=SimpleNamespace(success=False))
    a1 = next(c for c in result.checks if c.check_id == "A1")
    assert result.overall == "ATTEST_FAIL"
    assert a1.verdict == "FAIL"


# ---------------------------------------------------------------------------
# Real-log integration tests (guarded by file presence)
# ---------------------------------------------------------------------------

_FIELDS = Path("/Users/Zhuanz/Desktop/cfd-harness-unified/reports/phase5_fields")


def _resolve_latest_log(case: str) -> Path | None:
    case_dir = _FIELDS / case
    if not case_dir.is_dir():
        return None
    ts_candidates = [d for d in case_dir.iterdir() if d.is_dir() and d.name != "runs"]
    if not ts_candidates:
        return None
    ts_dir = sorted(ts_candidates)[-1]
    logs = list(ts_dir.glob("log.*"))
    return logs[0] if logs else None


def test_attestor_ldc_real_log_is_pass() -> None:
    """LDC is the gold-overlay PASS reference. Attestor MUST stay clean."""
    log = _resolve_latest_log("lid_driven_cavity")
    if log is None:
        pytest.skip("LDC phase7a log absent")
    result = ca.attest(log)
    assert result.overall == "ATTEST_PASS", (
        f"LDC attestor tripped unexpectedly: {[(c.check_id, c.verdict, c.summary) for c in result.checks if c.verdict != 'PASS']}"
    )


def test_attestor_bfs_real_log_is_hazard_plus_gate_fail() -> None:
    """BFS solver exploded (Codex audit: k≈1e30, ε≈1e30, sum_local≈1e18).

    Post DEC-038 round-1 A2/G5 split-brain fix: attestor alone returns
    ATTEST_HAZARD (A2 HAZARD + A3 HAZARD + A5 HAZARD — no FAIL-tier check
    fires because A4 is clean, A1 is clean). The FAIL contract status
    comes from the G5 gate at the gate layer catching sum_local > 1e-2.

    This test asserts the attestor HAZARD verdict; contract-FAIL coverage
    lives in test_comparator_gates_g3_g4_g5.py::test_gates_fire_on_real_bfs_audit_log.
    """
    log = _resolve_latest_log("backward_facing_step")
    if log is None:
        pytest.skip("BFS phase7a log absent")
    result = ca.attest(log)
    assert result.overall == "ATTEST_HAZARD", f"got {result.overall}"
    # Multiple HAZARD-tier concerns should be present.
    hazard_checks = [c for c in result.checks if c.verdict == "HAZARD"]
    assert len(hazard_checks) >= 2
    # A2 in particular must fire (sum_local=5.25e+18).
    a2 = next(c for c in result.checks if c.check_id == "A2")
    assert a2.verdict == "HAZARD"
