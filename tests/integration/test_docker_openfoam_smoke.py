"""DEC-V61-075 P2-T2.4 · executable_smoke_test for ExecutorMode.DOCKER_OPENFOAM.

Per RETRO-V61-053 risk_flag #4 (``executable_smoke_test``):

    Every new mode lands with a smoke test that runs end-to-end
    against at least one whitelist case (or returns
    MODE_NOT_APPLICABLE cleanly).

Whitelist case chosen: ``lid_driven_cavity`` (LDC). Rationale:
  - Smallest mesh in the whitelist (40×20 cells default).
  - Re=100 fully verified; converges in <30s on M-series Apple
    Silicon (DEC-V61-074 dogfood window measured 24.8s).
  - icoFoam laminar — no turbulence-model branch.
  - No environment-specific dependencies beyond the
    ``cfd-openfoam`` container.

The test skips when:
  - Docker SDK is not installed (no ``import docker``).
  - The ``cfd-openfoam`` container is not running on the host.

Skip semantics let CI environments without Docker support pass
this file (matching the ``cfd-real-solver`` optional-dep pattern in
pyproject.toml). When the smoke runs, it asserts the full
substantialized P2-T2 chain end-to-end:

  1. ``DockerOpenFOAMExecutor.execute(LDC task_spec)`` returns a
     ``RunReport(mode=DOCKER_OPENFOAM, status=OK,
     execution_result.success=True)``.
  2. ``build_manifest(executor=DockerOpenFOAMExecutor())`` produces
     a manifest with ``executor.mode == "docker_openfoam"`` (auto-
     tagging contract per spike F-3).
  3. The manifest's executor section's contract_hash matches the
     transient executor's contract_hash (single-source per T2.1).
  4. ``apply_executor_mode_routing`` does not raise on the
     manifest's ``executor`` section — TrustGate routing accepts
     the docker_openfoam mode for full triad verdict.
  5. ``serialize_zip_bytes`` succeeds — byte-determinism preserved
     across the new ``executor`` field per spike F-4.
"""

from __future__ import annotations

import pytest

from src.models import (
    Compressibility,
    FlowType,
    GeometryType,
    SteadyState,
    TaskSpec,
)


# ---------------------------------------------------------------------------
# Skip guards
# ---------------------------------------------------------------------------

def _docker_sdk_available() -> bool:
    try:
        import docker  # noqa: F401, PLC0415
        return True
    except ImportError:
        return False


def _cfd_openfoam_container_running() -> bool:
    if not _docker_sdk_available():
        return False
    try:
        import docker  # noqa: PLC0415

        client = docker.from_env()
        container = client.containers.get("cfd-openfoam")
        return container.status == "running"
    except Exception:  # noqa: BLE001 — any failure → skip
        return False


_SKIP_NO_DOCKER = pytest.mark.skipif(
    not _cfd_openfoam_container_running(),
    reason=(
        "Docker SDK + running cfd-openfoam container required for the "
        "executable_smoke_test (RETRO-V61-053 risk_flag #4). Install "
        "with: `.venv/bin/pip install -e '.[cfd-real-solver]'` and "
        "start the container: `docker start cfd-openfoam`."
    ),
)


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------

def _ldc_task_spec() -> TaskSpec:
    """Lid-Driven Cavity at Re=100 — canonical whitelist entry."""
    return TaskSpec(
        name="lid_driven_cavity",
        geometry_type=GeometryType.SIMPLE_GRID,
        flow_type=FlowType.INTERNAL,
        steady_state=SteadyState.STEADY,
        compressibility=Compressibility.INCOMPRESSIBLE,
        Re=100,
    )


@_SKIP_NO_DOCKER
def test_docker_openfoam_executable_smoke_ldc(tmp_path):
    """End-to-end DOCKER_OPENFOAM smoke against the LDC whitelist case.

    Closes RETRO-V61-053 risk_flag #4 (``executable_smoke_test``) for
    the docker_openfoam mode: the new ABC + bridge actually runs the
    real OpenFOAM solver and the manifest auto-tagging contract holds
    on real artifacts.
    """
    from src.audit_package.manifest import build_manifest
    from src.audit_package.serialize import serialize_zip_bytes
    from src.executor import DockerOpenFOAMExecutor, ExecutorMode, ExecutorStatus
    from src.metrics.base import MetricStatus
    from src.metrics.trust_gate import (
        TrustGateReport,
        apply_executor_mode_routing,
    )
    from types import MappingProxyType

    executor = DockerOpenFOAMExecutor()
    task_spec = _ldc_task_spec()

    # Step 1: execute the real solver
    report = executor.execute(task_spec)
    assert report.mode is ExecutorMode.DOCKER_OPENFOAM, (
        f"smoke: expected DOCKER_OPENFOAM mode, got {report.mode!r}"
    )
    assert report.status is ExecutorStatus.OK, (
        f"smoke: expected OK status, got {report.status!r}"
    )
    assert report.execution_result is not None
    assert report.execution_result.success is True, (
        f"smoke: solver run failed — error: "
        f"{report.execution_result.error_message!r}"
    )
    assert report.execution_result.raw_output_path is not None, (
        "smoke: raw_output_path must be populated on success"
    )

    # Step 2: build_manifest with auto-tagging
    manifest = build_manifest(
        case_id="lid_driven_cavity",
        run_id="t2_4_smoke_run",
        executor=executor,
        build_fingerprint="t2_4_smoke_deterministic",
    )
    assert manifest["executor"]["mode"] == "docker_openfoam", (
        f"smoke: manifest auto-tagging failed — got "
        f"{manifest['executor']['mode']!r}"
    )

    # Step 3: contract_hash single-sourcing — manifest's hash must
    # equal the executor's own contract_hash property
    assert manifest["executor"]["contract_hash"] == executor.contract_hash, (
        "smoke: manifest contract_hash drifted from executor "
        "contract_hash — single-source contract violated"
    )
    assert manifest["executor"]["version"] == executor.VERSION

    # Step 4: TrustGate routing accepts the mode (no exception)
    base_report = TrustGateReport(
        overall=MetricStatus.PASS,
        reports=(),
        count_by_status=MappingProxyType({
            MetricStatus.PASS: 0,
            MetricStatus.WARN: 0,
            MetricStatus.FAIL: 0,
        }),
    )
    routed = apply_executor_mode_routing(
        base_report,
        manifest["executor"],
    )
    # docker_openfoam → no ceiling; base_report unchanged.
    assert routed.overall is MetricStatus.PASS, (
        f"smoke: docker_openfoam routing imposed unexpected ceiling "
        f"({routed.overall!r}); expected base PASS unchanged"
    )

    # Step 5: serialize_zip_bytes succeeds — byte-determinism
    # preserved with the new executor field per spike F-4.
    zip_bytes = serialize_zip_bytes(manifest)
    assert isinstance(zip_bytes, bytes)
    assert len(zip_bytes) > 0
    # Byte-determinism: a second serialization must produce identical
    # bytes (the crux of HMAC signing's contract).
    zip_bytes_2 = serialize_zip_bytes(manifest)
    assert zip_bytes == zip_bytes_2, (
        "smoke: serialize_zip_bytes is non-deterministic — would "
        "break HMAC signing per spike F-4"
    )
