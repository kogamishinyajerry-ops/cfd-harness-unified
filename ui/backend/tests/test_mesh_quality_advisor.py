"""DEC-V61-138 (N2.4) · checkMesh advisor tests.

Validates the rule engine in :mod:`services.mesh_quality.advisor`
maps checkMesh metrics to MeshFixSuggestion records correctly,
emits empty list on graceful-degrade / clean meshes, and never
returns a ``recommended_change`` with shape that could be mistaken
for an apply-button payload (V132 contract — metadata only).
"""
from __future__ import annotations

import pytest

from ui.backend.services.mesh_quality.advisor import derive_suggestions
from ui.backend.services.mesh_quality.schemas import MeshQualityReportV126


def _base_v126(**overrides) -> MeshQualityReportV126:
    """Build a V126 report with defaults; override checkmesh_* fields per test."""
    base = dict(
        report_kind="v126",
        case_id="case_test",
        polymesh_present=True,
        cell_count=1000,
        point_count=2000,
        internal_face_count=2500,
        boundary_face_count=200,
        bounding_box_min=(0.0, 0.0, 0.0),
        bounding_box_max=(1.0, 1.0, 1.0),
        bounding_box_volume=1.0,
        cells_per_unit_volume=1000.0,
        patch_face_counts={"inlet": 50, "outlet": 50, "walls": 100},
        warnings=[],
        checkmesh_max_non_orthogonality_deg=None,
        checkmesh_max_skewness=None,
        checkmesh_max_aspect_ratio=None,
        checkmesh_mesh_ok=None,
        checkmesh_n_severe_non_ortho_faces=None,
        checkmesh_failed_checks=None,
        checkmesh_n_severe_non_ortho_faces_per_patch=None,
        suggestions=[],
    )
    base.update(overrides)
    return MeshQualityReportV126(**base)


# ────────── graceful degrade / clean ──────────


def test_graceful_degrade_returns_empty():
    """All checkmesh_* None (container unavailable) → no suggestions."""
    report = _base_v126()
    assert derive_suggestions(report) == []


def test_clean_mesh_returns_empty():
    """mesh_ok=True with all metrics under warning thresholds → no suggestions."""
    report = _base_v126(
        checkmesh_max_non_orthogonality_deg=40.0,
        checkmesh_max_skewness=0.3,
        checkmesh_max_aspect_ratio=8.0,
        checkmesh_mesh_ok=True,
        checkmesh_n_severe_non_ortho_faces=0,
    )
    assert derive_suggestions(report) == []


# ────────── severe non-ortho faces ──────────


def test_severe_faces_with_per_patch_localizes():
    report = _base_v126(
        checkmesh_max_non_orthogonality_deg=72.0,
        checkmesh_max_skewness=0.5,
        checkmesh_max_aspect_ratio=20.0,
        checkmesh_mesh_ok=True,
        checkmesh_n_severe_non_ortho_faces=15,
        checkmesh_n_severe_non_ortho_faces_per_patch={
            "walls": 12,
            "inlet": 3,
            "outlet": 0,
        },
    )
    suggestions = derive_suggestions(report)
    assert len(suggestions) >= 1
    severe = next(s for s in suggestions if s.metric == "n_severe_non_ortho_faces")
    assert severe.severity == "warning"
    assert "walls (12)" in severe.suggestion_text
    assert "inlet (3)" in severe.suggestion_text
    assert "outlet" not in severe.suggestion_text  # zero-count dropped
    assert severe.recommended_change is not None
    assert severe.recommended_change["patches_affected"] == ["walls", "inlet"]


def test_severe_faces_without_per_patch_generic_text():
    report = _base_v126(
        checkmesh_n_severe_non_ortho_faces=5,
        checkmesh_n_severe_non_ortho_faces_per_patch=None,
    )
    suggestions = derive_suggestions(report)
    severe = next(s for s in suggestions if s.metric == "n_severe_non_ortho_faces")
    assert severe.severity == "warning"
    assert "5 severely" in severe.suggestion_text
    # No per-patch breakdown — recommended_change still emitted but
    # patches_affected should be empty.
    assert severe.recommended_change is not None
    assert severe.recommended_change["patches_affected"] == []


def test_severe_faces_singular_grammar():
    report = _base_v126(checkmesh_n_severe_non_ortho_faces=1)
    suggestions = derive_suggestions(report)
    severe = next(s for s in suggestions if s.metric == "n_severe_non_ortho_faces")
    assert "1 severely non-orthogonal face " in severe.suggestion_text
    assert "faces" not in severe.suggestion_text.split("face")[0] + "face"


def test_severe_faces_zero_no_emit():
    report = _base_v126(checkmesh_n_severe_non_ortho_faces=0)
    suggestions = derive_suggestions(report)
    assert all(s.metric != "n_severe_non_ortho_faces" for s in suggestions)


def test_severe_faces_picks_top_three_patches():
    """Per-patch worst offenders capped at 3 to keep suggestion text terse."""
    report = _base_v126(
        checkmesh_n_severe_non_ortho_faces=100,
        checkmesh_n_severe_non_ortho_faces_per_patch={
            "p1": 50, "p2": 30, "p3": 10, "p4": 5, "p5": 5,
        },
    )
    suggestions = derive_suggestions(report)
    severe = next(s for s in suggestions if s.metric == "n_severe_non_ortho_faces")
    assert severe.recommended_change is not None
    assert severe.recommended_change["patches_affected"] == ["p1", "p2", "p3"]
    assert "p4" not in severe.suggestion_text
    assert "p5" not in severe.suggestion_text


# ────────── non-orthogonality ──────────


def test_non_ortho_critical_above_75():
    report = _base_v126(checkmesh_max_non_orthogonality_deg=80.0)
    suggestions = derive_suggestions(report)
    nod = next(s for s in suggestions if s.metric == "max_non_orthogonality")
    assert nod.severity == "critical"
    assert "80.0°" in nod.suggestion_text
    assert nod.recommended_change is not None


def test_non_ortho_warning_marginal_band():
    report = _base_v126(checkmesh_max_non_orthogonality_deg=70.0)
    suggestions = derive_suggestions(report)
    nod = next(s for s in suggestions if s.metric == "max_non_orthogonality")
    assert nod.severity == "warning"
    assert "70.0°" in nod.suggestion_text
    assert nod.recommended_change is None  # marginal: just informational


def test_non_ortho_good_no_emit():
    report = _base_v126(checkmesh_max_non_orthogonality_deg=45.0)
    suggestions = derive_suggestions(report)
    assert all(s.metric != "max_non_orthogonality" for s in suggestions)


# ────────── skewness ──────────


def test_skewness_critical_above_0_95():
    report = _base_v126(checkmesh_max_skewness=1.1)
    suggestions = derive_suggestions(report)
    sk = next(s for s in suggestions if s.metric == "max_skewness")
    assert sk.severity == "critical"
    assert "1.10" in sk.suggestion_text
    assert sk.recommended_change is not None


def test_skewness_warning_band():
    report = _base_v126(checkmesh_max_skewness=0.85)
    suggestions = derive_suggestions(report)
    sk = next(s for s in suggestions if s.metric == "max_skewness")
    assert sk.severity == "warning"
    assert sk.recommended_change is None


def test_skewness_clean_no_emit():
    report = _base_v126(checkmesh_max_skewness=0.4)
    suggestions = derive_suggestions(report)
    assert all(s.metric != "max_skewness" for s in suggestions)


# ────────── aspect ratio ──────────


def test_aspect_ratio_defect_above_1000():
    report = _base_v126(checkmesh_max_aspect_ratio=2500.0)
    suggestions = derive_suggestions(report)
    ar = next(s for s in suggestions if s.metric == "max_aspect_ratio")
    assert ar.severity == "warning"
    assert "2500" in ar.suggestion_text
    assert ar.recommended_change is not None
    assert "prism" in ar.recommended_change["step"]


def test_aspect_ratio_elevated_info():
    report = _base_v126(checkmesh_max_aspect_ratio=300.0)
    suggestions = derive_suggestions(report)
    ar = next(s for s in suggestions if s.metric == "max_aspect_ratio")
    assert ar.severity == "info"
    assert ar.recommended_change is None


def test_aspect_ratio_good_no_emit():
    report = _base_v126(checkmesh_max_aspect_ratio=8.0)
    suggestions = derive_suggestions(report)
    assert all(s.metric != "max_aspect_ratio" for s in suggestions)


# ────────── mesh_ok=False fallback ──────────


def test_mesh_ok_false_with_no_metric_breach_emits_generic():
    report = _base_v126(
        checkmesh_max_non_orthogonality_deg=40.0,
        checkmesh_max_skewness=0.3,
        checkmesh_max_aspect_ratio=8.0,
        checkmesh_mesh_ok=False,
        checkmesh_n_severe_non_ortho_faces=0,
        checkmesh_failed_checks=["some opaque check failed"],
    )
    suggestions = derive_suggestions(report)
    assert len(suggestions) == 1
    assert suggestions[0].metric == "mesh_ok"
    assert suggestions[0].severity == "warning"
    assert suggestions[0].recommended_change is None


def test_mesh_ok_false_with_metric_breach_no_generic_fallback():
    """When a specific metric already triggered a suggestion, the generic
    mesh_ok fallback is suppressed to avoid noise."""
    report = _base_v126(
        checkmesh_max_skewness=1.0,
        checkmesh_mesh_ok=False,
        checkmesh_failed_checks=["max skewness exceeded"],
    )
    suggestions = derive_suggestions(report)
    assert all(s.metric != "mesh_ok" for s in suggestions)


def test_mesh_ok_false_no_failed_checks_no_emit():
    """mesh_ok=False without failed_checks list → don't fabricate a suggestion."""
    report = _base_v126(
        checkmesh_max_non_orthogonality_deg=40.0,
        checkmesh_max_skewness=0.3,
        checkmesh_max_aspect_ratio=8.0,
        checkmesh_mesh_ok=False,
        checkmesh_n_severe_non_ortho_faces=0,
        checkmesh_failed_checks=None,
    )
    suggestions = derive_suggestions(report)
    assert suggestions == []


# ────────── multi-issue mesh ──────────


def test_combined_issues_all_emit():
    report = _base_v126(
        checkmesh_max_non_orthogonality_deg=80.0,
        checkmesh_max_skewness=1.0,
        checkmesh_max_aspect_ratio=2000.0,
        checkmesh_mesh_ok=False,
        checkmesh_n_severe_non_ortho_faces=20,
        checkmesh_n_severe_non_ortho_faces_per_patch={"walls": 20},
        checkmesh_failed_checks=["non-orthogonality", "skewness", "aspect ratio"],
    )
    suggestions = derive_suggestions(report)
    metrics = {s.metric for s in suggestions}
    assert metrics == {
        "n_severe_non_ortho_faces",
        "max_non_orthogonality",
        "max_skewness",
        "max_aspect_ratio",
    }
    # Generic mesh_ok fallback suppressed (specific metrics fired).
    assert "mesh_ok" not in metrics


# ────────── V132 contract: recommended_change is metadata only ──────────


def test_recommended_change_never_contains_route_or_endpoint():
    """V132 contract: recommended_change must NOT look like an apply-button
    payload. No HTTP method / URL / endpoint keys.
    """
    forbidden_keys = {"url", "method", "endpoint", "route", "POST", "PUT", "PATCH"}
    report = _base_v126(
        checkmesh_max_non_orthogonality_deg=80.0,
        checkmesh_max_skewness=1.0,
        checkmesh_max_aspect_ratio=2000.0,
        checkmesh_mesh_ok=False,
        checkmesh_n_severe_non_ortho_faces=20,
        checkmesh_n_severe_non_ortho_faces_per_patch={"walls": 20},
    )
    for s in derive_suggestions(report):
        if s.recommended_change is None:
            continue
        keys_lower = {k.lower() for k in s.recommended_change.keys()}
        assert not (forbidden_keys & {k.lower() for k in forbidden_keys} & keys_lower)
        # Recommended_change must always carry a human-readable "step" or
        # "hint" — never a callable payload.
        assert "step" in s.recommended_change or "hint" in s.recommended_change


def test_severity_enum_values_only():
    """All emitted severities are within the FixSeverity literal set."""
    report = _base_v126(
        checkmesh_max_non_orthogonality_deg=80.0,
        checkmesh_max_skewness=1.0,
        checkmesh_max_aspect_ratio=2000.0,
        checkmesh_mesh_ok=False,
        checkmesh_n_severe_non_ortho_faces=20,
    )
    for s in derive_suggestions(report):
        assert s.severity in {"critical", "warning", "info"}
