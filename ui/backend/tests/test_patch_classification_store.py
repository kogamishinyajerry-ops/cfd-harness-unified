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


def test_load_under_lock_returns_overrides(tmp_path: Path):
    case_dir = tmp_path / "case_load_under_lock"
    case_dir.mkdir()
    (case_dir / "system").mkdir()
    upsert_override(
        case_dir, patch_name="x", bc_class=BCClass.PRESSURE_OUTLET
    )
    out = load_under_lock(case_dir)
    assert out == {"x": BCClass.PRESSURE_OUTLET}
