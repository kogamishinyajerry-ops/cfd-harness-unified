"""B-ext-5.2 (DEC-V61-193) · F13 mitigation pre-flight test:
/solve must return HTTP 409 with failing_check=mesh_missing when
constant/polyMesh/ is absent, NOT a generic 502 solver_diverged with
a cryptic FOAM IO error.

R9 surfaced F13 as 11× /solve POST 502 across naca0012 + pipe_expansion
where the persona had reached an inconsistent case state in which
constant/polyMesh/ either didn't exist or was incomplete. The 502 body
carried failing_check=solver_diverged and a "simpleFoam exited with
code 1" detail — useful only if the persona reads the log.icoFoam file
on disk. Mapping the missing-mesh case to a structured 409 lets the
persona course-correct by re-running /mesh.

Coverage:
- constant/polyMesh/ entirely absent → 409 mesh_missing
- constant/polyMesh/ present but missing 'points' → 409 mesh_missing
- constant/polyMesh/ present but missing 'boundary' → 409 mesh_missing
- both 'points' and 'boundary' present + consistent BC → pre-flight
  passes (test stops there; container-side execution is out of scope
  for the unit test layer)
"""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path: Path, monkeypatch) -> TestClient:
    monkeypatch.setattr(
        "ui.backend.services.case_scaffold.IMPORTED_DIR", tmp_path
    )
    monkeypatch.setattr(
        "ui.backend.routes.case_solve.IMPORTED_DIR", tmp_path
    )
    from ui.backend.main import app

    return TestClient(app)


def _seed_case_with_controldict_only(case_dir: Path) -> None:
    """Bare case scaffold: system/controlDict exists (so the existing
    bc_not_setup pre-flight passes) but constant/polyMesh/ is absent."""
    case_dir.mkdir(parents=True, exist_ok=True)
    system = case_dir / "system"
    system.mkdir()
    (system / "controlDict").write_text(
        "FoamFile { object controlDict; }\n"
        "application     icoFoam;\n"
        "endTime         2.0;\n"
    )


def test_solve_returns_409_mesh_missing_when_polymesh_dir_absent(
    client: TestClient, tmp_path: Path
) -> None:
    case_dir = tmp_path / "imported_2026-test_F13_no_polymesh"
    _seed_case_with_controldict_only(case_dir)

    response = client.post(f"/api/import/{case_dir.name}/solve")

    assert response.status_code == 409, response.text
    detail = response.json()["detail"]
    assert detail["failing_check"] == "mesh_missing"
    assert "polyMesh" in detail["detail"]
    assert "/mesh" in detail["detail"]


def test_solve_returns_409_mesh_missing_when_points_file_absent(
    client: TestClient, tmp_path: Path
) -> None:
    case_dir = tmp_path / "imported_2026-test_F13_no_points"
    _seed_case_with_controldict_only(case_dir)
    polymesh = case_dir / "constant" / "polyMesh"
    polymesh.mkdir(parents=True)
    # boundary present, points missing
    (polymesh / "boundary").write_text(
        "FoamFile { object boundary; }\n0\n(\n)\n"
    )

    response = client.post(f"/api/import/{case_dir.name}/solve")

    assert response.status_code == 409, response.text
    detail = response.json()["detail"]
    assert detail["failing_check"] == "mesh_missing"
    assert "incomplete" in detail["detail"]
    assert "points" in detail["detail"]


def test_solve_returns_409_mesh_missing_when_boundary_file_absent(
    client: TestClient, tmp_path: Path
) -> None:
    case_dir = tmp_path / "imported_2026-test_F13_no_boundary"
    _seed_case_with_controldict_only(case_dir)
    polymesh = case_dir / "constant" / "polyMesh"
    polymesh.mkdir(parents=True)
    (polymesh / "points").write_text("0\n(\n)\n")

    response = client.post(f"/api/import/{case_dir.name}/solve")

    assert response.status_code == 409, response.text
    detail = response.json()["detail"]
    assert detail["failing_check"] == "mesh_missing"
    assert "incomplete" in detail["detail"]
    assert "boundary" in detail["detail"]


def test_check_mesh_present_helper_returns_none_for_complete_polymesh(
    tmp_path: Path,
) -> None:
    """Direct unit test on the helper: passes when both required files
    are present. The full /solve route delegates to this and proceeds
    past the pre-flight to the next check (mesh-BC consistency)."""
    from ui.backend.services.case_solve.solver_runner import (
        _check_mesh_present,
    )

    case_dir = tmp_path / "imported_2026-test_F13_complete"
    polymesh = case_dir / "constant" / "polyMesh"
    polymesh.mkdir(parents=True)
    (polymesh / "boundary").write_text("0\n(\n)\n")
    (polymesh / "points").write_text("0\n(\n)\n")

    assert _check_mesh_present(case_dir) is None


def test_check_mesh_present_helper_lists_all_missing_files(
    tmp_path: Path,
) -> None:
    """Both files missing → error message lists both, not just one."""
    from ui.backend.services.case_solve.solver_runner import (
        _check_mesh_present,
    )

    case_dir = tmp_path / "imported_2026-test_F13_partial"
    (case_dir / "constant" / "polyMesh").mkdir(parents=True)
    # neither file present

    msg = _check_mesh_present(case_dir)
    assert msg is not None
    assert msg.startswith("mesh_missing:")
    # Both files reported in the missing list
    assert "boundary" in msg
    assert "points" in msg
