"""P4 V71.A · DEC-V61-234 — supersonic-wedge workbench-DISPATCH tests.

Fast, mocked-docker regression locks proving the workbench execution backend
(``src.foam_agent_adapter.DockerOpenFOAMSolverExecutor``) DISPATCHES
``rhoCentralFoam`` on the ESI v2312 image for a ``SUPERSONIC_WEDGE`` TaskSpec —
the live wiring DEC-V61-233 explicitly DEFERRED — WITHOUT a multi-minute live
solve. The actual end-to-end solve lives in ``test_supersonic_wedge_live.py``
(opt-in gated).

Asserted invariants (the "the workbench can launch it" claim, test-enforced):
  - SUPERSONIC_WEDGE routes to the dedicated ``_execute_supersonic_wedge`` runner,
    short-circuiting BEFORE the Foundation-OF11 persistent-container connect.
  - ``_docker_run_esi_rm`` uses the ESI image + ``/openfoam/profile.rc`` (NOT the
    OF11 bashrc), in a FRESH ``--rm`` container that is always removed.
  - ``success`` is tied to a real solve + valid extraction; a non-zero solver exit
    or a failed extraction yields an HONEST BLOCK (success=False), never a fake PASS.
  - the incompressible honesty fence is un-weakened: rhoCentralFoam is NOT added to
    ``_OF11_INCOMPRESSIBLE_SOLVERS`` (the wedge bypasses it via its own ESI runner).
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from src import foam_agent_adapter as faa
from src.foam_agent_adapter import DockerOpenFOAMSolverExecutor
from src.models import (
    Compressibility,
    ExecutionResult,
    FlowType,
    GeometryType,
    SteadyState,
    TaskSpec,
)
from src.wedge_oblique_shock_extractor import WedgeShockQoIs


def _wedge_spec() -> TaskSpec:
    return TaskSpec(
        name="supersonic_wedge_m2_15deg",
        geometry_type=GeometryType.SUPERSONIC_WEDGE,
        flow_type=FlowType.EXTERNAL,
        steady_state=SteadyState.STEADY,
        compressibility=Compressibility.COMPRESSIBLE,
        Ma=2.0,
    )


def _fake_qois() -> WedgeShockQoIs:
    """A real-typed QoI bundle (the live measured values) so the real
    ``to_key_quantities`` maps it without a second mock."""
    return WedgeShockQoIs(
        shock_angle_beta_deg=45.24,
        mach_downstream=1.444,
        pressure_ratio=2.188,
        density_ratio=1.722,
        temperature_ratio=1.269,
        p1=1.0,
        rho1=1.0,
        t1=1.0,
        mach_freestream=2.0,
        p2=2.188,
        rho2=1.722,
        t2=1.269,
        y_shock_m=0.121,
        x_station_m=0.12,
    )


# --------------------------------------------------------------------------
# Routing — the wedge short-circuits to its own runner before the OF11 connect
# --------------------------------------------------------------------------

def test_wedge_routes_to_dedicated_runner_before_of11_connect():
    """A SUPERSONIC_WEDGE spec must short-circuit to ``_execute_supersonic_wedge``
    BEFORE the OF11 persistent-container connect — so it needs no 'cfd-openfoam'
    container and never touches the incompressible runtime."""
    executor = DockerOpenFOAMSolverExecutor()
    sentinel = ExecutionResult(success=True, is_mock=False, key_quantities={"beta": 45.24})
    mock_docker = MagicMock()
    with patch.object(faa, "_DOCKER_AVAILABLE", True), \
         patch.object(faa, "docker", mock_docker), \
         patch.object(
             DockerOpenFOAMSolverExecutor,
             "_execute_supersonic_wedge",
             return_value=sentinel,
         ) as mock_runner:
        result = executor.execute(_wedge_spec())
    mock_runner.assert_called_once()
    # The OF11 container connect (docker.from_env().containers.get) sits AFTER the
    # short-circuit and must never be reached for the wedge.
    mock_docker.from_env.assert_not_called()
    assert result is sentinel


def test_wedge_blocked_when_docker_sdk_absent():
    """If the docker SDK is unavailable the SDK-gate (step 1) fires first — the
    wedge runner is never reached and the result is an honest BLOCK (the gate
    precedes the short-circuit, so no fake success)."""
    executor = DockerOpenFOAMSolverExecutor()
    with patch.object(faa, "_DOCKER_AVAILABLE", False), \
         patch.object(DockerOpenFOAMSolverExecutor, "_execute_supersonic_wedge") as mock_runner:
        result = executor.execute(_wedge_spec())
    mock_runner.assert_not_called()
    assert result.success is False


# --------------------------------------------------------------------------
# ESI runtime selection — image + profile (NOT the OF11 bashrc), fresh --rm
# --------------------------------------------------------------------------

def test_docker_run_esi_rm_uses_esi_image_and_profile(tmp_path):
    """``_docker_run_esi_rm`` must launch a FRESH container on the ESI image,
    source ``/openfoam/profile.rc`` (NOT the Foundation OF11 bashrc), bind-mount
    the case at /work, and force-remove the container afterwards."""
    executor = DockerOpenFOAMSolverExecutor()
    mock_client = MagicMock()
    mock_container = MagicMock()
    mock_client.containers.run.return_value = mock_container
    mock_container.wait.return_value = {"StatusCode": 0}
    mock_container.logs.return_value = b"blockMesh ok\nrhoCentralFoam ok\n"
    executor._docker_client = mock_client  # avoid docker.from_env()

    code, logs = executor._docker_run_esi_rm(tmp_path, "blockMesh && rhoCentralFoam", 60)

    assert code == 0
    assert "rhoCentralFoam ok" in logs
    call = mock_client.containers.run.call_args
    assert call.args[0] == DockerOpenFOAMSolverExecutor.ESI_WEDGE_IMAGE
    assert call.kwargs["entrypoint"] == "bash"
    bash_cmd = call.kwargs["command"][1]
    assert "/openfoam/profile.rc" in bash_cmd
    assert "/opt/openfoam11/etc/bashrc" not in bash_cmd  # NOT the OF11 path
    assert "blockMesh && rhoCentralFoam" in bash_cmd
    assert call.kwargs["volumes"][str(tmp_path.resolve())]["bind"] == "/work"
    mock_container.remove.assert_called_once()  # --rm semantics (our own container)


def test_docker_run_esi_rm_blocks_on_docker_error(tmp_path):
    """A docker-level failure must surface as (-1, diagnostic), never a silent 0."""
    executor = DockerOpenFOAMSolverExecutor()
    mock_client = MagicMock()
    mock_client.containers.run.side_effect = RuntimeError("image not found")
    executor._docker_client = mock_client

    code, logs = executor._docker_run_esi_rm(tmp_path, "blockMesh", 60)

    assert code == -1
    assert "image not found" in logs


# --------------------------------------------------------------------------
# Honesty fences — BLOCK on failure, fence un-weakened
# --------------------------------------------------------------------------

def test_wedge_blocks_on_nonzero_solver_exit(tmp_path):
    """A non-zero rhoCentralFoam exit must yield an honest BLOCK, never a PASS."""
    executor = DockerOpenFOAMSolverExecutor(work_dir=str(tmp_path))
    with patch.object(executor, "_docker_run_esi_rm", return_value=(1, "blockMesh: boom")):
        result = executor._execute_supersonic_wedge(_wedge_spec(), t0=0.0)
    assert result.success is False
    assert result.is_mock is False
    assert "rhoCentralFoam run failed" in (result.error_message or "")


def test_wedge_blocks_on_extraction_failure(tmp_path):
    """A solver that 'exits 0' but produces no valid postProcessing must BLOCK on
    extraction — a green exit with no physics is NOT a fabricated PASS."""
    executor = DockerOpenFOAMSolverExecutor(work_dir=str(tmp_path))
    # solver mocked to exit 0, but the staged work dir has no postProcessing →
    # the real extractor raises FileNotFoundError → honest BLOCK.
    with patch.object(executor, "_docker_run_esi_rm", return_value=(0, "ok")):
        result = executor._execute_supersonic_wedge(_wedge_spec(), t0=0.0)
    assert result.success is False
    assert result.is_mock is False


def test_wedge_success_ties_to_real_extraction(tmp_path):
    """On a real solve + valid extraction the runner returns success=True,
    is_mock=False, with the measured QoIs in key_quantities."""
    executor = DockerOpenFOAMSolverExecutor(work_dir=str(tmp_path))
    with patch.object(executor, "_docker_run_esi_rm", return_value=(0, "ok")), \
         patch(
             "src.wedge_oblique_shock_extractor.extract_wedge_qois",
             return_value=_fake_qois(),
         ):
        result = executor._execute_supersonic_wedge(_wedge_spec(), t0=0.0)
    assert result.success is True
    assert result.is_mock is False
    assert len(result.key_quantities) > 0


def test_incompressible_solver_fence_unchanged():
    """The wedge wiring must NOT add rhoCentralFoam (or any compressible solver)
    to the OF11 incompressible whitelist — the wedge bypasses that fence via its
    own dedicated ESI runner, so the fence stays byte-identical."""
    fence = DockerOpenFOAMSolverExecutor._OF11_INCOMPRESSIBLE_SOLVERS
    assert fence == frozenset({"simpleFoam", "pimpleFoam", "icoFoam"})
    assert "rhoCentralFoam" not in fence
