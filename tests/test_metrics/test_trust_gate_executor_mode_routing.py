"""DEC-V61-074 P2-T1.b · TrustGate per-ExecutorMode routing.

Tests :func:`src.metrics.trust_gate.apply_executor_mode_routing`
against the EXECUTOR_ABSTRACTION.md §6.1 routing table:

| Mode               | Verdict surface                                |
|--------------------|------------------------------------------------|
| ``docker_openfoam``| full triad PASS / WARN / FAIL (unchanged)      |
| ``mock``           | ceiling = WARN with note                       |
|                    | ``mock_executor_no_truth_source``              |
| ``hybrid_init``    | full triad on canonical_artifacts;             |
|                    | first-ever run (no reference) → WARN with note |
|                    | ``hybrid_init_invariant_unverified`` per §6.3  |
| ``future_remote``  | refuses to score → ``ModeNotYetImplementedError``|

Plane invariant: ``src.metrics`` (Plane.EVALUATION) must not import
``src.executor`` (Plane.EXECUTION). The routing module compares the
manifest's ``executor.mode`` field as an opaque string against the
StrEnum values mirrored as constants — these tests deliberately
exercise the routing through string literals to pin that contract.
"""

from __future__ import annotations

import pytest

from src.metrics import (
    MetricClass,
    MetricReport,
    MetricStatus,
    ModeNotYetImplementedError,
    apply_executor_mode_routing,
    reduce_reports,
)


def _r(name: str, status: MetricStatus, notes: str | None = None) -> MetricReport:
    return MetricReport(
        name=name,
        metric_class=MetricClass.POINTWISE,
        status=status,
        notes=notes,
    )


def _all_pass_base():
    return reduce_reports(
        [_r("alpha", MetricStatus.PASS), _r("beta", MetricStatus.PASS)]
    )


def _has_fail_base():
    return reduce_reports(
        [_r("alpha", MetricStatus.PASS), _r("beta", MetricStatus.FAIL, "boom")]
    )


# ---------------------------------------------------------------------------
# §6.1 routing
# ---------------------------------------------------------------------------


class TestDockerOpenFoamPassThrough:
    """`docker_openfoam` is the canonical truth source — routing must
    NOT cap or alter the worst-wins verdict."""

    def test_pass_stays_pass(self):
        base = _all_pass_base()
        routed = apply_executor_mode_routing(
            base, {"mode": "docker_openfoam", "version": "0.2", "contract_hash": "x"}
        )
        assert routed.overall is MetricStatus.PASS
        assert routed.notes == base.notes

    def test_fail_stays_fail(self):
        base = _has_fail_base()
        routed = apply_executor_mode_routing(
            base, {"mode": "docker_openfoam", "version": "0.2", "contract_hash": "x"}
        )
        assert routed.overall is MetricStatus.FAIL


class TestMockCeiling:
    """`mock` mode caps the verdict at WARN regardless of the underlying
    metric statuses (the ceiling is a §6.1 invariant — synthetic
    artifacts can never reach PASS)."""

    def test_all_pass_metrics_capped_to_warn_with_note(self):
        base = _all_pass_base()
        routed = apply_executor_mode_routing(base, {"mode": "mock"})
        assert routed.overall is MetricStatus.WARN
        assert "mock_executor_no_truth_source" in routed.notes
        # underlying per-metric reports preserved for audit trail
        assert routed.reports == base.reports

    def test_fail_stays_fail_under_mock_ceiling(self):
        """Capping is monotone: a FAIL must NOT be lowered to WARN by
        the ceiling — that would mask real defects."""
        base = _has_fail_base()
        routed = apply_executor_mode_routing(base, {"mode": "mock"})
        assert routed.overall is MetricStatus.FAIL
        assert "mock_executor_no_truth_source" in routed.notes


class TestHybridInitGate:
    """§6.3: a hybrid_init run with no reference docker_openfoam run
    yet anchored MUST emit WARN + ``hybrid_init_invariant_unverified``.
    Once the reference exists, full triad is allowed."""

    def test_no_reference_run_warns(self):
        base = _all_pass_base()
        routed = apply_executor_mode_routing(
            base, {"mode": "hybrid_init"}, hybrid_init_reference_run_present=False
        )
        assert routed.overall is MetricStatus.WARN
        assert "hybrid_init_invariant_unverified" in routed.notes

    def test_reference_run_present_passes_unchanged(self):
        base = _all_pass_base()
        routed = apply_executor_mode_routing(
            base, {"mode": "hybrid_init"}, hybrid_init_reference_run_present=True
        )
        assert routed.overall is MetricStatus.PASS
        assert "hybrid_init_invariant_unverified" not in routed.notes


class TestFutureRemoteRefused:
    """§6.1 stub-only: TrustGate refuses to score; raises an explicit
    error so the CLI/UI can surface mode_not_yet_implemented without
    parsing message bodies."""

    def test_raises_mode_not_yet_implemented(self):
        base = _all_pass_base()
        with pytest.raises(ModeNotYetImplementedError) as exc_info:
            apply_executor_mode_routing(base, {"mode": "future_remote"})
        assert exc_info.value.mode == "future_remote"


# ---------------------------------------------------------------------------
# Forward-compat / legacy fallback
# ---------------------------------------------------------------------------


class TestLegacyAndUnknownModes:
    def test_legacy_manifest_treated_as_docker_openfoam(self):
        """A manifest from before P2 has no ``executor`` field; per
        EXECUTOR_ABSTRACTION §3 readers MUST treat absent as
        ``docker_openfoam`` — i.e., full triad, no ceiling."""
        base = _has_fail_base()
        routed = apply_executor_mode_routing(base, executor_section=None)
        assert routed.overall is MetricStatus.FAIL  # untouched
        assert routed.notes == base.notes

    def test_executor_section_missing_mode_key(self):
        """Malformed section (no ``mode`` key) must not blow up routing —
        falls through to the truth-source mode, conservative."""
        base = _all_pass_base()
        routed = apply_executor_mode_routing(
            base, {"version": "0.2", "contract_hash": "deadbeef"}
        )
        assert routed.overall is MetricStatus.PASS

    def test_unknown_mode_falls_through_unchanged(self):
        """An older deployment reading a manifest from a newer producer
        may see a mode it doesn't recognize. Routing returns the
        worst-wins verdict unchanged — no false WARN, no exception."""
        base = _all_pass_base()
        routed = apply_executor_mode_routing(base, {"mode": "spacetime_warp"})
        assert routed.overall is MetricStatus.PASS
