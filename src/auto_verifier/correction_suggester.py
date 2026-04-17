"""Suggest-only correction synthesis for AutoVerifier."""

from __future__ import annotations

from .schemas import ConvergenceReport, CorrectionSuggestion, GoldStandardComparison, PhysicsCheck


class CorrectionSuggester:
    """Map verification failures to structured, human-reviewable suggestions."""

    def suggest(
        self,
        convergence: ConvergenceReport,
        comparison: GoldStandardComparison,
        physics: PhysicsCheck,
        *,
        transient_case: bool = False,
    ) -> CorrectionSuggestion | None:
        if convergence.status == "DIVERGED":
            return CorrectionSuggestion(
                primary_cause="solver_settings",
                confidence="HIGH",
                suggested_correction="Tighten solver controls and inspect residual blow-up before replay.",
            )

        if convergence.status == "OSCILLATING":
            primary_cause = "time_stepping" if transient_case else "solver_settings"
            return CorrectionSuggestion(
                primary_cause=primary_cause,
                confidence="MEDIUM",
                suggested_correction="Stabilize iteration history before trusting numerical comparisons.",
            )

        if physics.status == "FAIL":
            return CorrectionSuggestion(
                primary_cause="boundary_condition",
                confidence="MEDIUM",
                suggested_correction="Verify inlet/outlet conservation and boundary consistency before replay.",
            )

        if comparison.overall == "FAIL":
            return CorrectionSuggestion(
                primary_cause="mesh_resolution",
                confidence="MEDIUM",
                suggested_correction="Refine the case setup around the failing observables and rerun comparison.",
            )

        if comparison.overall == "PASS_WITH_DEVIATIONS":
            return CorrectionSuggestion(
                primary_cause="unknown",
                confidence="LOW",
                suggested_correction="Review remaining deviations manually; no automatic correction is applied.",
            )

        return None

