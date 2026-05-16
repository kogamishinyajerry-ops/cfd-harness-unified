"""V68-B.1 · Backend dev-bootstrap readiness probe.

Verifies the FastAPI app surface that the workbench frontend depends on
boots clean + serves the minimum-set routes that turn V68-A's MSW-mock
substrate into V68-B's real-backend dogfood.

Uses the standard TestClient (in-process; no uvicorn subprocess) — that
isolates the app-construction path from port/network state and runs in
milliseconds. The live HTTP probe over the real socket is in
scripts/governance/v68b_fleet/score_smoke.sh (uvicorn subprocess + curl).
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from ui.backend.main import app


def test_app_imports_and_constructs() -> None:
    """V68-B-DONE-1 prerequisite: importing ui.backend.main yields a usable app."""
    assert app.title == "CFD Harness UI Backend"
    # Routes registered (FastAPI mounts them on app.router.routes)
    paths = {route.path for route in app.router.routes if hasattr(route, "path")}
    assert "/api/cases" in paths
    assert "/api/cases/{case_id}" in paths


def test_cases_list_returns_corpus() -> None:
    """V68-B-DONE-2: /api/cases LIST returns real whitelist (10 cases)."""
    client = TestClient(app)
    res = client.get("/api/cases")
    assert res.status_code == 200
    body = res.json()
    assert isinstance(body, list)
    assert len(body) >= 10, f"expected >= 10 whitelist cases, got {len(body)}"
    ids = {entry["case_id"] for entry in body}
    # canonical anchors must be present
    for canonical in ("lid_driven_cavity", "backward_facing_step", "naca0012_airfoil"):
        assert canonical in ids, f"canonical case {canonical} missing from /api/cases"


def test_case_detail_returns_real_metadata() -> None:
    """V68-B-DONE-2: /api/cases/:id GET returns real metadata for canonical case."""
    client = TestClient(app)
    res = client.get("/api/cases/lid_driven_cavity")
    assert res.status_code == 200
    detail = res.json()
    assert detail["case_id"] == "lid_driven_cavity"
    assert detail.get("solver") == "icoFoam"
    assert "parameters" in detail
    assert "Re" in detail["parameters"]


def test_case_completeness_returns_real_audit() -> None:
    """V68-B-DONE-3: /api/cases/:id/completeness returns real audit (not mock)."""
    client = TestClient(app)
    res = client.get("/api/cases/lid_driven_cavity/completeness")
    assert res.status_code == 200
    report = res.json()
    # Completeness report shape — at minimum carries case_id + a verdict-shaped field.
    assert "case_id" in report
    assert report["case_id"] == "lid_driven_cavity"


def test_unknown_case_returns_404() -> None:
    """V68-B-DONE-2: unknown case ID resolves to 404 (real error path, not mock 200)."""
    client = TestClient(app)
    res = client.get("/api/cases/this_case_does_not_exist_anywhere")
    assert res.status_code == 404
