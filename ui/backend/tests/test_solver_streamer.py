"""Tests for the streaming icoFoam runner (Codex round-1 round-2 follow-up).

Covers HIGH-1 (preflight raises BEFORE the generator yields, so the
route can map to HTTP 4xx/5xx) and HIGH-2 (per-case run lock + run_id
suffixed container_work_dir).

Docker is mocked end-to-end so these tests run without the cfd-openfoam
container.
"""
from __future__ import annotations

import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest


# ────────── shared fakes ──────────


class _FakeContainer:
    """Minimal stand-in for the docker ContainerModel."""

    def __init__(self, *, status: str = "running", exec_lines: list[bytes] | None = None):
        self.status = status
        self._exec_lines = exec_lines or []

    def exec_run(self, cmd, stream: bool = False, demux: bool = False):  # noqa: D401, ARG002
        if stream:
            result = types.SimpleNamespace(output=iter(self._exec_lines))
            return result
        # Non-streaming exec_run is used for mkdir/ls — return empty.
        return types.SimpleNamespace(output=b"", exit_code=0)

    def put_archive(self, path, data):  # noqa: ARG002
        return True

    def get_archive(self, path):  # noqa: ARG002
        return iter([b""]), {}


class _FakeClient:
    def __init__(self, container):
        self.containers = types.SimpleNamespace(get=lambda name: container)


def _install_fake_docker(monkeypatch, container, *, raise_init: Exception | None = None):
    """Install a fake `docker` module so the streamer's lazy imports
    pick it up. Closes a fast-path: the streamer does
    ``import docker`` and ``import docker.errors`` inside the body.
    """
    fake_docker = types.ModuleType("docker")
    fake_errors = types.ModuleType("docker.errors")

    class DockerException(Exception):
        pass

    class NotFound(DockerException):
        pass

    fake_errors.DockerException = DockerException
    fake_errors.NotFound = NotFound
    fake_docker.errors = fake_errors

    if raise_init is not None:
        def from_env():
            raise raise_init
        fake_docker.from_env = from_env
    else:
        fake_docker.from_env = lambda: _FakeClient(container)

    monkeypatch.setitem(sys.modules, "docker", fake_docker)
    monkeypatch.setitem(sys.modules, "docker.errors", fake_errors)


def _stage_minimal_case(case_dir: Path) -> None:
    """Make `case_dir` look like a setup-bc'd LDC case so preflight passes."""
    (case_dir / "system").mkdir(parents=True)
    (case_dir / "system" / "controlDict").write_text("// stub", encoding="utf-8")


# ────────── HIGH-1: preflight surfaces BEFORE the generator yields ──────────


def test_preflight_raises_before_first_yield_when_no_controldict(tmp_path):
    """Without system/controlDict, _prepare_stream_icofoam raises so
    the route can return HTTP 409 before any SSE bytes are sent.
    """
    from ui.backend.services.case_solve.solver_streamer import (
        SolverRunError,
        _prepare_stream_icofoam,
    )

    case_dir = tmp_path / "case_001"
    case_dir.mkdir()
    # Intentionally NOT staging system/controlDict.

    with pytest.raises(SolverRunError, match="no system/controlDict"):
        _prepare_stream_icofoam(case_host_dir=case_dir)


def test_preflight_raises_before_first_yield_when_container_missing(
    tmp_path, monkeypatch
):
    from ui.backend.services.case_solve.solver_streamer import (
        SolverRunError,
        _prepare_stream_icofoam,
    )

    case_dir = tmp_path / "case_001"
    case_dir.mkdir()
    _stage_minimal_case(case_dir)

    fake_docker = types.ModuleType("docker")
    fake_errors = types.ModuleType("docker.errors")

    class DockerException(Exception):
        pass

    class NotFound(DockerException):
        pass

    fake_errors.DockerException = DockerException
    fake_errors.NotFound = NotFound
    fake_docker.errors = fake_errors

    def from_env():
        client = _FakeClient(None)

        def get_missing(name):
            raise NotFound(f"no such container: {name}")

        client.containers = types.SimpleNamespace(get=get_missing)
        return client

    fake_docker.from_env = from_env
    monkeypatch.setitem(sys.modules, "docker", fake_docker)
    monkeypatch.setitem(sys.modules, "docker.errors", fake_errors)

    with pytest.raises(SolverRunError, match="not found"):
        _prepare_stream_icofoam(case_host_dir=case_dir)


def test_preflight_releases_run_id_on_failure(tmp_path, monkeypatch):
    """If preflight fails after _claim_run, the run_id must be released
    so the user can retry. Otherwise a single bad config would lock
    the case forever.
    """
    from ui.backend.services.case_solve.solver_streamer import (
        SolverRunError,
        _active_runs,
        _prepare_stream_icofoam,
    )

    case_dir = tmp_path / "case_release"
    case_dir.mkdir()
    _stage_minimal_case(case_dir)
    # Container exists but status='exited' → triggers the inner
    # SolverRunError("not running") AFTER claim_run, exercising the
    # outer except BaseException → _release_run path.
    container = _FakeContainer(status="exited")
    _install_fake_docker(monkeypatch, container)

    with pytest.raises(SolverRunError, match="not running"):
        _prepare_stream_icofoam(case_host_dir=case_dir)
    assert "case_release" not in _active_runs, (
        "preflight failure must release the run_id"
    )


# ────────── HIGH-2: concurrent runs rejected ──────────


def test_concurrent_run_rejected(tmp_path, monkeypatch):
    """A second _prepare_stream_icofoam for the same case while the
    first is still in-flight must raise SolveAlreadyRunning so the
    route returns HTTP 409.
    """
    from ui.backend.services.case_solve.solver_streamer import (
        SolveAlreadyRunning,
        _active_runs,
        _claim_run,
        _release_run,
    )

    # Manually claim a run to simulate one already in-flight.
    case_id = "case_concurrent"
    run_id = _claim_run(case_id)
    try:
        with pytest.raises(SolveAlreadyRunning, match="already running"):
            _claim_run(case_id)
    finally:
        _release_run(case_id, run_id)
    assert case_id not in _active_runs


def test_release_run_is_idempotent_on_mismatch():
    """Releasing a run_id that doesn't match the active one is a no-op
    (defensive: protects against a stale generator's finally clause
    racing with a freshly-claimed run).
    """
    from ui.backend.services.case_solve.solver_streamer import (
        _active_runs,
        _claim_run,
        _release_run,
    )

    case_id = "case_idem"
    run_id_a = _claim_run(case_id)
    # Release with a different run_id — must NOT clear the active entry.
    _release_run(case_id, "wrong_run_id")
    assert _active_runs.get(case_id) == run_id_a
    # Real release works.
    _release_run(case_id, run_id_a)
    assert case_id not in _active_runs


def test_run_id_suffixes_container_work_dir(tmp_path, monkeypatch):
    """The container_work_dir must be run_id-suffixed so concurrent
    abandoned runs cannot collide on log.icoFoam or time directories.
    """
    from ui.backend.services.case_solve import solver_streamer
    from ui.backend.services.case_solve.solver_streamer import (
        _active_runs,
        _prepare_stream_icofoam,
        _release_run,
    )

    case_dir = tmp_path / "case_suffix"
    case_dir.mkdir()
    _stage_minimal_case(case_dir)
    container = _FakeContainer(status="running", exec_lines=[])
    _install_fake_docker(monkeypatch, container)

    # Use a fixed run_id so the assertion is deterministic.
    forced_run_id = "deadbeefcafe"
    try:
        prepared = _prepare_stream_icofoam(
            case_host_dir=case_dir, run_id=forced_run_id
        )
        assert prepared.run_id == forced_run_id
        assert prepared.container_work_dir.endswith(
            f"case_suffix-{forced_run_id}"
        )
    finally:
        _release_run("case_suffix", forced_run_id)
    assert "case_suffix" not in _active_runs
