"""Unit tests for ``ui.backend.services.meshing_gmsh`` (M6.0 routine path).

Real gmsh API calls run on a tiny box STL produced via trimesh — that
keeps the suite deterministic and fast (≪1s on M-series). The
``gmshToFoam`` step lives in the cfd-openfoam container, so those
tests mock the docker SDK layer instead of requiring a running
container in CI.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ui.backend.services.meshing_gmsh.cell_budget import (
    BEGINNER_SOFT_CAP_CELLS,
    POWER_HARD_CAP_CELLS,
    classify_cell_count,
)
from ui.backend.services.meshing_gmsh.gmsh_runner import (
    GmshMeshGenerationError,
    run_gmsh_on_imported_case,
)
from ui.backend.services.meshing_gmsh.pipeline import (
    MeshPipelineError,
    mesh_imported_case,
)
from ui.backend.tests.conftest import box_stl


# ----- cell_budget --------------------------------------------------------


def test_cell_budget_beginner_under_soft_cap_is_clean():
    v = classify_cell_count(1_000, "beginner")
    assert v.ok is True
    assert v.warning is None
    assert v.rejection_reason is None


def test_cell_budget_beginner_over_soft_cap_warns_but_passes():
    v = classify_cell_count(BEGINNER_SOFT_CAP_CELLS + 1, "beginner")
    assert v.ok is True
    assert v.warning is not None and "beginner" in v.warning


def test_cell_budget_power_under_hard_cap_no_warning():
    v = classify_cell_count(BEGINNER_SOFT_CAP_CELLS + 1, "power")
    assert v.ok is True
    # Power mode does not emit the beginner soft-cap warning.
    assert v.warning is None


def test_cell_budget_over_hard_cap_rejects_in_either_mode():
    for mode in ("beginner", "power"):
        v = classify_cell_count(POWER_HARD_CAP_CELLS + 1, mode)
        assert v.ok is False
        assert v.rejection_reason is not None
        assert "50,000,000" in v.rejection_reason


# ----- gmsh_runner -------------------------------------------------------


def test_gmsh_runs_on_real_box_stl(tmp_path: Path):
    stl_path = tmp_path / "box.stl"
    stl_path.write_bytes(box_stl(size=0.1))
    msh_path = tmp_path / "out.msh"

    result = run_gmsh_on_imported_case(
        stl_path=stl_path,
        output_msh_path=msh_path,
        mesh_mode="beginner",
    )
    assert msh_path.exists()
    assert result.cell_count > 0
    assert result.point_count > 0
    assert result.face_count > 0
    assert result.generation_time_s >= 0.0


def test_gmsh_raises_on_missing_stl(tmp_path: Path):
    with pytest.raises(GmshMeshGenerationError, match="not found"):
        run_gmsh_on_imported_case(
            stl_path=tmp_path / "missing.stl",
            output_msh_path=tmp_path / "out.msh",
        )


# ----- pipeline ----------------------------------------------------------


def test_mesh_imported_case_unsafe_id_rejects():
    with pytest.raises(MeshPipelineError) as exc_info:
        mesh_imported_case("../etc/passwd")
    assert exc_info.value.failing_check == "case_not_found"


def test_mesh_imported_case_missing_dir_rejects():
    with pytest.raises(MeshPipelineError) as exc_info:
        mesh_imported_case("imported_2099-01-01T00-00-00Z_deadbeef")
    assert exc_info.value.failing_check == "case_not_found"


def test_mesh_imported_case_cap_exceeded_path_clean(tmp_path: Path, monkeypatch):
    """Force the gmsh runner to report a >50M cell count and confirm
    the pipeline rejects with the cell_cap_exceeded tag without
    invoking gmshToFoam."""
    from ui.backend.services.meshing_gmsh import pipeline as pipeline_mod

    case_dir = tmp_path / "imported_TEST_capcheck"
    (case_dir / "triSurface").mkdir(parents=True)
    (case_dir / "triSurface" / "input.stl").write_bytes(box_stl())

    fake_result = pipeline_mod.GmshRunResult(
        msh_path=case_dir / "imported.msh",
        cell_count=POWER_HARD_CAP_CELLS + 100,
        face_count=10,
        point_count=10,
        characteristic_length_used=0.05,
        generation_time_s=0.1,
    )

    def fake_resolve(case_id: str):
        return case_dir, case_dir / "triSurface" / "input.stl"

    monkeypatch.setattr(pipeline_mod, "_resolve_imported_case", fake_resolve)
    monkeypatch.setattr(
        pipeline_mod, "run_gmsh_on_imported_case", lambda **kw: fake_result
    )
    # If the pipeline incorrectly proceeds past the cap check, this
    # assertion will trip.
    monkeypatch.setattr(
        pipeline_mod,
        "run_gmsh_to_foam",
        lambda **kw: pytest.fail("gmshToFoam called after cap-exceeded"),
    )

    with pytest.raises(MeshPipelineError) as exc_info:
        mesh_imported_case("imported_TEST_capcheck", mesh_mode="power")
    assert exc_info.value.failing_check == "cell_cap_exceeded"


def test_pipeline_normalizes_raw_gmsh_exception(tmp_path: Path, monkeypatch):
    """Codex round-2 P1: gmsh's Python bindings raise plain Exception
    on geometry failures; the pipeline must convert those into the
    advertised gmsh_diverged tag rather than letting them surface as
    HTTP 500."""
    from ui.backend.services.meshing_gmsh import pipeline as pipeline_mod

    case_dir = tmp_path / "imported_TEST_rawgmsh"
    (case_dir / "triSurface").mkdir(parents=True)
    (case_dir / "triSurface" / "input.stl").write_bytes(box_stl())

    def fake_resolve(case_id: str):
        return case_dir, case_dir / "triSurface" / "input.stl"

    monkeypatch.setattr(pipeline_mod, "_resolve_imported_case", fake_resolve)
    monkeypatch.setattr(
        pipeline_mod,
        "run_gmsh_on_imported_case",
        lambda **kw: (_ for _ in ()).throw(Exception("gmsh raw error")),
    )

    with pytest.raises(MeshPipelineError) as exc_info:
        mesh_imported_case("imported_TEST_rawgmsh")
    assert exc_info.value.failing_check == "gmsh_diverged"
    assert "gmsh raw error" in str(exc_info.value)


def test_pipeline_normalizes_raw_docker_exception(tmp_path: Path, monkeypatch):
    """Codex round-2 P2: docker SDK calls inside run_gmsh_to_foam can
    raise DockerException directly. The pipeline must translate those
    to gmshToFoam_failed."""
    from ui.backend.services.meshing_gmsh import pipeline as pipeline_mod

    case_dir = tmp_path / "imported_TEST_rawdocker"
    (case_dir / "triSurface").mkdir(parents=True)
    (case_dir / "triSurface" / "input.stl").write_bytes(box_stl())

    fake_gmsh_result = pipeline_mod.GmshRunResult(
        msh_path=case_dir / "imported.msh",
        cell_count=1_000,
        face_count=100,
        point_count=200,
        characteristic_length_used=0.05,
        generation_time_s=0.1,
    )

    def fake_resolve(case_id: str):
        return case_dir, case_dir / "triSurface" / "input.stl"

    monkeypatch.setattr(pipeline_mod, "_resolve_imported_case", fake_resolve)
    monkeypatch.setattr(
        pipeline_mod, "run_gmsh_on_imported_case", lambda **kw: fake_gmsh_result
    )
    monkeypatch.setattr(
        pipeline_mod,
        "run_gmsh_to_foam",
        lambda **kw: (_ for _ in ()).throw(RuntimeError("docker daemon dropped")),
    )

    with pytest.raises(MeshPipelineError) as exc_info:
        mesh_imported_case("imported_TEST_rawdocker")
    assert exc_info.value.failing_check == "gmshToFoam_failed"
    assert "docker daemon" in str(exc_info.value)


def test_to_foam_raises_when_msh_missing(tmp_path: Path):
    from ui.backend.services.meshing_gmsh.to_foam import (
        GmshToFoamError,
        run_gmsh_to_foam,
    )

    case_dir = tmp_path / "no_msh_here"
    case_dir.mkdir()

    with pytest.raises(GmshToFoamError, match="does not exist"):
        run_gmsh_to_foam(case_host_dir=case_dir)


def test_to_foam_calls_docker_when_msh_present(tmp_path: Path):
    """Mock the docker SDK and confirm we copy the case in, exec
    gmshToFoam, copy logs + polyMesh out. Validates the surface
    contract — not gmshToFoam itself, which is a downstream tool."""
    from ui.backend.services.meshing_gmsh import to_foam as to_foam_mod

    case_dir = tmp_path / "imported_TEST_dock"
    case_dir.mkdir()
    (case_dir / "imported.msh").write_bytes(b"FAKE MSH")

    # Pre-create a host-side polyMesh dir so the post-run validation
    # passes (the mocked extract function will simulate the container
    # producing it).
    polyMesh = case_dir / "constant" / "polyMesh"
    polyMesh.mkdir(parents=True)
    for fname in ("points", "faces", "owner", "neighbour", "boundary"):
        (polyMesh / fname).write_text("dummy", encoding="utf-8")

    fake_container = MagicMock()
    fake_container.status = "running"
    fake_container.exec_run.return_value = MagicMock(exit_code=0, output=b"ok")
    fake_container.put_archive.return_value = True
    fake_container.get_archive.return_value = (iter([b""]), {})

    fake_client = MagicMock()
    fake_client.containers.get.return_value = fake_container

    with patch.object(to_foam_mod, "_extract_tarball", return_value=None):
        with patch("docker.from_env", return_value=fake_client):
            result = to_foam_mod.run_gmsh_to_foam(case_host_dir=case_dir)

    assert result.polyMesh_dir == polyMesh
    assert result.used_container is True
    fake_container.exec_run.assert_called()
