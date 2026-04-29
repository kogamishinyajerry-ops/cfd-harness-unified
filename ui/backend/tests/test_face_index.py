"""Tests for the face-index service + GET /face-index route.

DEC-V61-098 spec_v2 §A6. Verifies the cell-id → face_id mapping
emitted by the backend matches what the frontend pickMode expects:

- Primitive ordering matches bc_glb._build_bc_glb_bytes (lid first,
  then fixedWalls, then alphabetical) so the glTF primitive index in
  vtk.js maps directly to ``primitives[i]``.
- Each ``face_ids[j]`` is the stable face_id for the j-th triangle
  within that primitive (after fan-triangulation).
- All triangles of the same polyMesh face share the same face_id
  (a quad → 2 triangles → 2 identical entries).
- 422 / 404 surface on the same failure paths as bc_glb.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ui.backend.main import app
from ui.backend.services.case_annotations import face_id as compute_face_id
from ui.backend.services.case_scaffold import template_clone
from ui.backend.services.render.face_index import build_face_index


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


# ───────── service ─────────


def test_build_face_index_orders_lid_first(isolated_imported: Path):
    case_id = "imported_2026-04-29T00-00-00Z_face_index"
    case_dir = isolated_imported / case_id
    case_dir.mkdir()
    _stage_polymesh(case_dir)

    out = build_face_index(case_dir)
    assert out["case_id"] == case_id
    primitive_names = [p["patch_name"] for p in out["primitives"]]
    # Same ordering as bc_glb: lid → fixedWalls → alphabetical rest.
    assert primitive_names == ["lid", "fixedWalls", "frontAndBack"]


def test_build_face_index_quad_face_emits_two_identical_face_ids(
    isolated_imported: Path,
):
    case_id = "imported_2026-04-29T00-00-00Z_quad"
    case_dir = isolated_imported / case_id
    case_dir.mkdir()
    _stage_polymesh(case_dir)

    out = build_face_index(case_dir)
    # lid is a single quad → fan-triangulates to 2 triangles, both
    # carrying the same face_id.
    lid = next(p for p in out["primitives"] if p["patch_name"] == "lid")
    assert len(lid["face_ids"]) == 2
    assert lid["face_ids"][0] == lid["face_ids"][1]
    assert lid["face_ids"][0].startswith("fid_")


def test_build_face_index_face_id_matches_compute_face_id(
    isolated_imported: Path,
):
    """The face_id emitted for a triangle must equal compute_face_id()
    on the polyMesh face's vertex coordinates — that's the contract
    the frontend depends on (so when the engineer names a face via
    the AnnotationPanel and PUTs the same face_id, the route can
    locate it in face_annotations.yaml).
    """
    case_id = "imported_2026-04-29T00-00-00Z_id_parity"
    case_dir = isolated_imported / case_id
    case_dir.mkdir()
    _stage_polymesh(case_dir)

    out = build_face_index(case_dir)
    lid = next(p for p in out["primitives"] if p["patch_name"] == "lid")
    # The lid in the boundary file is faces[1] (startFace=1, nFaces=1),
    # which is "4(4 5 6 7)" — the z=1 quad.
    expected_fid = compute_face_id(
        [(0.0, 0.0, 1.0), (1.0, 0.0, 1.0), (1.0, 1.0, 1.0), (0.0, 1.0, 1.0)]
    )
    assert lid["face_ids"][0] == expected_fid


def test_build_face_index_fixedwalls_three_quads_six_triangles(
    isolated_imported: Path,
):
    case_id = "imported_2026-04-29T00-00-00Z_walls"
    case_dir = isolated_imported / case_id
    case_dir.mkdir()
    _stage_polymesh(case_dir)

    out = build_face_index(case_dir)
    walls = next(p for p in out["primitives"] if p["patch_name"] == "fixedWalls")
    # 3 quad faces × 2 triangles each = 6 triangles
    assert len(walls["face_ids"]) == 6
    # Triangles 0,1 share fid; 2,3 share another; 4,5 share a third.
    assert walls["face_ids"][0] == walls["face_ids"][1]
    assert walls["face_ids"][2] == walls["face_ids"][3]
    assert walls["face_ids"][4] == walls["face_ids"][5]
    # All three face_ids are distinct (different quads).
    assert len(set(walls["face_ids"])) == 3


def test_build_face_index_raises_on_missing_polymesh(tmp_path: Path):
    from ui.backend.services.render import BcRenderError

    case_dir = tmp_path / "no_polymesh"
    case_dir.mkdir()
    with pytest.raises(BcRenderError) as exc:
        build_face_index(case_dir)
    assert exc.value.failing_check == "no_polymesh"


# ───────── route ─────────


def test_route_returns_200_for_valid_case(isolated_imported: Path, monkeypatch):
    monkeypatch.setattr(
        "ui.backend.routes.case_annotations.IMPORTED_DIR", isolated_imported
    )
    case_id = "imported_2026-04-29T00-00-00Z_route"
    case_dir = isolated_imported / case_id
    case_dir.mkdir()
    _stage_polymesh(case_dir)

    client = TestClient(app)
    res = client.get(f"/api/cases/{case_id}/face-index")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["case_id"] == case_id
    assert [p["patch_name"] for p in body["primitives"]] == [
        "lid", "fixedWalls", "frontAndBack",
    ]


def test_route_returns_404_when_case_missing(isolated_imported: Path, monkeypatch):
    monkeypatch.setattr(
        "ui.backend.routes.case_annotations.IMPORTED_DIR", isolated_imported
    )
    client = TestClient(app)
    res = client.get("/api/cases/imported_does_not_exist/face-index")
    assert res.status_code == 404


def test_route_returns_404_when_polymesh_missing(
    isolated_imported: Path, monkeypatch
):
    monkeypatch.setattr(
        "ui.backend.routes.case_annotations.IMPORTED_DIR", isolated_imported
    )
    case_id = "imported_2026-04-29T00-00-00Z_nopoly"
    case_dir = isolated_imported / case_id
    case_dir.mkdir()
    # No polyMesh staged.

    client = TestClient(app)
    res = client.get(f"/api/cases/{case_id}/face-index")
    assert res.status_code == 404
    assert res.json()["detail"]["failing_check"] == "no_polymesh"


def test_route_rejects_unsafe_case_id(monkeypatch):
    client = TestClient(app)
    res = client.get("/api/cases/..%2F..%2Fetc/face-index")
    # FastAPI normalizes the path; any unsafe form should hit 400.
    # If FastAPI strips it before our handler, accept either 400 or 404.
    assert res.status_code in (400, 404)
