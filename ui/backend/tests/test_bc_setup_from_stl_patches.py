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


def _scaffold_case(case_dir: Path) -> None:
    """Minimal manifest + scaffold so case_lock + mark_ai_authored work."""
    case_dir.mkdir(parents=True, exist_ok=True)
    write_case_manifest(case_dir, CaseManifest(case_id=case_dir.name))


def test_three_patch_duct_authors_seven_dicts(tmp_path: Path):
    case_dir = tmp_path / "duct_case"
    _scaffold_case(case_dir)
    _write_polymesh_boundary(
        case_dir,
        [("inlet", 100, 1000), ("outlet", 100, 1100), ("walls", 2000, 1200)],
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
    _write_polymesh_boundary(
        case_dir,
        [
            ("inlet", 50, 1000),
            ("outlet", 50, 1050),
            ("walls", 800, 1100),
            ("symmetry", 200, 1900),
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
    _write_polymesh_boundary(
        case_dir,
        [
            ("inlet", 50, 1000),
            ("outlet", 50, 1050),
            ("mystery_zone", 500, 1100),
        ],
    )

    result = setup_bc_from_stl_patches(case_dir, case_id="unknown_case")
    bc_classes = dict(result.patches)
    assert bc_classes["mystery_zone"] == BCClass.NO_SLIP_WALL
    assert any("mystery_zone" in w for w in result.warnings)


def test_patch_name_case_insensitive(tmp_path: Path):
    case_dir = tmp_path / "case_case"
    _scaffold_case(case_dir)
    _write_polymesh_boundary(
        case_dir,
        [
            ("Inlet", 50, 1000),
            ("OUTLET", 50, 1050),
            ("Walls", 500, 1100),
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
    _write_polymesh_boundary(
        case_dir,
        [("inlet", 50, 1000), ("outlet", 50, 1050), ("walls", 500, 1100)],
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
    _write_polymesh_boundary(
        case_dir,
        [
            ("inlet_1", 50, 1000),
            ("inlet_2", 50, 1050),
            ("outlet_1", 100, 1100),
            ("walls01", 1500, 1200),
        ],
    )

    result = setup_bc_from_stl_patches(case_dir, case_id="numbered_case")
    bc_classes = dict(result.patches)
    assert bc_classes["inlet_1"] == BCClass.VELOCITY_INLET
    assert bc_classes["inlet_2"] == BCClass.VELOCITY_INLET
    assert bc_classes["outlet_1"] == BCClass.PRESSURE_OUTLET
    assert bc_classes["walls01"] == BCClass.NO_SLIP_WALL
    assert result.warnings == ()


def test_user_override_invariant_preserves_engineer_edits(tmp_path: Path):
    case_dir = tmp_path / "override_case"
    _scaffold_case(case_dir)
    _write_polymesh_boundary(
        case_dir,
        [("inlet", 50, 1000), ("outlet", 50, 1050), ("walls", 500, 1100)],
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
