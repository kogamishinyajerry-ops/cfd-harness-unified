"""Route tests for ``POST /api/import/{case_id}/mesh`` (M6.0)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from ui.backend.main import app
from ui.backend.services.meshing_gmsh.pipeline import MeshPipelineError


client = TestClient(app)


def test_mesh_route_case_not_found_returns_404():
    response = client.post(
        "/api/import/imported_2099-01-01T00-00-00Z_deadbeef/mesh",
        json={"mesh_mode": "beginner"},
    )
    assert response.status_code == 404
    body = response.json()
    assert body["detail"]["failing_check"] == "case_not_found"


def test_mesh_route_unsafe_case_id_returns_404():
    # Path-traversal attempts are caught by is_safe_case_id; the URL
    # router rejects them as malformed paths long before the handler,
    # so we use a malformed-but-safe id that fails downstream checks.
    response = client.post(
        "/api/import/not_a_real_case_id_xyz/mesh",
        json={"mesh_mode": "beginner"},
    )
    assert response.status_code == 404
    assert response.json()["detail"]["failing_check"] == "case_not_found"


def test_mesh_route_validation_rejects_bogus_mesh_mode():
    response = client.post(
        "/api/import/anything/mesh",
        json={"mesh_mode": "ultra"},
    )
    assert response.status_code == 422


def test_mesh_route_happy_path_returns_summary(tmp_path: Path):
    """Mock the pipeline so we exercise the route → schema conversion
    without depending on gmsh/docker availability in CI."""
    from ui.backend.services.meshing_gmsh.pipeline import MeshResult
    from ui.backend.routes import mesh_imported as route_mod

    fake = MeshResult(
        case_id="imported_TEST_route",
        mesh_mode="beginner",
        cell_count=12_345,
        face_count=4_567,
        point_count=2_345,
        polyMesh_path=tmp_path / "constant" / "polyMesh",
        msh_path=tmp_path / "imported.msh",
        generation_time_s=1.23,
        warning=None,
    )

    with patch.object(route_mod, "mesh_imported_case", return_value=fake):
        response = client.post(
            "/api/import/imported_TEST_route/mesh",
            json={"mesh_mode": "beginner"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["case_id"] == "imported_TEST_route"
    summary = body["mesh_summary"]
    assert summary["cell_count"] == 12_345
    assert summary["face_count"] == 4_567
    assert summary["point_count"] == 2_345
    assert summary["mesh_mode_used"] == "beginner"
    assert summary["warning"] is None


def test_mesh_route_cell_cap_exceeded_returns_422():
    from ui.backend.routes import mesh_imported as route_mod

    err = MeshPipelineError(
        "mesh has 60,000,000 cells — exceeds the 50,000,000-cell hard cap",
        "cell_cap_exceeded",
    )
    with patch.object(route_mod, "mesh_imported_case", side_effect=err):
        response = client.post(
            "/api/import/imported_TEST_overcap/mesh",
            json={"mesh_mode": "power"},
        )

    assert response.status_code == 422
    assert response.json()["detail"]["failing_check"] == "cell_cap_exceeded"


def test_mesh_route_gmsh_diverged_surfaces_failing_check():
    from ui.backend.routes import mesh_imported as route_mod

    err = MeshPipelineError("zero tetrahedra produced", "gmsh_diverged")
    with patch.object(route_mod, "mesh_imported_case", side_effect=err):
        response = client.post(
            "/api/import/imported_TEST_diverge/mesh",
            json={"mesh_mode": "beginner"},
        )

    assert response.status_code == 422
    assert response.json()["detail"]["failing_check"] == "gmsh_diverged"
