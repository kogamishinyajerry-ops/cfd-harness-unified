"""Phase 7c — comparison_report service unit tests (CI-safe, no real artifacts).

Builds a synthetic artifact tree in tmp_path, monkeypatches the module's root
constants, exercises render_report_html + build_report_context + the Codex
round-1 HIGH containment guards.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture
def synthetic_tree(tmp_path: pytest.TempPathFactory, monkeypatch):
    """Build a minimal Phase-7a-and-7b-compatible artifact tree in tmp_path."""
    root = tmp_path
    case = "lid_driven_cavity"
    ts = "20260421T000000Z"

    fields_root = root / "reports" / "phase5_fields"
    renders_root = root / "reports" / "phase5_renders"
    case_fields = fields_root / case / ts
    (case_fields / "sample" / "1000").mkdir(parents=True)
    (case_fields / "sample" / "1000" / "uCenterline.xy").write_text(
        "#   y   U_x   U_y   U_z   p\n"
        "0     0      0     0    0.5\n"
        "0.5  -0.2    0     0    0.5\n"
        "1.0   1.0    0     0    0.5\n",
        encoding="utf-8",
    )
    (case_fields / "residuals.csv").write_text(
        "Time,Ux,Uy,p\n0,N/A,N/A,N/A\n1,1.0,1.0,1.0\n2,0.1,0.1,0.1\n",
        encoding="utf-8",
    )
    (fields_root / case / "runs").mkdir(parents=True)
    (fields_root / case / "runs" / "audit_real_run.json").write_text(
        json.dumps({"timestamp": ts, "case_id": case, "run_label": "audit_real_run"}),
        encoding="utf-8",
    )

    # Minimal render outputs (empty PNGs are fine for containment checks).
    renders_case = renders_root / case / ts
    renders_case.mkdir(parents=True)
    for name in ["profile_u_centerline.png", "pointwise_deviation.png",
                 "contour_u_magnitude.png", "residuals.png"]:
        (renders_case / name).write_bytes(b"\x89PNG\r\n\x1a\n")  # 8-byte stub
    (renders_root / case / "runs").mkdir(parents=True)
    (renders_root / case / "runs" / "audit_real_run.json").write_text(
        json.dumps({
            "case_id": case, "run_label": "audit_real_run", "timestamp": ts,
            "outputs": {
                "profile_png": f"reports/phase5_renders/{case}/{ts}/profile_u_centerline.png",
                "pointwise_deviation_png": f"reports/phase5_renders/{case}/{ts}/pointwise_deviation.png",
                "contour_u_magnitude_png": f"reports/phase5_renders/{case}/{ts}/contour_u_magnitude.png",
                "residuals_png": f"reports/phase5_renders/{case}/{ts}/residuals.png",
            },
        }),
        encoding="utf-8",
    )

    # Minimal LDC gold YAML in tmp_path/knowledge/gold_standards/.
    gold_dir = root / "knowledge" / "gold_standards"
    gold_dir.mkdir(parents=True)
    (gold_dir / "lid_driven_cavity.yaml").write_text(
        "quantity: u_centerline\n"
        "reference_values:\n"
        "  - y: 0.0\n    u: 0.0\n"
        "  - y: 0.5\n    u: -0.20581\n"
        "  - y: 1.0\n    u: 1.0\n"
        "tolerance: 0.05\n"
        "source: Ghia Ghia Shin 1982 Table I Re=100\n"
        "literature_doi: 10.1016/0021-9991(82)90058-4\n",
        encoding="utf-8",
    )

    # Minimal mesh_{20,40,80,160} fixtures for grid-convergence table.
    fixture_case = root / "ui" / "backend" / "tests" / "fixtures" / "runs" / case
    fixture_case.mkdir(parents=True)
    for mesh, val in (("mesh_20", -0.055), ("mesh_40", -0.048),
                      ("mesh_80", -0.044), ("mesh_160", -0.042)):
        (fixture_case / f"{mesh}_measurement.yaml").write_text(
            f"measurement:\n  value: {val}\n", encoding="utf-8",
        )

    from ui.backend.services import comparison_report as svc
    monkeypatch.setattr(svc, "_REPO_ROOT", root)
    monkeypatch.setattr(svc, "_FIELDS_ROOT", fields_root)
    monkeypatch.setattr(svc, "_RENDERS_ROOT", renders_root)
    monkeypatch.setattr(svc, "_GOLD_ROOT", gold_dir)
    monkeypatch.setattr(svc, "_FIXTURE_ROOT", root / "ui" / "backend" / "tests" / "fixtures" / "runs")

    return {"root": root, "case": case, "ts": ts, "svc": svc}


def test_build_context_happy_path(synthetic_tree) -> None:
    svc = synthetic_tree["svc"]
    ctx = svc.build_report_context("lid_driven_cavity", "audit_real_run")
    assert ctx["case_id"] == "lid_driven_cavity"
    assert ctx["timestamp"] == "20260421T000000Z"
    assert ctx["metrics"]["n_total"] == 3
    assert ctx["verdict"] in ("PASS", "PARTIAL", "FAIL")


def test_render_html_contains_8_sections(synthetic_tree) -> None:
    svc = synthetic_tree["svc"]
    html = svc.render_report_html("lid_driven_cavity", "audit_real_run")
    for marker in ["参考文献", "中心线 profile", "逐点偏差分布",
                   "流场 contour", "残差收敛历史", "网格收敛",
                   "求解器元数据"]:
        assert marker in html, f"missing §: {marker}"


def test_rejects_tampered_manifest_timestamp(synthetic_tree) -> None:
    """Codex round 1 HIGH: manifest with timestamp='../../outside' must be rejected."""
    svc = synthetic_tree["svc"]
    root = synthetic_tree["root"]
    # Overwrite manifest with malicious timestamp.
    m = root / "reports" / "phase5_fields" / "lid_driven_cavity" / "runs" / "audit_real_run.json"
    m.write_text(json.dumps({"timestamp": "../../../../tmp/evil"}), encoding="utf-8")
    with pytest.raises(svc.ReportError, match="invalid timestamp"):
        svc.build_report_context("lid_driven_cavity", "audit_real_run")


def test_rejects_non_matching_timestamp_shape(synthetic_tree) -> None:
    """Timestamp must match exact YYYYMMDDTHHMMSSZ regex."""
    svc = synthetic_tree["svc"]
    root = synthetic_tree["root"]
    m = root / "reports" / "phase5_fields" / "lid_driven_cavity" / "runs" / "audit_real_run.json"
    m.write_text(json.dumps({"timestamp": "2026-04-21"}), encoding="utf-8")
    with pytest.raises(svc.ReportError):
        svc.build_report_context("lid_driven_cavity", "audit_real_run")


def test_rejects_tampered_renders_manifest_output_path(synthetic_tree) -> None:
    """Codex round 1 HIGH: img src in renders manifest must be inside renders root."""
    svc = synthetic_tree["svc"]
    root = synthetic_tree["root"]
    # Overwrite renders manifest with escape path.
    rm = root / "reports" / "phase5_renders" / "lid_driven_cavity" / "runs" / "audit_real_run.json"
    rm.write_text(
        json.dumps({
            "case_id": "lid_driven_cavity", "run_label": "audit_real_run",
            "timestamp": "20260421T000000Z",
            "outputs": {
                "profile_png": "../../../../etc/passwd",
                "pointwise_deviation_png": "/etc/passwd",
                "contour_u_magnitude_png": "reports/phase5_renders/lid_driven_cavity/20260421T000000Z/contour_u_magnitude.png",
                "residuals_png": "reports/phase5_renders/lid_driven_cavity/20260421T000000Z/residuals.png",
            },
        }),
        encoding="utf-8",
    )
    ctx = svc.build_report_context("lid_driven_cavity", "audit_real_run")
    # Escaped paths must be scrubbed to empty; the template will skip empty src.
    assert ctx["renders"]["profile_png_rel"] in ("", None) \
        or "etc/passwd" not in ctx["renders"]["profile_png_rel"]
    assert "etc/passwd" not in ctx["renders"]["pointwise_png_rel"]
    # Safe entries retained.
    assert "reports/phase5_renders" in ctx["renders"]["contour_png_rel"]


def test_rejects_non_object_run_manifest(synthetic_tree) -> None:
    """Codex round 2 (7a precedent): non-object JSON must fail closed."""
    svc = synthetic_tree["svc"]
    root = synthetic_tree["root"]
    m = root / "reports" / "phase5_fields" / "lid_driven_cavity" / "runs" / "audit_real_run.json"
    m.write_text(json.dumps(["not", "an", "object"]), encoding="utf-8")
    with pytest.raises(svc.ReportError, match="not an object"):
        svc.build_report_context("lid_driven_cavity", "audit_real_run")


def test_pdf_output_path_contained(synthetic_tree, tmp_path: Path) -> None:
    """Codex round 1 HIGH: caller-supplied output_path must stay under reports/phase5_reports/."""
    svc = synthetic_tree["svc"]
    # Attempt to write PDF outside the reports tree.
    evil = tmp_path / "outside" / "evil.pdf"
    with pytest.raises(svc.ReportError, match="escapes reports_root"):
        svc.render_report_pdf("lid_driven_cavity", "audit_real_run", output_path=evil)
