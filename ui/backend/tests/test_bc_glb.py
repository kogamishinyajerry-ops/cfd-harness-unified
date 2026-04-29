"""Tests for /api/cases/{id}/bc/render + the BC-overlay glb builder
(Phase-1A · DEC-V61-097, user feedback 2026-04-29 replacing the static
PNG with an interactive 3D viewport).

Uses the same unit-cube polyMesh fixture as test_mesh_wireframe, plus a
boundary file that splits the 6 cube faces into ``lid`` + ``fixedWalls``
+ ``frontAndBack`` patches — mirroring the post-setup-bc topology the
LDC fixture produces.
"""
from __future__ import annotations

import json
import struct
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ui.backend.main import app
from ui.backend.services.case_scaffold import template_clone
from ui.backend.services.render import BcRenderError, build_bc_render_glb


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

# 6 quad faces of the unit cube. Index 0 = z=0 (bottom), 1 = z=1 (lid),
# 2..5 = side walls. The boundary file references face IDs in this
# layout: lid=face[1], fixedWalls=faces[0,2,3], frontAndBack=faces[4,5].
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

_BOUNDARY_TEXT = """\
FoamFile
{
    version     2.0;
    format      ascii;
    class       polyBoundaryMesh;
    location    "constant/polyMesh";
    object      boundary;
}

3
(
    lid
    {
        type            wall;
        nFaces          1;
        startFace       1;
    }
    fixedWalls
    {
        type            wall;
        nFaces          3;
        startFace       2;
    }
    frontAndBack
    {
        type            empty;
        nFaces          2;
        startFace       4;
    }
)
"""


def _stage_polymesh(case_dir: Path) -> Path:
    polymesh = case_dir / "constant" / "polyMesh"
    polymesh.mkdir(parents=True)
    (polymesh / "points").write_text(_POINTS_TEXT, encoding="utf-8")
    (polymesh / "faces").write_text(_FACES_TEXT, encoding="utf-8")
    (polymesh / "boundary").write_text(_BOUNDARY_TEXT, encoding="utf-8")
    return polymesh


@pytest.fixture
def isolated_imported(tmp_path: Path, monkeypatch):
    drafts = tmp_path / "user_drafts"
    imported = drafts / "imported"
    imported.mkdir(parents=True)
    monkeypatch.setattr(template_clone, "DRAFTS_DIR", drafts)
    monkeypatch.setattr(template_clone, "IMPORTED_DIR", imported)
    return imported


# ───────── glb structural assertions ─────────


def _split_glb(payload: bytes) -> tuple[dict, bytes]:
    """Return the parsed JSON dict + the BIN chunk payload."""
    assert payload[:4] == b"glTF", "missing GLB magic"
    (length,) = struct.unpack("<I", payload[8:12])
    assert length == len(payload), "GLB length mismatch"
    cursor = 12
    json_chunk_len = struct.unpack("<I", payload[cursor:cursor + 4])[0]
    cursor += 8  # 4 bytes length + 4 bytes type
    json_bytes = payload[cursor:cursor + json_chunk_len]
    cursor += json_chunk_len
    bin_chunk_len = struct.unpack("<I", payload[cursor:cursor + 4])[0]
    cursor += 8
    bin_bytes = payload[cursor:cursor + bin_chunk_len]
    return json.loads(json_bytes.decode("ascii")), bin_bytes


def test_build_bc_glb_emits_one_primitive_per_patch(isolated_imported):
    case_dir = isolated_imported / "case_001"
    case_dir.mkdir()
    _stage_polymesh(case_dir)

    result = build_bc_render_glb("case_001")
    assert result.status == "miss"
    assert result.cache_path.exists()

    payload = result.cache_path.read_bytes()
    gltf, _ = _split_glb(payload)

    materials = gltf["materials"]
    primitives = gltf["meshes"][0]["primitives"]
    assert len(primitives) == 3, "lid + fixedWalls + frontAndBack → 3 primitives"
    assert len(materials) == 3
    assert {m["name"] for m in materials} == {"lid", "fixedWalls", "frontAndBack"}

    # Lid is the first primitive (priority sort puts it first so it
    # renders on top of any back-face fragments).
    assert materials[0]["name"] == "lid"
    lid_color = materials[0]["pbrMetallicRoughness"]["baseColorFactor"]
    assert lid_color[0] > lid_color[1] and lid_color[0] > lid_color[2], (
        "lid base color should be red-dominant"
    )

    # Lid has 1 quad → 2 triangles → 6 indices.
    lid_accessor = gltf["accessors"][primitives[0]["indices"]]
    assert lid_accessor["count"] == 6


def test_build_bc_glb_cache_hit_on_second_call(isolated_imported):
    case_dir = isolated_imported / "case_001"
    case_dir.mkdir()
    _stage_polymesh(case_dir)

    first = build_bc_render_glb("case_001")
    assert first.status == "miss"
    second = build_bc_render_glb("case_001")
    assert second.status == "hit"
    assert second.cache_path == first.cache_path


def test_build_bc_glb_404_when_polymesh_missing(isolated_imported):
    case_dir = isolated_imported / "case_001"
    case_dir.mkdir()  # case dir exists but no polyMesh
    with pytest.raises(BcRenderError) as exc:
        build_bc_render_glb("case_001")
    assert exc.value.failing_check == "no_polymesh"


def test_build_bc_glb_409_when_boundary_missing(isolated_imported):
    case_dir = isolated_imported / "case_001"
    case_dir.mkdir()
    polymesh = case_dir / "constant" / "polyMesh"
    polymesh.mkdir(parents=True)
    (polymesh / "points").write_text(_POINTS_TEXT, encoding="utf-8")
    (polymesh / "faces").write_text(_FACES_TEXT, encoding="utf-8")
    # No boundary file → setup-bc hasn't run yet.
    with pytest.raises(BcRenderError) as exc:
        build_bc_render_glb("case_001")
    assert exc.value.failing_check == "no_boundary"


def test_route_returns_glb(isolated_imported):
    case_dir = isolated_imported / "case_001"
    case_dir.mkdir()
    _stage_polymesh(case_dir)

    client = TestClient(app)
    resp = client.get("/api/cases/case_001/bc/render")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "model/gltf-binary"
    assert resp.content[:4] == b"glTF"


def test_route_404_when_case_missing(isolated_imported):
    client = TestClient(app)
    resp = client.get("/api/cases/nonexistent/bc/render")
    assert resp.status_code == 404


def test_route_409_when_pre_setup_bc(isolated_imported):
    case_dir = isolated_imported / "case_001"
    case_dir.mkdir()
    polymesh = case_dir / "constant" / "polyMesh"
    polymesh.mkdir(parents=True)
    (polymesh / "points").write_text(_POINTS_TEXT, encoding="utf-8")
    (polymesh / "faces").write_text(_FACES_TEXT, encoding="utf-8")

    client = TestClient(app)
    resp = client.get("/api/cases/case_001/bc/render")
    assert resp.status_code == 409


# ───────── Codex round-1 follow-up tests ─────────


def test_symlink_escape_rejected(isolated_imported, tmp_path):
    """Codex round-1 MED-3: a symlink at constant/polyMesh/points pointing
    outside the case dir must NOT be followed. The hardened
    _bc_source_files() resolves the symlink and asserts relative_to
    case_root, so this raises BcRenderError(no_polymesh) instead of
    serving an attacker-chosen file.
    """
    case_dir = isolated_imported / "case_001"
    case_dir.mkdir()
    polymesh = case_dir / "constant" / "polyMesh"
    polymesh.mkdir(parents=True)
    # Create a victim file outside the case dir + symlink to it.
    victim = tmp_path / "outside_case.txt"
    victim.write_text(_POINTS_TEXT, encoding="utf-8")
    (polymesh / "points").symlink_to(victim)
    (polymesh / "faces").write_text(_FACES_TEXT, encoding="utf-8")
    (polymesh / "boundary").write_text(_BOUNDARY_TEXT, encoding="utf-8")

    with pytest.raises(BcRenderError) as exc:
        build_bc_render_glb("case_001")
    assert exc.value.failing_check == "no_polymesh"
    assert "outside" in str(exc.value).lower()


def test_malformed_boundary_range_raises_parse_error(isolated_imported):
    """Codex round-1 MED-4: a boundary with startFace + nFaces beyond the
    faces array length used to silently truncate to a partial GLB.
    Now it raises BcRenderError(parse_error) so the route returns 422.
    """
    case_dir = isolated_imported / "case_001"
    case_dir.mkdir()
    polymesh = case_dir / "constant" / "polyMesh"
    polymesh.mkdir(parents=True)
    (polymesh / "points").write_text(_POINTS_TEXT, encoding="utf-8")
    (polymesh / "faces").write_text(_FACES_TEXT, encoding="utf-8")
    # Boundary references face 99 — way past the 6-face fixture.
    bad_boundary = """\
FoamFile
{
    version     2.0;
    format      ascii;
    class       polyBoundaryMesh;
    location    "constant/polyMesh";
    object      boundary;
}

1
(
    bogus
    {
        type            wall;
        nFaces          5;
        startFace       95;
    }
)
"""
    (polymesh / "boundary").write_text(bad_boundary, encoding="utf-8")

    with pytest.raises(BcRenderError) as exc:
        build_bc_render_glb("case_001")
    assert exc.value.failing_check == "parse_error"
    assert "face 95" in str(exc.value) or "faces has length 6" in str(exc.value)


def test_route_422_on_malformed_boundary(isolated_imported):
    """Same defect surfaced through the HTTP route -> 422 parse_error."""
    case_dir = isolated_imported / "case_001"
    case_dir.mkdir()
    polymesh = case_dir / "constant" / "polyMesh"
    polymesh.mkdir(parents=True)
    (polymesh / "points").write_text(_POINTS_TEXT, encoding="utf-8")
    (polymesh / "faces").write_text(_FACES_TEXT, encoding="utf-8")
    (polymesh / "boundary").write_text(
        _BOUNDARY_TEXT.replace("startFace       1;", "startFace       100;"),
        encoding="utf-8",
    )

    client = TestClient(app)
    resp = client.get("/api/cases/case_001/bc/render")
    assert resp.status_code == 422
