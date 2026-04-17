from auto_verifier import CorrectionSuggester
from auto_verifier.schemas import ConvergenceReport, GoldStandardComparison, PhysicsCheck


def test_correction_spec_generated():
    suggestion = CorrectionSuggester().suggest(
        ConvergenceReport("DIVERGED", 1e-2, 1e-5, 1000.0),
        GoldStandardComparison("FAIL"),
        PhysicsCheck("FAIL"),
        transient_case=False,
    )
    assert suggestion is not None
    assert suggestion.primary_cause == "solver_settings"


def test_correction_spec_not_generated():
    suggestion = CorrectionSuggester().suggest(
        ConvergenceReport("CONVERGED", 1e-6, 1e-5, 0.1),
        GoldStandardComparison("PASS"),
        PhysicsCheck("PASS"),
        transient_case=False,
    )
    assert suggestion is None


def test_transient_oscillation_prefers_time_stepping():
    suggestion = CorrectionSuggester().suggest(
        ConvergenceReport("OSCILLATING", 1e-4, 1e-5, 10.0),
        GoldStandardComparison("PASS_WITH_DEVIATIONS"),
        PhysicsCheck("PASS"),
        transient_case=True,
    )
    assert suggestion is not None
    assert suggestion.primary_cause == "time_stepping"

