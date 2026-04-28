"""Smoke tests for ``GET /api/cases/{case_id}/geometry/render`` (M-RENDER-API B.1).

Verifies the glb transcode + cache layer per DEC-V61-095 + spec_v2 §B.1:

  - 200 + valid binary glb (header magic ``b'glTF'``) for all 3
    bundled fixture shapes
  - Cache hit on second call returns byte-equal payload (no re-transcode)
  - Cache invalidation on source-mtime touch rebuilds the glb
  - Atomic write produces no partial-cache file even on concurrent readers
  - 404 for unknown case_id / unsafe case_id / missing case dir
  - 422 for case dir present but no STL on disk
  - Headers: Content-Type model/gltf-binary · Content-Length matches glb size
"""
from __future__ import annotations

import io
import os
import time
from pathlib import Path

import pytest
import trimesh
from fastapi.testclient import TestClient

from ui.backend.main import app
from ui.backend.services.case_scaffold import template_clone
from ui.backend.services.render import GeometryRenderError, build_geometry_glb
from ui.backend.services.render import geometry_glb as geometry_glb_mod
from ui.backend.tests.conftest import box_stl


def _cylinder_stl() -> bytes:
    m = trimesh.creation.cylinder(radius=0.05, height=0.2, sections=24)
    buf = io.BytesIO()
    m.export(buf, file_type="stl")
    return buf.getvalue()


def _airfoil_like_stl() -> bytes:
    m = trimesh.creation.box([0.3, 0.04, 0.05])
    buf = io.BytesIO()
    m.export(buf, file_type="stl")
    return buf.getvalue()


@pytest.fixture
def isolated_imported(tmp_path: Path, monkeypatch):
    """Redirect the IMPORTED_DIR template to tmp_path so cache dirs and
    case dirs both live under tmp_path · auto-cleaned per test."""
    drafts = tmp_path / "user_drafts"
    imported = drafts / "imported"
    imported.mkdir(parents=True)
    monkeypatch.setattr(template_clone, "DRAFTS_DIR", drafts)
    monkeypatch.setattr(template_clone, "IMPORTED_DIR", imported)
    return imported


def _stage_case(imported_root: Path, case_id: str, stl_bytes: bytes) -> Path:
    case_dir = imported_root / case_id
    triSurface = case_dir / "triSurface"
    triSurface.mkdir(parents=True)
    stl_path = triSurface / f"{case_id}.stl"
    stl_path.write_bytes(stl_bytes)
    return stl_path


# ───────── route happy paths ─────────


def test_get_case_geometry_render_returns_glb_for_cube(isolated_imported: Path):
    case_id = "imported_2026-04-28T00-00-00Z_cube0001"
    _stage_case(isolated_imported, case_id, box_stl())

    client = TestClient(app)
    response = client.get(f"/api/cases/{case_id}/geometry/render")

    assert response.status_code == 200
    assert response.content[:4] == b"glTF"
    assert response.headers["content-type"].startswith("model/gltf-binary")
    assert int(response.headers["content-length"]) == len(response.content)


@pytest.mark.parametrize(
    "fixture_label, stl_factory",
    [
        ("ldc_box", box_stl),
        ("cylinder", _cylinder_stl),
        ("naca0012_like", _airfoil_like_stl),
    ],
)
def test_get_case_geometry_render_serves_three_bundled_fixture_shapes(
    isolated_imported: Path, fixture_label: str, stl_factory
):
    case_id = f"imported_2026-04-28T00-00-00Z_{fixture_label}"
    _stage_case(isolated_imported, case_id, stl_factory())

    client = TestClient(app)
    response = client.get(f"/api/cases/{case_id}/geometry/render")
    assert response.status_code == 200, fixture_label
    assert response.content[:4] == b"glTF"
    assert len(response.content) > 0


# ───────── cache contract ─────────


def test_cache_hit_returns_byte_equal_payload(isolated_imported: Path):
    case_id = "imported_2026-04-28T00-00-00Z_cachehit"
    _stage_case(isolated_imported, case_id, box_stl())

    client = TestClient(app)
    first = client.get(f"/api/cases/{case_id}/geometry/render")
    second = client.get(f"/api/cases/{case_id}/geometry/render")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.content == second.content


def test_build_geometry_glb_status_progression(isolated_imported: Path):
    """Service-layer test for the cache-status discriminator. The route
    doesn't expose status, but the contract is the unit-test target."""
    case_id = "imported_2026-04-28T00-00-00Z_status"
    _stage_case(isolated_imported, case_id, box_stl())

    first = build_geometry_glb(case_id)
    assert first.status == "miss"
    assert first.cache_path.exists()

    second = build_geometry_glb(case_id)
    assert second.status == "hit"
    assert second.cache_path == first.cache_path


def test_cache_invalidates_on_source_mtime_change(isolated_imported: Path):
    case_id = "imported_2026-04-28T00-00-00Z_invalidate"
    stl_path = _stage_case(isolated_imported, case_id, box_stl())

    first = build_geometry_glb(case_id)
    assert first.status == "miss"
    first_glb_bytes = first.cache_path.read_bytes()
    original_cache_mtime = first.cache_path.stat().st_mtime

    # Replace the source STL with a different shape and bump its mtime
    # past the cache mtime so invalidation fires.
    new_stl = _cylinder_stl()
    stl_path.write_bytes(new_stl)
    bumped_mtime = original_cache_mtime + 5.0
    os.utime(stl_path, (bumped_mtime, bumped_mtime))

    second = build_geometry_glb(case_id)
    assert second.status == "rebuild"
    assert second.cache_path.read_bytes() != first_glb_bytes


def test_atomic_write_leaves_no_tempfile_on_success(isolated_imported: Path):
    """After a successful build the cache dir holds only ``geometry.glb`` —
    the ``.tmp.<hex>`` temp name from atomic-rename should be gone."""
    case_id = "imported_2026-04-28T00-00-00Z_atomic"
    _stage_case(isolated_imported, case_id, box_stl())

    build_geometry_glb(case_id)
    cache_dir = isolated_imported / case_id / ".render_cache"
    children = sorted(p.name for p in cache_dir.iterdir())
    assert children == ["geometry.glb"]


# ───────── failure paths ─────────


def test_get_case_geometry_render_404_for_unknown_case(isolated_imported: Path):
    client = TestClient(app)
    response = client.get("/api/cases/imported_unknown_case/geometry/render")
    assert response.status_code == 404


def test_get_case_geometry_render_404_for_unsafe_case_id():
    client = TestClient(app)
    response = client.get("/api/cases/bad@@id/geometry/render")
    assert response.status_code == 404


def test_get_case_geometry_render_422_when_no_stl(isolated_imported: Path):
    case_id = "imported_2026-04-28T00-00-00Z_nostl"
    (isolated_imported / case_id / "triSurface").mkdir(parents=True)

    client = TestClient(app)
    response = client.get(f"/api/cases/{case_id}/geometry/render")
    assert response.status_code == 422


def test_build_geometry_glb_raises_transcode_error_on_garbage(
    isolated_imported: Path, monkeypatch
):
    """Force the transcode path to fail to verify the
    ``transcode_error`` failing_check is reachable."""
    case_id = "imported_2026-04-28T00-00-00Z_garbage"
    _stage_case(isolated_imported, case_id, box_stl())

    def _explode(*args, **kwargs):
        raise RuntimeError("synthetic trimesh failure for test")

    monkeypatch.setattr(geometry_glb_mod.trimesh, "load", _explode)

    with pytest.raises(GeometryRenderError) as excinfo:
        build_geometry_glb(case_id)
    assert excinfo.value.failing_check == "transcode_error"


# ───────── case-insensitive STL match preserved (Codex M-VIZ R1 #1 behavior) ─────────


def test_get_case_geometry_render_matches_uppercase_stl(isolated_imported: Path):
    case_id = "imported_2026-04-28T00-00-00Z_upper"
    case_dir = isolated_imported / case_id
    triSurface = case_dir / "triSurface"
    triSurface.mkdir(parents=True)
    (triSurface / f"{case_id}.STL").write_bytes(box_stl())

    client = TestClient(app)
    response = client.get(f"/api/cases/{case_id}/geometry/render")
    assert response.status_code == 200
    assert response.content[:4] == b"glTF"
