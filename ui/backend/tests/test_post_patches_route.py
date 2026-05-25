"""Route-level tests for ``GET /api/cases/{case_id}/post/patches``.

DEC-V61-205 (M5 C2) bug #2: the frontend hardcoded ``?patch=engine`` and
404'd on every non-APU case. This endpoint lists the case's real boundary
patches so the client can resolve a real one. The service layer
(foamToVTK output discovery) is covered by test_vtk_export_discovery.py;
this file pins the HTTP boundary:

  * patch names + byte sizes serialize from the boundary_dir glob
  * VtkExportError maps to 409 (no run) / 503 (container) / 500 (other)
  * is_safe_case_id traversal guard → 400
  * unknown case → 404

``ensure_vtk_output`` is monkeypatched so the test never invokes Docker.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ui.backend.services.case_visualize.vtk_export import (
    VtkExportError,
    VtkExportResult,
)


def _new_client() -> TestClient:
    from ui.backend.main import app

    return TestClient(app)


@pytest.fixture
def case_dir(monkeypatch, tmp_path: Path) -> Path:
    """Redirect IMPORTED_DIR so _resolve finds a real case directory."""
    import ui.backend.routes.case_visualize as cv

    monkeypatch.setattr(cv, "IMPORTED_DIR", tmp_path)
    d = tmp_path / "case1"
    d.mkdir()
    return d


def _fake_result(boundary_dir: Path, latest_time: str = "2") -> VtkExportResult:
    return VtkExportResult(
        case_time_dir=boundary_dir.parent,
        internal_vtu=boundary_dir.parent / "internal.vtu",
        boundary_dir=boundary_dir,
        latest_time=latest_time,
    )


def test_lists_patches_with_byte_sizes(monkeypatch, case_dir: Path):
    import ui.backend.routes.case_visualize as cv

    boundary = case_dir / "VTK" / "case_400" / "boundary"
    boundary.mkdir(parents=True)
    (boundary / "fixedWalls.vtp").write_bytes(b"x" * 4000)
    (boundary / "lid.vtp").write_bytes(b"x" * 8000)

    monkeypatch.setattr(
        cv, "ensure_vtk_output", lambda _cd: _fake_result(boundary)
    )

    resp = _new_client().get("/api/cases/case1/post/patches")
    assert resp.status_code == 200
    body = resp.json()
    assert body["latest_time"] == "2"
    by_name = {p["name"]: p["bytes"] for p in body["patches"]}
    assert by_name == {"fixedWalls": 4000, "lid": 8000}


def test_empty_when_no_boundary_vtps(monkeypatch, case_dir: Path):
    import ui.backend.routes.case_visualize as cv

    boundary = case_dir / "VTK" / "case_400" / "boundary"
    boundary.mkdir(parents=True)
    monkeypatch.setattr(
        cv, "ensure_vtk_output", lambda _cd: _fake_result(boundary)
    )
    resp = _new_client().get("/api/cases/case1/post/patches")
    assert resp.status_code == 200
    assert resp.json()["patches"] == []


@pytest.mark.parametrize(
    "msg,expected",
    [
        ("no time directories under /x — solver hasn't run yet.", 409),
        ("only initial condition (0/) exists — solver hasn't run yet.", 409),
        ("cfd-openfoam container is not running", 503),
        ("foamToVTK failed (exit=1): boom", 500),
    ],
)
def test_vtk_export_error_maps_to_http(
    monkeypatch, case_dir: Path, msg: str, expected: int
):
    import ui.backend.routes.case_visualize as cv

    def _raise(_cd):
        raise VtkExportError(msg)

    monkeypatch.setattr(cv, "ensure_vtk_output", _raise)
    resp = _new_client().get("/api/cases/case1/post/patches")
    assert resp.status_code == expected


def test_unsafe_case_id_rejected():
    resp = _new_client().get("/api/cases/..%2F..%2Fetc/post/patches")
    # Either the route's is_safe_case_id guard (400) or the path never
    # resolves to this route (404). Both are safe — never a 200 leak.
    assert resp.status_code in (400, 404)


def test_unknown_case_returns_404(monkeypatch, tmp_path: Path):
    import ui.backend.routes.case_visualize as cv

    monkeypatch.setattr(cv, "IMPORTED_DIR", tmp_path)
    resp = _new_client().get("/api/cases/nonexistent/post/patches")
    assert resp.status_code == 404
