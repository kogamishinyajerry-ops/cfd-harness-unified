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


# ────────── Post-R3 live-run defect (DEC-V61-099): staging order ──────────


def test_staging_renames_extracted_dir_into_run_id_suffix(tmp_path, monkeypatch):
    """Post-R3 live-run defect (DEC-V61-099 · caught on first LDC dogfood
    after V61-097 R4 RESOLVED). The V61-097 round-1 HIGH-2 fix introduced
    a run_id-suffixed container_work_dir but the staging sequence
    silently bypassed the rename:

      1. ``mkdir -p {container_work_dir}``  ← suffix dir pre-created
      2. ``put_archive(path={CONTAINER_WORK_BASE})``  ← extracts as
         ``{BASE}/{case_id}`` (un-suffixed)
      3. ``if [ -d {BASE}/{case_id} ] && [ ! -d {container_work_dir} ];
            then mv ... fi``  ← guard FALSE because step 1 just created
            the suffix dir → ``mv`` SKIPPED → suffix dir stays empty

    icoFoam then ``cd``'d into the empty suffix dir and FOAM-Fatal'd
    on missing ``system/controlDict``.

    Codex's static review missed this in V61-097 because the staging
    test (``test_run_id_suffixes_container_work_dir``) only asserted the
    PATH STRING and the mock ``put_archive`` returned True without
    simulating actual extract. This test pins the failure mode by
    tracking the bash command sequence.

    Per RETRO-V61-053 addendum: this is the ``executable_smoke_test``
    risk-flag class — runtime-emergent, not visible to static review.
    """
    from ui.backend.services.case_solve.solver_streamer import (
        _prepare_stream_icofoam,
        _release_run,
    )

    case_dir = tmp_path / "case_staging_regression"
    case_dir.mkdir()
    _stage_minimal_case(case_dir)

    # Track every bash command sent to exec_run so we can assert the
    # staging sequence is correct.
    bash_commands: list[str] = []

    class TrackingContainer(_FakeContainer):
        def exec_run(self, cmd, stream=False, demux=False):  # noqa: ARG002
            if isinstance(cmd, list) and len(cmd) >= 3 and cmd[0] == "bash":
                bash_commands.append(cmd[2])
            return super().exec_run(cmd, stream=stream, demux=demux)

    container = TrackingContainer(status="running", exec_lines=[])
    _install_fake_docker(monkeypatch, container)

    forced_run_id = "regtest9999"
    suffix_path_fragment = f"case_staging_regression-{forced_run_id}"
    try:
        prepared = _prepare_stream_icofoam(
            case_host_dir=case_dir, run_id=forced_run_id
        )
        assert prepared.container_work_dir.endswith(suffix_path_fragment)
    finally:
        _release_run("case_staging_regression", forced_run_id)

    # Assertion 1: there is exactly ONE mkdir command before put_archive,
    # and it must NOT pre-create the run_id-suffixed dir (the buggy
    # version did, which is what neutered the subsequent mv).
    mkdir_cmds = [c for c in bash_commands if "mkdir -p" in c]
    assert mkdir_cmds, "expected at least one mkdir during staging"
    pre_archive_mkdirs = [
        c for c in mkdir_cmds if suffix_path_fragment in c
    ]
    assert not pre_archive_mkdirs, (
        f"REGRESSION: staging pre-created the run_id-suffixed dir via "
        f"mkdir -p — this is the V61-099 bug because the subsequent mv "
        f"is silently skipped under the [ ! -d suffix ] guard. "
        f"Offending command(s): {pre_archive_mkdirs}"
    )

    # Assertion 2: the rename of the extracted {case_id} dir into the
    # run_id-suffixed name must be UNCONDITIONAL (no [ ! -d ] guard
    # against the suffix dir, since under V61-099 the suffix dir does
    # not pre-exist for the same-run claim).
    mv_cmds = [c for c in bash_commands if " mv " in c and suffix_path_fragment in c]
    assert mv_cmds, (
        f"expected an `mv` command renaming the extracted dir into "
        f"the run_id-suffixed name; got commands: {bash_commands}"
    )
    for mv in mv_cmds:
        assert "[ ! -d" not in mv, (
            f"REGRESSION: rename guarded by [ ! -d {{suffix_dir}} ] — "
            f"this is what allowed V61-099 to silently skip the rename "
            f"after the (now-removed) pre-create mkdir. mv command: {mv!r}"
        )


def test_staging_raises_on_nonzero_exec_run_exit_code(tmp_path, monkeypatch):
    """V61-099 Codex round 1 MED closure: every staging exec_run must
    check exit_code, not just trap Docker transport exceptions. Without
    this, a failed mkdir/mv/chmod (e.g., extracted dir missing because
    put_archive silently lost it; permissions wrong; suffixed path
    uncleanable) returns silently and the route emits a 200 SSE stream
    that hits FOAM Fatal at the first icoFoam read.

    This test forces the rename step's exec_run to return non-zero
    exit_code; preflight must raise SolverRunError before
    StreamingResponse is constructed.
    """
    from ui.backend.services.case_solve.solver_streamer import (
        SolverRunError,
        _active_runs,
        _prepare_stream_icofoam,
    )

    case_dir = tmp_path / "case_exit_code_check"
    case_dir.mkdir()
    _stage_minimal_case(case_dir)

    class FailingRenameContainer(_FakeContainer):
        """exec_run returns exit_code=0 for the BASE-mkdir but
        exit_code=1 for the rename step (the rm/mv/chmod triplet).
        """

        def exec_run(self, cmd, stream=False, demux=False):  # noqa: ARG002
            if (
                isinstance(cmd, list)
                and len(cmd) >= 3
                and cmd[0] == "bash"
                and " mv " in cmd[2]
                and "case_exit_code_check-" in cmd[2]
            ):
                return types.SimpleNamespace(output=b"", exit_code=1)
            if stream:
                return types.SimpleNamespace(
                    output=iter(self._exec_lines)
                )
            return types.SimpleNamespace(output=b"", exit_code=0)

    container = FailingRenameContainer(status="running", exec_lines=[])
    _install_fake_docker(monkeypatch, container)

    with pytest.raises(SolverRunError, match="failed to rename"):
        _prepare_stream_icofoam(case_host_dir=case_dir)

    # The run lock must be released so the user can retry after fixing
    # whatever caused the rename to fail.
    assert "case_exit_code_check" not in _active_runs, (
        "preflight failure on staging exec_run must release the run lock "
        "(otherwise a failed staging permanently locks the case)"
    )


def test_staging_raises_on_nonzero_mkdir_exit_code(tmp_path, monkeypatch):
    """Companion to the rename-fail test: BASE mkdir failure must also
    surface as preflight SolverRunError. This is rarer in practice
    (CONTAINER_WORK_BASE is usually writable) but the contract should
    hold uniformly across staging exec_run calls.
    """
    from ui.backend.services.case_solve.solver_streamer import (
        SolverRunError,
        _active_runs,
        _prepare_stream_icofoam,
    )

    case_dir = tmp_path / "case_mkdir_fail"
    case_dir.mkdir()
    _stage_minimal_case(case_dir)

    class FailingMkdirContainer(_FakeContainer):
        def exec_run(self, cmd, stream=False, demux=False):  # noqa: ARG002
            if (
                isinstance(cmd, list)
                and len(cmd) >= 3
                and cmd[0] == "bash"
                and "mkdir -p" in cmd[2]
            ):
                return types.SimpleNamespace(output=b"", exit_code=1)
            return types.SimpleNamespace(output=b"", exit_code=0)

    container = FailingMkdirContainer(status="running", exec_lines=[])
    _install_fake_docker(monkeypatch, container)

    with pytest.raises(SolverRunError, match="failed to prepare container staging base"):
        _prepare_stream_icofoam(case_host_dir=case_dir)

    assert "case_mkdir_fail" not in _active_runs


# ────────── Codex round-2 R2.1: GeneratorExit must release the lock ──────────


def test_generator_close_releases_run_id_after_first_yield(
    tmp_path, monkeypatch
):
    """Codex round-3 finding: closing the generator IMMEDIATELY after
    the first `start` SSE — without ever entering the streaming loop —
    used to bypass the outer try/finally because the start yield was
    OUTSIDE it. Round 3 moved the yield inside; this test pins down
    the exact failure mode Codex flagged.
    """
    from ui.backend.services.case_solve.solver_streamer import (
        _active_runs,
        _prepare_stream_icofoam,
        stream_icofoam,
    )

    case_dir = tmp_path / "case_immediate_close"
    case_dir.mkdir()
    _stage_minimal_case(case_dir)

    # Empty exec_lines so even one extra next() would still happen,
    # but we close right after the first start yield.
    container = _FakeContainer(status="running", exec_lines=[])
    _install_fake_docker(monkeypatch, container)

    prepared = _prepare_stream_icofoam(case_host_dir=case_dir)
    assert "case_immediate_close" in _active_runs
    gen = stream_icofoam(prepared=prepared)

    # Consume ONLY the start event, then close. Generator is suspended
    # exactly on the start yield — the failure mode round 2 missed.
    first = next(gen)
    assert first.startswith(b"event: start"), "first event should be the start event"
    gen.close()  # raises GeneratorExit at the start yield

    assert "case_immediate_close" not in _active_runs, (
        "GeneratorExit on the start yield must release the run lock"
    )


def test_generator_close_releases_run_id_mid_loop(tmp_path, monkeypatch):
    """Round-2 R2.1: closing the generator mid-streaming-loop must also
    release. Complementary to the immediate-disconnect test above.
    """
    from ui.backend.services.case_solve.solver_streamer import (
        _active_runs,
        _prepare_stream_icofoam,
        stream_icofoam,
    )

    case_dir = tmp_path / "case_disconnect"
    case_dir.mkdir()
    _stage_minimal_case(case_dir)

    lines = [b"Time = 0.005s\n"] * 200
    container = _FakeContainer(status="running", exec_lines=lines)
    _install_fake_docker(monkeypatch, container)

    prepared = _prepare_stream_icofoam(case_host_dir=case_dir)
    assert "case_disconnect" in _active_runs
    gen = stream_icofoam(prepared=prepared)

    next(gen)  # start
    next(gen)  # mid-loop event
    gen.close()

    assert "case_disconnect" not in _active_runs, (
        "GeneratorExit mid-loop must release the per-case run lock"
    )
