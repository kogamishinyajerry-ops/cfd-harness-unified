"""DEC-V61-119 · system-prompt composition tests.

Covers:
  * Basic composition (case state line, missing-field rendering)
  * Severity ranking (critical > warning > info)
  * ``max_missing_to_inline`` cap + remainder summary
  * Empty missing list path
  * Notes pass-through
  * Suggested-default secret-shape heuristic skips token-like values
  * Pure function: no I/O, deterministic output
"""
from __future__ import annotations

import pytest

from ui.backend.services.case_completeness import (
    CaseCompletenessReport,
    MissingField,
)
from ui.backend.services.llm_coach import (
    DEFAULT_PROJECT_RULES,
    build_coach_system_prompt,
)


def _make_report(
    *,
    case_id: str = "ldc",
    case_kind: str = "whitelist",
    missing: list[MissingField] | None = None,
    notes: list[str] | None = None,
    ready: bool = False,
    blocked: int = 1,
    present: int = 4,
    total: int = 5,
) -> CaseCompletenessReport:
    return CaseCompletenessReport(
        case_id=case_id,
        case_kind=case_kind,  # type: ignore[arg-type]
        ready_for_archive=ready,
        blocked_by_critical=blocked,
        present_count=present,
        total_count=total,
        percentage=round(100.0 * present / total, 1),
        missing=missing or [],
        notes=notes or [],
    )


def test_prompt_includes_case_state_line():
    report = _make_report()
    prompt = build_coach_system_prompt(report)
    assert "case_id=ldc" in prompt
    assert "case_kind=whitelist" in prompt
    assert "completeness=80.0%" in prompt
    assert "ready_for_archive=False" in prompt
    assert "blocked_by_critical=1" in prompt


def test_prompt_includes_default_project_rules():
    report = _make_report()
    prompt = build_coach_system_prompt(report)
    # First layer is the role preamble; spot-check key constraints.
    # V61-121 updated the role from "Read-only adviser" to
    # "Adviser + proposer" — the engineer-approval guarantee remains
    # the load-bearing constraint.
    assert "Adviser + proposer" in prompt
    assert "MUST NOT claim that an action has been applied" in prompt
    assert DEFAULT_PROJECT_RULES.rstrip() in prompt


def test_prompt_includes_v121_proposal_protocol_and_tool_registry():
    """DEC-V61-121: the system prompt must enumerate the PROPOSAL
    delimiter rules and the registered tools so the LLM knows what
    it may emit."""
    report = _make_report()
    prompt = build_coach_system_prompt(report)
    assert "<<PROPOSAL" in prompt
    assert "PROPOSAL>>" in prompt
    assert "Registered tools" in prompt
    assert "set_patch_bc_type" in prompt


def test_prompt_renders_missing_field_entries():
    report = _make_report(
        missing=[
            MissingField(
                field_path="physics.turbulence_model",
                severity="critical",
                why="LDC at Re=1000 needs explicit laminar/RANS choice",
                suggested_default="laminar",
            ),
        ],
    )
    prompt = build_coach_system_prompt(report)
    assert "field_path=physics.turbulence_model" in prompt
    assert "[CRITICAL]" in prompt
    assert "suggested_default='laminar'" in prompt


def test_prompt_severity_rank_critical_before_warning():
    report = _make_report(
        missing=[
            MissingField(field_path="a", severity="warning", why="w"),
            MissingField(field_path="b", severity="critical", why="c"),
            MissingField(field_path="c", severity="info", why="i"),
        ],
    )
    prompt = build_coach_system_prompt(report)
    crit_idx = prompt.index("field_path=b")
    warn_idx = prompt.index("field_path=a")
    info_idx = prompt.index("field_path=c")
    assert crit_idx < warn_idx < info_idx


def test_prompt_caps_at_max_missing_to_inline():
    missing = [
        MissingField(field_path=f"f{i}", severity="critical", why=f"w{i}")
        for i in range(15)
    ]
    report = _make_report(missing=missing, blocked=15, present=0, total=15)
    prompt = build_coach_system_prompt(report, max_missing_to_inline=5)
    assert prompt.count("field_path=f") == 5
    assert "+ 10 more missing entries" in prompt


def test_prompt_no_remainder_summary_when_below_cap():
    missing = [
        MissingField(field_path=f"f{i}", severity="warning", why="w")
        for i in range(3)
    ]
    report = _make_report(missing=missing, blocked=0)
    prompt = build_coach_system_prompt(report, max_missing_to_inline=8)
    assert "+ " not in prompt or "more missing entries" not in prompt


def test_prompt_empty_missing_list_says_so():
    report = _make_report(missing=[], blocked=0, present=5, total=5, ready=True)
    prompt = build_coach_system_prompt(report)
    assert "all expected fields are present" in prompt


def test_prompt_includes_analyzer_notes():
    report = _make_report(notes=["No gold standard linked.", "STL ingest had 2 warnings."])
    prompt = build_coach_system_prompt(report)
    assert "No gold standard linked." in prompt
    assert "STL ingest had 2 warnings." in prompt


def test_prompt_skips_secret_shaped_suggested_default():
    secret = "sk-" + "x" * 60
    report = _make_report(
        missing=[
            MissingField(
                field_path="auth.api_key",
                severity="critical",
                why="not set",
                suggested_default=secret,
            ),
        ],
    )
    prompt = build_coach_system_prompt(report)
    # The field still appears (engineer needs to know it's missing)
    assert "field_path=auth.api_key" in prompt
    # But the token-shaped default is dropped.
    assert secret not in prompt


def test_prompt_keeps_short_non_secret_suggested_default():
    report = _make_report(
        missing=[
            MissingField(
                field_path="solver.maxIter",
                severity="warning",
                why="missing",
                suggested_default=2000,
            ),
        ],
    )
    prompt = build_coach_system_prompt(report)
    assert "suggested_default=2000" in prompt


def test_prompt_negative_max_rejected():
    report = _make_report()
    with pytest.raises(ValueError):
        build_coach_system_prompt(report, max_missing_to_inline=-1)


def test_prompt_is_pure_deterministic():
    """Same input → same output. No timestamps, no env reads."""
    report = _make_report(
        missing=[MissingField(field_path="x", severity="critical", why="y")]
    )
    a = build_coach_system_prompt(report)
    b = build_coach_system_prompt(report)
    assert a == b


def test_prompt_omits_mesh_section_when_no_report_passed():
    """V120/V121 callers compose without mesh_quality_report — the
    prompt must remain backwards-compatible (no mesh section)."""
    report = _make_report()
    prompt = build_coach_system_prompt(report)
    assert "Current mesh snapshot" not in prompt


def test_prompt_includes_mesh_section_when_report_passed():
    """DEC-V61-122: when a MeshQualityReport is passed, the prompt
    appends a 'Current mesh snapshot' section AFTER the case state."""
    from ui.backend.services.mesh_quality import (
        MeshQualityReport,
        MeshWarning,
    )

    mesh = MeshQualityReport(
        case_id="ldc",
        polymesh_present=True,
        cell_count=125,
        point_count=8,
        internal_face_count=200,
        boundary_face_count=100,
        bounding_box_min=(0.0, 0.0, 0.0),
        bounding_box_max=(1.0, 1.0, 1.0),
        bounding_box_volume=1.0,
        cells_per_unit_volume=125.0,
        patch_face_counts={"walls": 60, "inlet": 40},
        warnings=[
            MeshWarning(
                severity="warning",
                code="cell_count_low",
                message="125 cells; under-refined",
            )
        ],
    )
    report = _make_report()
    prompt = build_coach_system_prompt(report, mesh_quality_report=mesh)
    assert "Current mesh snapshot" in prompt
    assert "cells=125" in prompt
    assert "cell_count_low" in prompt
    assert "walls: 60" in prompt
    assert "inlet: 40" in prompt
    # Case state still appears BEFORE the mesh section.
    case_idx = prompt.index("Current case snapshot")
    mesh_idx = prompt.index("Current mesh snapshot")
    assert case_idx < mesh_idx


def test_prompt_does_not_leak_default_project_rules_when_overridden():
    """Custom project_rules string fully replaces the default — useful
    if a future deployment wants different role wording."""
    report = _make_report()
    prompt = build_coach_system_prompt(report, project_rules="CUSTOM RULES.")
    assert "CUSTOM RULES." in prompt
    assert "Read-only adviser" not in prompt
