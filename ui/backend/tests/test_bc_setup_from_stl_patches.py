"""Unit tests for DEC-V61-103 ``bc_setup_from_stl_patches``.

Covers the 8 cases mandated by the DEC's Phase 3 test plan:
1. 3-patch duct → produces 7 dicts with right BC class per patch
2. 4-patch case (incl. symmetry) → symmetry block emitted correctly
3. Unknown patch name → falls through to NO_SLIP_WALL with warning
4. Patch name case-insensitivity → ``Inlet`` matches ``inlet``
5. ``polyMesh/boundary`` missing → StlPatchBCError(failing_check=mesh_not_setup)
6. Legacy single ``patch0`` → StlPatchBCError(failing_check=no_named_patches)
7. Idempotent (calling twice yields same on-disk state)
8. User-override invariant: dicts edited by user (manifest source=user)
   are not clobbered by re-runs
"""
from __future__ import annotations

from pathlib import Path

import pytest

from ui.backend.services.case_manifest import (
    mark_user_override,
    read_case_manifest,
    write_case_manifest,
)
from ui.backend.services.case_manifest.schema import CaseManifest
from ui.backend.services.case_solve.bc_setup_from_stl_patches import (
    BCClass,
    StlPatchBCError,
    setup_bc_from_stl_patches,
)


def _write_polymesh_boundary(case_dir: Path, patches: list[tuple[str, int, int]]) -> None:
    """Author a minimal ``constant/polyMesh/boundary`` with the given
    (name, nFaces, startFace) patches. Mirrors the gmshToFoam output
    shape that defect-2a's fix produces.
    """
    polymesh = case_dir / "constant" / "polyMesh"
    polymesh.mkdir(parents=True, exist_ok=True)
    body = "\n".join(
        f"    {name}\n    {{\n        type            patch;\n"
        f"        nFaces          {nfaces};\n        startFace       {start};\n    }}"
        for name, nfaces, start in patches
    )
    (polymesh / "boundary").write_text(
        "FoamFile {}\n"
        f"{len(patches)}\n"
        "(\n"
        f"{body}\n"
        ")\n"
    )


def _write_polymesh_axis_aligned_box(
    case_dir: Path,
    patches: list[tuple[str, int, int, str]],
) -> None:
    """Write a fully-valid minimal polyMesh with 8-vertex unit cube
    points + per-patch face triangulations. ``patches`` items are
    ``(name, nFaces, startFace, side)`` where side is one of
    ``-x|+x|-y|+y|-z|+z``. Lets bc_setup_from_stl_patches compute
    actual face normals during tests.
    """
    polymesh = case_dir / "constant" / "polyMesh"
    polymesh.mkdir(parents=True, exist_ok=True)
    # Unit cube vertices indexed 0-7 by binary (x,y,z) mask.
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
    # Build face list: pad with placeholder faces if startFace > current
    # count, then emit nFaces copies of the chosen side quad.
    all_faces: list[list[int]] = []
    for name, nfaces, start, side in patches:
        while len(all_faces) < start:
            all_faces.append([0, 1, 2])  # placeholder triangle
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


def _scaffold_case(case_dir: Path) -> None:
    """Minimal manifest + scaffold so case_lock + mark_ai_authored work."""
    case_dir.mkdir(parents=True, exist_ok=True)
    write_case_manifest(case_dir, CaseManifest(case_id=case_dir.name))


def test_three_patch_duct_authors_seven_dicts(tmp_path: Path):
    case_dir = tmp_path / "duct_case"
    _scaffold_case(case_dir)
    _write_polymesh_axis_aligned_box(
        case_dir,
        [
            ("inlet", 100, 0, "-x"),
            ("outlet", 100, 100, "+x"),
            ("walls", 2000, 200, "+z"),
        ],
    )

    result = setup_bc_from_stl_patches(case_dir, case_id="duct_case")

    assert result.case_id == "duct_case"
    assert len(result.patches) == 3
    assert result.patches == (
        ("inlet", BCClass.VELOCITY_INLET),
        ("outlet", BCClass.PRESSURE_OUTLET),
        ("walls", BCClass.NO_SLIP_WALL),
    )
    assert set(result.written_files) == {
        "0/U",
        "0/p",
        "constant/physicalProperties",
        "constant/momentumTransport",
        "system/controlDict",
        "system/fvSchemes",
        "system/fvSolution",
    }
    assert result.warnings == ()

    # Spot-check the 0/U content references the actual patch names.
    u_text = (case_dir / "0/U").read_text()
    assert "inlet" in u_text and "outlet" in u_text and "walls" in u_text
    assert "fixedValue" in u_text  # inlet
    assert "noSlip" in u_text  # walls


def test_four_patch_with_symmetry_emits_symmetry_block(tmp_path: Path):
    case_dir = tmp_path / "sym_case"
    _scaffold_case(case_dir)
    _write_polymesh_axis_aligned_box(
        case_dir,
        [
            ("inlet", 50, 0, "-x"),
            ("outlet", 50, 50, "+x"),
            ("walls", 800, 100, "+z"),
            ("symmetry", 200, 900, "-z"),
        ],
    )

    result = setup_bc_from_stl_patches(case_dir, case_id="sym_case")
    bc_classes = dict(result.patches)
    assert bc_classes["symmetry"] == BCClass.SYMMETRY

    u_text = (case_dir / "0/U").read_text()
    p_text = (case_dir / "0/p").read_text()
    # Symmetry patch must use type symmetry on both U and p.
    assert "    symmetry\n    {\n        type            symmetry;" in u_text
    assert "    symmetry\n    {\n        type            symmetry;" in p_text


def test_unknown_patch_name_falls_through_with_warning(tmp_path: Path):
    case_dir = tmp_path / "unknown_case"
    _scaffold_case(case_dir)
    _write_polymesh_axis_aligned_box(
        case_dir,
        [
            ("inlet", 50, 0, "-x"),
            ("outlet", 50, 50, "+x"),
            ("mystery_zone", 500, 100, "+z"),
        ],
    )

    result = setup_bc_from_stl_patches(case_dir, case_id="unknown_case")
    bc_classes = dict(result.patches)
    assert bc_classes["mystery_zone"] == BCClass.NO_SLIP_WALL
    assert any("mystery_zone" in w for w in result.warnings)


def test_patch_name_case_insensitive(tmp_path: Path):
    case_dir = tmp_path / "case_case"
    _scaffold_case(case_dir)
    _write_polymesh_axis_aligned_box(
        case_dir,
        [
            ("Inlet", 50, 0, "-x"),
            ("OUTLET", 50, 50, "+x"),
            ("Walls", 500, 100, "+z"),
        ],
    )

    result = setup_bc_from_stl_patches(case_dir, case_id="case_case")
    bc_classes = dict(result.patches)
    # Names preserved verbatim from polyMesh, but classification is
    # case-insensitive.
    assert bc_classes["Inlet"] == BCClass.VELOCITY_INLET
    assert bc_classes["OUTLET"] == BCClass.PRESSURE_OUTLET
    assert bc_classes["Walls"] == BCClass.NO_SLIP_WALL
    assert result.warnings == ()


def test_missing_polymesh_boundary_raises_409(tmp_path: Path):
    case_dir = tmp_path / "no_mesh"
    _scaffold_case(case_dir)
    # Don't write polyMesh/boundary at all.

    with pytest.raises(StlPatchBCError) as exc:
        setup_bc_from_stl_patches(case_dir, case_id="no_mesh")
    assert exc.value.failing_check == "mesh_not_setup"


def test_legacy_patch0_only_rejects_with_no_named_patches(tmp_path: Path):
    case_dir = tmp_path / "legacy"
    _scaffold_case(case_dir)
    _write_polymesh_boundary(case_dir, [("patch0", 2298, 12191)])

    with pytest.raises(StlPatchBCError) as exc:
        setup_bc_from_stl_patches(case_dir, case_id="legacy")
    assert exc.value.failing_check == "no_named_patches"


def test_idempotent_two_calls_produce_same_state(tmp_path: Path):
    case_dir = tmp_path / "idem"
    _scaffold_case(case_dir)
    _write_polymesh_axis_aligned_box(
        case_dir,
        [
            ("inlet", 50, 0, "-x"),
            ("outlet", 50, 50, "+x"),
            ("walls", 500, 100, "+z"),
        ],
    )

    r1 = setup_bc_from_stl_patches(case_dir, case_id="idem")
    files_after_1 = {p: (case_dir / p).read_text() for p in r1.written_files}

    r2 = setup_bc_from_stl_patches(case_dir, case_id="idem")
    files_after_2 = {p: (case_dir / p).read_text() for p in r2.written_files}

    assert files_after_1 == files_after_2
    assert r1.skipped_user_overrides == ()
    assert r2.skipped_user_overrides == ()


def test_numbered_patch_suffixes_classify_via_prefix_match(tmp_path: Path):
    """Multi-instance patches like ``inlet_1``/``inlet_2``/``walls01``
    (canonical when a CAD exporter splits one logical patch into mesh
    regions) must classify by stripped prefix, not fall through to
    NO_SLIP_WALL."""
    case_dir = tmp_path / "numbered_case"
    _scaffold_case(case_dir)
    _write_polymesh_axis_aligned_box(
        case_dir,
        [
            ("inlet_1", 50, 0, "-x"),
            ("inlet_2", 50, 50, "-y"),
            ("outlet_1", 100, 100, "+x"),
            ("walls01", 1500, 200, "+z"),
        ],
    )

    result = setup_bc_from_stl_patches(case_dir, case_id="numbered_case")
    bc_classes = dict(result.patches)
    assert bc_classes["inlet_1"] == BCClass.VELOCITY_INLET
    assert bc_classes["inlet_2"] == BCClass.VELOCITY_INLET
    assert bc_classes["outlet_1"] == BCClass.PRESSURE_OUTLET
    assert bc_classes["walls01"] == BCClass.NO_SLIP_WALL
    assert result.warnings == ()


def test_inlet_velocity_follows_patch_inward_normal(tmp_path: Path):
    """Defect-6 fix: inlet velocity vector points along the patch's
    inward normal. For a -x face, the outward normal is (-1,0,0) and
    the inward direction is (+1,0,0); so an inlet on the -x face gets
    U=(speed, 0, 0). For a +y face, inward is (0,-1,0).
    """
    case_dir = tmp_path / "normal_case"
    _scaffold_case(case_dir)
    _write_polymesh_axis_aligned_box(
        case_dir,
        [
            ("inlet", 50, 0, "-x"),
            ("outlet", 50, 50, "+x"),
            ("walls", 100, 100, "+z"),
        ],
    )
    result = setup_bc_from_stl_patches(
        case_dir, case_id="normal_case", inlet_speed=0.5
    )
    inlet_u = dict(result.inlet_velocities)["inlet"]
    # Inlet on -x face: outward normal -x → inward +x → U=(+0.5, 0, 0).
    assert abs(inlet_u[0] - 0.5) < 1e-9, f"expected (+0.5,0,0), got {inlet_u}"
    assert abs(inlet_u[1]) < 1e-9
    assert abs(inlet_u[2]) < 1e-9


def test_inlet_velocity_handles_non_axis_face_correctly(tmp_path: Path):
    """Defect-6 fix coverage: inlet on the +y face → inward normal
    -y → U=(0, -speed, 0). Confirms the sign flip works on every axis."""
    case_dir = tmp_path / "ynormal_case"
    _scaffold_case(case_dir)
    _write_polymesh_axis_aligned_box(
        case_dir,
        [
            ("inlet", 30, 0, "+y"),
            ("outlet", 30, 30, "-y"),
            ("walls", 60, 60, "+z"),
        ],
    )
    result = setup_bc_from_stl_patches(
        case_dir, case_id="ynormal_case", inlet_speed=0.7
    )
    inlet_u = dict(result.inlet_velocities)["inlet"]
    # Inlet on +y face: outward +y → inward -y → U=(0, -0.7, 0).
    assert abs(inlet_u[0]) < 1e-9
    assert abs(inlet_u[1] + 0.7) < 1e-9, f"expected (0,-0.7,0), got {inlet_u}"
    assert abs(inlet_u[2]) < 1e-9


def test_inlet_velocity_falls_back_when_polymesh_files_missing(tmp_path: Path):
    """Defect-6 fix safety: when polyMesh/{points,faces} are missing
    (route called before mesh stage completed), we still author dicts
    using the legacy +x default and emit a warning so the engineer
    knows to override via raw-dict editor."""
    case_dir = tmp_path / "no_polymesh_files"
    _scaffold_case(case_dir)
    # Boundary file exists, but no points/faces — simulates the
    # mid-mesh-failure or partial-import state.
    _write_polymesh_boundary(
        case_dir,
        [("inlet", 50, 0), ("outlet", 50, 50), ("walls", 100, 100)],
    )
    result = setup_bc_from_stl_patches(
        case_dir, case_id="no_polymesh_files", inlet_speed=0.5
    )
    inlet_u = dict(result.inlet_velocities)["inlet"]
    # Fallback: +x axis at speed 0.5
    assert abs(inlet_u[0] - 0.5) < 1e-9
    assert abs(inlet_u[1]) < 1e-9
    assert abs(inlet_u[2]) < 1e-9
    # Warning surfaced
    assert any("face normals" in w for w in result.warnings), (
        f"expected fallback warning, got {result.warnings}"
    )


def test_user_override_invariant_preserves_engineer_edits(tmp_path: Path):
    case_dir = tmp_path / "override_case"
    _scaffold_case(case_dir)
    _write_polymesh_axis_aligned_box(
        case_dir,
        [
            ("inlet", 50, 0, "-x"),
            ("outlet", 50, 50, "+x"),
            ("walls", 500, 100, "+z"),
        ],
    )

    # First setup: AI authors all 7 dicts.
    r1 = setup_bc_from_stl_patches(case_dir, case_id="override_case")
    assert r1.skipped_user_overrides == ()

    # Engineer manually edits system/controlDict (raw-dict editor flow).
    custom_control_dict = (
        'FoamFile { version 2.0; format ascii; class dictionary; '
        'location "system"; object controlDict; }\n'
        "application icoFoam;\n"
        "endTime 100;\n"  # engineer wants longer simulation
        "deltaT 0.001;\n"  # finer dt
    )
    (case_dir / "system/controlDict").write_text(custom_control_dict)
    mark_user_override(
        case_dir,
        relative_path="system/controlDict",
        new_content=custom_control_dict.encode("utf-8"),
        detail={"reason": "engineer override for finer dt"},
    )

    # Re-run setup-bc — should NOT overwrite the engineer's controlDict.
    r2 = setup_bc_from_stl_patches(case_dir, case_id="override_case")
    assert "system/controlDict" in r2.skipped_user_overrides
    assert (case_dir / "system/controlDict").read_text() == custom_control_dict
