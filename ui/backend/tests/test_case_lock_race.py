"""DEC-V61-102 Phase 1 round-2 P1-HIGH closure · race-condition tests.

Codex round-2 (commit 1818ad2) flagged the user-override invariant as
fixed only for serial calls: a concurrent POST /dicts landing between
``is_user_override`` and the AI write could still clobber the user
content while the manifest ended up source=user (manifest+disk
divergence).

The fix is :func:`case_lock` serialization on both code paths. These
tests prove that under contention, the final state is always
self-consistent: manifest.source matches actual disk content.
"""
from __future__ import annotations

import threading
import time
from pathlib import Path

from ui.backend.services.case_manifest import (
    CaseManifest,
    case_lock,
    mark_user_override,
    read_case_manifest,
    write_case_manifest,
)
from ui.backend.services.case_solve import bc_setup as bc_setup_mod
from ui.backend.services.case_solve.bc_setup import _author_dicts


def _stage(case_dir: Path) -> None:
    case_dir.mkdir(parents=True, exist_ok=True)
    write_case_manifest(case_dir, CaseManifest(case_id=case_dir.name))


def test_case_lock_serializes_concurrent_holders(tmp_path):
    """Two threads grabbing the same case_lock cannot overlap critical
    sections — verifies the lock is actually exclusive and not just
    decorative."""
    case_dir = tmp_path / "case-lock-basic"
    case_dir.mkdir()

    in_critical = []  # noqa
    overlap_detected = threading.Event()

    def worker(tag: str):
        with case_lock(case_dir):
            in_critical.append(tag)
            if len(in_critical) > 1:
                overlap_detected.set()
            time.sleep(0.05)
            in_critical.remove(tag)

    threads = [threading.Thread(target=worker, args=(f"t{i}",)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not overlap_detected.is_set(), "case_lock failed to serialize critical section"


def test_concurrent_user_edit_and_ai_author_no_divergence(tmp_path, monkeypatch):
    """The race Codex flagged: user POST /dicts lands while bc_setup is
    mid-flight. With the lock in place, whichever holder runs first
    completes fully before the other starts, so the final manifest +
    disk are always consistent.

    Setup: monkeypatch ``is_user_override`` to sleep briefly so the
    race window is large enough for the test to deterministically
    schedule both threads. Without the lock the original race would
    fire here; with the lock, post-condition is always consistent."""
    case_dir = tmp_path / "case-race"
    _stage(case_dir)

    # Record the original is_user_override and wrap it with a delay
    # to widen the race window. We delay BEFORE returning so a
    # concurrent mark_user_override has time to land between the
    # check and our (locked) write decision.
    real_check = bc_setup_mod.is_user_override

    def slow_check(case_dir, *, relative_path):
        time.sleep(0.02)
        return real_check(case_dir, relative_path=relative_path)

    monkeypatch.setattr(bc_setup_mod, "is_user_override", slow_check)

    user_content = b"USER edited controlDict\n"

    def ai_author():
        # bc_setup._author_dicts is normally called via setup_ldc_bc
        # which already wraps it in case_lock. We acquire the lock
        # explicitly here so this test exercises the same critical
        # section without needing a real polyMesh.
        with case_lock(case_dir):
            _author_dicts(case_dir)

    def user_edit():
        # Slight head-start so user grabs the lock first; AI then
        # waits, observes source=user, and skips the path.
        time.sleep(0.005)
        with case_lock(case_dir):
            (case_dir / "system").mkdir(parents=True, exist_ok=True)
            (case_dir / "system" / "controlDict").write_bytes(user_content)
            mark_user_override(
                case_dir,
                relative_path="system/controlDict",
                new_content=user_content,
            )

    t1 = threading.Thread(target=ai_author)
    t2 = threading.Thread(target=user_edit)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    manifest = read_case_manifest(case_dir)
    entry = manifest.overrides.raw_dict_files.get("system/controlDict")
    on_disk = (case_dir / "system" / "controlDict").read_bytes()

    # The critical invariant: whatever order they ran in, the manifest
    # source must match the disk content's authoring side.
    if entry and entry.source == "user":
        assert on_disk == user_content, (
            "MANIFEST+DISK DIVERGENCE: manifest says source=user but "
            "disk content is the AI re-author"
        )
    else:
        # AI ran second and the user override was created before AI
        # could see it — but this would mean source=user on the manifest,
        # which contradicts entry.source != 'user'. So this branch only
        # fires if user_edit somehow didn't land at all (test bug).
        # Either way the invariant holds: source=ai means disk should
        # be AI-authored, NOT the user content.
        assert on_disk != user_content or entry is None, (
            "MANIFEST+DISK DIVERGENCE: manifest says source=ai (or none) "
            "but disk content is the user version"
        )


def test_lock_releases_on_exception(tmp_path):
    """fcntl.flock must release even if the body raises — otherwise
    a single failed bc_setup would deadlock the whole case."""
    case_dir = tmp_path / "case-exc"
    case_dir.mkdir()

    try:
        with case_lock(case_dir):
            raise RuntimeError("simulated mid-write failure")
    except RuntimeError:
        pass

    # Should be able to re-acquire immediately. If lock leaked, this
    # would block forever; thread+timeout makes the failure visible.
    acquired = threading.Event()

    def grab():
        with case_lock(case_dir):
            acquired.set()

    t = threading.Thread(target=grab)
    t.start()
    t.join(timeout=2.0)
    assert acquired.is_set(), "case_lock leaked after exception"
