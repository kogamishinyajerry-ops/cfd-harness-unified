"""F-NEW-20 wall-clock timeout for the gmsh subprocess.

V35 + V69: gmsh C++ stages do not yield to Python signal handlers, so
the timeout is enforced at the multiprocessing.Process boundary via
``join(timeout=N)`` + ``terminate()``. Verifies:

  1. ``run_gmsh_on_imported_case(timeout_s=N)`` raises GmshTimeoutError
     when the subprocess does not return within the budget.
  2. The pipeline maps that to ``failing_check=gmsh_timeout``.
  3. The route maps the failing_check to HTTP 504.

Uses an in-test ``multiprocessing.get_context`` mock to avoid spawning a
real gmsh subprocess (would need real STL geometry + slow). The mock
exercises the timeout-detection + terminate cleanup path with a Process
that reports ``is_alive()=True`` past the join budget.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ui.backend.services.meshing_gmsh.gmsh_runner import (
    GmshTimeoutError,
    run_gmsh_on_imported_case,
)


def _hung_process_context() -> MagicMock:
    """Return a fake multiprocessing context whose Process appears hung.

    is_alive() returns True after both the initial join(timeout=N) and
    the post-terminate cleanup join, simulating a subprocess that
    requires SIGKILL escalation. Queue is a no-op MagicMock — the
    timeout path raises before queue.get() is reached.
    """
    fake_proc = MagicMock(name="HungGmshProcess")
    fake_proc.start.return_value = None
    fake_proc.join.return_value = None
    fake_proc.is_alive.return_value = True  # hung past every join
    fake_proc.terminate.return_value = None
    fake_proc.kill.return_value = None
    fake_proc.exitcode = -9  # post-SIGKILL

    fake_ctx = MagicMock(name="SpawnContext")
    fake_ctx.Queue.return_value = MagicMock(name="FakeQueue")
    fake_ctx.Process.return_value = fake_proc
    fake_ctx.__fake_proc__ = fake_proc  # expose for assertion
    return fake_ctx


def test_run_gmsh_raises_timeout_when_subprocess_hangs(tmp_path: Path) -> None:
    stl = tmp_path / "in.stl"
    stl.write_bytes(b"solid x\nendsolid x\n")  # placeholder; not parsed
    out = tmp_path / "out.msh"

    fake_ctx = _hung_process_context()
    with patch(
        "ui.backend.services.meshing_gmsh.gmsh_runner.multiprocessing.get_context",
        return_value=fake_ctx,
    ):
        with pytest.raises(GmshTimeoutError) as exc_info:
            run_gmsh_on_imported_case(
                stl_path=stl,
                output_msh_path=out,
                mesh_mode="beginner",
                timeout_s=0.05,
            )

    msg = str(exc_info.value)
    assert "wall-clock timeout" in msg
    assert "F-NEW-20" in msg
    # Verify the escalation path fired: terminate → kill (since
    # is_alive stays True past every join in this mock).
    fake_ctx.__fake_proc__.terminate.assert_called_once()
    fake_ctx.__fake_proc__.kill.assert_called_once()


def test_pipeline_maps_gmsh_timeout_to_gmsh_timeout_failing_check(tmp_path: Path) -> None:
    """Spy at pipeline level: when run_gmsh_on_imported_case raises
    GmshTimeoutError, MeshPipelineError carries failing_check=gmsh_timeout
    (distinct from gmsh_diverged + refinement_zone_invalid).
    """
    from ui.backend.services.meshing_gmsh import pipeline as pipeline_mod
    from ui.backend.services.meshing_gmsh.pipeline import MeshPipelineError

    # Pipeline expects case_id resolution to succeed first; use the
    # existing case_drafts safe-id machinery the same way other tests do.
    # Easiest path: mock at the runner boundary and let pipeline's
    # earlier stages run minimally.
    def _raise_timeout(**kwargs):
        raise GmshTimeoutError(
            "gmsh subprocess exceeded wall-clock timeout 0.1s (F-NEW-20)..."
        )

    # We don't need a real case_id — patch the resolver to short-circuit.
    fake_paths = (tmp_path, tmp_path / "fake.stl")
    (tmp_path / "fake.stl").write_bytes(b"solid x\nendsolid x\n")

    with patch.object(pipeline_mod, "_resolve_imported_case", return_value=fake_paths), \
         patch.object(pipeline_mod, "run_gmsh_on_imported_case", side_effect=_raise_timeout):
        with pytest.raises(MeshPipelineError) as exc_info:
            pipeline_mod.mesh_imported_case(case_id="imported_test", mesh_mode="beginner")

    assert exc_info.value.failing_check == "gmsh_timeout"
    assert "wall-clock timeout" in str(exc_info.value)


def test_route_maps_gmsh_timeout_failing_check_to_504() -> None:
    """End-to-end: pipeline raises MeshPipelineError(gmsh_timeout) →
    route returns HTTP 504 with the failing_check echoed in the body.
    """
    from fastapi.testclient import TestClient

    from ui.backend.main import app
    from ui.backend.routes import mesh_imported as route_mod
    from ui.backend.services.meshing_gmsh.pipeline import MeshPipelineError

    client = TestClient(app)
    err = MeshPipelineError(
        "gmsh subprocess exceeded wall-clock timeout 600.0s (F-NEW-20)...",
        "gmsh_timeout",
    )
    with patch.object(route_mod, "mesh_imported_case", side_effect=err):
        response = client.post(
            "/api/import/imported_2026-05-12T00-00-00Z_deadbeef/mesh",
            json={"mesh_mode": "beginner"},
        )

    assert response.status_code == 504
    body = response.json()
    assert body["detail"]["failing_check"] == "gmsh_timeout"
    assert "wall-clock timeout" in body["detail"]["reason"]
