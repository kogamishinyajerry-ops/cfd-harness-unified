"""Tests for DEC-V61-108 Phase A — per-patch user-authored BC
classification overrides.

Coverage:
1. _classify_patch + overrides argument:
   - override beats heuristic
   - override beats canonical-token substring scan
   - missing override falls through to existing heuristic (regression
     guard so the override layer doesn't accidentally short-circuit
     legitimate auto-classifications)
2. load_patch_classification_overrides loader:
   - missing file → {}
   - empty file → {}
   - malformed YAML → {} (does NOT raise; the route layer is the
     single point of validation)
   - unknown bc_class string → silently dropped (other entries kept)
3. setup_bc_from_stl_patches end-to-end:
   - sidecar override flips a patch's class from heuristic-derived
     NO_SLIP_WALL to VELOCITY_INLET, and the authored 0/U dict
     reflects the override (fixedValue rather than noSlip).
"""
from __future__ import annotations

from pathlib import Path

import yaml

from ui.backend.services.case_manifest import write_case_manifest
from ui.backend.services.case_manifest.schema import CaseManifest
from ui.backend.services.case_solve.bc_setup_from_stl_patches import (
    BCClass,
    _classify_patch,
    load_patch_classification_overrides,
    setup_bc_from_stl_patches,
)


def _scaffold(case_dir: Path) -> None:
    case_dir.mkdir(parents=True, exist_ok=True)
    write_case_manifest(case_dir, CaseManifest(case_id=case_dir.name))


def _write_polymesh_axis_aligned_box(
    case_dir: Path,
    patches: list[tuple[str, int, int, str]],
) -> None:
    """Mirror of the helper from test_bc_setup_from_stl_patches.py.
    Inlined here so this test file is self-contained."""
    polymesh = case_dir / "constant" / "polyMesh"
    polymesh.mkdir(parents=True, exist_ok=True)
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
        "-x": [0, 4, 6, 2], "+x": [1, 3, 7, 5],
        "-y": [0, 1, 5, 4], "+y": [2, 6, 7, 3],
        "-z": [0, 2, 3, 1], "+z": [4, 5, 7, 6],
    }
    all_faces: list[list[int]] = []
    for name, nfaces, start, side in patches:
        while len(all_faces) < start:
            all_faces.append([0, 1, 2])
        for _ in range(nfaces):
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
        f"        nFaces          {nfaces};\n        startFace       {start};\n    }}"
        for name, nfaces, start, _side in patches
    )
    (polymesh / "boundary").write_text(
        "FoamFile {}\n"
        f"{len(patches)}\n"
        "(\n"
        f"{body_lines}\n"
        ")\n"
    )


# ─────────── _classify_patch + overrides ───────────


def test_override_beats_heuristic_for_unknown_name():
    cls, warning = _classify_patch(
        "patch_3", overrides={"patch_3": BCClass.VELOCITY_INLET}
    )
    assert cls == BCClass.VELOCITY_INLET
    assert warning is None


def test_override_beats_canonical_token_substring_scan():
    """A patch named ``inlet_branch`` would heuristically classify
    as VELOCITY_INLET via the canonical-token scan. An explicit
    override to NO_SLIP_WALL must win — engineers know better than
    the heuristic when they take the override path."""
    cls, warning = _classify_patch(
        "inlet_branch", overrides={"inlet_branch": BCClass.NO_SLIP_WALL}
    )
    assert cls == BCClass.NO_SLIP_WALL
    assert warning is None


def test_missing_override_falls_through_to_heuristic():
    cls, warning = _classify_patch(
        "outlet", overrides={"someother": BCClass.VELOCITY_INLET}
    )
    assert cls == BCClass.PRESSURE_OUTLET
    assert warning is None


def test_no_overrides_argument_preserves_existing_behavior():
    """Regression guard: callers that don't pass overrides at all
    must see the same behavior as the pre-V108 implementation."""
    cls, warning = _classify_patch("patch_unknown_xyz")
    assert cls == BCClass.NO_SLIP_WALL
    assert warning is not None and "patch_unknown_xyz" in warning


# ─────────── load_patch_classification_overrides ───────────


def test_load_overrides_missing_file_returns_empty(tmp_path: Path):
    case_dir = tmp_path / "case_no_overrides"
    case_dir.mkdir()
    assert load_patch_classification_overrides(case_dir) == {}


def test_load_overrides_empty_file_returns_empty(tmp_path: Path):
    case_dir = tmp_path / "case_empty"
    (case_dir / "system").mkdir(parents=True)
    (case_dir / "system" / "patch_classification.yaml").write_text("")
    assert load_patch_classification_overrides(case_dir) == {}


def test_load_overrides_malformed_yaml_returns_empty(tmp_path: Path):
    """Loader must NOT raise on bad YAML — the BC mapper has a hot
    path through here on every solve and a parse error must not
    block the whole case. The route layer is the single point of
    schema validation."""
    case_dir = tmp_path / "case_bad_yaml"
    (case_dir / "system").mkdir(parents=True)
    (case_dir / "system" / "patch_classification.yaml").write_text(
        "not: valid: yaml: ::\n: oops"
    )
    assert load_patch_classification_overrides(case_dir) == {}


def test_load_overrides_unknown_bc_class_silently_dropped(tmp_path: Path):
    """A stale override referencing a removed BCClass value must
    not poison the rest of the case's overrides."""
    case_dir = tmp_path / "case_partial_stale"
    (case_dir / "system").mkdir(parents=True)
    (case_dir / "system" / "patch_classification.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "overrides": {
                    "good_patch": "velocity_inlet",
                    "stale_patch": "no_such_bc_class_anymore",
                },
            }
        )
    )
    out = load_patch_classification_overrides(case_dir)
    assert out == {"good_patch": BCClass.VELOCITY_INLET}


def test_load_overrides_happy_path(tmp_path: Path):
    case_dir = tmp_path / "case_happy"
    (case_dir / "system").mkdir(parents=True)
    (case_dir / "system" / "patch_classification.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "overrides": {
                    "patch_3": "velocity_inlet",
                    "patch_4": "pressure_outlet",
                    "patch_5": "symmetry",
                },
            }
        )
    )
    out = load_patch_classification_overrides(case_dir)
    assert out == {
        "patch_3": BCClass.VELOCITY_INLET,
        "patch_4": BCClass.PRESSURE_OUTLET,
        "patch_5": BCClass.SYMMETRY,
    }


# ─────────── setup_bc_from_stl_patches end-to-end ───────────


def test_setup_bc_respects_patch_classification_override(tmp_path: Path):
    """End-to-end proof: a patch named ``custom_inlet_face`` is NOT in
    the canonical-token table and would heuristically classify as
    VELOCITY_INLET via substring (because ``inlet`` is a substring).
    With an override forcing it to NO_SLIP_WALL, the authored 0/U
    dict must reflect noSlip rather than fixedValue."""
    case_dir = tmp_path / "case_override_e2e"
    _scaffold(case_dir)
    _write_polymesh_axis_aligned_box(
        case_dir,
        [
            ("custom_inlet_face", 50, 0, "-x"),
            ("outlet", 50, 50, "+x"),
            ("walls", 500, 100, "+z"),
        ],
    )
    # First, prove the heuristic alone classifies it as inlet.
    r0 = setup_bc_from_stl_patches(case_dir, case_id="case_override_e2e")
    pre_classes = dict(r0.patches)
    assert pre_classes["custom_inlet_face"] == BCClass.VELOCITY_INLET

    # Now write the override and re-run.
    (case_dir / "system").mkdir(parents=True, exist_ok=True)
    (case_dir / "system" / "patch_classification.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "overrides": {"custom_inlet_face": "no_slip_wall"},
            }
        )
    )
    r1 = setup_bc_from_stl_patches(case_dir, case_id="case_override_e2e")
    post_classes = dict(r1.patches)
    assert post_classes["custom_inlet_face"] == BCClass.NO_SLIP_WALL

    # Verify the actual U dict reflects the override (noSlip block, not
    # fixedValue) — the heuristic-derived fixedValue would have a
    # ``value`` line; noSlip must not.
    u_text = (case_dir / "0" / "U").read_text()
    # Locate the custom_inlet_face block.
    block_match = u_text.split("custom_inlet_face")[1].split("}")[0]
    assert "noSlip" in block_match
    assert "fixedValue" not in block_match


def test_setup_bc_override_for_unknown_patch_still_authored(tmp_path: Path):
    """An override for a patch_name that's NOT in polyMesh/boundary
    must NOT raise inside setup_bc — orphan overrides are silently
    ignored at this layer (the route layer is responsible for
    catching the typo at write time)."""
    case_dir = tmp_path / "case_orphan_override"
    _scaffold(case_dir)
    _write_polymesh_axis_aligned_box(
        case_dir,
        [
            ("inlet", 50, 0, "-x"),
            ("outlet", 50, 50, "+x"),
            ("walls", 500, 100, "+z"),
        ],
    )
    (case_dir / "system").mkdir(parents=True, exist_ok=True)
    (case_dir / "system" / "patch_classification.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "overrides": {
                    "ghost_patch_does_not_exist": "velocity_inlet",
                },
            }
        )
    )
    # Should not raise; should classify the real patches via heuristic.
    r = setup_bc_from_stl_patches(case_dir, case_id="case_orphan_override")
    classes = dict(r.patches)
    assert classes["inlet"] == BCClass.VELOCITY_INLET
    assert classes["outlet"] == BCClass.PRESSURE_OUTLET
    assert classes["walls"] == BCClass.NO_SLIP_WALL
