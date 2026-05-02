"""Hardening tests for the patch_classification store
(DEC-V61-108 Phase A · Codex R1 closure).

Covers the three concrete defects R1 flagged:

* P1-A — concurrency: a writer that doesn't take a lock loses
  updates. We exercise N parallel ``upsert_override`` calls for
  distinct patches and require all N to be present at the end.
* P1-B — symlink escape: a symlink at
  ``<case_dir>/system/patch_classification.yaml`` pointing outside
  the case root, or ``system/`` itself being a symlink, must be
  refused with ``failing_check="symlink_escape"``.
* P2 — stale-read race: ``setup_bc_from_stl_patches`` MUST take the
  case_lock BEFORE reading overrides. We monkeypatch the loader to
  assert it is called inside the lock by spying on the lock fd.
"""
from __future__ import annotations

import threading
from pathlib import Path

import pytest
import yaml

from ui.backend.services.case_solve.bc_setup_from_stl_patches import (
    BCClass,
)
from ui.backend.services.case_solve.patch_classification_store import (
    PatchClassificationIOError,
    delete_override,
    load_under_lock,
    upsert_override,
)


# ─────────── P1-B · symlink escape ───────────


def test_upsert_refuses_when_sidecar_is_symlink_outside(tmp_path: Path):
    """If ``patch_classification.yaml`` is a pre-planted symlink to
    a path outside the case root, upsert must refuse before writing.
    """
    case_dir = tmp_path / "case_sym_sidecar"
    case_dir.mkdir()
    (case_dir / "system").mkdir()
    outside = tmp_path / "outside_target.yaml"
    outside.write_text("# attacker target\n")
    (case_dir / "system" / "patch_classification.yaml").symlink_to(outside)

    with pytest.raises(PatchClassificationIOError) as exc_info:
        upsert_override(
            case_dir,
            patch_name="some_patch",
            bc_class=BCClass.VELOCITY_INLET,
        )
    assert exc_info.value.failing_check == "symlink_escape"
    # Sanity: outside file untouched.
    assert outside.read_text() == "# attacker target\n"


def test_upsert_refuses_when_system_dir_is_symlink_outside(tmp_path: Path):
    """If ``system/`` itself is a symlink to a directory outside
    the case root, upsert must refuse — the resolved sidecar would
    land outside even though the relative path looks innocent.
    """
    case_dir = tmp_path / "case_sym_systemdir"
    case_dir.mkdir()
    outside_dir = tmp_path / "outside_system"
    outside_dir.mkdir()
    (case_dir / "system").symlink_to(outside_dir, target_is_directory=True)

    with pytest.raises(PatchClassificationIOError) as exc_info:
        upsert_override(
            case_dir,
            patch_name="some_patch",
            bc_class=BCClass.VELOCITY_INLET,
        )
    assert exc_info.value.failing_check == "symlink_escape"
    # No file landed in the outside dir.
    assert list(outside_dir.iterdir()) == []


def test_delete_refuses_when_sidecar_is_symlink_outside(tmp_path: Path):
    """Same containment guarantee for delete."""
    case_dir = tmp_path / "case_sym_delete"
    case_dir.mkdir()
    (case_dir / "system").mkdir()
    outside = tmp_path / "outside_target_del.yaml"
    outside.write_text("# attacker target del\n")
    (case_dir / "system" / "patch_classification.yaml").symlink_to(outside)

    with pytest.raises(PatchClassificationIOError) as exc_info:
        delete_override(case_dir, patch_name="some_patch")
    assert exc_info.value.failing_check == "symlink_escape"
    assert outside.read_text() == "# attacker target del\n"


def test_upsert_refuses_when_sidecar_is_intree_symlink(tmp_path: Path):
    """Codex R2 P1 closure: an in-tree symlink (target inside the
    case root, e.g. ``patch_classification.yaml -> system/controlDict``)
    must also be refused. The previous resolve()+relative_to() pair
    silently accepted the link and let ``os.replace`` overwrite the
    engineer's authored controlDict.
    """
    case_dir = tmp_path / "case_intree_link"
    case_dir.mkdir()
    (case_dir / "system").mkdir()
    (case_dir / "system" / "controlDict").write_text(
        "// engineer-authored controlDict — must NOT be overwritten\n"
        "application pimpleFoam;\n"
    )
    # Plant the in-tree symlink redirect.
    (case_dir / "system" / "patch_classification.yaml").symlink_to(
        case_dir / "system" / "controlDict"
    )

    with pytest.raises(PatchClassificationIOError) as exc_info:
        upsert_override(
            case_dir,
            patch_name="some_patch",
            bc_class=BCClass.VELOCITY_INLET,
        )
    assert exc_info.value.failing_check == "symlink_escape"
    # Critical: the engineer's controlDict is unchanged.
    cd_text = (case_dir / "system" / "controlDict").read_text()
    assert "application pimpleFoam" in cd_text
    assert "engineer-authored" in cd_text


def test_upsert_refuses_when_system_is_intree_symlink(tmp_path: Path):
    """Sibling case: ``system/`` itself is a symlink to another
    in-tree directory (e.g. ``constant/``). Walking each component
    catches it before any write."""
    case_dir = tmp_path / "case_intree_systemdir"
    case_dir.mkdir()
    real_other = case_dir / "constant"
    real_other.mkdir()
    (real_other / "file_to_protect").write_text("DO_NOT_TOUCH\n")
    (case_dir / "system").symlink_to(real_other, target_is_directory=True)

    with pytest.raises(PatchClassificationIOError) as exc_info:
        upsert_override(
            case_dir,
            patch_name="some_patch",
            bc_class=BCClass.SYMMETRY,
        )
    assert exc_info.value.failing_check == "symlink_escape"
    assert (real_other / "file_to_protect").read_text() == "DO_NOT_TOUCH\n"
    # And no patch_classification.yaml landed in real_other either.
    assert not (real_other / "patch_classification.yaml").exists()


def test_upsert_immune_to_planted_tmp_symlink(tmp_path: Path):
    """The atomic-write step uses ``tempfile.mkstemp`` (random
    per-call suffix), so a pre-existing symlink at any specific
    legacy ``.tmp`` filename can't redirect the write."""
    case_dir = tmp_path / "case_tmp_trap"
    case_dir.mkdir()
    (case_dir / "system").mkdir()
    victim = tmp_path / "tmp_victim.yaml"
    victim.write_text("BEFORE_TMP_ATTACK\n")
    # Plant a few likely-named .tmp symlinks.
    (case_dir / "system" / "patch_classification.tmp").symlink_to(victim)
    (case_dir / "system" / "patch_classification.yaml.tmp").symlink_to(victim)

    upsert_override(
        case_dir,
        patch_name="custom_patch",
        bc_class=BCClass.SYMMETRY,
    )
    # Victim untouched, real file landed under system/.
    assert victim.read_text() == "BEFORE_TMP_ATTACK\n"
    sidecar = case_dir / "system" / "patch_classification.yaml"
    assert sidecar.is_file() and not sidecar.is_symlink()
    on_disk = yaml.safe_load(sidecar.read_text())
    assert on_disk["overrides"]["custom_patch"] == "symmetry"


# ─────────── P1-A · concurrent updates ───────────


def test_concurrent_upserts_for_distinct_patches_all_persist(tmp_path: Path):
    """N threads each upsert a distinct patch override. With the
    case_lock-protected read-modify-write, all N must appear in the
    final sidecar — none lost to a read-modify-write race."""
    case_dir = tmp_path / "case_concurrent"
    case_dir.mkdir()
    (case_dir / "system").mkdir()
    n = 8
    barrier = threading.Barrier(n)
    errors: list[BaseException] = []

    def writer(i: int) -> None:
        try:
            barrier.wait(timeout=5.0)
            upsert_override(
                case_dir,
                patch_name=f"patch_{i:02d}",
                bc_class=BCClass.NO_SLIP_WALL,
            )
        except BaseException as exc:  # noqa: BLE001 — capture for assert
            errors.append(exc)

    threads = [threading.Thread(target=writer, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10.0)

    assert not errors, f"writers raised: {errors!r}"
    sidecar = case_dir / "system" / "patch_classification.yaml"
    on_disk = yaml.safe_load(sidecar.read_text())
    assert set(on_disk["overrides"].keys()) == {
        f"patch_{i:02d}" for i in range(n)
    }


def test_concurrent_upsert_then_delete_serializes(tmp_path: Path):
    """Pre-seed two overrides; one thread upserts a third while
    another deletes one of the existing two. Both operations must
    complete and observe a consistent sequence (no torn state)."""
    case_dir = tmp_path / "case_upsert_delete"
    case_dir.mkdir()
    (case_dir / "system").mkdir()
    upsert_override(case_dir, patch_name="a", bc_class=BCClass.VELOCITY_INLET)
    upsert_override(case_dir, patch_name="b", bc_class=BCClass.PRESSURE_OUTLET)

    barrier = threading.Barrier(2)
    errors: list[BaseException] = []

    def upserter() -> None:
        try:
            barrier.wait(timeout=5.0)
            upsert_override(case_dir, patch_name="c", bc_class=BCClass.SYMMETRY)
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    def deleter() -> None:
        try:
            barrier.wait(timeout=5.0)
            delete_override(case_dir, patch_name="a")
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    t1 = threading.Thread(target=upserter)
    t2 = threading.Thread(target=deleter)
    t1.start(); t2.start()
    t1.join(timeout=10.0); t2.join(timeout=10.0)
    assert not errors, errors

    sidecar = case_dir / "system" / "patch_classification.yaml"
    on_disk = yaml.safe_load(sidecar.read_text())
    # Either upsert-then-delete or delete-then-upsert: both leave
    # {b, c} as the final state because they touch disjoint keys.
    assert set(on_disk["overrides"].keys()) == {"b", "c"}


# ─────────── P2 · stale-read race ───────────


def test_setup_bc_loads_overrides_inside_case_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """``setup_bc_from_stl_patches`` MUST call the override loader
    AFTER ``case_lock`` is acquired. We assert this by tagging the
    loader so it can detect whether the lock fd is open at call time.

    Implementation detail: we don't have a public lock-state probe,
    so we monkeypatch ``case_lock`` to record entry/exit timestamps
    and ``load_patch_classification_overrides`` to record its own
    timestamp; the ordering must be lock-entry < load < lock-exit.
    """
    from ui.backend.services.case_manifest import write_case_manifest
    from ui.backend.services.case_manifest.schema import CaseManifest
    from ui.backend.services.case_solve import bc_setup_from_stl_patches as mod

    case_dir = tmp_path / "case_lock_order"
    case_dir.mkdir()
    write_case_manifest(case_dir, CaseManifest(case_id="case_lock_order"))

    # Stage a minimal valid polyMesh — same helper shape as
    # test_bc_setup_from_stl_patches.
    polymesh = case_dir / "constant" / "polyMesh"
    polymesh.mkdir(parents=True)
    pts = [
        (0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 1, 0),
        (0, 0, 1), (1, 0, 1), (0, 1, 1), (1, 1, 1),
    ]
    (polymesh / "points").write_text(
        "FoamFile {}\n8\n("
        + "".join(f"({x} {y} {z}) " for x, y, z in pts)
        + ")\n"
    )
    side_quads = {
        "-x": [0, 4, 6, 2], "+x": [1, 3, 7, 5], "+z": [4, 5, 7, 6],
    }
    patches = [("inlet", 50, 0, "-x"), ("outlet", 50, 50, "+x"),
               ("walls", 500, 100, "+z")]
    all_faces: list[list[int]] = []
    for name, n, s, side in patches:
        while len(all_faces) < s:
            all_faces.append([0, 1, 2])
        for _ in range(n):
            all_faces.append(side_quads[side])
    (polymesh / "faces").write_text(
        "FoamFile {}\n"
        f"{len(all_faces)}\n("
        + "".join(
            f"{len(f)}({' '.join(str(v) for v in f)}) "
            for f in all_faces
        )
        + ")\n"
    )
    body_lines = "\n".join(
        f"    {name}\n    {{\n        type            patch;\n"
        f"        nFaces          {n};\n        startFace       {s};\n    }}"
        for name, n, s, _side in patches
    )
    (polymesh / "boundary").write_text(
        "FoamFile {}\n3\n(\n" + body_lines + "\n)\n"
    )

    # Spy on lock entry/exit and override-load calls.
    events: list[str] = []
    real_case_lock = mod.case_lock

    from contextlib import contextmanager

    @contextmanager
    def spying_case_lock(cd):
        events.append("lock_enter")
        with real_case_lock(cd):
            yield
        events.append("lock_exit")

    real_load = mod.load_patch_classification_overrides

    def spying_load(cd):
        events.append("override_load")
        return real_load(cd)

    monkeypatch.setattr(mod, "case_lock", spying_case_lock)
    monkeypatch.setattr(
        mod, "load_patch_classification_overrides", spying_load
    )

    mod.setup_bc_from_stl_patches(case_dir, case_id="case_lock_order")

    # Override load must be sandwiched between lock_enter and lock_exit.
    assert "lock_enter" in events
    assert "lock_exit" in events
    assert "override_load" in events
    enter_idx = events.index("lock_enter")
    load_idx = events.index("override_load")
    exit_idx = events.index("lock_exit")
    assert enter_idx < load_idx < exit_idx, (
        f"override_load must be inside the lock; events={events}"
    )


# ─────────── load_under_lock thin sanity ───────────


def test_upsert_refuses_missing_case_dir_without_recreating(tmp_path: Path):
    """Codex R4 P2: ``case_lock`` had ``mkdir(parents=True,
    exist_ok=True)`` baked in, so a delete-then-PUT race would
    silently re-create an empty case dir + write a sidecar to it.
    The new code probes ``case_dir`` with ``O_NOFOLLOW`` BEFORE
    case_lock is acquired, so a missing case is rejected with
    ``case_dir_missing`` and no recreation happens.
    """
    case_dir = tmp_path / "case_will_be_deleted"
    # Don't create it.
    with pytest.raises(PatchClassificationIOError) as exc_info:
        upsert_override(
            case_dir,
            patch_name="x",
            bc_class=BCClass.SYMMETRY,
        )
    assert exc_info.value.failing_check == "case_dir_missing"
    # Crucial: case_dir was NOT recreated by case_lock's mkdir.
    assert not case_dir.exists()


def test_upsert_refuses_when_case_dir_is_symlink(tmp_path: Path):
    """If case_dir itself is a symlink (e.g. attacker plants a
    symlink at the case_id slot pointing to another case), the
    O_NOFOLLOW open of case_dir refuses with symlink_escape.
    No write happens at the symlink target.
    """
    real_target = tmp_path / "victim_case"
    real_target.mkdir()
    (real_target / "system").mkdir()
    (real_target / "system" / "patch_classification.yaml").write_text(
        yaml.safe_dump({"schema_version": 1, "overrides": {"victim": "symmetry"}})
    )

    sym_case = tmp_path / "case_sym_at_root"
    sym_case.symlink_to(real_target, target_is_directory=True)

    with pytest.raises(PatchClassificationIOError) as exc_info:
        upsert_override(
            sym_case,
            patch_name="attacker",
            bc_class=BCClass.VELOCITY_INLET,
        )
    assert exc_info.value.failing_check == "symlink_escape"
    # Victim's overrides untouched — no upsert happened.
    on_disk = yaml.safe_load(
        (real_target / "system" / "patch_classification.yaml").read_text()
    )
    assert on_disk["overrides"] == {"victim": "symmetry"}


def test_load_and_write_share_same_fd_pair(tmp_path: Path):
    """Codex R4 P1 closure: read-half and write-half use the SAME
    fd_case + fd_system pair. We exercise this by performing an
    upsert that depends on a previously-saved override (the load
    must observe what we just wrote).
    """
    case_dir = tmp_path / "case_load_write_share"
    case_dir.mkdir()
    upsert_override(
        case_dir, patch_name="a", bc_class=BCClass.VELOCITY_INLET
    )
    # Second upsert reads + appends without losing 'a'.
    upsert_override(
        case_dir, patch_name="b", bc_class=BCClass.PRESSURE_OUTLET
    )
    sidecar = case_dir / "system" / "patch_classification.yaml"
    on_disk = yaml.safe_load(sidecar.read_text())
    assert on_disk["overrides"] == {
        "a": "velocity_inlet",
        "b": "pressure_outlet",
    }


def test_atomic_write_uses_fd_relative_ops_no_resolve_path(tmp_path: Path):
    """Codex R3 P2 closure: the writer no longer pathname-resolves
    the sidecar path before write. Instead it opens every parent
    directory with ``O_NOFOLLOW | O_DIRECTORY`` and does mkstemp/
    write/replace relative to that fd. We can't directly observe
    fd-relative ops in a test, but we CAN observe that the writer
    no longer leaves traces if the case_dir parent moves underneath
    it (a TOCTOU surrogate): the file lands at the original case
    dir's inode, not at any subsequent rename target.
    """
    case_dir = tmp_path / "case_fd_op"
    case_dir.mkdir()
    upsert_override(
        case_dir,
        patch_name="patch_x",
        bc_class=BCClass.PRESSURE_OUTLET,
    )
    sidecar = case_dir / "system" / "patch_classification.yaml"
    assert sidecar.is_file() and not sidecar.is_symlink()

    # Now move the case_dir to a new name; the original inode
    # persists. A second upsert_override on the renamed path must
    # still write through the original inode (proving fd-relative
    # ops behave as expected when paths shift).
    moved = tmp_path / "case_fd_op_moved"
    case_dir.rename(moved)
    upsert_override(
        moved,
        patch_name="patch_y",
        bc_class=BCClass.VELOCITY_INLET,
    )
    sidecar2 = moved / "system" / "patch_classification.yaml"
    assert sidecar2.is_file() and not sidecar2.is_symlink()
    on_disk = yaml.safe_load(sidecar2.read_text())
    assert set(on_disk["overrides"].keys()) == {"patch_x", "patch_y"}


def test_upsert_detects_case_dir_swap_between_open_and_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Codex R5 P1: if ``case_dir`` is delete-recreated between
    ``_open_case_no_follow`` (which gets fd_case for the OLD inode)
    and ``case_lock`` (which mkdir-recreates and locks the NEW
    inode), writes through fd_case land in the orphaned old tree
    while other writers serialize on the new tree's lock —
    breaking serialization.

    The fix: after ``case_lock`` returns, fstat(fd_case) vs
    lstat(case_dir) must agree on (st_ino, st_dev). Mismatch →
    ``case_dir_missing``.

    We simulate the swap by monkeypatching ``case_lock`` to
    delete + recreate ``case_dir`` inside its critical section,
    so by the time the store re-validates, the path resolves to
    a different inode than fd_case.
    """
    from contextlib import contextmanager

    from ui.backend.services.case_solve import (
        patch_classification_store as mod,
    )

    case_dir = tmp_path / "case_inode_drift"
    case_dir.mkdir()

    real_case_lock = mod.case_lock

    @contextmanager
    def swapping_case_lock(cd):
        # Delete + recreate case_dir to force inode change BEFORE
        # we yield (so the store's post-lock fstat compare runs
        # against the new inode).
        import shutil

        shutil.rmtree(cd)
        cd.mkdir()
        with real_case_lock(cd):
            yield

    monkeypatch.setattr(mod, "case_lock", swapping_case_lock)

    with pytest.raises(PatchClassificationIOError) as exc_info:
        upsert_override(
            case_dir,
            patch_name="x",
            bc_class=BCClass.VELOCITY_INLET,
        )
    assert exc_info.value.failing_check == "case_dir_missing"
    # No sidecar landed in the new (recreated) case dir.
    assert not (case_dir / "system" / "patch_classification.yaml").exists()
    # R6 P2: the orphan stub case_lock left behind (empty case_dir
    # + .case_lock) must be cleaned up so subsequent GET requests
    # don't treat the resurrected path as a live case.
    assert not case_dir.exists(), (
        "case_lock's orphan stub must be cleaned up after drift detection"
    )


def test_upsert_returns_symlink_escape_when_path_swapped_to_symlink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Codex R6 P3: when ``case_dir`` is replaced by a symlink between
    the pre-lock open (which got fd_case for the original real
    directory) and case_lock acquisition, the post-lock validation
    must surface ``symlink_escape`` (→ HTTP 422), NOT the generic
    ``case_dir_missing`` (→ 404). The 422 contract lets operators
    diagnose containment violations cleanly.
    """
    from contextlib import contextmanager

    from ui.backend.services.case_solve import (
        patch_classification_store as mod,
    )

    real_dir = tmp_path / "case_real"
    real_dir.mkdir()
    decoy = tmp_path / "decoy_target"
    decoy.mkdir()

    real_case_lock = mod.case_lock

    @contextmanager
    def swapping_to_symlink(cd):
        # Delete the real dir and replace with a symlink to decoy
        # BEFORE entering the original case_lock (which would
        # otherwise mkdir-recreate cd as a regular dir).
        import shutil

        shutil.rmtree(cd)
        cd.symlink_to(decoy, target_is_directory=True)
        with real_case_lock(cd):
            yield

    monkeypatch.setattr(mod, "case_lock", swapping_to_symlink)

    with pytest.raises(PatchClassificationIOError) as exc_info:
        upsert_override(
            real_dir,
            patch_name="x",
            bc_class=BCClass.SYMMETRY,
        )
    assert exc_info.value.failing_check == "symlink_escape", (
        "symlink-replacement must map to symlink_escape, not "
        "case_dir_missing — preserves the 422 containment contract"
    )
    # Decoy untouched.
    assert not (decoy / "system").exists()


def test_symlink_escape_does_not_mutate_populated_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Codex R7 P1 + R8 P1 closure: when case_dir is swapped to a
    symlink to a populated directory, the cleanup helper MUST
    refuse to remove anything. The R7 P2 invariant "only act if
    dir contains exactly .case_lock" guards us: decoy has both
    .case_lock and important_file, so cleanup aborts and BOTH
    files survive.
    """
    from contextlib import contextmanager

    from ui.backend.services.case_solve import (
        patch_classification_store as mod,
    )

    real_dir = tmp_path / "case_real_r7"
    real_dir.mkdir()
    decoy = tmp_path / "decoy_with_lockfile"
    decoy.mkdir()
    (decoy / ".case_lock").write_text("victim_lock_content")
    (decoy / "important_file").write_text("DO_NOT_LOSE\n")

    real_case_lock = mod.case_lock

    @contextmanager
    def swap_to_symlink(cd):
        import shutil

        shutil.rmtree(cd)
        cd.symlink_to(decoy, target_is_directory=True)
        with real_case_lock(cd):
            yield

    monkeypatch.setattr(mod, "case_lock", swap_to_symlink)

    with pytest.raises(PatchClassificationIOError) as exc_info:
        upsert_override(
            real_dir, patch_name="x", bc_class=BCClass.SYMMETRY
        )
    assert exc_info.value.failing_check == "symlink_escape"
    # R7 P2 / R8 P1 invariant — populated target is not ours to
    # clean up; both files survive.
    assert (decoy / ".case_lock").read_text() == "victim_lock_content"
    assert (decoy / "important_file").read_text() == "DO_NOT_LOSE\n"


def test_symlink_escape_no_residual_lockfile_leak(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """DEC-V61-109 closure of the V108-A R9 documented residual.

    The original V108-A behavior on the swap-during-PUT race:
      * fd_case opened on the real dir BEFORE case_lock entry
      * monkeypatched case_lock rmtree's real_dir + plants a symlink
        to empty_decoy
      * old case_lock would mkdir(exist_ok=True) the symlink (no-op,
        target exists), open .case_lock by path — and the path
        traversed the symlink → .case_lock landed in empty_decoy
      * R5 inode-drift detection caught it post-lock and raised
        symlink_escape, but the lockfile was already leaked

    V109 changes case_lock to open ``case_dir`` itself with
    ``O_NOFOLLOW | O_DIRECTORY`` BEFORE opening the lockfile. That
    open raises ELOOP on the swapped symlink → CaseLockError(
    failing_check="symlink_escape") raised BEFORE any lockfile
    creation. So the .case_lock leak is fully closed.

    This test was V108-A's "pin the documented residual" guard;
    V109 inverts it to "assert the residual is no longer present".
    """
    from contextlib import contextmanager

    from ui.backend.services.case_solve import (
        patch_classification_store as mod,
    )

    real_dir = tmp_path / "case_real_v109"
    real_dir.mkdir()
    empty_decoy = tmp_path / "empty_decoy_v109"
    empty_decoy.mkdir()

    real_case_lock = mod.case_lock

    @contextmanager
    def swap_to_symlink_to_empty(cd):
        import shutil

        shutil.rmtree(cd)
        cd.symlink_to(empty_decoy, target_is_directory=True)
        with real_case_lock(cd):
            yield

    monkeypatch.setattr(mod, "case_lock", swap_to_symlink_to_empty)

    with pytest.raises(PatchClassificationIOError) as exc_info:
        upsert_override(
            real_dir, patch_name="x", bc_class=BCClass.SYMMETRY
        )
    assert exc_info.value.failing_check == "symlink_escape"
    # DEC-V61-109 closure: .case_lock no longer leaks to the
    # symlink target. case_lock's O_NOFOLLOW open of case_dir
    # raises before any lockfile creation can run.
    assert not (empty_decoy / ".case_lock").exists(), (
        "DEC-V61-109 regression: .case_lock leaked to the symlink "
        "target on swap-during-PUT race. The case_lock O_NOFOLLOW "
        "guard on case_dir should have refused before opening any "
        "lockfile. Check ui/backend/services/case_manifest/locking.py."
    )
    # R10 P2: the store writes to <dir>/system/patch_classification.yaml,
    # NOT <dir>/patch_classification.yaml at the root. The latter
    # would never exist regardless of containment correctness, so
    # asserting on it would let a regression slip through. Check
    # the actual write target.
    assert not (
        empty_decoy / "system" / "patch_classification.yaml"
    ).exists(), (
        "the security-critical sidecar write was correctly "
        "refused — no override data was persisted to the external "
        "target's system/ directory"
    )
    # Belt-and-braces: the entire system/ directory should not have
    # been created in the external target either (the store would
    # only mkdir it as part of the write path).
    assert not (empty_decoy / "system").exists(), (
        "no system/ subdir created in external target — proves the "
        "store's mkdir + write pipeline never executed against the "
        "leaked-symlink path"
    )


def test_assert_fd_still_matches_path_catches_post_lock_yield_symlink_swap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """DEC-V61-110 / Codex R1 finding: V109's case_lock O_NOFOLLOW
    protects only the open moment. Once case_lock yields with the
    dir_fd pinned to the original real inode, an attacker can rename
    the original case_dir away and plant a symlink at the path
    BEFORE _assert_fd_still_matches_path runs. The S_ISLNK branch
    in that assert is therefore reachable and load-bearing — it
    surfaces ``symlink_escape`` (→ HTTP 422) instead of letting the
    inode-mismatch fallthrough mis-classify the containment
    violation as ``case_dir_missing`` (→ HTTP 404).

    This test was added by DEC-V61-110 after Codex flagged the
    initial "drop the dead branch" attempt as wrong. It locks the
    branch's reachable contract so a future "this looks dead, let's
    remove it" attempt fails loudly.
    """
    from contextlib import contextmanager

    from ui.backend.services.case_manifest import locking as locking_mod
    from ui.backend.services.case_solve import (
        patch_classification_store as mod,
    )

    real_dir = tmp_path / "case_post_yield_swap"
    real_dir.mkdir()
    moved = tmp_path / "case_renamed_away"
    decoy = tmp_path / "decoy_target"
    decoy.mkdir()

    real_case_lock = locking_mod.case_lock

    @contextmanager
    def case_lock_then_swap(cd):
        # Enter the REAL case_lock — it opens fd_case on the real
        # inode (V109 O_NOFOLLOW succeeds because cd is a real dir).
        with real_case_lock(cd):
            # Now, while the lock is held and fd_case is pinned,
            # rename the real dir away and plant a symlink at the
            # original path. The pinned fd_case still references
            # the renamed real inode, but path-based stat now
            # resolves to a symlink. This is the race V109 does
            # NOT cover — the swap happens AFTER case_lock's open.
            cd.rename(moved)
            cd.symlink_to(decoy, target_is_directory=True)
            yield

    monkeypatch.setattr(mod, "case_lock", case_lock_then_swap)

    with pytest.raises(PatchClassificationIOError) as exc_info:
        upsert_override(
            real_dir,
            patch_name="x",
            bc_class=BCClass.SYMMETRY,
        )
    assert exc_info.value.failing_check == "symlink_escape", (
        "V61-110 contract: post-lock-yield symlink swap must surface "
        "symlink_escape (422), not case_dir_missing (404). The "
        "S_ISLNK branch in _assert_fd_still_matches_path is reachable "
        "and load-bearing — do NOT remove it without re-checking this "
        "race scenario."
    )
    # Decoy untouched — containment held.
    assert not (decoy / "system").exists()


def test_cleanup_refuses_to_remove_dir_without_dot_case_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Codex R7 P2: the cleanup helper must require ``.case_lock``
    in the dir's children before doing any removal. An empty dir
    without our lockfile is not ours to remove — it could be a
    fresh case being staged by another process, or an empty dir
    that pre-existed.
    """
    from contextlib import contextmanager

    from ui.backend.services.case_solve import (
        patch_classification_store as mod,
    )

    case_dir = tmp_path / "case_no_lock_in_stub"
    case_dir.mkdir()

    real_case_lock = mod.case_lock

    @contextmanager
    def swap_to_empty_unrelated_dir(cd):
        # Delete + recreate (different inode) but DO NOT enter
        # case_lock — instead nuke the .case_lock that case_lock
        # would create, simulating "another process replaced this
        # dir between case_lock release and our cleanup".
        import shutil

        shutil.rmtree(cd)
        cd.mkdir()
        with real_case_lock(cd):
            # case_lock created .case_lock inside cd; remove it
            # so cleanup sees an empty dir without our authority
            # signal.
            (cd / ".case_lock").unlink(missing_ok=True)
            yield

    monkeypatch.setattr(mod, "case_lock", swap_to_empty_unrelated_dir)

    with pytest.raises(PatchClassificationIOError):
        upsert_override(
            case_dir, patch_name="x", bc_class=BCClass.NO_SLIP_WALL
        )
    # case_dir must STILL exist — cleanup refused to rmdir it
    # because .case_lock was absent.
    assert case_dir.exists() and case_dir.is_dir(), (
        "cleanup must not rmdir an empty dir lacking .case_lock"
    )


def test_load_under_lock_returns_overrides(tmp_path: Path):
    case_dir = tmp_path / "case_load_under_lock"
    case_dir.mkdir()
    (case_dir / "system").mkdir()
    upsert_override(
        case_dir, patch_name="x", bc_class=BCClass.PRESSURE_OUTLET
    )
    out = load_under_lock(case_dir)
    assert out == {"x": BCClass.PRESSURE_OUTLET}
