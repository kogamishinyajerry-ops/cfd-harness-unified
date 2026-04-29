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
