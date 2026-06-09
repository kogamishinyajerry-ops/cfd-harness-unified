"""P4 V71B-FOLLOWUP-1 · DEC-V61-236 — OPT-IN live END-TO-END low-Re BFS launch test.

Launches the wall-RESOLVED low-Re kOmegaSST backward_facing_step THROUGH the workbench
execution backend (``foam_agent_adapter.execute()``), runs a REAL OF11
``foamRun -solver incompressibleFluid`` solve in a fresh ``--rm`` container, and asserts
the Control-plane gate PASSES on the BACKEND-produced output. This is the e2e evidence
DEC-V61-235 deferred: the hand-typed ``_v71b_bfs_lowre_probe`` proves SOLVER+GATE
correctness (LIVE_VALIDATED), NOT that a workbench BACKEND launched the case.

Gated (multi-minute incompressible solve + Docker): runs ONLY when
``CFDTRUST_LIVE_BFS_LOWRE_E2E=1`` AND the docker SDK + OF11 image are available. The
default unit suite SKIPS it. It uses a FRESH ``docker run --rm`` OF11 container,
disturbing no running container (the persistent ``cfd-openfoam`` is never touched).
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

_LIVE = os.environ.get("CFDTRUST_LIVE_BFS_LOWRE_E2E") == "1"

pytestmark = pytest.mark.skipif(
    not _LIVE,
    reason="opt-in live e2e: set CFDTRUST_LIVE_BFS_LOWRE_E2E=1 (needs docker + OF11 image)",
)

_OF11_IMAGE = "openfoam/openfoam11-paraview510"


def _docker_and_image_ready() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        import docker
    except Exception:
        return False
    try:
        client = docker.from_env()
        client.images.get(_OF11_IMAGE)
        return True
    except Exception:
        return False


def test_workbench_launches_bfs_lowre_e2e(tmp_path):
    """``foam_agent_adapter`` must launch a REAL OF11 incompressibleFluid solve of the
    wall-RESOLVED low-Re BFS and the Control-plane gate must PASS on its output —
    proving the workbench can run + verify the anchor end-to-end (DEC-V61-236)."""
    if not _docker_and_image_ready():
        pytest.skip(f"docker daemon or OF11 image {_OF11_IMAGE} not available")

    from src.bfs_lowre_gate import gate_bfs_lowre_against_gold
    from src.foam_agent_adapter import DockerOpenFOAMSolverExecutor
    from src.models import (
        Compressibility,
        FlowType,
        GeometryType,
        SteadyState,
        TaskSpec,
    )

    # name MUST be the literal 'backward_facing_step_lowre' — the dispatch is
    # identity-keyed on it (NOT geometry_type, which collides with the high-Re BFS).
    spec = TaskSpec(
        name="backward_facing_step_lowre",
        geometry_type=GeometryType.BACKWARD_FACING_STEP,
        flow_type=FlowType.INTERNAL,
        steady_state=SteadyState.STEADY,
        compressibility=Compressibility.INCOMPRESSIBLE,
        Re=5000.0,
        boundary_conditions={"wall_treatment": "resolved", "turbulence_model": "kOmegaSST"},
    )
    executor = DockerOpenFOAMSolverExecutor(work_dir=str(tmp_path))

    # (1) the BACKEND launches the solve (real container, not a hand-typed run).
    result = executor.execute(spec)
    assert result.success, f"backend launch failed (honest BLOCK): {result.error_message}"
    assert result.is_mock is False
    assert result.raw_output_path is not None
    assert len(result.key_quantities) > 0  # extractor produced measured QoIs

    # (2) the persistence contract: the gate's artifacts survive on the host.
    raw = Path(result.raw_output_path)
    assert (raw / "proof" / "floor_faces.csv").is_file(), "frozen floor CSV not derived"
    assert (raw / "VTK" / "allPatches").is_dir(), "allPatches VTK not on host (bind-mount?)"

    # (3) the Control-plane gate PASSES on the BACKEND-produced output (Xr/H within
    # 10% of 6.26 AND the y+<1 resolved precondition + 3 hard gates).
    gate = gate_bfs_lowre_against_gold(raw)
    assert gate.passed, f"bfs-lowre gate FAILED on backend output: {gate.summary}"
