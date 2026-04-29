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


# Faces of the 1×1×10 channel · same indexing scheme as the cube
# but the +z plane is at z=10 (outlet) and -z plane at z=0 (inlet).
_FACES_CHANNEL = """\
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

_BOUNDARY_CHANNEL_PRESPLIT = """\
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


def _stage_full_channel(case_dir: Path) -> Path:
    """DEC-V61-101: stage a complete 1×1×10 channel polyMesh fixture
    (points + faces + 1-patch boundary + owner). Used by tests that
    need the channel classifier to verify pinned inlet/outlet face_ids
    against the actual boundary faces.
    """
    polymesh = _stage_polymesh(
        case_dir,
        _POINTS_CHANNEL,
        faces_text=_FACES_CHANNEL,
        boundary_text=_BOUNDARY_CHANNEL_PRESPLIT,
    )
    (polymesh / "owner").write_text(_OWNER_CUBE, encoding="utf-8")
    return polymesh


def _bottom_face_id_of_channel() -> str:
    """face_id for the z=0 face of the channel (designated inlet)."""
    from ui.backend.services.case_annotations import face_id

    return face_id(
        [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0), (0.0, 1.0, 0.0)]
    )


def _top_face_id_of_channel() -> str:
    """face_id for the z=10 face of the channel (designated outlet)."""
    from ui.backend.services.case_annotations import face_id

    return face_id(
        [
            (0.0, 0.0, 10.0),
            (1.0, 0.0, 10.0),
            (1.0, 1.0, 10.0),
            (0.0, 1.0, 10.0),
        ]
    )


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


def test_classifier_channel_with_unverifiable_pins_returns_uncertain(
    tmp_path,
):
    """DEC-V61-101: pinning inlet+outlet by name but with face_ids that
    aren't on the current polyMesh boundary (e.g., after mesh regen)
    must return uncertain with a channel_pin_mismatch question — NOT
    confident. The classifier-executor parity rule from Codex M9 Step 2
    R2 applies to the channel branch too.
    """
    case_dir = tmp_path / "channel_stale_pins"
    case_dir.mkdir()
    _stage_polymesh(case_dir, _POINTS_CHANNEL)
    annotations = _empty_doc("channel_stale_pins")
    # Stub face_ids that don't actually exist on the polyMesh boundary —
    # the empty boundary file means _boundary_face_ids returns empty,
    # so any pin fails verification.
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
    assert res.confidence == "uncertain"
    assert res.geometry_class == "non_cube"
    assert any(q.id == "channel_pin_mismatch" for q in res.questions)
    # Confident-only fields stay empty when verification fails.
    assert res.inlet_face_ids == ()
    assert res.outlet_face_ids == ()


def test_classifier_channel_with_verified_inlet_outlet_returns_confident(
    tmp_path,
):
    """DEC-V61-101 happy path: with a proper channel polyMesh and
    user_authoritative pins whose face_ids ARE on the boundary, the
    classifier returns confident and exposes inlet_face_ids /
    outlet_face_ids for the wrapper to forward to setup_channel_bc.
    """
    case_dir = tmp_path / "channel_confident"
    case_dir.mkdir()
    _stage_full_channel(case_dir)
    annotations = _empty_doc("channel_confident")
    inlet_fid = _bottom_face_id_of_channel()  # z=0 face
    outlet_fid = _top_face_id_of_channel()  # z=10 face
    annotations["faces"].extend([
        {
            "face_id": inlet_fid,
            "name": "inlet_main",
            "confidence": "user_authoritative",
            "annotated_by": "human",
            "annotated_at": "2026-04-29T00:00:00Z",
        },
        {
            "face_id": outlet_fid,
            "name": "outlet_main",
            "confidence": "user_authoritative",
            "annotated_by": "human",
            "annotated_at": "2026-04-29T00:00:00Z",
        },
    ])
    res = classify_setup_bc(case_dir, annotations=annotations)
    assert res.confidence == "confident", res
    assert res.geometry_class == "non_cube"
    assert res.questions == []
    assert res.inlet_face_ids == (inlet_fid,)
    assert res.outlet_face_ids == (outlet_fid,)


def test_classifier_channel_rejects_same_face_for_inlet_and_outlet(
    tmp_path,
):
    """DEC-V61-101 disjointness check: an engineer who pins the same
    face under two different names ('inlet' and 'outlet') would let
    the executor write contradictory BCs. Classifier rejects via
    channel_pin_mismatch question.
    """
    case_dir = tmp_path / "channel_same_face"
    case_dir.mkdir()
    _stage_full_channel(case_dir)
    annotations = _empty_doc("channel_same_face")
    same_fid = _bottom_face_id_of_channel()
    annotations["faces"].extend([
        {
            "face_id": same_fid,
            "name": "inlet_a",
            "confidence": "user_authoritative",
            "annotated_by": "human",
            "annotated_at": "2026-04-29T00:00:00Z",
        },
        {
            "face_id": same_fid,
            "name": "outlet_b",
            "confidence": "user_authoritative",
            "annotated_by": "human",
            "annotated_at": "2026-04-29T00:00:00Z",
        },
    ])
    res = classify_setup_bc(case_dir, annotations=annotations)
    assert res.confidence == "uncertain"
    assert any(q.id == "channel_pin_mismatch" for q in res.questions)


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


def test_full_loop_channel_uncertain_pin_inlet_outlet_then_confident(tmp_path):
    """DEC-V61-101: full pick→annotate→re-run loop on the channel
    geometry (mirrors test_full_loop_uncertain_then_pin_top_lid* but
    for the non-cube branch).

      1. First call (no annotations) → uncertain · inlet+outlet questions.
      2. PUT inlet (z=0 face, name='inlet_main') and outlet (z=10,
         name='outlet_main') as user_authoritative.
      3. Re-run → classifier returns confident with verified pin set →
         wrapper invokes setup_channel_bc → 0/U, 0/p, system/, etc on
         disk + boundary patch split into inlet/outlet/walls.
    """
    case_dir = tmp_path / "channel_loop_test"
    case_dir.mkdir()
    _stage_full_channel(case_dir)

    env1 = setup_bc_with_annotations(
        case_dir=case_dir,
        case_id="channel_loop_test",
    )
    assert env1.confidence == "uncertain"
    qids = {q.id for q in env1.unresolved_questions}
    assert "inlet_face" in qids
    assert "outlet_face" in qids

    annotations = empty_annotations("channel_loop_test")
    inlet_fid = _bottom_face_id_of_channel()
    outlet_fid = _top_face_id_of_channel()
    annotations["faces"].extend([
        {
            "face_id": inlet_fid,
            "name": "inlet_main",
            "confidence": "user_authoritative",
            "annotated_by": "human",
            "annotated_at": "2026-04-29T00:00:00Z",
        },
        {
            "face_id": outlet_fid,
            "name": "outlet_main",
            "confidence": "user_authoritative",
            "annotated_by": "human",
            "annotated_at": "2026-04-29T00:00:00Z",
        },
    ])
    save_annotations(case_dir, annotations, if_match_revision=0)

    env2 = setup_bc_with_annotations(
        case_dir=case_dir,
        case_id="channel_loop_test",
    )
    assert env2.confidence == "confident", env2
    assert env2.unresolved_questions == []
    # Channel-specific summary mentions inlet/outlet face counts + Re.
    assert "inlet=" in env2.summary and "outlet=" in env2.summary
    # Executor wrote the dict tree.
    assert (case_dir / "0" / "U").is_file()
    assert (case_dir / "0" / "p").is_file()
    assert (case_dir / "system" / "controlDict").is_file()
    assert (case_dir / "constant" / "physicalProperties").is_file()
    # Boundary file got split into 3 named patches.
    bnd_text = (case_dir / "constant" / "polyMesh" / "boundary").read_text()
    assert "inlet" in bnd_text
    assert "outlet" in bnd_text
    assert "walls" in bnd_text


def test_channel_executor_rejects_partially_stale_pin_set(tmp_path):
    """Codex DEC-V61-101 R1 HIGH closure: setup_channel_bc must verify
    EVERY pinned face_id was consumed (not just ≥1 inlet, ≥1 outlet).
    A partially stale pin set [real_fid, bogus_fid] previously
    succeeded silently — exactly the silent-override class of bug
    that the LDC R2 fix closed at the classifier level.
    """
    from ui.backend.services.case_solve import setup_channel_bc, BCSetupError

    case_dir = tmp_path / "channel_partial_stale"
    case_dir.mkdir()
    _stage_full_channel(case_dir)
    real_inlet = _bottom_face_id_of_channel()
    real_outlet = _top_face_id_of_channel()
    bogus = "fid_bogus0000000"

    with pytest.raises(BCSetupError) as exc:
        setup_channel_bc(
            case_dir,
            case_id="channel_partial_stale",
            inlet_face_ids=(real_inlet, bogus),
            outlet_face_ids=(real_outlet,),
        )
    assert "stale pins" in str(exc.value)


def test_channel_executor_reports_re_100_on_unit_cross_section(tmp_path):
    """Codex DEC-V61-101 R1 LOW closure: Re must use min bbox extent
    (hydraulic diameter approximation), not max. For the 1×1×10
    fixture, U=1, D=1, ν=0.01 → Re=100 (matching the DEC's locked
    default text). The earlier max-extent code reported Re=1000.
    """
    from ui.backend.services.case_solve import setup_channel_bc

    case_dir = tmp_path / "channel_re_check"
    case_dir.mkdir()
    _stage_full_channel(case_dir)
    res = setup_channel_bc(
        case_dir,
        case_id="channel_re_check",
        inlet_face_ids=(_bottom_face_id_of_channel(),),
        outlet_face_ids=(_top_face_id_of_channel(),),
    )
    assert abs(res.reynolds - 100.0) < 0.5, res.reynolds


def test_setup_ldc_bc_is_idempotent_on_same_case_dir(tmp_path):
    """Engineers can re-click [AI 处理] without crashing. The
    polyMesh.pre_split backup is restored on second invocation so the
    boundary-parser sees the original single-patch shape both times.
    Surfaced as a real production gap by DEC-V61-101's off-axis topology
    test on 2026-04-30 (the LDC path had the same gap, just untested).
    """
    from ui.backend.services.case_solve import setup_ldc_bc

    case_dir = tmp_path / "ldc_idempotent"
    case_dir.mkdir()
    _stage_full_cube(case_dir)

    res1 = setup_ldc_bc(case_dir, case_id="ldc_idempotent")
    assert res1.n_lid_faces == 1
    assert res1.n_wall_faces == 5

    # Re-invoke: must not raise; counts should match.
    res2 = setup_ldc_bc(case_dir, case_id="ldc_idempotent")
    assert res2.n_lid_faces == 1
    assert res2.n_wall_faces == 5


def test_setup_channel_bc_is_idempotent_on_same_case_dir(tmp_path):
    """Same idempotency contract as the LDC path. Without the
    polyMesh.pre_split restore, the regex-based boundary parser would
    see {nFaces=1, startFace=0} from the inlet patch on second call
    and miss the outlet/wall faces.
    """
    from ui.backend.services.case_solve import setup_channel_bc

    case_dir = tmp_path / "channel_idempotent"
    case_dir.mkdir()
    _stage_full_channel(case_dir)
    inlet_fid = _bottom_face_id_of_channel()
    outlet_fid = _top_face_id_of_channel()

    res1 = setup_channel_bc(
        case_dir,
        case_id="channel_idempotent",
        inlet_face_ids=(inlet_fid,),
        outlet_face_ids=(outlet_fid,),
    )
    assert (res1.n_inlet_faces, res1.n_outlet_faces, res1.n_wall_faces) == (1, 1, 4)

    res2 = setup_channel_bc(
        case_dir,
        case_id="channel_idempotent",
        inlet_face_ids=(inlet_fid,),
        outlet_face_ids=(outlet_fid,),
    )
    assert (res2.n_inlet_faces, res2.n_outlet_faces, res2.n_wall_faces) == (1, 1, 4)


def test_channel_executor_handles_multi_inlet_with_distinct_names(tmp_path):
    """DEC-V61-101 implicit feature validation: when the engineer pins
    TWO different boundary faces both with names containing 'inlet'
    (e.g., 'inlet_north' + 'inlet_south' for a Y-junction manifold),
    the classifier collects both face_ids and the executor merges
    them into a single 'inlet' patch with nFaces=2.

    This is the simplest multi-inlet behavior — same velocity on all
    inlet faces. True per-inlet velocity differentiation belongs to a
    later UX milestone where the engineer specifies one BC per pinned
    face. For now we just prove N>1 doesn't break the path.
    """
    from ui.backend.services.case_solve import setup_channel_bc
    from ui.backend.services.case_annotations import face_id

    case_dir = tmp_path / "channel_multi_inlet"
    case_dir.mkdir()
    _stage_full_channel(case_dir)
    annotations = empty_annotations("channel_multi_inlet")
    # Pin TWO faces as inlets: y=0 side (inlet_north) and z=0 cap
    # (inlet_south). The executor should merge both into the inlet
    # patch.
    inlet_north_fid = face_id(
        [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 0.0, 10.0), (0.0, 0.0, 10.0)]
    )
    inlet_south_fid = _bottom_face_id_of_channel()  # z=0 cap
    outlet_fid = _top_face_id_of_channel()
    annotations["faces"].extend([
        {
            "face_id": inlet_north_fid,
            "name": "inlet_north",
            "confidence": "user_authoritative",
            "annotated_by": "human",
            "annotated_at": "2026-04-30T00:00:00Z",
        },
        {
            "face_id": inlet_south_fid,
            "name": "inlet_south",
            "confidence": "user_authoritative",
            "annotated_by": "human",
            "annotated_at": "2026-04-30T00:00:00Z",
        },
        {
            "face_id": outlet_fid,
            "name": "outlet_main",
            "confidence": "user_authoritative",
            "annotated_by": "human",
            "annotated_at": "2026-04-30T00:00:00Z",
        },
    ])
    save_annotations(case_dir, annotations, if_match_revision=0)

    # Classifier sees both inlet substrings, verifies both face_ids on
    # boundary, returns confident with inlet_face_ids=(north, south).
    res = classify_setup_bc(case_dir, annotations=annotations)
    assert res.confidence == "confident", res
    assert len(res.inlet_face_ids) == 2
    assert set(res.inlet_face_ids) == {inlet_north_fid, inlet_south_fid}
    assert len(res.outlet_face_ids) == 1

    # Executor merges both into inlet patch with nFaces=2.
    exec_res = setup_channel_bc(
        case_dir,
        case_id="channel_multi_inlet",
        inlet_face_ids=res.inlet_face_ids,
        outlet_face_ids=res.outlet_face_ids,
    )
    assert exec_res.n_inlet_faces == 2
    assert exec_res.n_outlet_faces == 1
    assert exec_res.n_wall_faces == 3  # 6 boundary - 2 inlet - 1 outlet

    # Boundary file shows the inlet patch with 2 contiguous faces.
    bnd = (case_dir / "constant" / "polyMesh" / "boundary").read_text()
    assert "nFaces          2" in bnd or "nFaces 2" in bnd


def test_setup_bc_rejects_stale_pre_split_backup_after_remesh(tmp_path):
    """Codex DEC-V61-101 idempotency R1 HIGH closure:
    polyMesh.pre_split is invalidated by Step 2 re-mesh (the gmshToFoam
    materialization deletes it). Without that, the BC executor's
    'restore from backup' logic would silently resurrect the old mesh,
    overwriting the engineer's freshly regenerated points + faces.

    We simulate the post-re-mesh state directly: write a fresh
    polyMesh after a setup_*_bc has already created a backup, but
    WITH the backup pre-deleted (mirrors what to_foam.py now does).
    The second setup_*_bc call must operate on the new mesh, not the
    backup.
    """
    import shutil
    from ui.backend.services.case_solve import setup_channel_bc

    case_dir = tmp_path / "channel_remesh"
    case_dir.mkdir()
    _stage_full_channel(case_dir)
    inlet_fid = _bottom_face_id_of_channel()
    outlet_fid = _top_face_id_of_channel()

    # First call creates polyMesh.pre_split backup of original mesh.
    res1 = setup_channel_bc(
        case_dir,
        case_id="channel_remesh",
        inlet_face_ids=(inlet_fid,),
        outlet_face_ids=(outlet_fid,),
    )
    assert res1.n_wall_faces == 4
    backup = case_dir / "constant" / "polyMesh.pre_split"
    assert backup.is_dir()

    # Simulate Step 2 re-mesh: fresh polyMesh + delete the now-stale
    # pre_split backup (this is exactly what gmsh_to_foam.py does
    # after writing the new constant/polyMesh).
    polymesh = case_dir / "constant" / "polyMesh"
    shutil.rmtree(polymesh)
    shutil.rmtree(backup)
    # Restage with a SHIFTED channel (z range 0..20 instead of 0..10).
    polymesh.mkdir(parents=True)
    shifted_points = _POINTS_CHANNEL.replace(" 10)", " 20)")
    (polymesh / "points").write_text(shifted_points, encoding="utf-8")
    (polymesh / "faces").write_text(_FACES_CHANNEL, encoding="utf-8")
    (polymesh / "boundary").write_text(_BOUNDARY_CHANNEL_PRESPLIT, encoding="utf-8")
    (polymesh / "owner").write_text(_OWNER_CUBE, encoding="utf-8")

    # Pin the NEW outlet face_id (z=20 plane this time).
    from ui.backend.services.case_annotations import face_id

    new_outlet_fid = face_id(
        [
            (0.0, 0.0, 20.0),
            (1.0, 0.0, 20.0),
            (1.0, 1.0, 20.0),
            (0.0, 1.0, 20.0),
        ]
    )

    # Second call must operate on the FRESH mesh, not resurrect the
    # backup. Re ought to use min extent = 1 (not 20).
    res2 = setup_channel_bc(
        case_dir,
        case_id="channel_remesh",
        inlet_face_ids=(inlet_fid,),  # z=0 still valid
        outlet_face_ids=(new_outlet_fid,),  # z=20 — only on new mesh
    )
    assert res2.n_inlet_faces == 1
    assert res2.n_outlet_faces == 1
    # If the stale backup had been resurrected, the z=20 face_id
    # wouldn't be on the boundary and we'd raise BCSetupError.
    # Reaching here proves the new mesh survived.


def test_channel_executor_handles_off_axis_inlet_outlet_topology(tmp_path):
    """DEC-V61-101 topology-independence claim: the patch splitter
    routes by face_id (not plane heuristics), so engineers can pin
    inlet/outlet on ANY pair of distinct boundary faces — not just the
    z-axis caps. Critical for engineering geometries (elbow ducts,
    branching manifolds, off-axis intakes) where the inlet isn't
    necessarily the +z face.

    This test pins a SIDE face (y=0 plane, face index 2) as inlet and
    another SIDE face (y=1 plane, face index 3) as outlet on the
    1×1×10 fixture. The classifier-executor handshake must succeed
    without complaint. If it doesn't, the patch splitter's claim of
    being plane-agnostic is false.
    """
    from ui.backend.services.case_solve import setup_channel_bc
    from ui.backend.services.case_annotations import face_id

    case_dir = tmp_path / "channel_off_axis"
    case_dir.mkdir()
    _stage_full_channel(case_dir)
    annotations = empty_annotations("channel_off_axis")
    # y=0 face: vertices (0,0,0)(1,0,0)(1,0,10)(0,0,10) — side wall.
    side_inlet_fid = face_id(
        [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 0.0, 10.0), (0.0, 0.0, 10.0)]
    )
    # y=1 face: vertices (0,1,0)(1,1,0)(1,1,10)(0,1,10) — opposite side.
    side_outlet_fid = face_id(
        [(0.0, 1.0, 0.0), (1.0, 1.0, 0.0), (1.0, 1.0, 10.0), (0.0, 1.0, 10.0)]
    )
    annotations["faces"].extend([
        {
            "face_id": side_inlet_fid,
            "name": "side_inlet",
            "confidence": "user_authoritative",
            "annotated_by": "human",
            "annotated_at": "2026-04-30T00:00:00Z",
        },
        {
            "face_id": side_outlet_fid,
            "name": "side_outlet",
            "confidence": "user_authoritative",
            "annotated_by": "human",
            "annotated_at": "2026-04-30T00:00:00Z",
        },
    ])
    save_annotations(case_dir, annotations, if_match_revision=0)

    # Classifier sees side_inlet/side_outlet (substring match on
    # "inlet"/"outlet") and verifies face_ids on boundary → confident.
    env = setup_bc_with_annotations(
        case_dir=case_dir, case_id="channel_off_axis"
    )
    assert env.confidence == "confident", env
    # Executor wrote dicts with inlet/outlet/walls split — boundary
    # file should contain all three patches.
    bnd = (case_dir / "constant" / "polyMesh" / "boundary").read_text()
    assert "inlet" in bnd
    assert "outlet" in bnd
    assert "walls" in bnd

    # Cross-check face counts on a FRESH case_dir (avoiding the
    # known same-dir non-idempotency: _split_channel_patches reads
    # only the first patch's nFaces/startFace, so re-invoking on a
    # post-split polyMesh wouldn't see the original 6 boundary faces.
    # That's a separate hardening for a future DEC; the wrapper calls
    # the executor exactly once per envelope round-trip, which is
    # the only contract this DEC commits to.)
    fresh_case = tmp_path / "channel_off_axis_direct"
    fresh_case.mkdir()
    _stage_full_channel(fresh_case)
    res = setup_channel_bc(
        fresh_case,
        case_id="channel_off_axis_direct",
        inlet_face_ids=(side_inlet_fid,),
        outlet_face_ids=(side_outlet_fid,),
    )
    assert res.n_inlet_faces == 1
    assert res.n_outlet_faces == 1
    assert res.n_wall_faces == 4


def test_full_loop_channel_executor_writes_correct_inlet_velocity(tmp_path):
    """DEC-V61-101 BC sanity: 0/U boundary field for inlet must be
    fixedValue (1 0 0) and outlet must be zeroGradient. Defends
    against silent BC default changes.
    """
    case_dir = tmp_path / "channel_bc_check"
    case_dir.mkdir()
    _stage_full_channel(case_dir)
    annotations = empty_annotations("channel_bc_check")
    annotations["faces"].extend([
        {
            "face_id": _bottom_face_id_of_channel(),
            "name": "inlet_a",
            "confidence": "user_authoritative",
            "annotated_by": "human",
            "annotated_at": "2026-04-29T00:00:00Z",
        },
        {
            "face_id": _top_face_id_of_channel(),
            "name": "outlet_b",
            "confidence": "user_authoritative",
            "annotated_by": "human",
            "annotated_at": "2026-04-29T00:00:00Z",
        },
    ])
    save_annotations(case_dir, annotations, if_match_revision=0)

    env = setup_bc_with_annotations(
        case_dir=case_dir,
        case_id="channel_bc_check",
    )
    assert env.confidence == "confident"
    u_text = (case_dir / "0" / "U").read_text()
    assert "inlet" in u_text
    assert "fixedValue" in u_text
    assert "(1.0 0.0 0.0)" in u_text or "(1 0 0)" in u_text
    assert "outlet" in u_text
    assert "zeroGradient" in u_text
    assert "walls" in u_text
    assert "noSlip" in u_text
