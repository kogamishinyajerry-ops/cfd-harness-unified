"""Unit tests for ``geometry_ingest.low_re_komegasst_trigger_advisor``.

DEC-V61-235 · V104 evidence row · V71.B slice.
Mirrors the test pattern from ``test_solver_block_advisor.py``:
small focused cases per predicate branch, normalization, and clean-
config baselines.
"""
from __future__ import annotations

import pytest

from ui.backend.services.geometry_ingest.low_re_komegasst_trigger_advisor import (
    LowReKOmegaSSTFinding,
    LowReKOmegaSSTReport,
    LowReKOmegaSSTSnapshot,
    check_low_re_komegasst,
)


# ---- Positive cases (predicate fires) --------------------------------


def test_komegasst_wall_treatment_resolved_fires_one_info_finding():
    """kOmegaSST + wall_treatment='resolved' → one info finding with V104 code."""
    snap = LowReKOmegaSSTSnapshot(
        turbulence_model="kOmegaSST",
        wall_treatment="resolved",
    )
    report = check_low_re_komegasst(snap)

    assert len(report.findings) == 1
    f = report.findings[0]
    assert f.severity == "info"
    assert f.code == "v104_low_re_komegasst_underprediction"
    assert f.location == "turbulenceProperties.RAS.RASModel"
    # Detail must reference V104 witnesses
    assert "V104" in f.detail
    assert "backward-facing step" in f.detail or "reattachment" in f.detail
    assert "Cl_max" in f.detail or "NACA" in f.detail


def test_komegasst_first_cell_yplus_below_one_fires():
    """kOmegaSST + first_cell_yplus=0.3 → fires (wall-resolved by y+ criterion)."""
    snap = LowReKOmegaSSTSnapshot(
        turbulence_model="kOmegaSST",
        first_cell_yplus=0.3,
    )
    report = check_low_re_komegasst(snap)

    assert len(report.findings) == 1
    assert report.findings[0].code == "v104_low_re_komegasst_underprediction"
    assert report.findings[0].severity == "info"


def test_hyphenated_variant_fires():
    """'k-omega SST' (hyphenated, spaced) normalizes to kOmegaSST → fires."""
    snap = LowReKOmegaSSTSnapshot(
        turbulence_model="k-omega SST",
        wall_treatment="resolved",
    )
    report = check_low_re_komegasst(snap)

    assert len(report.findings) == 1
    assert report.findings[0].code == "v104_low_re_komegasst_underprediction"


def test_all_lowercase_komegasst_variant_fires():
    """'komegasst' all-lowercase → fires (normalization)."""
    snap = LowReKOmegaSSTSnapshot(
        turbulence_model="komegasst",
        wall_treatment="resolved",
    )
    report = check_low_re_komegasst(snap)

    assert len(report.findings) == 1


def test_e21_case_036_documented_config_fires_one_info_finding():
    """The E21 canonical case (case_036) BEHAVIORALLY triggers this advisor.

    Closes the V69.2 KNOWN_F_NEW skip with a real FIRING, not merely advisor-
    surface name-registration: the canonical-eval harness only checks the
    advisor name appears in the surface, so this test pins the documented E21
    config (simpleFoam + kOmegaSST, low-Re wall-resolved y+~0.5-1, no wall fn —
    `.planning/evals/canonical/E21_case_036_kOmegaSST_lowRe.md`) to exactly one
    INFO finding with the V104 code. If a future edit silently breaks the
    predicate, the E21 row's `✓ info` claim goes red here (not just in the
    generic positive-case test).
    """
    snap = LowReKOmegaSSTSnapshot(
        turbulence_model="kOmegaSST",
        wall_treatment="resolved",
        first_cell_yplus=0.8,  # E21 documents y+~0.5-1 (resolved, no wall fn)
    )
    report = check_low_re_komegasst(snap)
    assert len(report.findings) == 1
    f = report.findings[0]
    assert f.severity == "info"
    assert f.code == "v104_low_re_komegasst_underprediction"


def test_first_cell_yplus_exactly_at_threshold_does_not_fire():
    """first_cell_yplus=1.0 is NOT < 1.0; predicate must not fire."""
    snap = LowReKOmegaSSTSnapshot(
        turbulence_model="kOmegaSST",
        first_cell_yplus=1.0,
    )
    report = check_low_re_komegasst(snap)
    assert report.findings == ()


# ---- Negative cases (predicate does NOT fire) ------------------------


def test_komegasst_wall_function_does_not_fire():
    """kOmegaSST + wall_treatment='wall_function' → empty (not wall-resolved)."""
    snap = LowReKOmegaSSTSnapshot(
        turbulence_model="kOmegaSST",
        wall_treatment="wall_function",
    )
    report = check_low_re_komegasst(snap)
    assert report.findings == ()


def test_komegasst_high_yplus_does_not_fire():
    """kOmegaSST + first_cell_yplus=5.0 → empty (y+ > 1.0, wall-function regime)."""
    snap = LowReKOmegaSSTSnapshot(
        turbulence_model="kOmegaSST",
        first_cell_yplus=5.0,
    )
    report = check_low_re_komegasst(snap)
    assert report.findings == ()


def test_measured_yplus_overrides_resolved_wall_treatment():
    """wall_treatment='resolved' but measured y+=5 → NO fire (y+ is authoritative).

    Codex R1 P2: the documented LowReKOmegaSSTSnapshot contract says measured
    first_cell_yplus takes priority over the coarse wall_treatment enum. A config
    that CLAIMS 'resolved' while the mesh measures y+=5 is NOT resolved, so the V104
    advisory must NOT fire — the numeric y+ disambiguates the regime.
    """
    snap = LowReKOmegaSSTSnapshot(
        turbulence_model="kOmegaSST",
        wall_treatment="resolved",
        first_cell_yplus=5.0,
    )
    report = check_low_re_komegasst(snap)
    assert report.findings == ()


def test_measured_yplus_fires_even_if_wall_treatment_says_wall_function():
    """wall_treatment='wall_function' but measured y+=0.3 → FIRES (y+ authoritative).

    The mirror of the override: a genuinely resolved mesh (y+<1) is in the V104
    regime regardless of a stale/mislabeled wall_treatment enum.
    """
    snap = LowReKOmegaSSTSnapshot(
        turbulence_model="kOmegaSST",
        wall_treatment="wall_function",
        first_cell_yplus=0.3,
    )
    report = check_low_re_komegasst(snap)
    assert len(report.findings) == 1
    assert report.findings[0].code == "v104_low_re_komegasst_underprediction"


def test_kepsilon_resolved_does_not_fire():
    """kEpsilon + wall_treatment='resolved' → empty (not a kOmegaSST variant)."""
    snap = LowReKOmegaSSTSnapshot(
        turbulence_model="kEpsilon",
        wall_treatment="resolved",
    )
    report = check_low_re_komegasst(snap)
    assert report.findings == ()


def test_spalart_allmaras_resolved_does_not_fire():
    """SpalartAllmaras + resolved → empty (different model class)."""
    snap = LowReKOmegaSSTSnapshot(
        turbulence_model="SpalartAllmaras",
        wall_treatment="resolved",
        first_cell_yplus=0.5,
    )
    report = check_low_re_komegasst(snap)
    assert report.findings == ()


def test_komegasst_no_wall_info_does_not_fire():
    """kOmegaSST with wall_treatment=None and no yplus → empty (cannot confirm wall-resolved)."""
    snap = LowReKOmegaSSTSnapshot(
        turbulence_model="kOmegaSST",
        wall_treatment=None,
        first_cell_yplus=None,
    )
    report = check_low_re_komegasst(snap)
    assert report.findings == ()


# ---- Frozen dataclass contract ----------------------------------------


def test_finding_is_frozen():
    """Findings cannot be mutated (V130 advisory-only contract)."""
    snap = LowReKOmegaSSTSnapshot(
        turbulence_model="kOmegaSST",
        wall_treatment="resolved",
    )
    report = check_low_re_komegasst(snap)
    with pytest.raises((AttributeError, TypeError)):
        report.findings[0].severity = "warning"  # type: ignore[misc]


def test_report_is_frozen():
    """LowReKOmegaSSTReport itself is frozen."""
    snap = LowReKOmegaSSTSnapshot(
        turbulence_model="kEpsilon",
        wall_treatment="resolved",
    )
    report = check_low_re_komegasst(snap)
    with pytest.raises((AttributeError, TypeError)):
        report.findings = (  # type: ignore[misc]
            LowReKOmegaSSTFinding("info", "x", "y", "z"),
        )


def test_snapshot_is_frozen():
    """LowReKOmegaSSTSnapshot cannot be mutated."""
    snap = LowReKOmegaSSTSnapshot(turbulence_model="kOmegaSST")
    with pytest.raises((AttributeError, TypeError)):
        snap.turbulence_model = "kEpsilon"  # type: ignore[misc]


# ---- Dispatch integration test ----------------------------------------


def test_assemble_stack_dispatches_low_re_komegasst_advisor():
    """assemble_stack(low_re_komegasst_inputs=...) increments advisor_count by 1."""
    from ui.backend.services.advisor_stack import assemble_stack
    from ui.backend.services.geometry_ingest.low_re_komegasst_trigger_advisor import (
        LowReKOmegaSSTSnapshot,
    )

    # Baseline: no inputs → 0 advisors
    r_none = assemble_stack()
    baseline = r_none.advisor_count

    # With low_re_komegasst_inputs → +1 advisor
    snap = LowReKOmegaSSTSnapshot(
        turbulence_model="kOmegaSST",
        wall_treatment="resolved",
    )
    r_with = assemble_stack(low_re_komegasst_inputs=snap)

    assert r_with.advisor_count == baseline + 1

    # Confirm the advisor appears in the call log
    names = {c.advisor_name for c in r_with.advisor_calls}
    assert "low_re_komegasst_trigger_advisor" in names

    # Confirm the finding surfaced
    findings = [
        f for f in r_with.findings
        if f.source_advisor == "low_re_komegasst_trigger_advisor"
    ]
    assert len(findings) == 1
    assert findings[0].severity == "info"
    assert findings[0].code == "v104_low_re_komegasst_underprediction"

    # V104 must be in evidence_refs
    assert "V104" in r_with.evidence_refs


def test_assemble_stack_non_komegasst_does_not_surface_finding():
    """kEpsilon + resolved → advisor dispatched but zero findings from it."""
    from ui.backend.services.advisor_stack import assemble_stack
    from ui.backend.services.geometry_ingest.low_re_komegasst_trigger_advisor import (
        LowReKOmegaSSTSnapshot,
    )

    snap = LowReKOmegaSSTSnapshot(
        turbulence_model="kEpsilon",
        wall_treatment="resolved",
    )
    r = assemble_stack(low_re_komegasst_inputs=snap)

    names = {c.advisor_name for c in r.advisor_calls}
    assert "low_re_komegasst_trigger_advisor" in names

    findings = [
        f for f in r.findings
        if f.source_advisor == "low_re_komegasst_trigger_advisor"
    ]
    assert findings == []
