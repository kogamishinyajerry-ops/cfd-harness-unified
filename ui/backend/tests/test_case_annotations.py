"""Tests for the case_annotations package (M-AI-COPILOT Tier-A · DEC-V61-098).

Spec_v2 §F failure-mode classes covered:

- ``Stability``: face_id stability across mesh regen (the critical
  novel-failure-mode test per surface_scan_2026-04-29.md §5).
- ``Persistence``: AI write of a user_authoritative face is silently
  dropped (sticky invariant).
- ``4xx surface``: schema_version mismatch · case_id mismatch ·
  parse_error · symlink_escape all map to AnnotationsIOError with
  the correct ``failing_check`` tag.
- ``Concurrency``: revision conflict on save raises
  AnnotationsRevisionConflict with both attempted and current revisions.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml

from ui.backend.services.case_annotations import (
    FACE_ID_HASH_LEN,
    FACE_ID_PREFIX,
    SCHEMA_VERSION,
    AnnotationsIOError,
    AnnotationsRevisionConflict,
    empty_annotations,
    face_id,
    load_annotations,
    merge_face,
    save_annotations,
)


# ────────── face_id stability ──────────


def test_face_id_format():
    """face_id has the canonical fid_<16hex> shape."""
    fid = face_id([(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0)])
    assert fid.startswith(FACE_ID_PREFIX)
    suffix = fid[len(FACE_ID_PREFIX):]
    assert len(suffix) == FACE_ID_HASH_LEN
    int(suffix, 16)  # must be valid hex; raises ValueError otherwise


def test_face_id_independent_of_vertex_order():
    """Same face presented with different vertex orderings → same id."""
    v1 = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0), (0.0, 1.0, 0.0)]
    v2 = [(1.0, 1.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 0.0), (1.0, 0.0, 0.0)]
    v3 = [(0.0, 1.0, 0.0), (1.0, 1.0, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, 0.0)]
    assert face_id(v1) == face_id(v2) == face_id(v3)


def test_face_id_distinguishes_different_faces():
    """Two different geometric faces → different ids."""
    f1 = face_id([(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)])
    f2 = face_id([(0.0, 0.0, 1.0), (1.0, 0.0, 1.0), (0.0, 1.0, 1.0)])
    assert f1 != f2


def test_face_id_absorbs_floating_point_drift_at_9_decimals():
    """Coordinates equal at 9 decimals → same id (mesh regen tolerance).

    This is the critical novel-failure-mode test per spec_v2 §F
    Stability class. gmshToFoam is deterministic for the same input
    geometry, but tiny last-bit drift (e.g., 1.0 vs 1.0 + 1e-12)
    must NOT change the face_id.
    """
    base = [(0.123456789, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0)]
    drift = [
        # Drift at decimal 12 — well below 9-decimal rounding.
        (0.123456789 + 1e-12, 0.0, 0.0),
        (1.0 + 1e-13, 0.0, 0.0),
        (1.0, 1.0 + 5e-13, 0.0),
    ]
    assert face_id(base) == face_id(drift)


def test_face_id_normalizes_signed_zero():
    """Codex DEC-V61-098 round-1 finding: ``gmshToFoam`` may emit
    either ``0.0`` or ``-0.0`` depending on numerical context, and
    ``repr()`` distinguishes them — without normalization the same
    geometric face produced different hashes across mesh regens.

    Fix: signed-zero normalization via ``+ 0.0`` (IEEE 754 flips
    ``-0.0 → 0.0``). This test pins the contract.
    """
    f_neg = [(-0.0, 0.0, 0.0), (1.0, -0.0, 0.0), (0.0, 1.0, -0.0)]
    f_pos = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)]
    f_mixed = [(-0.0, 0.0, 0.0), (1.0, 0.0, -0.0), (-0.0, 1.0, 0.0)]
    assert face_id(f_neg) == face_id(f_pos) == face_id(f_mixed), (
        "signed-zero normalization must collapse -0.0 → 0.0 so the "
        "same geometric face hashes consistently across gmshToFoam runs"
    )


def test_face_id_distinguishes_at_8th_decimal():
    """Drift at the 8th decimal IS large enough to flip the hash.

    9-decimal rounding tolerates up to ~5e-10 drift; anything coarser
    (1e-8 or larger) will round to a distinct number and the hash
    changes. This bounds how much numerical noise the face_id can
    absorb — useful contract for downstream callers.
    """
    base = [(0.5, 0.5, 0.5), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)]
    coarser_drift = [(0.500000001, 0.5, 0.5), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)]
    assert face_id(base) != face_id(coarser_drift)


# ────────── empty_annotations + merge_face ──────────


def test_empty_annotations_initial_shape():
    doc = empty_annotations("case_001")
    assert doc["schema_version"] == SCHEMA_VERSION
    assert doc["case_id"] == "case_001"
    assert doc["revision"] == 0
    assert doc["faces"] == []
    assert "last_modified" in doc


def test_merge_face_inserts_new_face():
    doc = empty_annotations("case_001")
    fid = face_id([(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)])
    new = {
        "face_id": fid,
        "name": "lid",
        "patch_type": "wall",
        "confidence": "ai_confident",
    }
    merge_face(doc, new, annotated_by="ai:rule-based")
    assert len(doc["faces"]) == 1
    assert doc["faces"][0]["face_id"] == fid
    assert doc["faces"][0]["name"] == "lid"
    assert doc["faces"][0]["annotated_by"] == "ai:rule-based"
    assert "annotated_at" in doc["faces"][0]


def test_merge_face_updates_existing_face():
    doc = empty_annotations("case_001")
    fid = face_id([(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)])
    merge_face(doc, {"face_id": fid, "name": "old"}, annotated_by="human")
    merge_face(doc, {"face_id": fid, "name": "new"}, annotated_by="human")
    assert len(doc["faces"]) == 1
    assert doc["faces"][0]["name"] == "new"


def test_merge_face_user_authoritative_is_sticky_against_ai():
    """Sticky invariant per spec_v2 §B.1: AI write of a
    user_authoritative face is silently dropped.
    """
    doc = empty_annotations("case_001")
    fid = face_id([(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)])
    merge_face(
        doc,
        {"face_id": fid, "name": "inlet", "confidence": "user_authoritative"},
        annotated_by="human",
    )
    # AI tries to overwrite — should be silently ignored.
    merge_face(
        doc,
        {"face_id": fid, "name": "wall", "confidence": "ai_confident"},
        annotated_by="ai:rule-based",
    )
    assert doc["faces"][0]["name"] == "inlet"
    assert doc["faces"][0]["confidence"] == "user_authoritative"
    assert doc["faces"][0]["annotated_by"] == "human"


def test_merge_face_user_can_override_user_authoritative():
    """Sticky invariant only blocks AI writes; another human write
    DOES override (engineer changing their own mind).
    """
    doc = empty_annotations("case_001")
    fid = face_id([(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)])
    merge_face(
        doc,
        {"face_id": fid, "name": "inlet", "confidence": "user_authoritative"},
        annotated_by="human",
    )
    merge_face(
        doc,
        {"face_id": fid, "name": "outlet", "confidence": "user_authoritative"},
        annotated_by="human",
    )
    assert doc["faces"][0]["name"] == "outlet"


# ────────── load + save round-trip ──────────


def test_save_then_load_roundtrip(tmp_path):
    case_dir = tmp_path / "case_rt"
    case_dir.mkdir()
    doc = empty_annotations("case_rt")
    fid = face_id([(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)])
    merge_face(
        doc, {"face_id": fid, "name": "lid"}, annotated_by="human"
    )
    saved = save_annotations(case_dir, doc, if_match_revision=0)
    assert saved["revision"] == 1
    loaded = load_annotations(case_dir, case_id="case_rt")
    assert loaded["revision"] == 1
    assert loaded["faces"][0]["face_id"] == fid
    assert loaded["faces"][0]["name"] == "lid"


def test_load_returns_empty_when_file_missing(tmp_path):
    case_dir = tmp_path / "case_empty"
    case_dir.mkdir()
    loaded = load_annotations(case_dir, case_id="case_empty")
    assert loaded["revision"] == 0
    assert loaded["faces"] == []


def test_load_raises_on_case_dir_missing(tmp_path):
    with pytest.raises(AnnotationsIOError) as exc:
        load_annotations(tmp_path / "does_not_exist", case_id="x")
    assert exc.value.failing_check == "case_dir_missing"


def test_load_raises_on_schema_version_mismatch(tmp_path):
    case_dir = tmp_path / "case_sv"
    case_dir.mkdir()
    bad = {
        "schema_version": 999,
        "case_id": "case_sv",
        "revision": 1,
        "last_modified": "2026-04-29T00:00:00Z",
        "faces": [],
    }
    (case_dir / "face_annotations.yaml").write_text(yaml.safe_dump(bad))
    with pytest.raises(AnnotationsIOError) as exc:
        load_annotations(case_dir, case_id="case_sv")
    assert exc.value.failing_check == "schema_version_mismatch"


def test_load_raises_on_case_id_mismatch(tmp_path):
    case_dir = tmp_path / "case_cid"
    case_dir.mkdir()
    save_annotations(case_dir, empty_annotations("case_cid"), if_match_revision=0)
    with pytest.raises(AnnotationsIOError) as exc:
        load_annotations(case_dir, case_id="WRONG_ID")
    assert exc.value.failing_check == "parse_error"


def test_load_raises_on_yaml_corruption(tmp_path):
    case_dir = tmp_path / "case_corrupt"
    case_dir.mkdir()
    (case_dir / "face_annotations.yaml").write_text("not: valid: yaml: nested:")
    with pytest.raises(AnnotationsIOError) as exc:
        load_annotations(case_dir, case_id="case_corrupt")
    assert exc.value.failing_check == "parse_error"


def test_load_raises_on_root_not_a_mapping(tmp_path):
    case_dir = tmp_path / "case_list_root"
    case_dir.mkdir()
    (case_dir / "face_annotations.yaml").write_text("- a\n- b\n")
    with pytest.raises(AnnotationsIOError) as exc:
        load_annotations(case_dir, case_id="case_list_root")
    assert exc.value.failing_check == "parse_error"


# ────────── revision conflict ──────────


def test_save_raises_on_revision_mismatch(tmp_path):
    case_dir = tmp_path / "case_rc"
    case_dir.mkdir()
    save_annotations(case_dir, empty_annotations("case_rc"), if_match_revision=0)
    # On-disk revision is now 1. Caller passes if_match_revision=0 (stale).
    with pytest.raises(AnnotationsRevisionConflict) as exc:
        save_annotations(
            case_dir, empty_annotations("case_rc"), if_match_revision=0
        )
    assert exc.value.attempted_revision == 0
    assert exc.value.current_revision == 1


def test_save_revision_check_skipped_when_if_match_is_none(tmp_path):
    """First save (file missing) caller may pass if_match_revision=None;
    save proceeds without checking on-disk revision.
    """
    case_dir = tmp_path / "case_rcn"
    case_dir.mkdir()
    saved = save_annotations(
        case_dir, empty_annotations("case_rcn"), if_match_revision=None
    )
    assert saved["revision"] == 1


def test_save_bumps_revision_monotonically(tmp_path):
    case_dir = tmp_path / "case_mono"
    case_dir.mkdir()
    doc = empty_annotations("case_mono")
    save_annotations(case_dir, doc, if_match_revision=0)
    save_annotations(case_dir, doc, if_match_revision=1)
    final = save_annotations(case_dir, doc, if_match_revision=2)
    assert final["revision"] == 3


# ────────── symlink containment ──────────


def test_save_rejects_symlink_escape(tmp_path):
    """If the case dir contains a symlink to face_annotations.yaml that
    points outside the case root, the save must refuse.
    """
    case_dir = tmp_path / "case_symlink"
    case_dir.mkdir()
    outside = tmp_path / "outside_target.yaml"
    outside.write_text("# attacker target\n")
    # Replace the (would-be) annotations file with a symlink to outside.
    (case_dir / "face_annotations.yaml").symlink_to(outside)

    with pytest.raises(AnnotationsIOError) as exc:
        save_annotations(
            case_dir, empty_annotations("case_symlink"), if_match_revision=None
        )
    assert exc.value.failing_check == "symlink_escape"
    # Sanity: outside file untouched.
    assert outside.read_text() == "# attacker target\n"


def test_load_rejects_symlink_escape(tmp_path):
    case_dir = tmp_path / "case_symlink_load"
    case_dir.mkdir()
    outside = tmp_path / "outside.yaml"
    outside.write_text("schema_version: 1\ncase_id: x\nrevision: 0\nfaces: []\n")
    (case_dir / "face_annotations.yaml").symlink_to(outside)

    with pytest.raises(AnnotationsIOError) as exc:
        load_annotations(case_dir, case_id="case_symlink_load")
    assert exc.value.failing_check == "symlink_escape"


def test_save_immune_to_planted_tmp_symlink(tmp_path):
    """Codex DEC-V61-098 round-1 SECURITY finding: a fixed-name
    ``face_annotations.yaml.tmp`` was vulnerable to symlink planting.
    The fix uses ``tempfile.mkstemp`` to generate a random per-call
    suffix, so no pre-existing symlink at the legacy fixed filename
    can be followed.

    This test plants a symlink at the OLD fixed ``.tmp`` path AND
    pollutes the dir with a few other ``.tmp`` symlinks; save must
    succeed without touching any of the victim files.
    """
    case_dir = tmp_path / "case_tmp_symlink"
    case_dir.mkdir()
    victim = tmp_path / "victim.yaml"
    victim.write_text("BEFORE_ATTACK\n")
    # Plant the legacy fixed-name trap.
    (case_dir / "face_annotations.yaml.tmp").symlink_to(victim)
    # Plant a couple more nuisance traps with similar names.
    (case_dir / "face_annotations.bak.tmp").symlink_to(victim)
    (case_dir / "annotations.tmp").symlink_to(victim)

    saved = save_annotations(
        case_dir, empty_annotations("case_tmp_symlink"),
        if_match_revision=None,
    )
    assert saved["revision"] == 1, "save must succeed despite planted traps"
    # Critical: victim file untouched.
    assert victim.read_text() == "BEFORE_ATTACK\n", (
        "victim file was modified — random-suffix .tmp defense failed"
    )
    # And the final annotations file landed correctly.
    final = case_dir / "face_annotations.yaml"
    assert final.exists() and not final.is_symlink()


def test_save_rejects_lock_symlink_escape(tmp_path):
    """Codex DEC-V61-098 round-2 SECURITY finding: the lock file
    `.face_annotations.lock` introduced by round-1's concurrent-write
    fix is itself opened with `os.open(O_RDWR | O_CREAT)` — without
    O_NOFOLLOW, an attacker who plants a symlink at the lock path
    can redirect file creation to ANY path the backend can write to.

    Demonstrated by Codex's repro: save_ok + `outside_created_by_lock`
    (0-byte file) materialized outside the case root.

    Fix: O_NOFOLLOW on the lock open. This test pins the defense.
    """
    case_dir = tmp_path / "case_lock_symlink"
    case_dir.mkdir()
    outside = tmp_path / "lock_target_should_not_be_created"
    # Plant the symlink at the lock path. outside doesn't exist yet —
    # if the open follows the symlink it would CREATE the target.
    (case_dir / ".face_annotations.lock").symlink_to(outside)

    with pytest.raises(AnnotationsIOError) as exc:
        save_annotations(
            case_dir, empty_annotations("case_lock_symlink"),
            if_match_revision=None,
        )
    assert exc.value.failing_check == "symlink_escape"
    # Critical: the symlink target must NOT have been created.
    assert not outside.exists(), (
        "lock-file symlink target was created — O_NOFOLLOW defense failed"
    )


def test_save_rejects_lock_symlink_to_directory(tmp_path):
    """Codex DEC-V61-098 round-2 also surfaced a contract-leak case:
    when ``.face_annotations.lock`` points to a directory (or a
    symlink to a directory), the open raises ``IsADirectoryError``,
    and without wrapping it leaks as an uncategorized 500.

    Fix: wrap the os.open OSError → AnnotationsIOError so the route
    sees the uniform symlink_escape contract.
    """
    case_dir = tmp_path / "case_lock_dir"
    case_dir.mkdir()
    target_dir = tmp_path / "lock_target_dir"
    target_dir.mkdir()
    # Plant a symlink at the lock path pointing to a directory.
    (case_dir / ".face_annotations.lock").symlink_to(target_dir)

    with pytest.raises(AnnotationsIOError) as exc:
        save_annotations(
            case_dir, empty_annotations("case_lock_dir"),
            if_match_revision=None,
        )
    assert exc.value.failing_check == "symlink_escape"
    # Critical: target dir contents must not have been touched —
    # specifically no file should have been created inside it.
    assert list(target_dir.iterdir()) == [], (
        "lock-file directory-symlink defense failed: target dir was modified"
    )


def test_save_concurrent_writers_no_tmp_collision(tmp_path):
    """Codex DEC-V61-098 round-1 finding: two threads calling
    save_annotations on the same case used to collide on the shared
    ``face_annotations.yaml.tmp`` filename — one thread's rename
    moved the other thread's mid-write file, causing
    FileNotFoundError on the loser's rename.

    Fix: mkstemp generates a unique suffix per call. This test
    verifies two concurrent writers BOTH succeed without
    FileNotFoundError or other transient collision symptoms.
    Note: the second writer hits AnnotationsRevisionConflict on the
    if_match_revision check (correct behavior — it observes the
    first writer's bumped revision), NOT a transient OS race.
    """
    import threading

    case_dir = tmp_path / "case_concurrent"
    case_dir.mkdir()
    # Initialize at revision 1.
    save_annotations(case_dir, empty_annotations("case_concurrent"),
                     if_match_revision=0)

    barrier = threading.Barrier(2)
    results: list[tuple[str, str]] = []
    lock = threading.Lock()

    def worker(name: str) -> None:
        barrier.wait(timeout=5)
        try:
            out = save_annotations(
                case_dir,
                empty_annotations("case_concurrent"),
                if_match_revision=1,
            )
            with lock:
                results.append((name, f"OK rev={out['revision']}"))
        except AnnotationsRevisionConflict:
            with lock:
                results.append((name, "REVISION_CONFLICT"))
        except Exception as e:  # noqa: BLE001
            with lock:
                results.append((name, f"UNEXPECTED:{type(e).__name__}"))

    t1 = threading.Thread(target=worker, args=("a",))
    t2 = threading.Thread(target=worker, args=("b",))
    t1.start(); t2.start(); t1.join(); t2.join()

    # Exactly one writer wins; the other gets RevisionConflict.
    # Critically: NEITHER gets UNEXPECTED:FileNotFoundError or
    # similar transient OS errors from .tmp filename collision.
    outcomes = sorted(r[1] for r in results)
    unexpected = [r for r in results if r[1].startswith("UNEXPECTED")]
    assert not unexpected, (
        f"transient OS race observed: {unexpected}; "
        f"mkstemp per-call defense failed"
    )
    # One should succeed, one should hit revision conflict.
    ok_count = sum(1 for r in results if r[1].startswith("OK"))
    conflict_count = sum(1 for r in results if r[1] == "REVISION_CONFLICT")
    assert ok_count == 1 and conflict_count == 1, (
        f"expected exactly 1 OK + 1 REVISION_CONFLICT; got {outcomes}"
    )

    # Final on-disk state: revision 2.
    final = load_annotations(case_dir, case_id="case_concurrent")
    assert final["revision"] == 2


# ────────── atomic write ──────────


def test_save_is_atomic(tmp_path):
    """save_annotations must use tmp+rename so a crash mid-write
    doesn't corrupt the existing file.
    """
    case_dir = tmp_path / "case_atomic"
    case_dir.mkdir()
    save_annotations(case_dir, empty_annotations("case_atomic"), if_match_revision=0)
    annotations_file = case_dir / "face_annotations.yaml"
    original_inode = os.stat(annotations_file).st_ino

    # Second write — should NOT preserve the inode (rename creates new
    # inode for the .tmp file). This test pins the atomic-rename
    # behavior; if a future refactor switches to in-place writes, this
    # test fails loud.
    save_annotations(case_dir, empty_annotations("case_atomic"), if_match_revision=1)
    new_inode = os.stat(annotations_file).st_ino
    assert original_inode != new_inode, (
        "expected save to use tmp+rename (new inode); got in-place write"
    )

    # No leftover .tmp file.
    leftover = list(case_dir.glob("*.tmp"))
    assert leftover == [], f"tmp file leftover after save: {leftover}"
