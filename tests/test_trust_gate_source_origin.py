"""DEC-V61-091 M5.1 · :func:`apply_source_origin_routing` unit tests.

Covers the source-origin verdict ceiling for workbench imported user
cases. The routing-imposed cap must:

  - Lower a PASS verdict to WARN with the disclaimer note appended.
  - Leave WARN unchanged but still append the note (audit trail).
  - Leave FAIL unchanged (worst-wins monotone — never raises severity).
  - Fall through unchanged on non-imported origins (None, unknown
    string, future tags).
  - Compose monotonically with the existing executor-mode ceiling.
"""

from __future__ import annotations

from types import MappingProxyType

import pytest

from src.metrics.base import MetricReport, MetricStatus
from src.metrics.trust_gate import (
    SOURCE_ORIGIN_IMPORTED_USER,
    TrustGateReport,
    apply_executor_mode_routing,
    apply_source_origin_routing,
)


_DISCLAIMER_NOTE = (
    "imported_user_no_literature_ground_truth_pass_with_disclaimer"
)
_MOCK_NOTE = "mock_executor_no_truth_source"


def _report(
    overall: MetricStatus,
    *,
    pass_count: int = 0,
    warn_count: int = 0,
    fail_count: int = 0,
    notes: tuple = (),
) -> TrustGateReport:
    counts = {
        MetricStatus.PASS: pass_count,
        MetricStatus.WARN: warn_count,
        MetricStatus.FAIL: fail_count,
    }
    return TrustGateReport(
        overall=overall,
        reports=(),
        count_by_status=MappingProxyType(counts),
        notes=notes,
    )


class TestApplySourceOriginRouting:
    def test_imported_user_pass_capped_to_warn_with_disclaimer_note(self) -> None:
        base = _report(MetricStatus.PASS, pass_count=3)
        out = apply_source_origin_routing(base, SOURCE_ORIGIN_IMPORTED_USER)
        assert out.overall is MetricStatus.WARN
        assert _DISCLAIMER_NOTE in out.notes
        # _ceiling_to_warn bumps WARN count when promoting from PASS so
        # has_warnings + summary stay truthful.
        assert out.count_by_status[MetricStatus.WARN] == 1
        assert out.count_by_status[MetricStatus.PASS] == 3

    def test_imported_user_warn_stays_warn_with_note_appended(self) -> None:
        base = _report(MetricStatus.WARN, warn_count=2, notes=("metric_x [warn]: drift",))
        out = apply_source_origin_routing(base, SOURCE_ORIGIN_IMPORTED_USER)
        assert out.overall is MetricStatus.WARN
        assert out.notes[-1] == _DISCLAIMER_NOTE
        assert "metric_x [warn]: drift" in out.notes
        # No spurious bump — base already had WARN entries.
        assert out.count_by_status[MetricStatus.WARN] == 2

    def test_imported_user_fail_stays_fail_worst_wins_monotone(self) -> None:
        base = _report(MetricStatus.FAIL, fail_count=1, warn_count=1)
        out = apply_source_origin_routing(base, SOURCE_ORIGIN_IMPORTED_USER)
        assert out.overall is MetricStatus.FAIL
        assert out.notes[-1] == _DISCLAIMER_NOTE
        assert out.count_by_status[MetricStatus.FAIL] == 1

    def test_none_origin_falls_through_unchanged(self) -> None:
        base = _report(MetricStatus.PASS, pass_count=2)
        out = apply_source_origin_routing(base, None)
        assert out is base

    def test_unknown_origin_falls_through_unchanged(self) -> None:
        base = _report(MetricStatus.PASS, pass_count=2)
        # Forward-compat: any tag this module hasn't been taught about
        # (whitelist, draft, future imported_step / imported_msh, etc.)
        # leaves the base report unchanged.
        for tag in ("whitelist", "draft", "imported_step", ""):
            assert apply_source_origin_routing(base, tag) is base

    def test_pass_non_imported_unchanged_regression_guard(self) -> None:
        base = _report(MetricStatus.PASS, pass_count=5)
        out = apply_source_origin_routing(base, "whitelist")
        assert out is base
        assert out.overall is MetricStatus.PASS
        assert _DISCLAIMER_NOTE not in out.notes


class TestSourceOriginRoutingCompositionWithExecutorMode:
    """M5.1 source-origin cap composes with M-existing executor-mode cap.

    Both ceilings funnel through `_ceiling_to_warn` which is idempotent
    and worst-wins-preserving, so the order doesn't matter — but the
    DEC pins source-origin AFTER executor-mode for stable note ordering.
    """

    def test_mock_executor_then_imported_user_both_notes_present(self) -> None:
        base = _report(MetricStatus.PASS, pass_count=3)
        after_mode = apply_executor_mode_routing(base, {"mode": "mock"})
        after_origin = apply_source_origin_routing(
            after_mode, SOURCE_ORIGIN_IMPORTED_USER
        )
        assert after_origin.overall is MetricStatus.WARN
        assert _MOCK_NOTE in after_origin.notes
        assert _DISCLAIMER_NOTE in after_origin.notes
        # mode-cap appended first per DEC composition order.
        assert after_origin.notes.index(_MOCK_NOTE) < after_origin.notes.index(
            _DISCLAIMER_NOTE
        )

    def test_severity_idempotent_with_note_accumulation(self) -> None:
        # Severity is idempotent (WARN stays WARN) and count_by_status
        # is stable after the first application, but the notes tuple
        # accumulates the disclaimer on every reapplication — that is
        # the formal contract so the audit trail records each cap
        # event. Codex R1 P3: prevent future readers from over-reading
        # "idempotent" to mean full-report idempotence.
        base = _report(MetricStatus.PASS, pass_count=1)
        once = apply_source_origin_routing(base, SOURCE_ORIGIN_IMPORTED_USER)
        twice = apply_source_origin_routing(once, SOURCE_ORIGIN_IMPORTED_USER)
        assert once.overall is MetricStatus.WARN
        assert twice.overall is MetricStatus.WARN
        # count_by_status is stable across reapplication.
        assert (
            once.count_by_status[MetricStatus.WARN]
            == twice.count_by_status[MetricStatus.WARN]
        )
        # Notes accumulate honestly.
        assert twice.notes.count(_DISCLAIMER_NOTE) == 2

    def test_docker_openfoam_then_imported_user_only_disclaimer_note(self) -> None:
        base = _report(MetricStatus.PASS, pass_count=2)
        after_mode = apply_executor_mode_routing(base, {"mode": "docker_openfoam"})
        # docker_openfoam is the canonical truth-source mode — no ceiling.
        assert after_mode is base
        after_origin = apply_source_origin_routing(
            after_mode, SOURCE_ORIGIN_IMPORTED_USER
        )
        assert after_origin.overall is MetricStatus.WARN
        assert _DISCLAIMER_NOTE in after_origin.notes
        assert _MOCK_NOTE not in after_origin.notes

    def test_executor_mode_plus_imported_user_records_both_notes_in_application_order(
        self,
    ) -> None:
        # Kogami P2 #3: pin the multi-cap audit shape as an explicit
        # contract. When BOTH the executor-mode ceiling (mock) and the
        # source-origin ceiling (imported_user) fire on the same run,
        # the resulting `notes` tuple records BOTH cap events
        # separately, in application order (executor-mode first per
        # task_runner composition order, source-origin second). This
        # is honest audit-trail behavior — downstream UI / audit-
        # package renderers are responsible for any presentation-time
        # dedup (deferred to M8 / dogfood per §Out of scope).
        base = _report(MetricStatus.PASS, pass_count=4)
        after_mode = apply_executor_mode_routing(base, {"mode": "mock"})
        after_origin = apply_source_origin_routing(
            after_mode, SOURCE_ORIGIN_IMPORTED_USER
        )
        assert after_origin.overall is MetricStatus.WARN
        # Both cap notes present, in application order, exactly once each.
        assert after_origin.notes.count(_MOCK_NOTE) == 1
        assert after_origin.notes.count(_DISCLAIMER_NOTE) == 1
        mock_idx = after_origin.notes.index(_MOCK_NOTE)
        disclaimer_idx = after_origin.notes.index(_DISCLAIMER_NOTE)
        assert mock_idx < disclaimer_idx, (
            "task_runner composition order requires executor-mode note "
            "to precede source-origin note"
        )
        # count_by_status reflects the routing-imposed WARN exactly once
        # (both ceilings funnel through _ceiling_to_warn which only bumps
        # the WARN count when promoting from PASS, and only on the first
        # promotion).
        assert after_origin.count_by_status[MetricStatus.WARN] == 1
