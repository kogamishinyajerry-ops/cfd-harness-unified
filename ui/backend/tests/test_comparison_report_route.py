"""Phase 7c — comparison report route tests.

Guards route-level behavior: 200 on valid case/run, 404 on missing, 400 on
traversal attempts. Actual HTML content is covered by unit tests of the
service module.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from ui.backend.main import app

client = TestClient(app)

# These tests run against the real reports/phase5_fields/lid_driven_cavity/
# artifact set which is .gitignored. In CI (no artifacts), they should 404 —
# which is fine, they'll be re-collected on developer machines.


def _has_ldc_artifacts() -> bool:
    from pathlib import Path
    manifest = Path("reports/phase5_fields/lid_driven_cavity/runs/audit_real_run.json")
    return manifest.is_file()


def test_html_200_when_artifacts_present() -> None:
    if not _has_ldc_artifacts():
        return  # skip silently on CI-style clean checkout
    r = client.get("/api/cases/lid_driven_cavity/runs/audit_real_run/comparison-report")
    assert r.status_code == 200, r.text
    body = r.text
    # 8 section markers from the Jinja template.
    for marker in [
        "参考文献",           # §2
        "中心线 profile",      # §3
        "逐点偏差分布",        # §4
        "流场 contour",        # §5
        "残差收敛历史",        # §6
        "网格收敛",            # §7
        "求解器元数据",        # §8
    ]:
        assert marker in body, f"missing section marker: {marker}"
    # Verdict card must be present.
    assert "verdict-card" in body


def test_context_200_when_artifacts_present() -> None:
    if not _has_ldc_artifacts():
        return
    r = client.get(
        "/api/cases/lid_driven_cavity/runs/audit_real_run/comparison-report/context",
    )
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["case_id"] == "lid_driven_cavity"
    assert d["run_label"] == "audit_real_run"
    assert "metrics" in d
    assert d["metrics"]["n_total"] > 0
    assert d["verdict"] in ("PASS", "PARTIAL", "FAIL")


def test_html_404_unknown_case() -> None:
    r = client.get("/api/cases/nonexistent_case/runs/audit_real_run/comparison-report")
    assert r.status_code == 404


def test_html_400_traversal_case_id() -> None:
    r = client.get("/api/cases/..__pwn/runs/audit_real_run/comparison-report")
    assert r.status_code == 400


def test_html_400_traversal_run_label() -> None:
    r = client.get("/api/cases/lid_driven_cavity/runs/..__pwn/comparison-report")
    assert r.status_code == 400


def test_context_400_urlencoded_traversal() -> None:
    r = client.get(
        "/api/cases/%2e%2e__pwn/runs/audit_real_run/comparison-report/context",
    )
    assert r.status_code == 400


# ---------- CI-safe success path (Codex round 2 LOW follow-up) --------------
# Builds a synthetic tree and monkeypatches module globals so CI without
# real OpenFOAM artifacts still exercises the 200 path end-to-end.

import json
from pathlib import Path as _P

import pytest as _pytest


@_pytest.fixture
def _synth_route_tree(tmp_path: _P, monkeypatch):
    case = "lid_driven_cavity"
    ts = "20260421T000000Z"
    fields_root = tmp_path / "reports" / "phase5_fields"
    renders_root = tmp_path / "reports" / "phase5_renders"
    (fields_root / case / ts / "sample" / "1000").mkdir(parents=True)
    (fields_root / case / ts / "sample" / "1000" / "uCenterline.xy").write_text(
        "# y Ux Uy Uz p\n0 0 0 0 0\n0.5 -0.2 0 0 0\n1.0 1.0 0 0 0\n",
        encoding="utf-8",
    )
    (fields_root / case / ts / "residuals.csv").write_text(
        "Time,Ux,Uy,p\n1,1.0,1.0,1.0\n2,0.1,0.1,0.1\n", encoding="utf-8",
    )
    (fields_root / case / "runs").mkdir(parents=True)
    (fields_root / case / "runs" / "audit_real_run.json").write_text(
        json.dumps({"timestamp": ts, "case_id": case, "run_label": "audit_real_run"}),
        encoding="utf-8",
    )
    (renders_root / case / ts).mkdir(parents=True)
    for n in ["profile_u_centerline.png", "pointwise_deviation.png",
              "contour_u_magnitude.png", "residuals.png"]:
        (renders_root / case / ts / n).write_bytes(b"\x89PNG\r\n\x1a\n")
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
    gold = tmp_path / "knowledge" / "gold_standards"
    gold.mkdir(parents=True)
    (gold / "lid_driven_cavity.yaml").write_text(
        "quantity: u_centerline\n"
        "reference_values:\n"
        "  - y: 0.0\n    u: 0.0\n"
        "  - y: 0.5\n    u: -0.20581\n"
        "  - y: 1.0\n    u: 1.0\n"
        "tolerance: 0.05\n"
        "source: Ghia 1982\n"
        "literature_doi: 10.1016/0021-9991(82)90058-4\n",
        encoding="utf-8",
    )
    fixtures = tmp_path / "ui" / "backend" / "tests" / "fixtures" / "runs" / case
    fixtures.mkdir(parents=True)
    for m, v in (("mesh_20", -0.055), ("mesh_40", -0.048),
                 ("mesh_80", -0.044), ("mesh_160", -0.042)):
        (fixtures / f"{m}_measurement.yaml").write_text(
            f"measurement:\n  value: {v}\n", encoding="utf-8",
        )
    from ui.backend.services import comparison_report as svc
    monkeypatch.setattr(svc, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(svc, "_FIELDS_ROOT", fields_root)
    monkeypatch.setattr(svc, "_RENDERS_ROOT", renders_root)
    monkeypatch.setattr(svc, "_GOLD_ROOT", gold)
    monkeypatch.setattr(svc, "_FIXTURE_ROOT",
                        tmp_path / "ui" / "backend" / "tests" / "fixtures" / "runs")
    yield tmp_path


def test_html_200_end_to_end_synthetic(_synth_route_tree) -> None:
    """CI-safe: route → service → template with monkeypatched roots."""
    r = client.get(
        "/api/cases/lid_driven_cavity/runs/audit_real_run/comparison-report",
    )
    assert r.status_code == 200, r.text
    # Verify all 8 sections rendered.
    for marker in ["参考文献", "中心线 profile", "逐点偏差分布",
                   "流场 contour", "残差收敛历史", "网格收敛",
                   "求解器元数据"]:
        assert marker in r.text, marker


def test_context_json_end_to_end_synthetic(_synth_route_tree) -> None:
    r = client.get(
        "/api/cases/lid_driven_cavity/runs/audit_real_run/comparison-report/context",
    )
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["case_id"] == "lid_driven_cavity"
    assert d["timestamp"] == "20260421T000000Z"
    assert d["metrics"]["n_total"] == 3


def test_pdf_get_returns_503_on_oserror(_synth_route_tree, monkeypatch) -> None:
    """Codex round 3: GET .../comparison-report.pdf must map OSError → 503."""
    from ui.backend.routes import comparison_report as route_mod

    def _raise_oserror(*a, **kw):
        raise OSError("libpango missing (synthetic)")

    monkeypatch.setattr(route_mod, "render_report_pdf", _raise_oserror)
    r = client.get(
        "/api/cases/lid_driven_cavity/runs/audit_real_run/comparison-report.pdf",
    )
    assert r.status_code == 503, r.text
    assert "WeasyPrint unavailable" in r.json().get("detail", "")


def test_pdf_build_post_returns_503_on_oserror(_synth_route_tree, monkeypatch) -> None:
    """Codex round 3 MED follow-up: POST .../comparison-report/build must ALSO
    map OSError → 503. Previously it returned 500 on native lib load failure."""
    from ui.backend.routes import comparison_report as route_mod

    def _raise_oserror(*a, **kw):
        raise OSError("libpango missing (synthetic)")

    monkeypatch.setattr(route_mod, "render_report_pdf", _raise_oserror)
    r = client.post(
        "/api/cases/lid_driven_cavity/runs/audit_real_run/comparison-report/build",
    )
    assert r.status_code == 503, r.text
    assert "WeasyPrint unavailable" in r.json().get("detail", "")
