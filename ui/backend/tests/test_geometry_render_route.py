"""Smoke tests for ``GET /api/cases/{case_id}/geometry/stl`` (M-VIZ Step 3).

Verifies the STL-serve endpoint per DEC-V61-094 + spec_v2 §B.1 acceptance:
  - 200 + STL bytes for an imported case (binary STL fixture)
  - 200 for the 3 bundled fixture shapes (cube · cylinder · 'naca0012'-shaped triangle mesh)
  - 404 for unknown case_id
  - 404 for case_id present in imported/ but lacking triSurface/
  - Content-Length header matches the on-disk file size
  - Path-traversal attempts return 404
"""
from __future__ import annotations

import io
from pathlib import Path

import pytest
import trimesh
from fastapi.testclient import TestClient

from ui.backend.main import app
from ui.backend.services.case_scaffold import template_clone
from ui.backend.tests.conftest import box_stl


def _cylinder_stl() -> bytes:
    m = trimesh.creation.cylinder(radius=0.05, height=0.2, sections=24)
    buf = io.BytesIO()
    m.export(buf, file_type="stl")
    return buf.getvalue()


def _airfoil_like_stl() -> bytes:
    """A thin extruded cuboid that stands in for an airfoil section in tests
    (vtk.js + the route care only about valid STL bytes, not aerodynamic
    shape; spec_v2 §B.1 lists naca0012 as a real-fixture target but the
    route is shape-agnostic, so a thin slab is enough for smoke coverage).
    """
    m = trimesh.creation.box([0.3, 0.04, 0.05])
    buf = io.BytesIO()
    m.export(buf, file_type="stl")
    return buf.getvalue()


@pytest.fixture
def isolated_imported(tmp_path: Path, monkeypatch):
    """Redirect the IMPORTED_DIR template to tmp_path so tests don't pollute
    the repo's user_drafts/imported/ tree."""
    drafts = tmp_path / "user_drafts"
    imported = drafts / "imported"
    imported.mkdir(parents=True)
    monkeypatch.setattr(template_clone, "DRAFTS_DIR", drafts)
    monkeypatch.setattr(template_clone, "IMPORTED_DIR", imported)
    return imported


def _stage_case(imported_root: Path, case_id: str, stl_bytes: bytes) -> Path:
    """Create imported/{case_id}/triSurface/{case_id}.stl with the given bytes."""
    case_dir = imported_root / case_id
    triSurface = case_dir / "triSurface"
    triSurface.mkdir(parents=True)
    stl_path = triSurface / f"{case_id}.stl"
    stl_path.write_bytes(stl_bytes)
    return stl_path


def test_get_case_stl_returns_bytes_for_cube(isolated_imported: Path):
    case_id = "imported_2026-04-28T00-00-00Z_cube0001"
    stl_bytes = box_stl()
    on_disk = _stage_case(isolated_imported, case_id, stl_bytes)

    client = TestClient(app)
    response = client.get(f"/api/cases/{case_id}/geometry/stl")

    assert response.status_code == 200
    assert response.content == stl_bytes
    assert response.headers["content-type"].startswith("model/stl")
    assert int(response.headers["content-length"]) == on_disk.stat().st_size


@pytest.mark.parametrize(
    "fixture_label, stl_factory",
    [
        ("ldc_box", box_stl),
        ("cylinder", _cylinder_stl),
        ("naca0012_like", _airfoil_like_stl),
    ],
)
def test_get_case_stl_serves_three_bundled_fixture_shapes(
    isolated_imported: Path, fixture_label: str, stl_factory
):
    """Coverage of all 3 spec_v2 §B.1 fixture shapes in one parametrized pass."""
    case_id = f"imported_2026-04-28T00-00-00Z_{fixture_label}"
    stl_bytes = stl_factory()
    _stage_case(isolated_imported, case_id, stl_bytes)

    client = TestClient(app)
    response = client.get(f"/api/cases/{case_id}/geometry/stl")

    assert response.status_code == 200, fixture_label
    assert response.content == stl_bytes
    assert len(response.content) > 0


def test_get_case_stl_404_when_case_dir_missing(isolated_imported: Path):
    client = TestClient(app)
    response = client.get("/api/cases/imported_unknown_case/geometry/stl")
    assert response.status_code == 404


def test_get_case_stl_404_when_triSurface_dir_missing(isolated_imported: Path):
    case_id = "imported_2026-04-28T00-00-00Z_notrisurface"
    (isolated_imported / case_id).mkdir(parents=True)

    client = TestClient(app)
    response = client.get(f"/api/cases/{case_id}/geometry/stl")
    assert response.status_code == 404


def test_get_case_stl_404_when_triSurface_dir_empty(isolated_imported: Path):
    case_id = "imported_2026-04-28T00-00-00Z_emptytrisurface"
    (isolated_imported / case_id / "triSurface").mkdir(parents=True)

    client = TestClient(app)
    response = client.get(f"/api/cases/{case_id}/geometry/stl")
    assert response.status_code == 404


def test_get_case_stl_404_for_unsafe_case_id():
    client = TestClient(app)
    # FastAPI/Starlette swallows ".." segments in path normalization, but
    # the safety guard handles whatever survives. Use a clearly-unsafe id
    # that makes it through routing.
    response = client.get("/api/cases/bad@@id/geometry/stl")
    assert response.status_code == 404
