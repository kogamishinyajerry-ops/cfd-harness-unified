"""P1-T5 · task_runner TrustGateReport integration tests.

Verifies that `_build_trust_gate_report` correctly aggregates the
existing ComparisonResult + AttestationResult outputs into a
TrustGateReport populated on the RunReport, without changing the
comparator/attestor paths themselves.

Scenarios covered:
  - clean pass (ATTEST_PASS + comparison.passed=True) → overall PASS
  - gold miss (ATTEST_PASS + comparison.passed=False) → overall FAIL
  - attestor HAZARD + gold pass → overall WARN
  - attestor FAIL (short-circuits comparator) → overall FAIL, only
    attestation report present
  - no attestation + no comparison (edge case) → trust_gate_report=None
  - attestor NOT_APPLICABLE (no log) → overall WARN
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from src.metrics import MetricClass, MetricStatus
from src.models import ComparisonResult, DeviationDetail, ExecutionResult
from src.task_runner import _build_trust_gate_report


class _FakeAttestorCheck:
    """Duck-typed check (matches src.convergence_attestor.AttestorCheck fields
    used by _build_trust_gate_report — no need to import the real class for
    tests since the helper only reads .verdict / .check_id / .concern_type /
    .summary)."""

    def __init__(
        self, check_id: str, concern_type: str, verdict: str, summary: str = ""
    ) -> None:
        self.check_id = check_id
        self.concern_type = concern_type
        self.verdict = verdict
        self.summary = summary


class _FakeAttestation:
    def __init__(self, overall: str, checks: list) -> None:
        self.overall = overall
        self.checks = checks


# ---------------------------------------------------------------------------
# Clean pass path
# ---------------------------------------------------------------------------


def test_clean_attest_pass_plus_comparison_pass_yields_overall_pass() -> None:
    attestation = _FakeAttestation(
        overall="ATTEST_PASS",
        checks=[
            _FakeAttestorCheck("A1", "SOLVER_CRASH_LOG", "PASS"),
            _FakeAttestorCheck("A2", "CONTINUITY", "PASS"),
        ],
    )
    comparison = ComparisonResult(
        passed=True,
        deviations=[],
        summary="Quantity: cd_mean | Tolerance: 5.0% | PASS",
        gold_standard_id="backward_facing_step",
    )
    tg = _build_trust_gate_report(
        task_name="bfs", comparison=comparison, attestation=attestation
    )
    assert tg is not None
    assert tg.overall is MetricStatus.PASS
    assert tg.count_by_status[MetricStatus.PASS] == 2
    assert tg.count_by_status[MetricStatus.FAIL] == 0
    # Two synthetic reports: attestation + comparison
    assert len(tg.reports) == 2
    names = {r.name for r in tg.reports}
    assert "bfs_convergence_attestation" in names
    assert "bfs_gold_comparison" in names


# ---------------------------------------------------------------------------
# Gold miss → overall FAIL
# ---------------------------------------------------------------------------


def test_gold_miss_with_clean_attestation_yields_overall_fail() -> None:
    attestation = _FakeAttestation(overall="ATTEST_PASS", checks=[])
    comparison = ComparisonResult(
        passed=False,
        deviations=[
            DeviationDetail(
                quantity="cd_mean",
                expected=1.0,
                actual=1.5,
                relative_error=0.5,
                tolerance=0.1,
            )
        ],
        summary="Quantity: cd_mean | deviation 0.5 > 0.1",
        gold_standard_id="bfs",
    )
    tg = _build_trust_gate_report(
        task_name="bfs", comparison=comparison, attestation=attestation
    )
    assert tg is not None
    assert tg.overall is MetricStatus.FAIL
    # attestation report → PASS, comparison → FAIL
    assert tg.count_by_status[MetricStatus.PASS] == 1
    assert tg.count_by_status[MetricStatus.FAIL] == 1
    # Deviation surfaced on the comparison MetricReport
    gold_report = next(r for r in tg.reports if r.name.endswith("_gold_comparison"))
    assert gold_report.deviation == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# Attestor HAZARD → overall WARN (when gold passes)
# ---------------------------------------------------------------------------


def test_attestor_hazard_plus_gold_pass_yields_overall_warn() -> None:
    attestation = _FakeAttestation(
        overall="ATTEST_HAZARD",
        checks=[
            _FakeAttestorCheck(
                "A2",
                "CONTINUITY_NOT_CONVERGED",
                "HAZARD",
                "sum_local=5e-4 exceeds floor",
            ),
        ],
    )
    comparison = ComparisonResult(
        passed=True, deviations=[], summary="PASS", gold_standard_id="x"
    )
    tg = _build_trust_gate_report(
        task_name="x", comparison=comparison, attestation=attestation
    )
    assert tg is not None
    assert tg.overall is MetricStatus.WARN
    # hazard notes surfaced
    assert any("A2" in n or "CONTINUITY" in n for n in tg.notes)


# ---------------------------------------------------------------------------
# Attestor FAIL short-circuits comparator (comparison=None)
# ---------------------------------------------------------------------------


def test_attestor_fail_with_no_comparison_yields_overall_fail() -> None:
    attestation = _FakeAttestation(
        overall="ATTEST_FAIL",
        checks=[
            _FakeAttestorCheck(
                "A1", "SOLVER_CRASH_LOG", "FAIL", "FOAM FATAL ERROR"
            ),
        ],
    )
    # task_runner skips comparator when ATTEST_FAIL, so comparison is None
    tg = _build_trust_gate_report(
        task_name="x", comparison=None, attestation=attestation
    )
    assert tg is not None
    assert tg.overall is MetricStatus.FAIL
    assert len(tg.reports) == 1
    assert tg.reports[0].name == "x_convergence_attestation"
    assert tg.reports[0].metric_class is MetricClass.RESIDUAL
    assert tg.reports[0].provenance["attest_verdict"] == "ATTEST_FAIL"


# ---------------------------------------------------------------------------
# Neither attestation nor comparison → None
# ---------------------------------------------------------------------------


def test_no_inputs_returns_none() -> None:
    tg = _build_trust_gate_report(
        task_name="x", comparison=None, attestation=None
    )
    assert tg is None


# ---------------------------------------------------------------------------
# Attestor NOT_APPLICABLE → overall WARN (no solver log resolvable)
# ---------------------------------------------------------------------------


def test_attestor_not_applicable_yields_overall_warn() -> None:
    attestation = _FakeAttestation(overall="ATTEST_NOT_APPLICABLE", checks=[])
    comparison = ComparisonResult(
        passed=True, deviations=[], summary="PASS", gold_standard_id="x"
    )
    tg = _build_trust_gate_report(
        task_name="x", comparison=comparison, attestation=attestation
    )
    assert tg is not None
    # attestation → WARN, comparison → PASS. worst-wins → WARN.
    assert tg.overall is MetricStatus.WARN


# ---------------------------------------------------------------------------
# E2E via actual TaskRunner.run_task — verifies RunReport.trust_gate_report
# is populated by the integrated call site (not just the helper directly).
# ---------------------------------------------------------------------------


def test_run_report_populates_trust_gate_on_happy_path(tmp_path: Path) -> None:
    """Full pipeline: MockExecutor + attestor + comparator → RunReport.
    trust_gate_report should be present and PASS/WARN/FAIL consistent with
    the attestation+comparison inputs."""
    from unittest.mock import MagicMock

    from src.models import (
        Compressibility,
        FlowType,
        GeometryType,
        SteadyState,
        TaskSpec,
    )
    from src.task_runner import TaskRunner

    # Write a clean solver log so attestor returns ATTEST_PASS.
    log_dir = tmp_path / "solver_output"
    log_dir.mkdir()
    (log_dir / "log.simpleFoam").write_text(
        "Time = 1\nExecutionTime = 1 s\nEnd\n", encoding="utf-8"
    )

    class _CleanExecutor:
        def execute(self, task_spec):
            return ExecutionResult(
                success=True,
                is_mock=False,
                key_quantities={"u_centerline": [0.025]},
                raw_output_path=str(log_dir),
                exit_code=0,
            )

    stub_notion = MagicMock()
    stub_notion.write_execution_result = MagicMock()
    stub_db = MagicMock()
    stub_db.load_gold_standard = MagicMock(return_value=None)  # no gold → no comparison
    stub_db.save_correction = MagicMock()

    runner = TaskRunner(
        executor=_CleanExecutor(),
        notion_client=stub_notion,
        knowledge_db=stub_db,
    )
    task = TaskSpec(
        name="lid_driven_cavity",
        geometry_type=GeometryType.SIMPLE_GRID,
        flow_type=FlowType.INTERNAL,
        steady_state=SteadyState.STEADY,
        compressibility=Compressibility.INCOMPRESSIBLE,
    )

    report = runner.run_task(task)

    # With no gold → no comparison. Only attestation contributes.
    # ATTEST_PASS → overall PASS.
    assert report.trust_gate_report is not None
    assert report.trust_gate_report.overall is MetricStatus.PASS
    assert len(report.trust_gate_report.reports) == 1
    assert (
        report.trust_gate_report.reports[0].name
        == "lid_driven_cavity_convergence_attestation"
    )


# ---------------------------------------------------------------------------
# Codex V61-056 finding #1: ATTEST_NOT_APPLICABLE with no concerns must still
# surface the WARN reason — previously silently dropped.
# ---------------------------------------------------------------------------


def test_attestor_not_applicable_surfaces_explicit_note() -> None:
    attestation = _FakeAttestation(overall="ATTEST_NOT_APPLICABLE", checks=[])
    tg = _build_trust_gate_report(
        task_name="x", comparison=None, attestation=attestation
    )
    assert tg is not None
    assert tg.overall is MetricStatus.WARN
    assert len(tg.reports) == 1
    residual = tg.reports[0]
    assert residual.notes is not None
    assert "not applicable" in residual.notes.lower()
    # And the formatted note flows through to TrustGateReport.notes tuple
    assert any("not applicable" in n.lower() for n in tg.notes)


# ---------------------------------------------------------------------------
# Codex V61-056 finding #2: Deviation-extraction edge case when comparison
# has deviations but all relative_error values are None.
# ---------------------------------------------------------------------------


def test_comparison_with_none_relative_errors_yields_no_deviation() -> None:
    attestation = _FakeAttestation(overall="ATTEST_PASS", checks=[])
    # Comparison with deviations but none carrying relative_error (legacy
    # comparator code paths existed that produced abstract-deviation records
    # without numeric error). Wrapper must not crash and must leave
    # MetricReport.deviation = None.
    comparison = ComparisonResult(
        passed=False,
        deviations=[
            DeviationDetail(
                quantity="x",
                expected=1.0,
                actual=None,
                relative_error=None,
                tolerance=0.05,
            ),
        ],
        summary="Quantity x not found in execution result",
        gold_standard_id="x",
    )
    tg = _build_trust_gate_report(
        task_name="x", comparison=comparison, attestation=attestation
    )
    assert tg is not None
    assert tg.overall is MetricStatus.FAIL  # comparison.passed=False
    gold_report = next(r for r in tg.reports if r.name.endswith("_gold_comparison"))
    assert gold_report.deviation is None  # no relative_error available
    assert gold_report.status is MetricStatus.FAIL


# ---------------------------------------------------------------------------
# DEC-V61-071 · P1 tail · load_tolerance_policy dispatch wiring
# ---------------------------------------------------------------------------


def _write_case_profile(tmp_path: Path, case_id: str, observables: list[str]) -> None:
    body_lines = [
        f"case_id: {case_id}",
        "schema_version: 1",
        'last_assessed: "2026-04-26"',
        "tolerance_policy:",
    ]
    for obs in observables:
        body_lines.append(f"  {obs}:")
        body_lines.append("    tolerance: 0.05")
    (tmp_path / f"{case_id}.yaml").write_text("\n".join(body_lines) + "\n")


def test_build_trust_gate_report_invokes_load_tolerance_policy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """DEC-V61-071: verify load_tolerance_policy is dispatched and the
    loaded observables surface on the comparison report's provenance.
    Today (pre-P1-T4) this is a wiring exercise — verdict semantics are
    unchanged. The provenance trail makes the dispatch path observable
    so the eventual ObservableDef migration has live test coverage."""
    from src.metrics import case_profile_loader

    monkeypatch.setattr(
        case_profile_loader, "_DEFAULT_CASE_PROFILES_DIR", tmp_path
    )
    monkeypatch.setattr(
        case_profile_loader,
        "_resolve_case_profiles_dir",
        lambda override: tmp_path if override is None else override,
    )

    _write_case_profile(
        tmp_path, "wired_case", ["u_centerline", "v_centerline", "p_drop"]
    )

    attestation = _FakeAttestation(overall="ATTEST_PASS", checks=[])
    comparison = ComparisonResult(
        passed=True,
        deviations=[],
        summary="ok",
        gold_standard_id="wired_case",
    )
    tg = _build_trust_gate_report(
        task_name="wired_case", comparison=comparison, attestation=attestation
    )
    assert tg is not None
    gold_report = next(r for r in tg.reports if r.name.endswith("_gold_comparison"))
    obs = gold_report.provenance.get("tolerance_policy_observables")
    assert obs == ["p_drop", "u_centerline", "v_centerline"]


def test_build_trust_gate_report_handles_missing_case_profile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Loader fail-soft: missing CaseProfile file yields empty observables
    list on provenance — wiring is exercised, no crash."""
    from src.metrics import case_profile_loader

    monkeypatch.setattr(
        case_profile_loader,
        "_resolve_case_profiles_dir",
        lambda override: tmp_path if override is None else override,
    )

    attestation = _FakeAttestation(overall="ATTEST_PASS", checks=[])
    comparison = ComparisonResult(
        passed=True, deviations=[], summary="ok", gold_standard_id="absent"
    )
    tg = _build_trust_gate_report(
        task_name="absent", comparison=comparison, attestation=attestation
    )
    assert tg is not None
    gold_report = next(r for r in tg.reports if r.name.endswith("_gold_comparison"))
    assert gold_report.provenance.get("tolerance_policy_observables") == []


# ---------------------------------------------------------------------------
# DEC-V61-071 R1 F#1 verbatim regression: display-title → slug resolution.
# TaskSpec.name often comes from whitelist `name` field or Notion page title
# ("Lid-Driven Cavity"), not the slug ("lid_driven_cavity"). Without slug
# resolution, load_tolerance_policy silently misses real CaseProfiles.
# ---------------------------------------------------------------------------


def test_build_trust_gate_report_resolves_display_title_to_slug(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Display-title task name resolves to canonical slug via whitelist
    before load_tolerance_policy is called."""
    from src.metrics import case_profile_loader
    from src import task_runner as tr

    monkeypatch.setattr(
        case_profile_loader,
        "_resolve_case_profiles_dir",
        lambda override: tmp_path if override is None else override,
    )
    _write_case_profile(
        tmp_path, "demo_case", ["alpha_obs", "beta_obs"]
    )

    fake_whitelist = {
        "cases": [
            {"id": "demo_case", "name": "Demo Display Title"},
            {"id": "other_case", "name": "Other Title"},
        ]
    }

    class _FakeDB:
        def _load_whitelist(self) -> dict:
            return fake_whitelist

    monkeypatch.setattr(tr, "_resolve_case_slug_for_policy",
                        lambda task_name: next(
                            (c["id"] for c in fake_whitelist["cases"]
                             if c["name"] == task_name or c["id"] == task_name),
                            task_name,
                        ))

    attestation = _FakeAttestation(overall="ATTEST_PASS", checks=[])
    comparison = ComparisonResult(
        passed=True, deviations=[], summary="ok", gold_standard_id="demo_case"
    )

    # Display-title task_name → slug resolution → policy populated.
    tg = _build_trust_gate_report(
        task_name="Demo Display Title", comparison=comparison, attestation=attestation
    )
    assert tg is not None
    gold_report = next(r for r in tg.reports if r.name.endswith("_gold_comparison"))
    assert gold_report.provenance.get("tolerance_policy_observables") == [
        "alpha_obs",
        "beta_obs",
    ]


def test_resolve_case_slug_for_policy_via_real_whitelist() -> None:
    """DEC-V61-071 R2 non-blocking comment: exercise the real whitelist
    walker (not a monkeypatched stub) to prove production-path slug
    resolution works against `knowledge/whitelist.yaml`. Display title
    "Lid-Driven Cavity" must resolve to slug "lid_driven_cavity"; an
    unknown name must pass through unchanged."""
    from src.task_runner import _resolve_case_slug_for_policy

    assert _resolve_case_slug_for_policy("Lid-Driven Cavity") == "lid_driven_cavity"
    assert _resolve_case_slug_for_policy("lid_driven_cavity") == "lid_driven_cavity"
    # Unknown name passes through (fail-soft per docstring contract)
    assert _resolve_case_slug_for_policy("totally_unknown_xyz") == "totally_unknown_xyz"


# ---------------------------------------------------------------------------
# DEC-V61-071 R1 F#2 verbatim regression: lazy-load on attestation-only and
# no-input paths. The loader must not run when there is no comparison report
# to receive the provenance — avoids unnecessary filesystem I/O + warning
# noise on those paths.
# ---------------------------------------------------------------------------


def test_build_trust_gate_report_skips_loader_on_attestation_only_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Attestation-only path does not invoke load_tolerance_policy."""
    from src.metrics import case_profile_loader
    from src import task_runner as tr

    call_count = {"n": 0}
    real_loader = tr.load_tolerance_policy

    def _counted_loader(*args, **kwargs):
        call_count["n"] += 1
        return real_loader(*args, **kwargs)

    monkeypatch.setattr(tr, "load_tolerance_policy", _counted_loader)
    monkeypatch.setattr(
        case_profile_loader,
        "_resolve_case_profiles_dir",
        lambda override: tmp_path if override is None else override,
    )

    attestation = _FakeAttestation(overall="ATTEST_FAIL", checks=[])
    tg = _build_trust_gate_report(
        task_name="anything", comparison=None, attestation=attestation
    )
    assert tg is not None
    assert call_count["n"] == 0  # loader skipped on attestation-only


def test_build_trust_gate_report_skips_loader_on_no_input_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """comparison=None + attestation=None → return None without loading."""
    from src.metrics import case_profile_loader
    from src import task_runner as tr

    call_count = {"n": 0}
    real_loader = tr.load_tolerance_policy

    def _counted_loader(*args, **kwargs):
        call_count["n"] += 1
        return real_loader(*args, **kwargs)

    monkeypatch.setattr(tr, "load_tolerance_policy", _counted_loader)
    monkeypatch.setattr(
        case_profile_loader,
        "_resolve_case_profiles_dir",
        lambda override: tmp_path if override is None else override,
    )

    tg = _build_trust_gate_report(
        task_name="anything", comparison=None, attestation=None
    )
    assert tg is None
    assert call_count["n"] == 0


def test_build_trust_gate_report_handles_malformed_case_profile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Loader CaseProfileError is caught and logged; wiring degrades to
    empty observables rather than killing the run."""
    from src.metrics import case_profile_loader

    monkeypatch.setattr(
        case_profile_loader,
        "_resolve_case_profiles_dir",
        lambda override: tmp_path if override is None else override,
    )
    # Malformed: tolerance_policy is a list instead of a mapping → CaseProfileError
    (tmp_path / "broken.yaml").write_text(
        "case_id: broken\nschema_version: 1\ntolerance_policy:\n  - not\n  - a\n  - mapping\n"
    )

    attestation = _FakeAttestation(overall="ATTEST_PASS", checks=[])
    comparison = ComparisonResult(
        passed=True, deviations=[], summary="ok", gold_standard_id="broken"
    )
    import logging
    with caplog.at_level(logging.WARNING, logger="src.task_runner"):
        tg = _build_trust_gate_report(
            task_name="broken", comparison=comparison, attestation=attestation
        )
    assert tg is not None
    gold_report = next(r for r in tg.reports if r.name.endswith("_gold_comparison"))
    assert gold_report.provenance.get("tolerance_policy_observables") == []
    assert any("load_tolerance_policy failed" in rec.message for rec in caplog.records)

# ---------------------------------------------------------------------------
# Codex V61-056 finding #2b: E2E TaskRunner with gold present (comparison
# branch actually exercised, not just attestation-only).
# ---------------------------------------------------------------------------


def test_run_report_populates_trust_gate_with_comparison_present(
    tmp_path: Path,
) -> None:
    from unittest.mock import MagicMock

    from src.models import (
        Compressibility,
        FlowType,
        GeometryType,
        SteadyState,
        TaskSpec,
    )
    from src.task_runner import TaskRunner

    log_dir = tmp_path / "solver_output"
    log_dir.mkdir()
    (log_dir / "log.simpleFoam").write_text(
        "Time = 1\nExecutionTime = 1 s\nEnd\n", encoding="utf-8"
    )

    class _Executor:
        def execute(self, task_spec):
            return ExecutionResult(
                success=True,
                is_mock=False,
                key_quantities={"u_centerline": 0.98},
                raw_output_path=str(log_dir),
                exit_code=0,
            )

    # Gold declares quantity=u_centerline, ref=1.0, tolerance=0.05. Actual=0.98,
    # deviation=0.02 < tolerance → comparison PASSes.
    gold = {
        "quantity": "u_centerline",
        "reference_values": [{"value": 1.0}],
        "tolerance": 0.05,
        "id": "lid_driven_cavity",
    }
    stub_notion = MagicMock()
    stub_notion.write_execution_result = MagicMock()
    stub_db = MagicMock()
    stub_db.load_gold_standard = MagicMock(return_value=gold)
    stub_db.save_correction = MagicMock()

    runner = TaskRunner(
        executor=_Executor(),
        notion_client=stub_notion,
        knowledge_db=stub_db,
    )
    task = TaskSpec(
        name="lid_driven_cavity",
        geometry_type=GeometryType.SIMPLE_GRID,
        flow_type=FlowType.INTERNAL,
        steady_state=SteadyState.STEADY,
        compressibility=Compressibility.INCOMPRESSIBLE,
    )
    report = runner.run_task(task)

    # ATTEST_PASS + comparison PASS → overall PASS, 2 reports
    assert report.trust_gate_report is not None
    assert report.trust_gate_report.overall is MetricStatus.PASS
    assert len(report.trust_gate_report.reports) == 2
    names = {r.name for r in report.trust_gate_report.reports}
    assert names == {
        "lid_driven_cavity_convergence_attestation",
        "lid_driven_cavity_gold_comparison",
    }
