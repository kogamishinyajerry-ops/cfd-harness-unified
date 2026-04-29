"""Tests for the M9 Tier-B AI geometric classifier (DEC-V61-100 Step 2).

Covers the four geometric categories the classifier emits:

  - ldc_cube (no user pins) → uncertain · 1 lid_orientation question
  - ldc_cube (with user_authoritative pins) → confident · no questions
  - non_cube (no user pins) → uncertain · inlet_face + outlet_face
  - non_cube (with inlet+outlet pinned by name) → confident · no questions
  - degenerate (no polyMesh) → blocked · 1 run_step2_first question
  - degenerate (<8 vertices) → blocked · 1 degenerate_mesh question

Plus the classifier's contract with the wrapper:
  - setup_bc_with_annotations(use_classifier=True) on an LDC-cube
    fixture with no annotations returns uncertain (lid orientation)
  - same fixture WITH user_authoritative pin returns confident
  - force_uncertain / force_blocked take precedence over the classifier
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from ui.backend.services.ai_actions import (
    AIActionError,
    setup_bc_with_annotations,
)
from ui.backend.services.ai_actions.classifier import (
    classify_setup_bc,
)
from ui.backend.services.case_annotations import (
    SCHEMA_VERSION,
    empty_annotations,
    save_annotations,
)


# ────────── polyMesh fixtures ──────────


_POINTS_CUBE = """\
FoamFile
{
    version     2.0;
    format      ascii;
    class       vectorField;
    location    "constant/polyMesh";
    object      points;
}

8
(
(0 0 0)
(1 0 0)
(1 1 0)
(0 1 0)
(0 0 1)
(1 0 1)
(1 1 1)
(0 1 1)
)
"""

# Faces of the unit cube · 6 quad faces. Index 1 = top (z=1) — the
# lid plane setup_ldc_bc picks. Indices 0,2,3,4,5 are the other walls.
_FACES_CUBE = """\
FoamFile
{
    version     2.0;
    format      ascii;
    class       faceList;
    location    "constant/polyMesh";
    object      faces;
}

6
(
4(0 1 2 3)
4(4 5 6 7)
4(0 1 5 4)
4(2 3 7 6)
4(1 2 6 5)
4(0 3 7 4)
)
"""

# Boundary that exposes all 6 faces on a single boundary patch. After
# Step 3 (setup-bc) splits this into lid + fixedWalls, the boundary
# changes; for the classifier verification we just need the
# top-plane face to be reachable via the boundary file.
_BOUNDARY_CUBE_PRESPLIT = """\
FoamFile
{
    version     2.0;
    format      ascii;
    class       polyBoundaryMesh;
    location    "constant/polyMesh";
    object      boundary;
}

1
(
    walls
    {
        type            wall;
        nFaces          6;
        startFace       0;
    }
)
"""

# 1×1×10 channel (aspect ratio 10) — distinctly non-cube.
_POINTS_CHANNEL = """\
FoamFile
{
    version     2.0;
    format      ascii;
    class       vectorField;
    location    "constant/polyMesh";
    object      points;
}

8
(
(0 0 0)
(1 0 0)
(1 1 0)
(0 1 0)
(0 0 10)
(1 0 10)
(1 1 10)
(0 1 10)
)
"""

# 4 vertices · obviously degenerate
_POINTS_DEGENERATE = """\
FoamFile
{
    version     2.0;
    format      ascii;
    class       vectorField;
    location    "constant/polyMesh";
    object      points;
}

4
(
(0 0 0)
(1 0 0)
(0 1 0)
(0 0 1)
)
"""


def _stage_polymesh(
    case_dir: Path,
    points_text: str,
    *,
    faces_text: str | None = None,
    boundary_text: str | None = None,
) -> Path:
    """Stage a polyMesh fixture. Defaults to minimal (empty faces +
    boundary) for tests that only need points; pass ``faces_text`` and
    ``boundary_text`` for tests that need top-plane face verification.
    """
    polymesh = case_dir / "constant" / "polyMesh"
    polymesh.mkdir(parents=True)
    (polymesh / "points").write_text(points_text, encoding="utf-8")
    (polymesh / "faces").write_text(
        faces_text if faces_text is not None else "0\n(\n)\n",
        encoding="utf-8",
    )
    (polymesh / "boundary").write_text(
        boundary_text if boundary_text is not None else "0\n(\n)\n",
        encoding="utf-8",
    )
    return polymesh


_OWNER_CUBE = """\
FoamFile
{
    version     2.0;
    format      ascii;
    class       labelList;
    location    "constant/polyMesh";
    object      owner;
}

6
(
0
0
0
0
0
0
)
"""


def _stage_full_cube(case_dir: Path) -> Path:
    """Stage a complete unit-cube polyMesh fixture (points + faces +
    boundary mapping all 6 faces on a single 'walls' patch + owner).
    Returns the polyMesh dir. Used by tests that need the classifier
    to verify lid pin against actual top-plane face_ids.
    """
    polymesh = _stage_polymesh(
        case_dir,
        _POINTS_CUBE,
        faces_text=_FACES_CUBE,
        boundary_text=_BOUNDARY_CUBE_PRESPLIT,
    )
    (polymesh / "owner").write_text(_OWNER_CUBE, encoding="utf-8")
    return polymesh


def _top_face_id_of_unit_cube() -> str:
    """The face_id of the top (z=1) face of the unit cube fixture.
    Faces[1] = (4 5 6 7) → vertices (0 0 1) (1 0 1) (1 1 1) (0 1 1).
    """
    from ui.backend.services.case_annotations import face_id

    return face_id(
        [(0.0, 0.0, 1.0), (1.0, 0.0, 1.0), (1.0, 1.0, 1.0), (0.0, 1.0, 1.0)]
    )


def _empty_doc(case_id: str) -> dict[str, Any]:
    return empty_annotations(case_id)


# ────────── classifier · degenerate ──────────


def test_classifier_no_polymesh_blocks(tmp_path):
    case_dir = tmp_path / "no_mesh"
    case_dir.mkdir()
    res = classify_setup_bc(case_dir, annotations=_empty_doc("no_mesh"))
    assert res.confidence == "blocked"
    assert res.geometry_class == "degenerate"
    assert len(res.questions) == 1
    assert res.questions[0].id == "run_step2_first"


def test_classifier_too_few_vertices_blocks(tmp_path):
    case_dir = tmp_path / "tiny"
    case_dir.mkdir()
    _stage_polymesh(case_dir, _POINTS_DEGENERATE)
    res = classify_setup_bc(case_dir, annotations=_empty_doc("tiny"))
    assert res.confidence == "blocked"
    assert res.geometry_class == "degenerate"
    assert "degenerate_mesh" in {q.id for q in res.questions}


# ────────── classifier · ldc_cube ──────────


def test_classifier_cube_no_user_pins_is_uncertain(tmp_path):
    case_dir = tmp_path / "cube"
    case_dir.mkdir()
    _stage_polymesh(case_dir, _POINTS_CUBE)
    res = classify_setup_bc(case_dir, annotations=_empty_doc("cube"))
    assert res.confidence == "uncertain"
    assert res.geometry_class == "ldc_cube"
    assert len(res.questions) == 1
    assert res.questions[0].id == "lid_orientation"
    assert res.questions[0].needs_face_selection is True
    # The summary should reflect the cube finding.
    assert "cube" in res.summary.lower()


def test_classifier_cube_with_lid_named_pin_on_top_plane_is_confident(
    tmp_path,
):
    """Codex round 2 HIGH (3e8e7e1 review): a lid-named pin is
    confident ONLY if the face_id is on the top plane. This pins
    the verified-OK case: name='lid' AND face_id matches the top
    quad of the unit cube.
    """
    case_dir = tmp_path / "cube_pinned"
    case_dir.mkdir()
    _stage_full_cube(case_dir)
    annotations = _empty_doc("cube_pinned")
    annotations["faces"].append({
        "face_id": _top_face_id_of_unit_cube(),
        "name": "lid",
        "patch_type": "wall",
        "confidence": "user_authoritative",
        "annotated_by": "human",
        "annotated_at": "2026-04-29T00:00:00Z",
    })
    res = classify_setup_bc(case_dir, annotations=annotations)
    assert res.confidence == "confident"
    assert res.geometry_class == "ldc_cube"
    assert res.questions == []
    assert "verified" in res.summary.lower()


def test_classifier_cube_with_lid_named_pin_off_top_plane_is_uncertain(
    tmp_path,
):
    """Codex round 2 HIGH closure: even when the user pins a face
    NAMED 'lid', if its face_id is NOT on the top plane, classifier
    must keep the dialog open — otherwise setup_ldc_bc would silently
    use the top plane and ignore the user's intent.
    """
    case_dir = tmp_path / "cube_lid_wrong_face"
    case_dir.mkdir()
    _stage_full_cube(case_dir)
    annotations = _empty_doc("cube_lid_wrong_face")
    annotations["faces"].append({
        "face_id": "fid_definitely_not_top_plane_xxx",
        "name": "lid",  # named lid, but face_id doesn't match top plane
        "confidence": "user_authoritative",
        "annotated_by": "human",
        "annotated_at": "2026-04-29T00:00:00Z",
    })
    res = classify_setup_bc(case_dir, annotations=annotations)
    assert res.confidence == "uncertain"
    # Specific message + candidate_face_ids hint pointing at top plane.
    q = next(q for q in res.questions if q.id == "lid_orientation")
    assert "isn't on the top" in q.prompt
    assert _top_face_id_of_unit_cube() in q.candidate_face_ids


def test_classifier_cube_with_non_lid_pin_stays_uncertain(tmp_path):
    """Codex round 1 HIGH-1 closure: pinning a non-lid face (e.g. a
    side wall) does NOT make the classifier confident — setup_ldc_bc
    will still pick the top plane, so the engineer must explicitly
    confirm the lid before we hand off.
    """
    case_dir = tmp_path / "cube_side_pin"
    case_dir.mkdir()
    _stage_polymesh(case_dir, _POINTS_CUBE)
    annotations = _empty_doc("cube_side_pin")
    annotations["faces"].append({
        "face_id": "fid_side_face",
        "name": "left_wall",  # NOT 'lid'
        "patch_type": "wall",
        "confidence": "user_authoritative",
        "annotated_by": "human",
        "annotated_at": "2026-04-29T00:00:00Z",
    })
    res = classify_setup_bc(case_dir, annotations=annotations)
    assert res.confidence == "uncertain"
    assert any(q.id == "lid_orientation" for q in res.questions)


def test_classifier_cube_lid_name_case_insensitive(tmp_path):
    """The `lid` substring match should be case-insensitive — but the
    face_id still has to match the top plane."""
    case_dir = tmp_path / "cube_lid_case"
    case_dir.mkdir()
    _stage_full_cube(case_dir)
    annotations = _empty_doc("cube_lid_case")
    annotations["faces"].append({
        "face_id": _top_face_id_of_unit_cube(),
        "name": "Top_LID_face",  # mixed-case + extra prefix
        "confidence": "user_authoritative",
        "annotated_by": "human",
        "annotated_at": "2026-04-29T00:00:00Z",
    })
    res = classify_setup_bc(case_dir, annotations=annotations)
    assert res.confidence == "confident"


# ────────── classifier · non_cube ──────────


def test_classifier_channel_no_pins_asks_inlet_and_outlet(tmp_path):
    case_dir = tmp_path / "channel"
    case_dir.mkdir()
    _stage_polymesh(case_dir, _POINTS_CHANNEL)
    res = classify_setup_bc(case_dir, annotations=_empty_doc("channel"))
    assert res.confidence == "uncertain"
    assert res.geometry_class == "non_cube"
    q_ids = {q.id for q in res.questions}
    assert "inlet_face" in q_ids
    assert "outlet_face" in q_ids


def test_classifier_channel_with_inlet_and_outlet_pinned_is_blocked_until_executor_ships(
    tmp_path,
):
    """Codex round 1 HIGH-2 (cb8b8e3 review): non-cube cannot return
    confident — the only downstream executor (setup_ldc_bc) is
    LDC-only and would write incorrect lid/fixedWalls boundaries on a
    channel. Until M10/M11 ship a non-LDC executor, the path stays
    blocked even with full inlet+outlet pinning. The engineer's
    annotations are saved for future use.
    """
    case_dir = tmp_path / "channel_done"
    case_dir.mkdir()
    _stage_polymesh(case_dir, _POINTS_CHANNEL)
    annotations = _empty_doc("channel_done")
    for fid, name in [("fid_in", "inlet_main"), ("fid_out", "outlet_main")]:
        annotations["faces"].append({
            "face_id": fid,
            "name": name,
            "patch_type": "patch",
            "confidence": "user_authoritative",
            "annotated_by": "human",
            "annotated_at": "2026-04-29T00:00:00Z",
        })
    res = classify_setup_bc(case_dir, annotations=annotations)
    assert res.confidence == "blocked"
    assert res.geometry_class == "non_cube"
    assert any(
        q.id == "non_cube_executor_pending" for q in res.questions
    )


def test_classifier_channel_with_only_inlet_pinned_still_asks_outlet(
    tmp_path,
):
    case_dir = tmp_path / "channel_partial"
    case_dir.mkdir()
    _stage_polymesh(case_dir, _POINTS_CHANNEL)
    annotations = _empty_doc("channel_partial")
    annotations["faces"].append({
        "face_id": "fid_in",
        "name": "inlet_x",
        "confidence": "user_authoritative",
        "annotated_by": "human",
        "annotated_at": "2026-04-29T00:00:00Z",
    })
    res = classify_setup_bc(case_dir, annotations=annotations)
    assert res.confidence == "uncertain"
    q_ids = {q.id for q in res.questions}
    assert "inlet_face" not in q_ids  # inlet was pinned
    assert "outlet_face" in q_ids  # outlet still asked


# ────────── wrapper integration ──────────


def test_wrapper_classifier_default_on_cube_returns_uncertain(tmp_path):
    """setup_bc_with_annotations now defaults to use_classifier=True
    (DEC-V61-100 M9 Step 2). Cube fixture with no annotations should
    return uncertain — the engineer needs to confirm the lid.
    """
    case_dir = tmp_path / "wrapper_cube"
    case_dir.mkdir()
    _stage_polymesh(case_dir, _POINTS_CUBE)
    env = setup_bc_with_annotations(
        case_dir=case_dir,
        case_id="wrapper_cube",
    )
    assert env.confidence == "uncertain"
    assert any(q.id == "lid_orientation" for q in env.unresolved_questions)
    # Underlying setup_ldc_bc was NOT called — no dicts written.
    assert not (case_dir / "0").exists() and not (case_dir / "system").exists()


def test_wrapper_classifier_with_top_plane_lid_pin_returns_confident(
    tmp_path,
):
    """When the engineer pins the actual top-plane face named 'lid',
    classifier returns confident, and the wrapper runs setup_ldc_bc
    to write the dicts. The full fixture has enough polyMesh files
    for setup_ldc_bc to actually succeed end-to-end.
    """
    case_dir = tmp_path / "wrapper_cube_pinned"
    case_dir.mkdir()
    _stage_full_cube(case_dir)
    annotations = _empty_doc("wrapper_cube_pinned")
    annotations["faces"].append({
        "face_id": _top_face_id_of_unit_cube(),
        "name": "lid",
        "confidence": "user_authoritative",
        "annotated_by": "human",
        "annotated_at": "2026-04-29T00:00:00Z",
    })
    save_annotations(case_dir, annotations, if_match_revision=0)

    env = setup_bc_with_annotations(
        case_dir=case_dir,
        case_id="wrapper_cube_pinned",
    )
    assert env.confidence == "confident"
    assert env.unresolved_questions == []
    # setup_ldc_bc actually wrote the dicts.
    assert (case_dir / "0").is_dir()
    assert (case_dir / "system").is_dir()


def test_wrapper_classifier_with_non_lid_pin_stays_uncertain_no_setup_run(
    tmp_path,
):
    """Codex round 1 HIGH-1 closure (wrapper level): pinning a side
    face does NOT trigger setup_ldc_bc. Wrapper returns the
    classifier's uncertain envelope, no dicts written.
    """
    case_dir = tmp_path / "wrapper_side_pin"
    case_dir.mkdir()
    _stage_polymesh(case_dir, _POINTS_CUBE)
    annotations = _empty_doc("wrapper_side_pin")
    annotations["faces"].append({
        "face_id": "fid_left",
        "name": "left_wall",
        "confidence": "user_authoritative",
        "annotated_by": "human",
        "annotated_at": "2026-04-29T00:00:00Z",
    })
    save_annotations(case_dir, annotations, if_match_revision=0)

    env = setup_bc_with_annotations(
        case_dir=case_dir,
        case_id="wrapper_side_pin",
    )
    # Critical: classifier kept the dialog open instead of letting
    # setup_ldc_bc clobber the user's intent with a top-plane lid.
    assert env.confidence == "uncertain"
    assert any(
        q.id == "lid_orientation" for q in env.unresolved_questions
    )


def test_wrapper_force_blocked_overrides_classifier(tmp_path):
    """force_blocked still wins — even if the classifier would have
    said confident on this cube, force_blocked short-circuits.
    """
    case_dir = tmp_path / "force_block"
    case_dir.mkdir()
    _stage_polymesh(case_dir, _POINTS_CUBE)
    env = setup_bc_with_annotations(
        case_dir=case_dir,
        case_id="force_block",
        force_blocked=True,
    )
    assert env.confidence == "blocked"


def test_wrapper_use_classifier_false_falls_back_to_legacy(tmp_path):
    """Passing use_classifier=False reverts to Tier-A behavior: no
    classifier call, runs setup_ldc_bc directly. This is what tests
    that need the legacy contract pass in.
    """
    case_dir = tmp_path / "no_classifier"
    case_dir.mkdir()
    _stage_polymesh(case_dir, _POINTS_CUBE)
    # Without classifier, wrapper goes straight to setup_ldc_bc which
    # fails on this minimal fixture — we just want to verify no
    # classifier short-circuit happened.
    with pytest.raises(AIActionError) as exc:
        setup_bc_with_annotations(
            case_dir=case_dir,
            case_id="no_classifier",
            use_classifier=False,
        )
    assert exc.value.failing_check == "setup_bc_failed"


def test_wrapper_classifier_on_degenerate_mesh_blocks(tmp_path):
    case_dir = tmp_path / "wrapper_degenerate"
    case_dir.mkdir()
    # No polyMesh staged → classifier blocks immediately.
    env = setup_bc_with_annotations(
        case_dir=case_dir,
        case_id="wrapper_degenerate",
    )
    assert env.confidence == "blocked"
    assert any(
        q.id == "run_step2_first" for q in env.unresolved_questions
    )


def test_full_loop_uncertain_then_pin_top_lid_then_confident(tmp_path):
    """Codex round 2 closure: full pick→annotate→re-run loop with
    geometric verification. The loop only closes when the engineer
    pins the ACTUAL top-plane face — pinning any other face stays
    uncertain (preventing silent override by setup_ldc_bc).

      1. First call (no annotations) → uncertain · lid_orientation.
      2. PUT face_annotations name='lid' face_id=<actual top plane>
         confidence='user_authoritative'.
      3. Re-run → classifier returns confident → wrapper invokes
         setup_ldc_bc.
    """
    case_dir = tmp_path / "loop_test"
    case_dir.mkdir()
    _stage_full_cube(case_dir)

    # Step 1: first envelope call returns uncertain.
    env1 = setup_bc_with_annotations(
        case_dir=case_dir,
        case_id="loop_test",
    )
    assert env1.confidence == "uncertain"
    assert any(
        q.id == "lid_orientation" for q in env1.unresolved_questions
    )

    # Step 2: simulate the resume PUT with the actual top-plane face_id.
    annotations = empty_annotations("loop_test")
    annotations["faces"].append({
        "face_id": _top_face_id_of_unit_cube(),
        "name": "lid",
        "confidence": "user_authoritative",
        "annotated_by": "human",
        "annotated_at": "2026-04-29T00:00:00Z",
    })
    save_annotations(case_dir, annotations, if_match_revision=0)

    # Step 3: re-run wrapper — classifier verifies the lid pin
    # geometrically + returns confident → setup_ldc_bc runs to
    # completion → confident envelope back, dicts on disk.
    env2 = setup_bc_with_annotations(
        case_dir=case_dir,
        case_id="loop_test",
    )
    assert env2.confidence == "confident"
    assert env2.unresolved_questions == []
    assert (case_dir / "0").is_dir()
    assert (case_dir / "system").is_dir()
