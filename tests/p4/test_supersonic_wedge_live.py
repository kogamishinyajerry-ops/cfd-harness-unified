"""P4 V71.A · DEC-V61-234 — OPT-IN live END-TO-END wedge launch test.

This is the NEW e2e evidence DEC-V61-233 lacked: it launches the supersonic wedge
THROUGH the workbench execution backend (``foam_agent_adapter``), runs a REAL
``rhoCentralFoam`` solve on the ESI image, and asserts the Control-plane
oblique-shock gate PASSES on the BACKEND-produced postProcessing. The
direct-container ``_w71a_wedge_probe`` does NOT count as this evidence — it proves
SOLVER+GATE correctness (already accepted LIVE_VALIDATED in DEC-V61-233), NOT that
a workbench BACKEND launched the case. That delta is exactly what 233 was failed on.

Gated (multi-minute density solve + Docker): runs ONLY when
``CFDTRUST_LIVE_WEDGE_E2E=1`` AND the docker SDK + ESI image are available. The
default unit suite SKIPS it, mirroring the ``CFDTRUST_LIVE_NETWORK_TESTS`` /
``_PROBE.is_dir()`` opt-in patterns. It uses a FRESH ``docker run --rm`` ESI
container, disturbing no running container.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

_LIVE = os.environ.get("CFDTRUST_LIVE_WEDGE_E2E") == "1"

pytestmark = pytest.mark.skipif(
    not _LIVE,
    reason="opt-in live e2e: set CFDTRUST_LIVE_WEDGE_E2E=1 (needs docker + ESI image)",
)

_ESI_IMAGE = "opencfd/openfoam-default:2312"


def _docker_and_image_ready() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        import docker
    except Exception:
        return False
    try:
        client = docker.from_env()
        client.images.get(_ESI_IMAGE)
        return True
    except Exception:
        return False


def test_workbench_launches_supersonic_wedge_e2e(tmp_path):
    """``foam_agent_adapter`` must launch a REAL rhoCentralFoam solve on the ESI
    image and the Control-plane oblique-shock gate must PASS on its output —
    proving the workbench can run a supersonic case end-to-end (Law-1 / 224(b))."""
    if not _docker_and_image_ready():
        pytest.skip(f"docker daemon or ESI image {_ESI_IMAGE} not available")

    from src.foam_agent_adapter import DockerOpenFOAMSolverExecutor
    from src.models import (
        Compressibility,
        FlowType,
        GeometryType,
        SteadyState,
        TaskSpec,
    )
    from src.wedge_oblique_shock_gate import gate_wedge_against_gold

    spec = TaskSpec(
        name="p4_v71a_wedge_e2e",
        geometry_type=GeometryType.SUPERSONIC_WEDGE,
        flow_type=FlowType.EXTERNAL,
        steady_state=SteadyState.STEADY,
        compressibility=Compressibility.COMPRESSIBLE,
        Ma=2.0,
    )
    executor = DockerOpenFOAMSolverExecutor(work_dir=str(tmp_path))

    # (1) the BACKEND launches the solve (real container, not a hand-typed run).
    result = executor.execute(spec)
    assert result.success, f"backend launch failed (honest BLOCK): {result.error_message}"
    assert result.is_mock is False
    assert result.raw_output_path is not None
    assert len(result.key_quantities) > 0  # extractor produced measured QoIs

    # (2) the Control-plane oblique-shock gate PASSES on the BACKEND-produced
    # postProcessing (every observable within tol + all 6 hard gates).
    gate = gate_wedge_against_gold(Path(result.raw_output_path))
    assert gate.passed, f"oblique-shock gate FAILED on backend output: {gate.summary}"
