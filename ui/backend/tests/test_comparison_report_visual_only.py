"""Phase 7c Tier C (DEC-V61-034) — visual-only context + render-serving route tests.

Guards:
- build_report_context returns visual_only=True for VISUAL_ONLY_CASES
- Render route serves PNG with path-containment defense
- Traversal attempts in render filename are rejected (404)
- Missing case / run_label produces 404 (not 500)
- Tampered run-manifest timestamp is rejected (404)
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ui.backend.main import app
from ui.backend.services.comparison_report import (
    _VISUAL_ONLY_CASES,
    ReportError,
    build_report_context,
)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _plant_run_manifest(
    repo_root: Path, case_id: str, timestamp: str = "20260101T000000Z",
) -> Path:
    """Write a minimal Phase 7a runs/{label}.json + corresponding renders
    manifest + both PNGs into reports/phase5_{fields,renders}/{case}/.
    """
    fields_dir = repo_root / "reports" / "phase5_fields" / case_id
    renders_dir = repo_root / "reports" / "phase5_renders" / case_id
    artifact_dir = fields_dir / timestamp
    render_ts_dir = renders_dir / timestamp
    artifact_dir.mkdir(parents=True, exist_ok=True)
    render_ts_dir.mkdir(parents=True, exist_ok=True)
    (fields_dir / "runs").mkdir(parents=True, exist_ok=True)
    (fields_dir / "runs" / "audit_real_run.json").write_text(
        json.dumps({
            "run_label": "audit_real_run",
            "timestamp": timestamp,
            "case_id": case_id,
            "artifact_dir_rel": str(artifact_dir.relative_to(repo_root)),
        }),
        encoding="utf-8",
    )
    (artifact_dir / "log.simpleFoam").write_text("Time = 1s\n", encoding="utf-8")
    (render_ts_dir / "contour_u_magnitude.png").write_bytes(b"\x89PNG\r\n\x1a\nfake")
    (render_ts_dir / "residuals.png").write_bytes(b"\x89PNG\r\n\x1a\nfake2")
    (renders_dir / "runs").mkdir(parents=True, exist_ok=True)
    (renders_dir / "runs" / "audit_real_run.json").write_text(
        json.dumps({
            "run_label": "audit_real_run",
            "timestamp": timestamp,
            "case_id": case_id,
            "outputs": {
                "contour_u_magnitude_png":
                    f"reports/phase5_renders/{case_id}/{timestamp}/contour_u_magnitude.png",
                "residuals_png":
                    f"reports/phase5_renders/{case_id}/{timestamp}/residuals.png",
            },
        }),
        encoding="utf-8",
    )
    return artifact_dir


def test_visual_only_cases_are_nine() -> None:
    """VISUAL_ONLY_CASES covers all 9 non-LDC whitelist cases per DEC-V61-034."""
    assert "lid_driven_cavity" not in _VISUAL_ONLY_CASES
    expected = {
        "backward_facing_step", "plane_channel_flow", "turbulent_flat_plate",
        "circular_cylinder_wake", "impinging_jet", "naca0012_airfoil",
        "rayleigh_benard_convection", "differential_heated_cavity", "duct_flow",
    }
    assert _VISUAL_ONLY_CASES == expected


def test_visual_only_context_shape(tmp_path, monkeypatch) -> None:
    """build_report_context returns visual_only=True with renders populated."""
    case = "backward_facing_step"
    _plant_run_manifest(tmp_path, case)
    monkeypatch.setattr(
        "ui.backend.services.comparison_report._FIELDS_ROOT",
        tmp_path / "reports" / "phase5_fields",
    )
    monkeypatch.setattr(
        "ui.backend.services.comparison_report._RENDERS_ROOT",
        tmp_path / "reports" / "phase5_renders",
    )
    monkeypatch.setattr(
        "ui.backend.services.comparison_report._REPO_ROOT", tmp_path,
    )

    ctx = build_report_context(case, "audit_real_run")
    assert ctx["visual_only"] is True
    assert ctx["case_id"] == case
    assert ctx["run_label"] == "audit_real_run"
    assert ctx["verdict"] is None
    assert ctx["metrics"] is None
    assert ctx["paper"] is None
    assert ctx["renders"]["contour_png_rel"].endswith("contour_u_magnitude.png")
    assert ctx["renders"]["residuals_png_rel"].endswith("residuals.png")
    assert ctx["solver"] == "simpleFoam"
    assert "visual-only" in ctx["subtitle"].lower()


def test_unknown_case_404(client) -> None:
    """Unsupported case → 404, not 500."""
    resp = client.get(
        "/api/cases/totally_unknown_case/runs/audit_real_run/comparison-report/context",
    )
    assert resp.status_code == 404


def test_render_route_traversal_rejected(client) -> None:
    """../../secret in render filename is rejected as 404 (traversal defense)."""
    resp = client.get(
        "/api/cases/backward_facing_step/runs/audit_real_run/renders/..%2F..%2F..%2Fetc%2Fpasswd",
    )
    assert resp.status_code == 404


def test_render_route_missing_run_manifest_404(client, tmp_path, monkeypatch) -> None:
    """Case id in supported set but no run manifest → 404 (no 500)."""
    monkeypatch.setattr(
        "ui.backend.services.comparison_report._FIELDS_ROOT",
        tmp_path / "reports" / "phase5_fields",
    )
    resp = client.get(
        "/api/cases/duct_flow/runs/nonexistent_run/renders/contour_u_magnitude.png",
    )
    assert resp.status_code == 404


def test_visual_only_context_rejects_tampered_timestamp(tmp_path, monkeypatch) -> None:
    """Run manifest with timestamp='../../etc' is rejected by _validated_timestamp."""
    case = "plane_channel_flow"
    fields_dir = tmp_path / "reports" / "phase5_fields" / case
    (fields_dir / "runs").mkdir(parents=True)
    (fields_dir / "runs" / "audit_real_run.json").write_text(
        json.dumps({
            "run_label": "audit_real_run",
            "timestamp": "../../../etc/passwd",  # malicious
            "case_id": case,
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "ui.backend.services.comparison_report._FIELDS_ROOT",
        tmp_path / "reports" / "phase5_fields",
    )

    with pytest.raises(ReportError, match="invalid timestamp"):
        build_report_context(case, "audit_real_run")


def test_render_report_html_raises_for_visual_only(tmp_path, monkeypatch) -> None:
    """Codex round 1 CR (2026-04-21): render_report_html on a visual-only case
    must raise ReportError (→ 404), NOT 500 from template dereferencing
    None metrics/paper fields.
    """
    from ui.backend.services.comparison_report import render_report_html
    case = "backward_facing_step"
    _plant_run_manifest(tmp_path, case)
    monkeypatch.setattr(
        "ui.backend.services.comparison_report._FIELDS_ROOT",
        tmp_path / "reports" / "phase5_fields",
    )
    monkeypatch.setattr(
        "ui.backend.services.comparison_report._RENDERS_ROOT",
        tmp_path / "reports" / "phase5_renders",
    )
    monkeypatch.setattr(
        "ui.backend.services.comparison_report._REPO_ROOT", tmp_path,
    )
    with pytest.raises(ReportError, match="visual-only"):
        render_report_html(case, "audit_real_run")


def test_render_report_pdf_raises_for_visual_only(tmp_path, monkeypatch) -> None:
    """PDF path runs through render_report_html internally, so the same
    ReportError guard fires; nothing else downstream can crash."""
    from ui.backend.services.comparison_report import render_report_pdf
    case = "plane_channel_flow"
    _plant_run_manifest(tmp_path, case)
    monkeypatch.setattr(
        "ui.backend.services.comparison_report._FIELDS_ROOT",
        tmp_path / "reports" / "phase5_fields",
    )
    monkeypatch.setattr(
        "ui.backend.services.comparison_report._RENDERS_ROOT",
        tmp_path / "reports" / "phase5_renders",
    )
    monkeypatch.setattr(
        "ui.backend.services.comparison_report._REPO_ROOT", tmp_path,
    )
    with pytest.raises(ReportError, match="visual-only"):
        render_report_pdf(case, "audit_real_run")


def test_route_html_returns_404_for_visual_only(client) -> None:
    """End-to-end: GET /api/cases/BFS/runs/audit_real_run/comparison-report
    returns 404 (via ReportError) for visual-only case, NOT 500."""
    resp = client.get(
        "/api/cases/backward_facing_step/runs/audit_real_run/comparison-report",
    )
    assert resp.status_code == 404, f"expected 404, got {resp.status_code}: {resp.text[:200]}"


def test_gold_overlay_case_not_affected_by_visual_only_branch(tmp_path, monkeypatch) -> None:
    """LDC does NOT take the visual_only branch — existing gold-overlay flow
    preserved. This test ensures the dispatch check is case-set membership,
    not a global flag."""
    from ui.backend.services.comparison_report import _GOLD_OVERLAY_CASES
    assert "lid_driven_cavity" in _GOLD_OVERLAY_CASES
    for c in _VISUAL_ONLY_CASES:
        assert c not in _GOLD_OVERLAY_CASES
