"""DEC-V61-122 · GET /api/cases/{case_id}/mesh-quality route tests."""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ui.backend.routes import mesh_quality as mesh_quality_route


def _make_app(tmp_path: Path, monkeypatch) -> FastAPI:
    monkeypatch.setattr(mesh_quality_route, "IMPORTED_DIR", tmp_path)
    app = FastAPI()
    app.include_router(mesh_quality_route.router, prefix="/api")
    return app


def _write_complete_polymesh(case_dir: Path) -> None:
    """Build a minimal, parse-clean polyMesh — same shape as
    test_mesh_quality.py's helper but condensed."""
    polymesh = case_dir / "constant" / "polyMesh"
    polymesh.mkdir(parents=True, exist_ok=True)
    points = [
        (0.0, 0.0, 0.0),
        (1.0, 0.0, 0.0),
        (0.0, 1.0, 0.0),
        (1.0, 1.0, 0.0),
        (0.0, 0.0, 1.0),
        (1.0, 0.0, 1.0),
        (0.0, 1.0, 1.0),
        (1.0, 1.0, 1.0),
    ]
    pts_body = "\n".join(f"({x} {y} {z})" for x, y, z in points)
    (polymesh / "points").write_text(
        f"FoamFile{{}}\n{len(points)}\n(\n{pts_body}\n)\n"
    )
    cells = 8
    n_faces = cells * 6
    (polymesh / "owner").write_text(
        f"FoamFile{{}}\n{n_faces}\n(\n"
        + "\n".join(str(i % cells) for i in range(n_faces))
        + "\n)\n"
    )
    n_internal = cells * 3
    (polymesh / "neighbour").write_text(
        f"FoamFile{{}}\n{n_internal}\n(\n"
        + "\n".join(str(i % cells) for i in range(n_internal))
        + "\n)\n"
    )
    (polymesh / "boundary").write_text(
        "FoamFile{}\n2\n(\n"
        "    walls\n    {\n        type            patch;\n"
        f"        nFaces          {n_faces - n_internal};\n"
        f"        startFace       {n_internal};\n    }}\n"
        "    inlet\n    {\n        type            patch;\n"
        "        nFaces          0;\n        startFace       0;\n    }\n"
        ")\n"
    )


def test_route_200_with_report(tmp_path, monkeypatch):
    case_dir = tmp_path / "ldc"
    case_dir.mkdir()
    _write_complete_polymesh(case_dir)
    app = _make_app(tmp_path, monkeypatch)
    with TestClient(app) as client:
        resp = client.get("/api/cases/ldc/mesh-quality")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["case_id"] == "ldc"
        assert body["polymesh_present"] is True
        assert body["cell_count"] == 8
        assert body["point_count"] == 8
        assert "walls" in body["patch_face_counts"]
        # Zero-faces patch triggers a warning.
        codes = [w["code"] for w in body["warnings"]]
        assert "patch_zero_faces" in codes


def test_route_404_when_case_dir_missing(tmp_path, monkeypatch):
    app = _make_app(tmp_path, monkeypatch)
    with TestClient(app) as client:
        resp = client.get("/api/cases/missing/mesh-quality")
        assert resp.status_code == 404
        assert resp.json()["detail"]["failing_check"] == "case_not_found"


def test_route_404_when_polymesh_missing(tmp_path, monkeypatch):
    case_dir = tmp_path / "fresh"
    case_dir.mkdir()
    app = _make_app(tmp_path, monkeypatch)
    with TestClient(app) as client:
        resp = client.get("/api/cases/fresh/mesh-quality")
        assert resp.status_code == 404
        assert resp.json()["detail"]["failing_check"] == "polymesh_not_ready"


def test_route_400_on_bad_case_id(tmp_path, monkeypatch):
    app = _make_app(tmp_path, monkeypatch)
    with TestClient(app) as client:
        resp = client.get("/api/cases/..%2Fetc%2Fpasswd/mesh-quality")
        # FastAPI may decode the percent-escapes; either 400 or 404
        # is acceptable but the bad_case_id branch must not crash.
        assert resp.status_code in (400, 404)


def test_route_500_on_corrupt_polymesh(tmp_path, monkeypatch):
    case_dir = tmp_path / "broken"
    case_dir.mkdir()
    polymesh = case_dir / "constant" / "polyMesh"
    polymesh.mkdir(parents=True)
    # Provide a points file that's a valid parens-list but
    # declares a count that doesn't match the body, triggering
    # MeshQualityParseError(failing_check="points_count_mismatch").
    (polymesh / "points").write_text(
        "FoamFile{}\n999\n(\n(0.0 0.0 0.0)\n)\n"
    )
    (polymesh / "owner").write_text("FoamFile{}\n0\n(\n)\n")
    (polymesh / "boundary").write_text("FoamFile{}\n0\n(\n)\n")
    app = _make_app(tmp_path, monkeypatch)
    with TestClient(app) as client:
        resp = client.get("/api/cases/broken/mesh-quality")
        assert resp.status_code == 500
        assert resp.json()["detail"]["failing_check"] == "points_count_mismatch"
