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

import re
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

    # Defect-8 (iter06) regression: ``constant/polyMesh/boundary`` must
    # ALSO upgrade the symmetry patch's ``type`` from the gmshToFoam
    # default ``patch`` to ``symmetry``. Without this, icoFoam exits
    # with FATAL IO ERROR ``patch type 'patch' not constraint type
    # 'symmetry'`` when reading 0/p.
    boundary_text = (case_dir / "constant" / "polyMesh" / "boundary").read_text()
    assert "constant/polyMesh/boundary" in result.written_files
    # Find the symmetry block and assert type is symmetry.
    sym_match = re.search(
        r"\bsymmetry\s*\{[^}]*?type\s+(\w+);", boundary_text, re.DOTALL
    )
    assert sym_match is not None, "symmetry block not found in boundary file"
    assert sym_match.group(1) == "symmetry"
    # And the non-constraint patches stay as ``patch``.
    inlet_match = re.search(
        r"\binlet\s*\{[^}]*?type\s+(\w+);", boundary_text, re.DOTALL
    )
    assert inlet_match is not None and inlet_match.group(1) == "patch"


def test_symmetry_boundary_rewrite_ignores_line_comments(tmp_path: Path):
    """Codex post-merge HIGH finding: the original regex-only rewrite
    matched ``// type patch;`` (commented out) and rewrote the comment
    while leaving the live ``type patch;`` line unchanged, so icoFoam
    still hit the constraint-type FATAL IO ERROR. The line-based
    parser strips ``//`` comments before matching. This test injects
    a hostile comment line and asserts the LIVE field is what gets
    rewritten."""
    from ui.backend.services.case_solve.bc_setup_from_stl_patches import (
        _rewrite_polymesh_boundary_constraint_types,
    )

    hostile_text = (
        "FoamFile {}\n"
        "1\n"
        "(\n"
        "    symmetry\n"
        "    {\n"
        "        // type patch;  // sneaky commented-out line\n"
        "        type            patch;\n"
        "        physicalType    patch;\n"
        "        nFaces          100;\n"
        "        startFace       0;\n"
        "    }\n"
        ")\n"
    )
    rewritten = _rewrite_polymesh_boundary_constraint_types(
        hostile_text, [("symmetry", BCClass.SYMMETRY)]
    )
    assert rewritten is not None
    # The LIVE type/physicalType fields must have been upgraded to
    # ``symmetry``. The commented-out line must be left unchanged.
    assert "        type            symmetry;" in rewritten
    assert "        physicalType    symmetry;" in rewritten
    assert "// type patch;  // sneaky commented-out line" in rewritten
    # Sanity: no leftover live ``type patch;`` for the symmetry patch.
    sym_block = rewritten[
        rewritten.index("symmetry") : rewritten.index("}", rewritten.index("symmetry"))
    ]
    assert "type            patch;" not in sym_block


def test_setup_bc_idempotent_with_symmetry_patch(tmp_path: Path):
    """Defect-8 fix correctness: re-running setup_bc_from_stl_patches
    on a case that ALREADY had its boundary file rewritten must be a
    no-op (idempotent). Re-rewrites of ``type symmetry; → type
    symmetry;`` should produce the same byte-identical content."""
    case_dir = tmp_path / "idem_sym_case"
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
    boundary_path = case_dir / "constant" / "polyMesh" / "boundary"

    setup_bc_from_stl_patches(case_dir, case_id="idem_sym_case")
    first_boundary = boundary_path.read_bytes()

    setup_bc_from_stl_patches(case_dir, case_id="idem_sym_case")
    second_boundary = boundary_path.read_bytes()

    assert first_boundary == second_boundary, (
        "boundary file changed on second setup-bc run — not idempotent"
    )


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


def test_compound_patch_names_classify_via_canonical_token_scan(tmp_path: Path):
    """Adversarial-loop iter05 (T-junction) regression + Codex post-merge
    finding: compound names embedding ``inlet`` / ``outlet`` / ``wall``
    as a substring must classify by that role token regardless of
    surrounding qualifiers (``outlet_branch``, ``left_inlet``,
    ``walls_perimeter``).

    The Codex finding showed that the original strip-after-first-underscore
    rule mis-classified ``left_inlet`` as wall (because ``left`` matched
    the default wall token), defeating the very purpose of the fix.
    Replaced with canonical-role-token substring scan."""
    case_dir = tmp_path / "compound_case"
    _scaffold_case(case_dir)
    _write_polymesh_axis_aligned_box(
        case_dir,
        [
            ("inlet_main", 50, 0, "-x"),
            ("left_inlet", 50, 50, "+x"),
            ("outlet_branch", 50, 100, "+y"),
            ("walls_perimeter", 200, 150, "+z"),
        ],
    )
    result = setup_bc_from_stl_patches(case_dir, case_id="compound_case")
    bc_classes = dict(result.patches)
    assert bc_classes["inlet_main"] == BCClass.VELOCITY_INLET
    assert bc_classes["left_inlet"] == BCClass.VELOCITY_INLET
    assert bc_classes["outlet_branch"] == BCClass.PRESSURE_OUTLET
    assert bc_classes["walls_perimeter"] == BCClass.NO_SLIP_WALL
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


def test_user_override_with_icofoam_marker_raises(tmp_path: Path):
    """DEC-V61-107.5 / Codex R12 P1 + R13 P2-B: refuse only when a
    user-overridden file carries an icoFoam-ONLY marker (e.g.
    `application icoFoam` in controlDict). Mixing icoFoam-flavored
    controlDict with AI-authored pimpleFoam fvSolution would abort the
    solver at startup. Single-file edits that PRESERVE pimpleFoam
    family markers (e.g. tuning endTime / deltaT) are now allowed —
    see test_user_override_pimplefoam_compatible_tuning_proceeds."""
    case_dir = tmp_path / "icofoam_marker_case"
    _scaffold_case(case_dir)
    _write_polymesh_axis_aligned_box(
        case_dir,
        [
            ("inlet", 50, 0, "-x"),
            ("outlet", 50, 50, "+x"),
            ("walls", 500, 100, "+z"),
        ],
    )

    # First setup: AI authors all dicts (pimpleFoam template).
    r1 = setup_bc_from_stl_patches(case_dir, case_id="icofoam_marker_case")
    assert r1.skipped_user_overrides == ()

    # Engineer overrides controlDict and reverts to icoFoam — DANGEROUS.
    custom_control_dict = (
        'FoamFile { version 2.0; format ascii; class dictionary; '
        'location "system"; object controlDict; }\n'
        "application icoFoam;\n"
        "endTime 100;\n"
        "deltaT 0.001;\n"
    )
    (case_dir / "system/controlDict").write_text(custom_control_dict)
    mark_user_override(
        case_dir,
        relative_path="system/controlDict",
        new_content=custom_control_dict.encode("utf-8"),
        detail={"reason": "engineer reverted to icoFoam"},
    )

    with pytest.raises(StlPatchBCError) as exc:
        setup_bc_from_stl_patches(case_dir, case_id="icofoam_marker_case")
    assert exc.value.failing_check == "solver_dicts_partial_override"
    assert "system/controlDict" in str(exc.value)


def test_user_override_with_piso_only_fvsolution_raises(tmp_path: Path):
    """DEC-V61-107.5 / Codex R13 P2-B: PISO block (without PIMPLE) in
    a user-overridden fvSolution is also an icoFoam-only marker —
    pimpleFoam reads PIMPLE, not PISO."""
    case_dir = tmp_path / "piso_only_case"
    _scaffold_case(case_dir)
    _write_polymesh_axis_aligned_box(
        case_dir,
        [
            ("inlet", 50, 0, "-x"),
            ("outlet", 50, 50, "+x"),
            ("walls", 500, 100, "+z"),
        ],
    )
    setup_bc_from_stl_patches(case_dir, case_id="piso_only_case")

    custom_fv_solution = (
        'FoamFile { version 2.0; format ascii; class dictionary; '
        'location "system"; object fvSolution; }\n'
        "solvers { p { solver PCG; preconditioner DIC; tolerance 1e-06; relTol 0.05; } "
        "U { solver smoothSolver; smoother symGaussSeidel; tolerance 1e-05; relTol 0; } }\n"
        "PISO\n{\nnCorrectors 2;\nnNonOrthogonalCorrectors 2;\npRefCell 0;\npRefValue 0;\n}\n"
    )
    (case_dir / "system/fvSolution").write_text(custom_fv_solution)
    mark_user_override(
        case_dir, relative_path="system/fvSolution",
        new_content=custom_fv_solution.encode("utf-8"),
        detail={"reason": "engineer wrote PISO block (icoFoam-style)"},
    )

    with pytest.raises(StlPatchBCError) as exc:
        setup_bc_from_stl_patches(case_dir, case_id="piso_only_case")
    assert exc.value.failing_check == "solver_dicts_partial_override"
    assert "system/fvSolution" in str(exc.value)


def test_user_override_pimplefoam_compatible_tuning_proceeds(tmp_path: Path):
    """DEC-V61-107.5 / Codex R13 P2-B: legitimate raw-dict tuning
    that keeps the pimpleFoam family markers should proceed normally
    and be preserved. Engineer adjusts endTime + deltaT in a
    pimpleFoam controlDict — no icoFoam marker, content-aware guard
    must NOT refuse."""
    case_dir = tmp_path / "compat_case"
    _scaffold_case(case_dir)
    _write_polymesh_axis_aligned_box(
        case_dir,
        [
            ("inlet", 50, 0, "-x"),
            ("outlet", 50, 50, "+x"),
            ("walls", 500, 100, "+z"),
        ],
    )
    setup_bc_from_stl_patches(case_dir, case_id="compat_case")

    # User changes ONLY endTime + deltaT, keeps `application pimpleFoam`.
    custom_compat = (
        'FoamFile { version 2.0; format ascii; class dictionary; '
        'location "system"; object controlDict; }\n'
        "application pimpleFoam;\n"  # KEY: still pimpleFoam
        "endTime 999;\n"
        "deltaT 0.0005;\n"
        "adjustTimeStep yes;\n"
        "maxCo 0.5;\n"
    )
    (case_dir / "system/controlDict").write_text(custom_compat)
    mark_user_override(
        case_dir, relative_path="system/controlDict",
        new_content=custom_compat.encode("utf-8"),
        detail={"reason": "tune endTime + deltaT"},
    )

    # Should PROCEED (not raise), and preserve the engineer's edit.
    r2 = setup_bc_from_stl_patches(case_dir, case_id="compat_case")
    assert "system/controlDict" in r2.skipped_user_overrides
    assert (case_dir / "system/controlDict").read_text() == custom_compat


def test_user_override_fvschemes_alone_proceeds(tmp_path: Path):
    """DEC-V61-107.5 / Codex R13 P2-B: fvSchemes has no flavor-
    specific marker that distinguishes icoFoam from pimpleFoam (both
    accept the same scheme keys). A standalone fvSchemes override
    should NOT trigger the guard."""
    case_dir = tmp_path / "fvschemes_only_case"
    _scaffold_case(case_dir)
    _write_polymesh_axis_aligned_box(
        case_dir,
        [
            ("inlet", 50, 0, "-x"),
            ("outlet", 50, 50, "+x"),
            ("walls", 500, 100, "+z"),
        ],
    )
    setup_bc_from_stl_patches(case_dir, case_id="fvschemes_only_case")

    custom_fvschemes = (
        'FoamFile { version 2.0; format ascii; class dictionary; '
        'location "system"; object fvSchemes; }\n'
        "ddtSchemes  { default Euler; }\n"
        "gradSchemes { default Gauss linear; }\n"
        "divSchemes  { default none; div(phi,U) Gauss upwind; }\n"
        "laplacianSchemes { default Gauss linear corrected; }\n"
        "interpolationSchemes { default linear; }\n"
        "snGradSchemes { default corrected; }\n"
    )
    (case_dir / "system/fvSchemes").write_text(custom_fvschemes)
    mark_user_override(
        case_dir, relative_path="system/fvSchemes",
        new_content=custom_fvschemes.encode("utf-8"),
        detail={"reason": "engineer wants pure upwind"},
    )

    r2 = setup_bc_from_stl_patches(case_dir, case_id="fvschemes_only_case")
    assert "system/fvSchemes" in r2.skipped_user_overrides
    assert (case_dir / "system/fvSchemes").read_text() == custom_fvschemes


def test_user_override_full_solver_group_preserves_all_three(tmp_path: Path):
    """DEC-V61-107.5 / Codex R12 P1: when the engineer overrides ALL
    THREE of {controlDict, fvSchemes, fvSolution} together, the
    re-author proceeds and the engineer-authored set is preserved
    intact (the override-preservation contract still holds for the
    coherent group case)."""
    case_dir = tmp_path / "override_full"
    _scaffold_case(case_dir)
    _write_polymesh_axis_aligned_box(
        case_dir,
        [
            ("inlet", 50, 0, "-x"),
            ("outlet", 50, 50, "+x"),
            ("walls", 500, 100, "+z"),
        ],
    )
    setup_bc_from_stl_patches(case_dir, case_id="override_full")

    custom = {
        "system/controlDict": (
            'FoamFile { version 2.0; format ascii; class dictionary; '
            'location "system"; object controlDict; }\n'
            "application icoFoam;\nendTime 100;\ndeltaT 0.001;\n"
        ),
        "system/fvSchemes": (
            'FoamFile { version 2.0; format ascii; class dictionary; '
            'location "system"; object fvSchemes; }\n'
            "ddtSchemes  { default Euler; }\n"
        ),
        "system/fvSolution": (
            'FoamFile { version 2.0; format ascii; class dictionary; '
            'location "system"; object fvSolution; }\n'
            "solvers { p { solver PCG; } }\nPISO { nCorrectors 2; }\n"
        ),
    }
    for rel, content in custom.items():
        (case_dir / rel).write_text(content)
        mark_user_override(
            case_dir, relative_path=rel,
            new_content=content.encode("utf-8"),
            detail={"reason": "coherent icoFoam override group"},
        )

    r2 = setup_bc_from_stl_patches(case_dir, case_id="override_full")
    for rel in custom:
        assert rel in r2.skipped_user_overrides
        assert (case_dir / rel).read_text() == custom[rel]


def test_max_delta_t_honors_caller_delta_t(tmp_path: Path):
    """DEC-V61-107.5 / Codex R12 P2: maxDeltaT must equal the
    caller's delta_t so pimpleFoam can scale DOWN for stability but
    cannot ramp UP past the caller's requested cap (which would defeat
    the smoke runner's max_steps budgeting for cases like
    iter04/05/06 that declare dt=0.001-0.002)."""
    case_dir = tmp_path / "maxdt_case"
    _scaffold_case(case_dir)
    _write_polymesh_axis_aligned_box(
        case_dir,
        [
            ("inlet", 50, 0, "-x"),
            ("outlet", 50, 50, "+x"),
            ("walls", 500, 100, "+z"),
        ],
    )
    setup_bc_from_stl_patches(
        case_dir, case_id="maxdt_case", delta_t=0.002, end_time=1.0,
    )
    control_dict = (case_dir / "system/controlDict").read_text()
    assert "maxDeltaT 0.002" in control_dict, (
        f"maxDeltaT must equal the caller's delta_t (0.002), got "
        f"controlDict:\n{control_dict}"
    )
    # Also verify adjustTimeStep is enabled (otherwise maxDeltaT is
    # silently ignored — the V61-107 lesson).
    assert "adjustTimeStep yes" in control_dict
    assert "maxCo 0.5" in control_dict
