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
    """Codex Round 7 P2: a missing STL is a filesystem fault, not a
    user-geometry fault. Surfaces as OSError (FileNotFoundError ⊂ OSError)
    so the pipeline routes it as 5xx, NOT as gmsh_diverged / 422.
    """
    with pytest.raises(OSError, match="not found") as excinfo:
        run_gmsh_on_imported_case(
            stl_path=tmp_path / "missing.stl",
            output_msh_path=tmp_path / "out.msh",
        )
    assert not isinstance(excinfo.value, GmshMeshGenerationError)


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


def test_gmsh_runner_normalizes_raw_binding_exception(tmp_path: Path, monkeypatch):
    """Codex round-2 P1 / round-3 P1: gmsh's Python bindings raise
    plain Exception on geometry-level failures (merge / classify /
    generate). Those must be wrapped INSIDE gmsh_runner as
    GmshMeshGenerationError so the pipeline maps them to
    gmsh_diverged. ModuleNotFoundError / OSError must NOT be caught
    here — those are backend / config faults that belong as 5xx."""
    from ui.backend.services.meshing_gmsh import gmsh_runner as runner_mod

    stl_path = tmp_path / "input.stl"
    stl_path.write_bytes(box_stl())

    class _FakeGmsh:
        # Minimal stub that mimics the gmsh module surface used by
        # run_gmsh_on_imported_case but raises plain Exception from
        # merge() — that's the round-3 worry.
        class option:
            @staticmethod
            def setNumber(*args, **kwargs):
                return None

        @staticmethod
        def initialize():
            return None

        @staticmethod
        def finalize():
            return None

        @staticmethod
        def merge(_path):
            raise Exception("gmsh raw error in merge()")

    import sys

    monkeypatch.setitem(sys.modules, "gmsh", _FakeGmsh)
    # M-PANELS Step 10 visual-smoke fix: gmsh logic now runs in a
    # multiprocessing child so signal.signal works. The exception-
    # normalization contract still lives in _gmsh_inline; target it
    # directly because monkeypatch.setitem(sys.modules, "gmsh", ...)
    # only affects this parent process — the spawned child re-imports
    # the real gmsh module.
    with pytest.raises(runner_mod.GmshMeshGenerationError, match="raw error"):
        runner_mod._gmsh_inline(
            stl_path=stl_path,
            output_msh_path=tmp_path / "out.msh",
            mesh_mode="beginner",
            characteristic_length_override=None,
        )


def test_gmsh_runner_wraps_late_api_exceptions(tmp_path: Path, monkeypatch):
    """Codex round-4 P1: gmsh bindings raise plain Exception from many
    call sites beyond merge/classify/generate (synchronize,
    addSurfaceLoop, getEntities, etc.). The single outer boundary
    must catch all of them as GmshMeshGenerationError."""
    from ui.backend.services.meshing_gmsh import gmsh_runner as runner_mod

    stl_path = tmp_path / "input.stl"
    stl_path.write_bytes(box_stl())

    class _FakeGeo:
        @staticmethod
        def addSurfaceLoop(_tags):
            return 1

        @staticmethod
        def addVolume(_loops):
            return 1

        @staticmethod
        def synchronize():
            raise Exception("synchronize() blew up")

    class _FakeMesh:
        @staticmethod
        def classifySurfaces(**_kwargs):
            return None

        @staticmethod
        def createGeometry():
            return None

        @staticmethod
        def generate(_dim):
            return None

        @staticmethod
        def getNodes():
            return ([], [], [])

        @staticmethod
        def getElements(dim):
            return ([], [], [])

    class _FakeModel:
        geo = _FakeGeo
        mesh = _FakeMesh

        @staticmethod
        def getEntities(dim):
            return [(2, 1)]

    class _FakeGmsh:
        class option:
            @staticmethod
            def setNumber(*args, **kwargs):
                return None

        model = _FakeModel

        @staticmethod
        def initialize():
            return None

        @staticmethod
        def finalize():
            return None

        @staticmethod
        def merge(_path):
            return None

        @staticmethod
        def write(_path):
            return None

    import sys

    monkeypatch.setitem(sys.modules, "gmsh", _FakeGmsh)
    # M-PANELS Step 10: target _gmsh_inline directly — see the
    # parallel comment on test_gmsh_runner_normalizes_raw_binding_exception.
    with pytest.raises(runner_mod.GmshMeshGenerationError, match="synchronize"):
        runner_mod._gmsh_inline(
            stl_path=stl_path,
            output_msh_path=tmp_path / "out.msh",
            mesh_mode="beginner",
            characteristic_length_override=None,
        )


def test_gmsh_runner_lets_oserror_bubble(tmp_path: Path, monkeypatch):
    """Codex round-5 P2: host-side I/O failures (OSError /
    PermissionError from gmsh.write()) must NOT be misreported as
    gmsh_diverged. They are backend faults — let them surface as 5xx."""
    from ui.backend.services.meshing_gmsh import gmsh_runner as runner_mod

    stl_path = tmp_path / "input.stl"
    stl_path.write_bytes(box_stl())

    class _FakeGeo:
        @staticmethod
        def addSurfaceLoop(_tags):
            return 1

        @staticmethod
        def addVolume(_loops):
            return 1

        @staticmethod
        def synchronize():
            return None

    class _FakeMesh:
        @staticmethod
        def classifySurfaces(**_kwargs):
            return None

        @staticmethod
        def createGeometry():
            return None

        @staticmethod
        def generate(_dim):
            return None

        @staticmethod
        def getNodes():
            return ([], [], [])

        @staticmethod
        def getElements(dim):
            # Produce one tetrahedron so the cell-count check passes.
            if dim == 3:
                return ([4], [[1]], [])
            return ([], [], [])

    class _FakeModel:
        geo = _FakeGeo
        mesh = _FakeMesh

        @staticmethod
        def getEntities(dim):
            return [(2, 1)]

    class _FakeGmsh:
        class option:
            @staticmethod
            def setNumber(*args, **kwargs):
                return None

        model = _FakeModel

        @staticmethod
        def initialize():
            return None

        @staticmethod
        def finalize():
            return None

        @staticmethod
        def merge(_path):
            return None

        @staticmethod
        def write(_path):
            raise PermissionError("disk full / read-only filesystem")

    import sys

    monkeypatch.setitem(sys.modules, "gmsh", _FakeGmsh)
    # M-PANELS Step 10: target _gmsh_inline directly. The subprocess
    # wrapper translates OSError into a re-raised OSError as well, but
    # via Queue marshaling — testing the inline contract is sufficient.
    # PermissionError is a subclass of OSError — must bubble unchanged.
    with pytest.raises(PermissionError, match="disk full"):
        runner_mod._gmsh_inline(
            stl_path=stl_path,
            output_msh_path=tmp_path / "out.msh",
            mesh_mode="beginner",
            characteristic_length_override=None,
        )


def test_to_foam_normalizes_docker_sdk_failures(tmp_path: Path):
    """Codex round-2 P2 / round-3 P2: docker SDK calls inside
    run_gmsh_to_foam (exec_run / put_archive / get_archive) raise
    DockerException; those must surface as GmshToFoamError so the
    pipeline maps them to gmshToFoam_failed. Host-side failures
    (PermissionError, tarfile errors) are NOT normalized here —
    those belong as 5xx for accurate diagnosis."""
    from ui.backend.services.meshing_gmsh import to_foam as to_foam_mod

    case_dir = tmp_path / "imported_TEST_dockerfail"
    case_dir.mkdir()
    (case_dir / "imported.msh").write_bytes(b"FAKE MSH")

    import docker.errors

    fake_container = MagicMock()
    fake_container.status = "running"
    fake_container.exec_run.side_effect = docker.errors.APIError("connection lost")

    fake_client = MagicMock()
    fake_client.containers.get.return_value = fake_container

    with patch("docker.from_env", return_value=fake_client):
        with pytest.raises(to_foam_mod.GmshToFoamError, match="docker SDK"):
            to_foam_mod.run_gmsh_to_foam(case_host_dir=case_dir)


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


# ----- subprocess wrapper (M-PANELS Step 10 visual-smoke fix) -----


def test_gmsh_runner_subprocess_wrapper_returns_inline_result(tmp_path: Path):
    """The public run_gmsh_on_imported_case wrapper spawns a child
    process and marshals the GmshRunResult back across the queue.

    Tests the wrapper's happy path against the real gmsh binding so we
    catch the original "signal only works in main thread" regression
    if the multiprocessing wrap is ever removed. Output mesh is tiny
    (a 12-triangle box STL) so this stays fast.
    """
    from ui.backend.services.meshing_gmsh import gmsh_runner as runner_mod

    stl_path = tmp_path / "input.stl"
    stl_path.write_bytes(box_stl())
    out_msh = tmp_path / "out.msh"

    result = runner_mod.run_gmsh_on_imported_case(
        stl_path=stl_path,
        output_msh_path=out_msh,
        mesh_mode="beginner",
    )
    assert result.msh_path == out_msh
    assert out_msh.exists()
    assert result.cell_count > 0
    assert result.point_count > 0


def test_gmsh_runner_subprocess_wrapper_marshals_missing_stl_as_filesystem_fault(tmp_path: Path):
    """Codex Round 7 P2: a missing STL is a filesystem / operator
    fault, not a user-geometry fault. _gmsh_inline raises
    FileNotFoundError (⊂ OSError), the wrapper marshals it as
    'os_error', and the parent re-raises as OSError so the pipeline
    routes it as 5xx — NOT as GmshMeshGenerationError → 4xx.
    """
    from ui.backend.services.meshing_gmsh import gmsh_runner as runner_mod

    stl_path = tmp_path / "missing.stl"  # intentionally not created
    with pytest.raises(OSError, match="STL not found") as excinfo:
        runner_mod.run_gmsh_on_imported_case(
            stl_path=stl_path,
            output_msh_path=tmp_path / "out.msh",
            mesh_mode="beginner",
        )
    # Must NOT be GmshMeshGenerationError (which would 4xx-relabel
    # the missing-file fault as "bad geometry").
    assert not isinstance(excinfo.value, runner_mod.GmshMeshGenerationError)


def test_subprocess_target_routes_oserror_as_os_error(tmp_path: Path):
    """Codex Round 5 P1 unit-level guard for the 'os_error' kind.

    Calls _subprocess_target directly (bypassing multiprocessing) with a
    Queue and verifies that an OSError from _gmsh_inline (e.g. disk full
    / read-only filesystem at gmsh.write()) marshals back as
    ('os_error', msg). The parent then re-raises OSError → 5xx backend,
    NOT GmshMeshGenerationError → 4xx 'bad geometry'.
    """
    from queue import Queue
    from ui.backend.services.meshing_gmsh import gmsh_runner as runner_mod

    captured = Queue()

    def _fake_inline(**_kwargs):
        raise PermissionError("disk full / read-only filesystem")

    original = runner_mod._gmsh_inline
    runner_mod._gmsh_inline = _fake_inline
    try:
        runner_mod._subprocess_target(
            stl_path_str=str(tmp_path / "x.stl"),
            output_msh_path_str=str(tmp_path / "x.msh"),
            mesh_mode="beginner",
            characteristic_length_override=None,
            queue=captured,
        )
    finally:
        runner_mod._gmsh_inline = original

    kind, payload = captured.get_nowait()
    assert kind == "os_error"
    assert "disk full" in payload


def test_subprocess_target_routes_import_error_as_import_error(tmp_path: Path):
    """Codex Round 5 P1 unit-level guard for the 'import_error' kind.

    Calls _subprocess_target directly (bypassing multiprocessing) with
    a Queue and verifies that an ImportError from _gmsh_inline (e.g.
    gmsh missing from the [workbench] extra) lands as ('import_error',
    msg) — distinct from ('gmsh_error', ...) which would 4xx-relabel.
    """
    from queue import Queue
    from ui.backend.services.meshing_gmsh import gmsh_runner as runner_mod

    captured = Queue()

    def _fake_inline(**_kwargs):
        raise ModuleNotFoundError("No module named 'gmsh'")

    # Patch _gmsh_inline so the synchronous _subprocess_target invokes
    # our raiser in the same process. (Avoids needing to spawn a real
    # child to exercise the dispatch logic.)
    original = runner_mod._gmsh_inline
    runner_mod._gmsh_inline = _fake_inline
    try:
        runner_mod._subprocess_target(
            stl_path_str=str(tmp_path / "x.stl"),
            output_msh_path_str=str(tmp_path / "x.msh"),
            mesh_mode="beginner",
            characteristic_length_override=None,
            queue=captured,
        )
    finally:
        runner_mod._gmsh_inline = original

    kind, payload = captured.get_nowait()
    assert kind == "import_error", (
        f"ModuleNotFoundError must marshal as 'import_error' "
        f"(non-gmsh, non-OSError backend fault); got {kind!r}"
    )
    assert "ModuleNotFoundError" in payload


def test_subprocess_target_routes_unknown_as_backend_error(tmp_path: Path):
    """Codex Round 5 P1: unknown exception classes from the child must
    land as 'backend_error', so the parent can re-raise as RuntimeError
    (5xx) instead of GmshMeshGenerationError (which would 4xx-collapse
    every backend bug into 'bad geometry').
    """
    from queue import Queue
    from ui.backend.services.meshing_gmsh import gmsh_runner as runner_mod

    captured = Queue()

    class _SomeBackendBug(RuntimeError):
        pass

    def _fake_inline(**_kwargs):
        raise _SomeBackendBug("unexpected child-process failure")

    original = runner_mod._gmsh_inline
    runner_mod._gmsh_inline = _fake_inline
    try:
        runner_mod._subprocess_target(
            stl_path_str=str(tmp_path / "x.stl"),
            output_msh_path_str=str(tmp_path / "x.msh"),
            mesh_mode="beginner",
            characteristic_length_override=None,
            queue=captured,
        )
    finally:
        runner_mod._gmsh_inline = original

    kind, payload = captured.get_nowait()
    assert kind == "backend_error"
    assert "_SomeBackendBug" in payload


def test_subprocess_wrapper_hard_crash_raises_gmsh_subprocess_error(tmp_path: Path, monkeypatch):
    """Codex Round 6 P1 regression guard: a hard child-process crash
    (segfault, OOM kill, os._exit, gmsh native abort) leaves no
    payload on the queue. The wrapper's ``proc.exitcode != 0 and
    queue.empty()`` branch must raise GmshSubprocessError (5xx
    backend), NOT GmshMeshGenerationError (which would 4xx-relabel
    the crash as 'bad geometry').

    We simulate by stubbing the multiprocessing context to return a
    fake Process that exits with code 1 immediately, leaving the
    queue empty.
    """
    from ui.backend.services.meshing_gmsh import gmsh_runner as runner_mod

    class _FakeProc:
        def __init__(self, *_a, **_kw):
            self.exitcode = 1

        def start(self) -> None:
            return None

        def join(self) -> None:
            return None

    class _FakeCtx:
        def Queue(self):
            import queue as _q

            return _q.Queue()  # always empty

        def Process(self, *args, **kwargs):
            return _FakeProc(*args, **kwargs)

    monkeypatch.setattr(
        runner_mod.multiprocessing, "get_context", lambda *_a, **_kw: _FakeCtx()
    )

    stl_path = tmp_path / "input.stl"
    stl_path.write_bytes(box_stl())

    raised: BaseException | None = None
    try:
        runner_mod.run_gmsh_on_imported_case(
            stl_path=stl_path,
            output_msh_path=tmp_path / "out.msh",
            mesh_mode="beginner",
        )
    except BaseException as e:  # noqa: BLE001
        raised = e

    assert raised is not None
    assert isinstance(raised, runner_mod.GmshSubprocessError), (
        f"Hard child crash must raise GmshSubprocessError; "
        f"got {type(raised).__name__}: {raised}"
    )
    assert not isinstance(raised, runner_mod.GmshMeshGenerationError), (
        f"Hard child crash must NOT collapse to GmshMeshGenerationError "
        f"(would 4xx-relabel as 'bad geometry'); got {type(raised).__name__}"
    )
    assert "exited with code 1" in str(raised)


def test_gmsh_inline_re_checks_stl_after_merge_failure(tmp_path: Path, monkeypatch):
    """Codex Round 8 Finding 1 regression guard: if gmsh.merge() raises
    AFTER the entry-time exists() check (concurrent deletion races
    through that gap), and the STL is now missing, _gmsh_inline must
    raise FileNotFoundError — NOT wrap as GmshMeshGenerationError
    (which would 4xx-relabel the operator deletion as 'bad geometry').
    """
    from ui.backend.services.meshing_gmsh import gmsh_runner as runner_mod

    stl_path = tmp_path / "input.stl"
    stl_path.write_bytes(box_stl())

    class _FakeGmsh:
        class option:
            @staticmethod
            def setNumber(*_a, **_kw):
                return None

        @staticmethod
        def initialize():
            return None

        @staticmethod
        def finalize():
            return None

        @staticmethod
        def merge(_path):
            # Simulate the file disappearing between the entry-time
            # check and the merge call. gmsh raises a generic
            # Exception in this case (its bindings don't preserve
            # FileNotFoundError shape).
            stl_path.unlink()
            raise Exception("gmsh: cannot merge file (vanished)")

    import sys

    monkeypatch.setitem(sys.modules, "gmsh", _FakeGmsh)

    raised: BaseException | None = None
    try:
        runner_mod._gmsh_inline(
            stl_path=stl_path,
            output_msh_path=tmp_path / "out.msh",
            mesh_mode="beginner",
            characteristic_length_override=None,
        )
    except BaseException as e:  # noqa: BLE001
        raised = e

    assert isinstance(raised, FileNotFoundError), (
        f"Disappearing STL during meshing must raise FileNotFoundError "
        f"so the wrapper marshals it as os_error → 5xx; got "
        f"{type(raised).__name__}: {raised}"
    )
    assert not isinstance(raised, runner_mod.GmshMeshGenerationError), (
        "Filesystem fault must not be re-labeled as user-geometry rejection"
    )


def test_gmsh_inline_re_checks_output_dir_writability_after_write_failure(
    tmp_path: Path, monkeypatch
):
    """Codex Round 9 Finding 1 regression guard: when gmsh.write()
    raises a generic Exception because the output dir is not
    writable (host fault), _gmsh_inline must surface as OSError
    (5xx) — NOT GmshMeshGenerationError (which would 4xx-relabel
    a host fault as 'bad geometry').
    """
    from ui.backend.services.meshing_gmsh import gmsh_runner as runner_mod

    stl_path = tmp_path / "input.stl"
    stl_path.write_bytes(box_stl())

    locked = tmp_path / "locked"
    locked.mkdir(mode=0o555)
    out_msh = locked / "out.msh"

    class _FakeMesh:
        @staticmethod
        def classifySurfaces(**_kw):
            return None

        @staticmethod
        def createGeometry():
            return None

        @staticmethod
        def generate(_dim):
            return None

        @staticmethod
        def getNodes():
            return ([1, 2, 3], None, None)

        @staticmethod
        def getElements(dim):
            if dim == 3:
                return ([4], [[1, 2, 3]], None)
            return ([2], [[]], None)

    class _FakeGeo:
        @staticmethod
        def addSurfaceLoop(_):
            return 1

        @staticmethod
        def addVolume(_):
            return 1

        @staticmethod
        def synchronize():
            return None

    class _FakeModel:
        mesh = _FakeMesh

        class geo:
            addSurfaceLoop = _FakeGeo.addSurfaceLoop
            addVolume = _FakeGeo.addVolume
            synchronize = _FakeGeo.synchronize

        @staticmethod
        def getEntities(dim):
            return [(2, 1)]

    class _FakeGmsh:
        class option:
            @staticmethod
            def setNumber(*_a, **_kw):
                return None

        model = _FakeModel

        @staticmethod
        def initialize():
            return None

        @staticmethod
        def finalize():
            return None

        @staticmethod
        def merge(_path):
            return None

        @staticmethod
        def write(_path):
            # Simulate gmsh's bindings raising a generic Exception on
            # a non-writable output dir (instead of OSError).
            raise Exception("gmsh: cannot write output file")

    import sys

    monkeypatch.setitem(sys.modules, "gmsh", _FakeGmsh)

    raised: BaseException | None = None
    try:
        runner_mod._gmsh_inline(
            stl_path=stl_path,
            output_msh_path=out_msh,
            mesh_mode="beginner",
            characteristic_length_override=None,
        )
    except BaseException as e:  # noqa: BLE001
        raised = e

    assert isinstance(raised, OSError), (
        f"non-writable output dir + plain-Exception write failure must "
        f"surface as OSError (5xx host fault), not "
        f"{type(raised).__name__ if raised else 'None'}"
    )
    assert not isinstance(raised, runner_mod.GmshMeshGenerationError)


def test_resolve_imported_case_handles_concurrent_triSurface_deletion(
    tmp_path: Path, monkeypatch
):
    """Codex Round 9 Finding 3 regression guard: TOCTTOU between
    triSurface.is_dir() and triSurface.iterdir() must not let raw
    FileNotFoundError escape — it must become MeshPipelineError
    with failing_check='source_not_imported'.
    """
    from ui.backend.services.meshing_gmsh import pipeline as pipeline_mod

    case_id = "imported_2026-04-28T00-00-00Z_racecase"
    case_dir = tmp_path / "imported" / case_id
    triSurface = case_dir / "triSurface"
    triSurface.mkdir(parents=True)
    (triSurface / "input.stl").write_bytes(box_stl())

    monkeypatch.setattr(pipeline_mod, "IMPORTED_DIR", tmp_path / "imported")

    real_iterdir = Path.iterdir

    def _racing_iterdir(self):
        if self.name == "triSurface":
            raise FileNotFoundError(self)
        return real_iterdir(self)

    monkeypatch.setattr(Path, "iterdir", _racing_iterdir)

    with pytest.raises(MeshPipelineError) as excinfo:
        pipeline_mod._resolve_imported_case(case_id)
    assert excinfo.value.failing_check == "source_not_imported"


def test_to_foam_normalizes_filenotfound_during_tarball_build(tmp_path: Path):
    """Codex Round 9 Finding 2 regression guard: if the case dir
    (or imported.msh inside it) disappears while _make_tarball walks
    it, the raised FileNotFoundError must surface as the structured
    GmshToFoamError contract — NOT escape as a raw 500.
    """
    from ui.backend.services.meshing_gmsh import to_foam as to_foam_mod

    case_dir = tmp_path / "imported_TEST_tarball_race"
    case_dir.mkdir()
    (case_dir / "imported.msh").write_text("dummy", encoding="utf-8")

    fake_container = MagicMock()
    fake_container.status = "running"
    fake_container.exec_run.return_value = MagicMock(exit_code=0, output=b"ok")
    fake_client = MagicMock()
    fake_client.containers.get.return_value = fake_container

    def _racing_make_tarball(_path):
        # Simulate the case dir disappearing mid-tarball build.
        raise FileNotFoundError(case_dir)

    with patch.object(to_foam_mod, "_make_tarball", _racing_make_tarball):
        with patch("docker.from_env", return_value=fake_client):
            with pytest.raises(to_foam_mod.GmshToFoamError) as excinfo:
                to_foam_mod.run_gmsh_to_foam(case_host_dir=case_dir)
    assert "tarball" in str(excinfo.value).lower() or "vanished" in str(excinfo.value).lower()


def test_gmsh_inline_disk_full_during_write_surfaces_as_oserror(
    tmp_path: Path, monkeypatch
):
    """Codex Round 10 Finding 1 regression guard: if gmsh.write()
    raises a plain Exception for a write-time backend fault while the
    output directory still passes both .exists() and os.access(W_OK)
    (e.g. ENOSPC / disk-full / transient I/O error), the previous
    R9 heuristic would relabel it as GmshMeshGenerationError → 4xx
    'gmsh_diverged'. R10 wraps gmsh.write() in its own try/except so
    the failure surfaces as OSError (5xx) regardless.
    """
    from ui.backend.services.meshing_gmsh import gmsh_runner as runner_mod

    stl_path = tmp_path / "input.stl"
    stl_path.write_bytes(box_stl())

    out_dir = tmp_path / "out"
    out_dir.mkdir()  # dir is writable AND exists — R9 heuristic won't fire
    out_msh = out_dir / "out.msh"

    class _FakeMesh:
        @staticmethod
        def classifySurfaces(**_kw):
            return None

        @staticmethod
        def createGeometry():
            return None

        @staticmethod
        def generate(_dim):
            return None

        @staticmethod
        def getNodes():
            # Return empty arrays so the bbox + point_count paths short-circuit
            # cleanly and we actually reach gmsh.write().
            return ([], [], [])

        @staticmethod
        def getElements(dim):
            if dim == 3:
                return ([4], [[1, 2, 3]], None)
            return ([2], [[]], None)

    class _FakeGmsh:
        class option:
            @staticmethod
            def setNumber(*_a, **_kw):
                return None

        class model:
            mesh = _FakeMesh

            class geo:
                @staticmethod
                def addSurfaceLoop(_):
                    return 1

                @staticmethod
                def addVolume(_):
                    return 1

                @staticmethod
                def synchronize():
                    return None

            @staticmethod
            def getEntities(dim):
                return [(2, 1)]

        @staticmethod
        def initialize():
            return None

        @staticmethod
        def finalize():
            return None

        @staticmethod
        def merge(_path):
            return None

        @staticmethod
        def write(_path):
            # gmsh's bindings can raise plain Exception for ENOSPC.
            raise Exception("gmsh: write failed (no space left on device)")

    import sys

    monkeypatch.setitem(sys.modules, "gmsh", _FakeGmsh)

    raised: BaseException | None = None
    try:
        runner_mod._gmsh_inline(
            stl_path=stl_path,
            output_msh_path=out_msh,
            mesh_mode="beginner",
            characteristic_length_override=None,
        )
    except BaseException as e:  # noqa: BLE001
        raised = e

    assert isinstance(raised, OSError), (
        f"gmsh.write() raising plain Exception while output dir is "
        f"healthy must surface as OSError (5xx host fault), not "
        f"{type(raised).__name__ if raised else 'None'}"
    )
    assert not isinstance(raised, runner_mod.GmshMeshGenerationError)


def test_to_foam_log_fallback_write_failure_surfaces_as_gmshtofoam_error(
    tmp_path: Path,
):
    """Codex Round 10 Finding 2 regression guard: when log retrieval
    from the container fails AND the host-side fallback write_text()
    itself raises OSError (e.g. case dir vanished, read-only fs,
    ENOSPC), the failure must surface as GmshToFoamError — not as a
    raw 500 escape.
    """
    from ui.backend.services.meshing_gmsh import to_foam as to_foam_mod

    case_dir = tmp_path / "imported_TEST_log_fallback_race"
    case_dir.mkdir()
    (case_dir / "imported.msh").write_text("dummy", encoding="utf-8")

    fake_container = MagicMock()
    fake_container.status = "running"
    # exec_run twice: mkdir prep + gmshToFoam invocation. Both succeed.
    fake_container.exec_run.return_value = MagicMock(exit_code=0, output=b"ok")
    fake_container.put_archive.return_value = True
    # First get_archive (log) raises so we fall into the fallback branch.
    fake_container.get_archive.side_effect = RuntimeError(
        "container connection dropped while streaming log"
    )
    fake_client = MagicMock()
    fake_client.containers.get.return_value = fake_container

    real_write_text = Path.write_text

    def _disk_full_write_text(self, *_a, **_kw):
        if self.name.startswith("log."):
            raise OSError("[Errno 28] No space left on device")
        return real_write_text(self, *_a, **_kw)

    with patch.object(to_foam_mod, "_make_tarball", lambda _p: b""):
        with patch("docker.from_env", return_value=fake_client):
            with patch.object(Path, "write_text", _disk_full_write_text):
                with pytest.raises(to_foam_mod.GmshToFoamError) as excinfo:
                    to_foam_mod.run_gmsh_to_foam(case_host_dir=case_dir)

    msg = str(excinfo.value).lower()
    assert "log" in msg or "fallback" in msg, (
        f"OSError from fallback write_text must surface as "
        f"GmshToFoamError mentioning the log fallback, got: {excinfo.value}"
    )
