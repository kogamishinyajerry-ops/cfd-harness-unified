"""DEC-V61-202-SUB-M32-CYCLE1 · rail severity surfacing tests.

M3.1 cycle 7 added critical info_gaps (corrupted manifest) and cycle 8
added info-level info_gaps (typo'd patch_type), but RailPrimary had no
severity field — both surfaced as identical amber rails. M3.2 cycle 1
adds the severity field + populates it from the source gap/problem
severity so the frontend can render distinct tones.

Tests cover both the rail-builder helpers directly + the full decide()
end-to-end for the M3.1 cycle-7 and cycle-8 fixtures.
"""
from __future__ import annotations

from ui.backend.schemas.workbench_frame import CaseStateSnapshot
from ui.backend.services.workbench_decide import (
    _rail_from_gap,
    _rail_from_problem,
    decide,
)


def _state(step: int = 4) -> CaseStateSnapshot:
    return CaseStateSnapshot(
        case_id="case_test",
        step=step,
        manifest={"case_id": "case_test"},
        artifacts={},
        completeness=None,
        focus_patch=None,
        focus_region=None,
        focus_panel=None,
    )


# ─── _rail_from_gap: gap severity → rail severity ───


def test_critical_gap_produces_fail_severity_rail():
    gap = {
        "field_path": "case_manifest.yaml",
        "severity": "critical",
        "why": "Imported manifest fails schema validation.",
    }
    rail = _rail_from_gap(gap, _state())
    assert rail.kind == "info_gap"
    assert rail.severity == "fail"


def test_warning_gap_produces_warn_severity_rail():
    gap = {
        "field_path": "case_family",
        "severity": "warning",
        "why": "case_family unset; helper skeleton unavailable.",
    }
    rail = _rail_from_gap(gap, _state())
    assert rail.severity == "warn"


def test_info_gap_produces_info_severity_rail():
    gap = {
        "field_path": "bc.patches.inlet.patch_type",
        "severity": "info",
        "why": "Patch type 'fixedValue_typo' not in OpenFOAM vocabulary.",
    }
    rail = _rail_from_gap(gap, _state())
    assert rail.severity == "info"


def test_gap_with_unknown_severity_defaults_to_info():
    gap = {
        "field_path": "some.field",
        "severity": "mystery_value",
        "why": "test edge",
    }
    rail = _rail_from_gap(gap, _state())
    # _normalize_severity returns "info" for anything outside its known set
    assert rail.severity == "info"


# ─── _rail_from_problem: audit severity → rail severity ───


def test_fail_problem_produces_fail_severity_rail():
    problem = {
        "severity": "fail",
        "title": "Mesh quality FAIL",
        "field_path": "mesh_contract.y_plus_target.max",
    }
    rail = _rail_from_problem(problem, _state())
    assert rail.kind == "problem_fix"
    assert rail.severity == "fail"


def test_warn_problem_produces_warn_severity_rail():
    problem = {"severity": "warn", "title": "non-orthogonality"}
    rail = _rail_from_problem(problem, _state())
    assert rail.severity == "warn"


def test_critical_problem_normalizes_to_fail():
    """`_normalize_severity` collapses 'critical' / 'error' / 'blocker'
    onto 'fail' — keep the contract pinned for the rail surface.
    """
    problem = {"severity": "critical", "title": "test"}
    rail = _rail_from_problem(problem, _state())
    assert rail.severity == "fail"


# ─── _rail_default ───


def test_step_default_rail_keeps_info_severity():
    """No blockers = no severity signal. Default 'info' preserves
    legacy fixtures (other tests assume the field exists with this
    default).
    """
    state = _state()
    frame = decide(state)
    assert frame.rail_primary.kind == "step_default"
    assert frame.rail_primary.severity == "info"


# ─── Integration: end-to-end via decide() for M3.1 fixtures ───


def test_corrupted_manifest_rail_surfaces_fail_severity():
    """M3.1 cycle 7 fixture: corruption detector → critical gap →
    rail.severity must be "fail" so frontend tones it as urgent."""
    state = CaseStateSnapshot(
        case_id="case_corrupted",
        step=4,
        manifest={"case_id": "case_corrupted"},
        artifacts={},
        completeness={
            "missing": [
                {
                    "field_path": "case_manifest.yaml",
                    "severity": "critical",
                    "why": "Imported manifest fails schema validation.",
                }
            ]
        },
        focus_patch=None,
        focus_region=None,
        focus_panel=None,
    )
    frame = decide(state)
    assert frame.rail_primary.kind == "info_gap"
    assert frame.rail_primary.severity == "fail"
    assert frame.topbar_cta.enabled is False


def test_typo_patch_type_rail_surfaces_info_severity():
    """M3.1 cycle 8 fixture: unknown patch_type → info gap →
    rail.severity must be "info" so frontend tones it as soft."""
    state = CaseStateSnapshot(
        case_id="case_typo",
        step=4,
        manifest={"case_id": "case_typo"},
        artifacts={},
        completeness={
            "missing": [
                {
                    "field_path": "bc.patches.inlet.patch_type",
                    "severity": "info",
                    "why": "Patch 'inlet' has patch_type='fixedValue_typo'.",
                }
            ]
        },
        focus_patch=None,
        focus_region=None,
        focus_panel=None,
    )
    frame = decide(state)
    assert frame.rail_primary.kind == "info_gap"
    assert frame.rail_primary.severity == "info"
    # info gaps don't block proceed
    assert frame.topbar_cta.enabled is True


def test_critical_outranks_info_when_both_present():
    """When both critical + info gaps exist, the critical wins the
    rail (per _pick_rail_primary priority order). Severity reflects
    the winning gap, not a mix.
    """
    state = CaseStateSnapshot(
        case_id="case_mixed",
        step=4,
        manifest={"case_id": "case_mixed"},
        artifacts={},
        completeness={
            "missing": [
                {
                    "field_path": "bc.patches.inlet.patch_type",
                    "severity": "info",
                    "why": "Typo'd patch_type.",
                },
                {
                    "field_path": "case_manifest.yaml",
                    "severity": "critical",
                    "why": "Schema invalid.",
                },
            ]
        },
        focus_patch=None,
        focus_region=None,
        focus_panel=None,
    )
    frame = decide(state)
    assert frame.rail_primary.severity == "fail"
    assert frame.rail_primary.field_path == "case_manifest.yaml"
