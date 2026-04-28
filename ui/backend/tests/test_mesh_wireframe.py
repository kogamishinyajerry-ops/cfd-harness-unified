"""Tests for /api/cases/{id}/mesh/render + the polyMesh parser
(M-RENDER-API B.2 · DEC-V61-095 spec_v2 §B.2).

A unit-cube polyMesh has 8 points, 6 quad faces, and 12 unique edges;
that's the canonical fixture used across the parser, edge extractor,
glTF builder, and the route.
"""
from __future__ import annotations

import os
import struct
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from ui.backend.main import app
from ui.backend.services.case_scaffold import template_clone
from ui.backend.services.render import (
    MeshRenderError,
    build_mesh_wireframe_glb,
)
from ui.backend.services.render import mesh_wireframe as mesh_wireframe_mod
from ui.backend.services.render.gltf_lines_builder import build_lines_glb
from ui.backend.services.render.polymesh_parser import (
    PolyMeshParseError,
    extract_unique_edges,
    parse_faces,
    parse_points,
    validate_face_indices,
)


# ───────── unit-cube polyMesh fixture (8 points · 6 quad faces) ─────────

_POINTS_TEXT = """\
FoamFile
{
    version     2.0;
    format      ascii;
    class       vectorField;
    location    "constant/polyMesh";
    object      points;
}

8
(
(0 0 0)
(1 0 0)
(1 1 0)
(0 1 0)
(0 0 1)
(1 0 1)
(1 1 1)
(0 1 1)
)
"""

_FACES_TEXT = """\
FoamFile
{
    version     2.0;
    format      ascii;
    class       faceList;
    location    "constant/polyMesh";
    object      faces;
}

6
(
4(0 1 2 3)
4(4 5 6 7)
4(0 1 5 4)
4(2 3 7 6)
4(1 2 6 5)
4(0 3 7 4)
)
"""


def _stage_polymesh(case_dir: Path) -> tuple[Path, Path]:
    polymesh = case_dir / "constant" / "polyMesh"
    polymesh.mkdir(parents=True)
    points = polymesh / "points"
    faces = polymesh / "faces"
    points.write_text(_POINTS_TEXT, encoding="utf-8")
    faces.write_text(_FACES_TEXT, encoding="utf-8")
    return points, faces


@pytest.fixture
def isolated_imported(tmp_path: Path, monkeypatch):
    drafts = tmp_path / "user_drafts"
    imported = drafts / "imported"
    imported.mkdir(parents=True)
    monkeypatch.setattr(template_clone, "DRAFTS_DIR", drafts)
    monkeypatch.setattr(template_clone, "IMPORTED_DIR", imported)
    return imported


# ───────── parser ─────────


def test_parse_points_returns_eight_cube_vertices(tmp_path: Path):
    points_path = tmp_path / "points"
    points_path.write_text(_POINTS_TEXT, encoding="utf-8")
    pts = parse_points(points_path)
    assert pts.shape == (8, 3)
    assert pts.dtype == np.float64
    np.testing.assert_array_equal(pts[0], [0, 0, 0])
    np.testing.assert_array_equal(pts[6], [1, 1, 1])


def test_parse_faces_returns_six_quad_faces(tmp_path: Path):
    faces_path = tmp_path / "faces"
    faces_path.write_text(_FACES_TEXT, encoding="utf-8")
    faces = parse_faces(faces_path)
    assert len(faces) == 6
    assert all(len(f) == 4 for f in faces)
    assert faces[0] == [0, 1, 2, 3]


def test_parse_faces_rejects_count_mismatch(tmp_path: Path):
    faces_path = tmp_path / "faces"
    faces_path.write_text("1\n(\n4(0 1 2)\n)\n", encoding="utf-8")
    with pytest.raises(PolyMeshParseError, match="did not match"):
        parse_faces(faces_path)


def test_validate_face_indices_passes_for_in_range_faces():
    """Round-2 Finding 4: faces with vertex IDs ∈ [0, n_points) accepted."""
    faces = [[0, 1, 2, 3], [4, 5, 6, 7]]
    validate_face_indices(faces, n_points=8)  # no raise


def test_validate_face_indices_rejects_out_of_range_vertex():
    """Round-2 Finding 4: a vertex ID >= n_points must raise rather than
    flow through to the GLB indices accessor."""
    faces = [[0, 1, 2, 3], [4, 5, 6, 999]]
    with pytest.raises(PolyMeshParseError, match="vertex 999"):
        validate_face_indices(faces, n_points=8)


def test_validate_face_indices_rejects_negative_vertex():
    """Negative IDs are rejected even though the regex never produces them
    — defensive guard for parser extensions."""
    faces = [[0, 1, -1, 3]]
    with pytest.raises(PolyMeshParseError, match=r"vertex -1"):
        validate_face_indices(faces, n_points=8)


def test_build_mesh_wireframe_422_on_face_index_out_of_range(
    isolated_imported: Path,
):
    """End-to-end: a polyMesh whose faces reference vertex IDs past
    n_points - 1 must surface as a polymesh_parse_error, not a 200
    with a malformed GLB."""
    case_id = "imported_2026-04-28T00-00-00Z_oob_face"
    case_dir = isolated_imported / case_id
    case_dir.mkdir()
    polymesh = case_dir / "constant" / "polyMesh"
    polymesh.mkdir(parents=True)
    # 4 points but a face that references vertex 999.
    (polymesh / "points").write_text(
        "FoamFile{}\n4\n((0 0 0)(1 0 0)(0 1 0)(0 0 1))\n",
        encoding="utf-8",
    )
    (polymesh / "faces").write_text(
        "FoamFile{}\n1\n(\n4(0 1 2 999)\n)\n",
        encoding="utf-8",
    )
    with pytest.raises(MeshRenderError) as excinfo:
        build_mesh_wireframe_glb(case_id)
    assert excinfo.value.failing_check == "polymesh_parse_error"
    assert "vertex 999" in excinfo.value.message


def test_build_mesh_wireframe_rejects_polymesh_symlink_escape(
    isolated_imported: Path, tmp_path: Path,
):
    """Round-2 Finding 1: a symlink at constant/polyMesh/points pointing
    outside the case dir must be rejected by the resolve+relative_to
    containment guard."""
    case_id = "imported_2026-04-28T00-00-00Z_polymesh_symlink"
    case_dir = isolated_imported / case_id
    case_dir.mkdir()
    polymesh = case_dir / "constant" / "polyMesh"
    polymesh.mkdir(parents=True)
    outside_points = tmp_path / "evil_points"
    outside_points.write_text("not foam points", encoding="utf-8")
    (polymesh / "points").symlink_to(outside_points)
    (polymesh / "faces").write_text(
        "FoamFile{}\n1\n(\n3(0 1 2)\n)\n",
        encoding="utf-8",
    )

    with pytest.raises(MeshRenderError) as excinfo:
        build_mesh_wireframe_glb(case_id)
    assert excinfo.value.failing_check == "no_polymesh"


def test_parse_points_rejects_empty(tmp_path: Path):
    points_path = tmp_path / "points"
    points_path.write_text("FoamFile{}\n0\n(\n)\n", encoding="utf-8")
    with pytest.raises(PolyMeshParseError, match="no point entries"):
        parse_points(points_path)


# ───────── edge extraction ─────────


def test_extract_unique_edges_cube_has_12():
    """A cube has exactly 12 edges; per-face quads contribute 24 directed
    edges that dedupe to 12 unique sorted-pair entries."""
    faces = [
        [0, 1, 2, 3],   # bottom
        [4, 5, 6, 7],   # top
        [0, 1, 5, 4],
        [2, 3, 7, 6],
        [1, 2, 6, 5],
        [0, 3, 7, 4],
    ]
    edges = extract_unique_edges(faces)
    assert edges.shape == (12, 2)
    assert edges.dtype == np.uint32
    # All edges should be sorted with a < b
    assert np.all(edges[:, 0] < edges[:, 1])
    # Sample a known edge
    assert any((row == [0, 1]).all() for row in edges)
    assert any((row == [6, 7]).all() for row in edges)


def test_extract_unique_edges_dedups_shared_edges():
    """Two faces sharing an edge produce only one entry for that edge."""
    faces = [[0, 1, 2], [0, 2, 3]]   # two triangles sharing edge 0-2
    edges = extract_unique_edges(faces)
    # Triangle 1 contributes (0,1), (1,2), (2,0); triangle 2 contributes
    # (0,2), (2,3), (3,0). Dedup: (0,1), (0,2), (1,2), (2,3), (0,3) → 5.
    assert edges.shape == (5, 2)


# ───────── glTF lines builder ─────────


def test_build_lines_glb_produces_valid_glb_header():
    pts = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], dtype=np.float64)
    edges = np.array([[0, 1], [1, 2], [0, 2]], dtype=np.uint32)
    glb = build_lines_glb(pts, edges)

    assert glb[:4] == b"glTF"
    magic, version, total_len = struct.unpack("<III", glb[:12])
    assert magic == 0x46546C67
    assert version == 2
    assert total_len == len(glb)


def test_build_lines_glb_rejects_empty_inputs():
    with pytest.raises(ValueError):
        build_lines_glb(
            np.zeros((0, 3), dtype=np.float64),
            np.zeros((0, 2), dtype=np.uint32),
        )
    with pytest.raises(ValueError, match=r"\(N, 3\)"):
        build_lines_glb(
            np.zeros((1, 4), dtype=np.float64),
            np.array([[0, 0]], dtype=np.uint32),
        )


# ───────── service layer ─────────


def test_build_mesh_wireframe_glb_status_progression(isolated_imported: Path):
    case_id = "imported_2026-04-28T00-00-00Z_meshhit"
    case_dir = isolated_imported / case_id
    case_dir.mkdir()
    _stage_polymesh(case_dir)

    first = build_mesh_wireframe_glb(case_id)
    assert first.status == "miss"
    assert first.cache_path.exists()

    second = build_mesh_wireframe_glb(case_id)
    assert second.status == "hit"
    assert second.cache_path == first.cache_path


def test_build_mesh_wireframe_glb_invalidates_on_mtime_change(isolated_imported: Path):
    case_id = "imported_2026-04-28T00-00-00Z_meshinval"
    case_dir = isolated_imported / case_id
    case_dir.mkdir()
    points_path, _faces_path = _stage_polymesh(case_dir)

    first = build_mesh_wireframe_glb(case_id)
    cache_mtime = first.cache_path.stat().st_mtime

    bumped = cache_mtime + 5.0
    os.utime(points_path, (bumped, bumped))

    second = build_mesh_wireframe_glb(case_id)
    assert second.status == "rebuild"


def test_build_mesh_wireframe_glb_404_for_unknown_case(isolated_imported: Path):
    with pytest.raises(MeshRenderError) as excinfo:
        build_mesh_wireframe_glb("imported_unknown")
    assert excinfo.value.failing_check == "case_not_found"


def test_build_mesh_wireframe_glb_404_for_unsafe_case_id(isolated_imported: Path):
    with pytest.raises(MeshRenderError) as excinfo:
        build_mesh_wireframe_glb("bad@@id")
    assert excinfo.value.failing_check == "case_not_found"


def test_build_mesh_wireframe_glb_404_when_polymesh_missing(isolated_imported: Path):
    case_id = "imported_2026-04-28T00-00-00Z_nomesh"
    (isolated_imported / case_id).mkdir()

    with pytest.raises(MeshRenderError) as excinfo:
        build_mesh_wireframe_glb(case_id)
    assert excinfo.value.failing_check == "no_polymesh"


def test_build_mesh_wireframe_glb_422_on_polymesh_garbage(isolated_imported: Path):
    case_id = "imported_2026-04-28T00-00-00Z_garbage"
    case_dir = isolated_imported / case_id
    polymesh = case_dir / "constant" / "polyMesh"
    polymesh.mkdir(parents=True)
    (polymesh / "points").write_text("definitely not a polyMesh", encoding="utf-8")
    (polymesh / "faces").write_text("definitely not a faces file", encoding="utf-8")

    with pytest.raises(MeshRenderError) as excinfo:
        build_mesh_wireframe_glb(case_id)
    assert excinfo.value.failing_check == "polymesh_parse_error"


# ───────── route ─────────


def test_get_case_mesh_render_returns_glb_for_cube(isolated_imported: Path):
    case_id = "imported_2026-04-28T00-00-00Z_cubemesh"
    case_dir = isolated_imported / case_id
    case_dir.mkdir()
    _stage_polymesh(case_dir)

    client = TestClient(app)
    response = client.get(f"/api/cases/{case_id}/mesh/render")

    assert response.status_code == 200
    assert response.content[:4] == b"glTF"
    assert response.headers["content-type"].startswith("model/gltf-binary")


def test_get_case_mesh_render_404_for_unknown_case(isolated_imported: Path):
    client = TestClient(app)
    response = client.get("/api/cases/imported_unknown/mesh/render")
    assert response.status_code == 404


def test_get_case_mesh_render_404_when_polymesh_missing(isolated_imported: Path):
    case_id = "imported_2026-04-28T00-00-00Z_nopolymesh"
    (isolated_imported / case_id).mkdir()

    client = TestClient(app)
    response = client.get(f"/api/cases/{case_id}/mesh/render")
    assert response.status_code == 404


def test_get_case_mesh_render_422_on_garbage(isolated_imported: Path):
    case_id = "imported_2026-04-28T00-00-00Z_garbagemesh"
    case_dir = isolated_imported / case_id
    polymesh = case_dir / "constant" / "polyMesh"
    polymesh.mkdir(parents=True)
    (polymesh / "points").write_text("not a polyMesh", encoding="utf-8")
    (polymesh / "faces").write_text("also not a polyMesh", encoding="utf-8")

    client = TestClient(app)
    response = client.get(f"/api/cases/{case_id}/mesh/render")
    assert response.status_code == 422


def test_get_case_mesh_render_byte_equal_on_cache_hit(isolated_imported: Path):
    case_id = "imported_2026-04-28T00-00-00Z_cachebyteequal"
    case_dir = isolated_imported / case_id
    case_dir.mkdir()
    _stage_polymesh(case_dir)

    client = TestClient(app)
    first = client.get(f"/api/cases/{case_id}/mesh/render")
    second = client.get(f"/api/cases/{case_id}/mesh/render")
    assert first.status_code == 200
    assert second.content == first.content


def test_atomic_write_leaves_no_tempfile(isolated_imported: Path):
    case_id = "imported_2026-04-28T00-00-00Z_atomicmesh"
    case_dir = isolated_imported / case_id
    case_dir.mkdir()
    _stage_polymesh(case_dir)

    build_mesh_wireframe_glb(case_id)
    cache_dir = case_dir / ".render_cache"
    children = sorted(p.name for p in cache_dir.iterdir())
    assert children == ["mesh.glb"]
