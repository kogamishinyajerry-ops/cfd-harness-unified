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


def test_user_override_with_piso_only_fvsolution_proceeds_without_static_guard(tmp_path: Path):
    """DEC-V61-107.5 / Codex R16 closure (scope reduction): PISO-block
    fvSolution overrides are NO LONGER caught by the static guard.
    The override-content guard's scope is now restricted to the
    dominant defect class (`application icoFoam;` literal in
    controlDict). Long-tail mismatches like PISO-without-PIMPLE in
    user fvSolution will surface as solver_diverged at /solve time —
    the engineer sees the OpenFOAM error directly, not a regex
    proxy. This trades false-positive risk for missed false-negatives
    that the regex stack couldn't reliably detect anyway (Codex R14
    P2 brace formatting + R15 P2 comment precedence + R16 P2/P3
    fundamental parser limits)."""
    case_dir = tmp_path / "piso_proceeds"
    _scaffold_case(case_dir)
    _write_polymesh_axis_aligned_box(
        case_dir,
        [
            ("inlet", 50, 0, "-x"),
            ("outlet", 50, 50, "+x"),
            ("walls", 500, 100, "+z"),
        ],
    )
    setup_bc_from_stl_patches(case_dir, case_id="piso_proceeds")

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
        detail={"reason": "engineer wrote PISO block; out of static guard scope"},
    )

    # Setup proceeds; PISO mismatch surfaces at solve time, not here.
    r2 = setup_bc_from_stl_patches(case_dir, case_id="piso_proceeds")
    assert "system/fvSolution" in r2.skipped_user_overrides


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


def test_user_override_fvschemes_with_pimplefoam_terms_proceeds(tmp_path: Path):
    """DEC-V61-107.5 / Codex R14 P1: fvSchemes overrides that PRESERVE
    the pimpleFoam-required div((nuEff*dev2(T(grad(U))))) entry are
    safe and should proceed (engineer changes div(phi,U) scheme but
    keeps the divDevReff term)."""
    case_dir = tmp_path / "fvschemes_compat_case"
    _scaffold_case(case_dir)
    _write_polymesh_axis_aligned_box(
        case_dir,
        [
            ("inlet", 50, 0, "-x"),
            ("outlet", 50, 50, "+x"),
            ("walls", 500, 100, "+z"),
        ],
    )
    setup_bc_from_stl_patches(case_dir, case_id="fvschemes_compat_case")

    custom_fvschemes = (
        'FoamFile { version 2.0; format ascii; class dictionary; '
        'location "system"; object fvSchemes; }\n'
        "ddtSchemes  { default Euler; }\n"
        "gradSchemes { default Gauss linear; }\n"
        "divSchemes  { default none; div(phi,U) Gauss upwind; "
        "div((nuEff*dev2(T(grad(U))))) Gauss linear; }\n"
        "laplacianSchemes { default Gauss linear corrected; }\n"
        "interpolationSchemes { default linear; }\n"
        "snGradSchemes { default corrected; }\n"
    )
    (case_dir / "system/fvSchemes").write_text(custom_fvschemes)
    mark_user_override(
        case_dir, relative_path="system/fvSchemes",
        new_content=custom_fvschemes.encode("utf-8"),
        detail={"reason": "engineer wants pure upwind, kept divDevReff"},
    )

    r2 = setup_bc_from_stl_patches(case_dir, case_id="fvschemes_compat_case")
    assert "system/fvSchemes" in r2.skipped_user_overrides
    assert (case_dir / "system/fvSchemes").read_text() == custom_fvschemes


def test_user_override_fvschemes_dropping_divdevreff_proceeds_without_guard(tmp_path: Path):
    """DEC-V61-107.5 / Codex R16 closure (scope reduction): fvSchemes
    overrides that drop divDevReff are no longer caught statically.
    They surface as solver_diverged at /solve time with OpenFOAM's
    `keyword undefined` error in the response — the engineer sees
    the actual cause."""
    case_dir = tmp_path / "fvschemes_broken_case"
    _scaffold_case(case_dir)
    _write_polymesh_axis_aligned_box(
        case_dir,
        [
            ("inlet", 50, 0, "-x"),
            ("outlet", 50, 50, "+x"),
            ("walls", 500, 100, "+z"),
        ],
    )
    setup_bc_from_stl_patches(case_dir, case_id="fvschemes_broken_case")

    custom_broken = (
        'FoamFile { version 2.0; format ascii; class dictionary; '
        'location "system"; object fvSchemes; }\n'
        "ddtSchemes  { default Euler; }\n"
        "gradSchemes { default Gauss linear; }\n"
        "divSchemes  { default none; div(phi,U) Gauss upwind; }\n"
        "laplacianSchemes { default Gauss linear corrected; }\n"
        "interpolationSchemes { default linear; }\n"
        "snGradSchemes { default corrected; }\n"
    )
    (case_dir / "system/fvSchemes").write_text(custom_broken)
    mark_user_override(
        case_dir, relative_path="system/fvSchemes",
        new_content=custom_broken.encode("utf-8"),
        detail={"reason": "engineer omitted divDevReff; out of guard scope"},
    )

    r2 = setup_bc_from_stl_patches(case_dir, case_id="fvschemes_broken_case")
    assert "system/fvSchemes" in r2.skipped_user_overrides


def test_user_override_fvschemes_with_nonnone_default_proceeds(tmp_path: Path):
    """DEC-V61-107.5 / Codex R15 P2-A: an fvSchemes that omits the
    explicit div((nuEff*dev2(T(grad(U))))) term but has a non-none
    divSchemes.default is still coherent with pimpleFoam (OpenFOAM
    falls back to default for unmatched div terms). Must NOT trigger
    the guard."""
    case_dir = tmp_path / "default_div_case"
    _scaffold_case(case_dir)
    _write_polymesh_axis_aligned_box(
        case_dir,
        [
            ("inlet", 50, 0, "-x"),
            ("outlet", 50, 50, "+x"),
            ("walls", 500, 100, "+z"),
        ],
    )
    setup_bc_from_stl_patches(case_dir, case_id="default_div_case")

    # divSchemes default is `Gauss linear` (non-none). No explicit
    # divDevReff entry — pimpleFoam will use the default for it.
    custom_default = (
        'FoamFile { version 2.0; format ascii; class dictionary; '
        'location "system"; object fvSchemes; }\n'
        "ddtSchemes  { default Euler; }\n"
        "gradSchemes { default Gauss linear; }\n"
        "divSchemes  { default Gauss linear; div(phi,U) Gauss upwind; }\n"
        "laplacianSchemes { default Gauss linear corrected; }\n"
        "interpolationSchemes { default linear; }\n"
        "snGradSchemes { default corrected; }\n"
    )
    (case_dir / "system/fvSchemes").write_text(custom_default)
    mark_user_override(
        case_dir, relative_path="system/fvSchemes",
        new_content=custom_default.encode("utf-8"),
        detail={"reason": "engineer relies on divSchemes default"},
    )

    r2 = setup_bc_from_stl_patches(case_dir, case_id="default_div_case")
    assert "system/fvSchemes" in r2.skipped_user_overrides


def test_user_override_fvschemes_with_default_none_proceeds(tmp_path: Path):
    """DEC-V61-107.5 / Codex R16 closure: fvSchemes content is no longer
    statically inspected. Override proceeds; if it's actually broken,
    pimpleFoam will diverge at /solve time and `solver_diverged` surfaces."""
    case_dir = tmp_path / "default_none_case"
    _scaffold_case(case_dir)
    _write_polymesh_axis_aligned_box(
        case_dir,
        [
            ("inlet", 50, 0, "-x"),
            ("outlet", 50, 50, "+x"),
            ("walls", 500, 100, "+z"),
        ],
    )
    setup_bc_from_stl_patches(case_dir, case_id="default_none_case")

    custom_none = (
        'FoamFile { version 2.0; format ascii; class dictionary; '
        'location "system"; object fvSchemes; }\n'
        "ddtSchemes  { default Euler; }\n"
        "gradSchemes { default Gauss linear; }\n"
        "divSchemes  { default none; div(phi,U) Gauss upwind; }\n"
        "laplacianSchemes { default Gauss linear corrected; }\n"
        "interpolationSchemes { default linear; }\n"
        "snGradSchemes { default corrected; }\n"
    )
    (case_dir / "system/fvSchemes").write_text(custom_none)
    mark_user_override(
        case_dir, relative_path="system/fvSchemes",
        new_content=custom_none.encode("utf-8"),
        detail={"reason": "engineer omitted both default and divDevReff"},
    )

    r2 = setup_bc_from_stl_patches(case_dir, case_id="default_none_case")
    assert "system/fvSchemes" in r2.skipped_user_overrides


def test_user_override_fvschemes_commented_divdevreff_proceeds(tmp_path: Path):
    """DEC-V61-107.5 / Codex R16 closure: fvSchemes content is no longer
    statically inspected, so commented-out divDevReff no longer matters
    to the guard — divergence (if any) surfaces at /solve time."""
    case_dir = tmp_path / "commented_case"
    _scaffold_case(case_dir)
    _write_polymesh_axis_aligned_box(
        case_dir,
        [
            ("inlet", 50, 0, "-x"),
            ("outlet", 50, 50, "+x"),
            ("walls", 500, 100, "+z"),
        ],
    )
    setup_bc_from_stl_patches(case_dir, case_id="commented_case")

    custom_comment = (
        'FoamFile { version 2.0; format ascii; class dictionary; '
        'location "system"; object fvSchemes; }\n'
        "ddtSchemes  { default Euler; }\n"
        "gradSchemes { default Gauss linear; }\n"
        "divSchemes  { default none; div(phi,U) Gauss upwind; "
        "// div((nuEff*dev2(T(grad(U))))) Gauss linear; }\n"
        "laplacianSchemes { default Gauss linear corrected; }\n"
        "interpolationSchemes { default linear; }\n"
        "snGradSchemes { default corrected; }\n"
    )
    (case_dir / "system/fvSchemes").write_text(custom_comment)
    mark_user_override(
        case_dir, relative_path="system/fvSchemes",
        new_content=custom_comment.encode("utf-8"),
        detail={"reason": "engineer commented out divDevReff by mistake"},
    )

    r2 = setup_bc_from_stl_patches(case_dir, case_id="commented_case")
    assert "system/fvSchemes" in r2.skipped_user_overrides


def test_user_override_controldict_with_commented_icofoam_proceeds(tmp_path: Path):
    """DEC-V61-107.5 / Codex R15 P2-B: comment stripping should also
    prevent commented-out icoFoam markers from triggering false
    positives in controlDict."""
    case_dir = tmp_path / "commented_appl"
    _scaffold_case(case_dir)
    _write_polymesh_axis_aligned_box(
        case_dir,
        [
            ("inlet", 50, 0, "-x"),
            ("outlet", 50, 50, "+x"),
            ("walls", 500, 100, "+z"),
        ],
    )
    setup_bc_from_stl_patches(case_dir, case_id="commented_appl")

    custom = (
        'FoamFile { version 2.0; format ascii; class dictionary; '
        'location "system"; object controlDict; }\n'
        "// application icoFoam;  // engineer's old comment\n"
        "application pimpleFoam;\n"
        "endTime 999;\n"
    )
    (case_dir / "system/controlDict").write_text(custom)
    mark_user_override(
        case_dir, relative_path="system/controlDict",
        new_content=custom.encode("utf-8"),
        detail={"reason": "old comment, still pimpleFoam"},
    )

    r2 = setup_bc_from_stl_patches(case_dir, case_id="commented_appl")
    assert "system/controlDict" in r2.skipped_user_overrides


def test_user_override_controldict_with_block_commented_icofoam_proceeds(tmp_path: Path):
    """DEC-V61-107.5 / Codex R17 P3: an ``application icoFoam;`` token
    wrapped in a C-style block comment ``/* ... */`` must not trigger
    the static guard. OpenFOAM strips block comments at parse time,
    so it sees only the live ``application pimpleFoam;`` and runs the
    pimple-friendly authored dicts unchanged."""
    case_dir = tmp_path / "block_commented_appl"
    _scaffold_case(case_dir)
    _write_polymesh_axis_aligned_box(
        case_dir,
        [
            ("inlet", 50, 0, "-x"),
            ("outlet", 50, 50, "+x"),
            ("walls", 500, 100, "+z"),
        ],
    )
    setup_bc_from_stl_patches(case_dir, case_id="block_commented_appl")

    custom = (
        'FoamFile { version 2.0; format ascii; class dictionary; '
        'location "system"; object controlDict; }\n'
        "/* old config kept for posterity:\n"
        "   application icoFoam;\n"
        "   endTime 100;\n"
        "*/\n"
        "application pimpleFoam;\n"
        "endTime 999;\n"
    )
    (case_dir / "system/controlDict").write_text(custom)
    mark_user_override(
        case_dir, relative_path="system/controlDict",
        new_content=custom.encode("utf-8"),
        detail={"reason": "block-commented historical config"},
    )

    r2 = setup_bc_from_stl_patches(case_dir, case_id="block_commented_appl")
    assert "system/controlDict" in r2.skipped_user_overrides


def test_piso_block_inline_brace_proceeds_without_static_guard(tmp_path: Path):
    """DEC-V61-107.5 / Codex R16 closure (scope reduction): inline-
    brace PISO blocks in fvSolution are no longer caught by the
    static guard. The engineer sees the actual mismatch as a solve-
    time `solver_diverged` HTTP 502 with OpenFOAM's error in the
    response."""
    case_dir = tmp_path / "piso_inline_proceeds"
    _scaffold_case(case_dir)
    _write_polymesh_axis_aligned_box(
        case_dir,
        [
            ("inlet", 50, 0, "-x"),
            ("outlet", 50, 50, "+x"),
            ("walls", 500, 100, "+z"),
        ],
    )
    setup_bc_from_stl_patches(case_dir, case_id="piso_inline_proceeds")

    custom_inline = (
        'FoamFile { version 2.0; format ascii; class dictionary; '
        'location "system"; object fvSolution; }\n'
        "solvers { p { solver PCG; preconditioner DIC; tolerance 1e-06; relTol 0.05; } "
        "U { solver smoothSolver; smoother symGaussSeidel; tolerance 1e-05; relTol 0; } }\n"
        "PISO { nCorrectors 2; nNonOrthogonalCorrectors 2; pRefCell 0; pRefValue 0; }\n"
    )
    (case_dir / "system/fvSolution").write_text(custom_inline)
    mark_user_override(
        case_dir, relative_path="system/fvSolution",
        new_content=custom_inline.encode("utf-8"),
        detail={"reason": "engineer wrote inline-brace PISO"},
    )

    r2 = setup_bc_from_stl_patches(case_dir, case_id="piso_inline_proceeds")
    assert "system/fvSolution" in r2.skipped_user_overrides


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


# DEC-V61-111: solver_name routing tests.


def test_solver_name_default_authors_pimplefoam(tmp_path: Path):
    """V61-111: omitting ``solver_name`` preserves pre-V61-111 behavior
    (pimpleFoam template). This pins the backward-compat invariant —
    every existing call site that does not pass solver_name continues
    to get the V61-107.5 transient PIMPLE template byte-identical to
    the pre-V61-111 output."""
    case_dir = tmp_path / "default_solver_case"
    _scaffold_case(case_dir)
    _write_polymesh_axis_aligned_box(
        case_dir,
        [
            ("inlet", 50, 0, "-x"),
            ("outlet", 50, 50, "+x"),
            ("walls", 500, 100, "+z"),
        ],
    )
    result = setup_bc_from_stl_patches(case_dir, case_id="default_solver_case")
    assert result.solver_name == "pimpleFoam"
    control_dict = (case_dir / "system/controlDict").read_text()
    assert "application pimpleFoam;" in control_dict
    fv_solution = (case_dir / "system/fvSolution").read_text()
    assert "PIMPLE" in fv_solution
    assert "SIMPLE" not in fv_solution
    fv_schemes = (case_dir / "system/fvSchemes").read_text()
    assert "ddtSchemes  { default Euler; }" in fv_schemes


def test_solver_name_simplefoam_authors_steady_state_template(tmp_path: Path):
    """V61-111 Phase 1.3: passing ``solver_name='simpleFoam'`` writes
    the steady-state SIMPLE template — application simpleFoam,
    ddtSchemes steadyState, SIMPLE block (not PIMPLE), bounded
    linearUpwind divSchemes, relaxationFactors p=0.3 / U=0.7. This is
    the contract iter01 relies on to escape the transient-PIMPLE
    NaN-divergence regime (V61-106 Phase 1.3 deferred root cause)."""
    case_dir = tmp_path / "simplefoam_case"
    _scaffold_case(case_dir)
    _write_polymesh_axis_aligned_box(
        case_dir,
        [
            ("inlet", 50, 0, "-x"),
            ("outlet", 50, 50, "+x"),
            ("walls", 500, 100, "+z"),
        ],
    )
    result = setup_bc_from_stl_patches(
        case_dir,
        case_id="simplefoam_case",
        solver_name="simpleFoam",
        end_time=200,
    )
    assert result.solver_name == "simpleFoam"
    # No "icoFoam upgrade" warning since the caller asked for a
    # supported solver explicitly.
    assert all("simpleFoam" in w for w in result.warnings) or result.warnings == ()

    control_dict = (case_dir / "system/controlDict").read_text()
    assert "application simpleFoam;" in control_dict
    # simpleFoam interprets endTime as iteration count when deltaT=1.
    assert "endTime 200" in control_dict
    assert "deltaT 1" in control_dict
    # adjustTimeStep / maxCo / maxDeltaT must NOT be in simpleFoam
    # controlDict (no physical time coordinate).
    assert "adjustTimeStep" not in control_dict
    assert "maxCo" not in control_dict
    assert "maxDeltaT" not in control_dict

    fv_schemes = (case_dir / "system/fvSchemes").read_text()
    # ddtSchemes steadyState is THE distinguishing simpleFoam scheme.
    assert "ddtSchemes  { default steadyState; }" in fv_schemes
    # bounded linearUpwind for steady-state convection stability.
    assert "div(phi,U) bounded Gauss linearUpwind grad(U)" in fv_schemes
    # corrected laplacian/snGrad (non-orthogonal STL meshes).
    assert "laplacianSchemes { default Gauss linear corrected; }" in fv_schemes

    fv_solution = (case_dir / "system/fvSolution").read_text()
    # simpleFoam reads SIMPLE not PIMPLE.
    assert "SIMPLE" in fv_solution
    assert "PIMPLE" not in fv_solution
    # OpenFOAM-tutorial-standard SIMPLE relaxation factors.
    assert "p   0.3;" in fv_solution
    assert "U   0.7;" in fv_solution
    # residualControl gates convergence at loose targets.
    assert "residualControl" in fv_solution
    assert "p   1e-3;" in fv_solution
    assert "U   1e-4;" in fv_solution


def test_solver_name_simplefoam_min_iteration_floor(tmp_path: Path):
    """V61-111 controlDict: simpleFoam interprets endTime as iteration
    count. If callers pass a transient-style end_time (small floats
    like 2.5s), the floor at 100 iterations gives the steady solver
    enough marching room to converge from zero-IC. iter01-class
    smoke runs declare end_time_s=600 in intent.json, far above the
    floor — the floor only protects misconfigured short windows."""
    case_dir = tmp_path / "min_iter_case"
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
        case_dir,
        case_id="min_iter_case",
        solver_name="simpleFoam",
        end_time=2.5,  # transient-style; simpleFoam needs more iterations
    )
    control_dict = (case_dir / "system/controlDict").read_text()
    # Floor at 100 iterations.
    assert "endTime 100" in control_dict


def test_solver_name_icofoam_upgraded_to_pimplefoam_with_warning(tmp_path: Path):
    """V61-111: icoFoam requests are upgraded to pimpleFoam per
    V61-107.5 (icoFoam on STL meshes produces NaN regardless of dt).
    The upgrade is silent at the controlDict level (`application
    pimpleFoam` written) but surfaced as a warning in the result.
    Engineers who genuinely need icoFoam authoring can override
    controlDict via the raw-dict editor."""
    case_dir = tmp_path / "icofoam_upgrade_case"
    _scaffold_case(case_dir)
    _write_polymesh_axis_aligned_box(
        case_dir,
        [
            ("inlet", 50, 0, "-x"),
            ("outlet", 50, 50, "+x"),
            ("walls", 500, 100, "+z"),
        ],
    )
    result = setup_bc_from_stl_patches(
        case_dir, case_id="icofoam_upgrade_case", solver_name="icoFoam"
    )
    assert result.solver_name == "pimpleFoam"
    # Warning must mention BOTH the requested solver AND the upgrade target.
    warning_text = " ".join(result.warnings)
    assert "icoFoam" in warning_text
    assert "pimpleFoam" in warning_text
    # controlDict is the pimpleFoam template, NOT icoFoam.
    control_dict = (case_dir / "system/controlDict").read_text()
    assert "application pimpleFoam;" in control_dict
    assert "application icoFoam" not in control_dict


def test_solver_name_unrecognized_falls_back_to_pimplefoam_with_warning(tmp_path: Path):
    """V61-111: unrecognized solver names default to pimpleFoam (the
    safe baseline) with a warning. Protects against typos +
    intent.json mistakes; the warning surfaces the typo to the
    engineer rather than silently authoring a degenerate template."""
    case_dir = tmp_path / "unknown_solver_case"
    _scaffold_case(case_dir)
    _write_polymesh_axis_aligned_box(
        case_dir,
        [
            ("inlet", 50, 0, "-x"),
            ("outlet", 50, 50, "+x"),
            ("walls", 500, 100, "+z"),
        ],
    )
    result = setup_bc_from_stl_patches(
        case_dir,
        case_id="unknown_solver_case",
        solver_name="pisoFoam",  # plausible-looking typo
    )
    assert result.solver_name == "pimpleFoam"
    warning_text = " ".join(result.warnings)
    assert "pisoFoam" in warning_text
    assert "pimpleFoam" in warning_text
    control_dict = (case_dir / "system/controlDict").read_text()
    assert "application pimpleFoam;" in control_dict


# DEC-V61-111 / Codex R1 closure tests.


def test_simplefoam_authoring_rejects_user_pimplefoam_marker_override(tmp_path: Path):
    """V61-111 / Codex R1 P1-1: when the AI authors simpleFoam, a
    user-overridden controlDict that still says ``application
    pimpleFoam;`` would land an incoherent solver group on disk
    (AI-authored simpleFoam fvSolution with SIMPLE block + user
    pimpleFoam controlDict). The solver-marker guard MUST detect
    this and raise solver_dicts_partial_override (mirror behavior
    of the pre-V61-111 icoFoam-marker case for AI-pimpleFoam)."""
    case_dir = tmp_path / "stale_pimplefoam_override_case"
    _scaffold_case(case_dir)
    _write_polymesh_axis_aligned_box(
        case_dir,
        [
            ("inlet", 50, 0, "-x"),
            ("outlet", 50, 50, "+x"),
            ("walls", 500, 100, "+z"),
        ],
    )
    # First setup: AI authors pimpleFoam (default).
    setup_bc_from_stl_patches(
        case_dir, case_id="stale_pimplefoam_override_case"
    )
    # Engineer overrides controlDict to keep custom endTime but
    # leaves application pimpleFoam (the default era). Now a
    # different intent calls for simpleFoam.
    custom_control_dict = (
        'FoamFile { version 2.0; format ascii; class dictionary; '
        'location "system"; object controlDict; }\n'
        "application pimpleFoam;\n"
        "endTime 100;\n"
        "deltaT 0.001;\n"
        "adjustTimeStep yes;\n"
        "maxCo 0.5;\n"
    )
    (case_dir / "system/controlDict").write_text(custom_control_dict)
    mark_user_override(
        case_dir,
        relative_path="system/controlDict",
        new_content=custom_control_dict.encode("utf-8"),
        detail={"reason": "engineer pinned pimpleFoam endTime"},
    )

    # AI now requested for simpleFoam (e.g. intent.json:solver.name
    # changed to simpleFoam). The user controlDict mismatches.
    with pytest.raises(StlPatchBCError) as exc:
        setup_bc_from_stl_patches(
            case_dir,
            case_id="stale_pimplefoam_override_case",
            solver_name="simpleFoam",
        )
    assert exc.value.failing_check == "solver_dicts_partial_override"
    err = str(exc.value)
    assert "simpleFoam" in err  # AI's requested solver
    assert "system/controlDict" in err  # the offending file


def test_pimplefoam_authoring_rejects_user_simplefoam_marker_override(tmp_path: Path):
    """V61-111 / Codex R1 P1-1: symmetric to the
    pimpleFoam-mismatch test above. AI authoring pimpleFoam +
    user controlDict carrying ``application simpleFoam;`` would
    land an incoherent group (AI's pimpleFoam fvSolution PIMPLE
    block + user's simpleFoam controlDict, expecting SIMPLE
    + relaxationFactors that AI didn't author). Must raise."""
    case_dir = tmp_path / "stale_simplefoam_override_case"
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
        case_dir,
        case_id="stale_simplefoam_override_case",
        solver_name="simpleFoam",
    )
    custom_control_dict = (
        'FoamFile { version 2.0; format ascii; class dictionary; '
        'location "system"; object controlDict; }\n'
        "application simpleFoam;\n"
        "endTime 500;\n"
        "deltaT 1;\n"
    )
    (case_dir / "system/controlDict").write_text(custom_control_dict)
    mark_user_override(
        case_dir,
        relative_path="system/controlDict",
        new_content=custom_control_dict.encode("utf-8"),
        detail={"reason": "engineer pinned simpleFoam iteration cap"},
    )

    # AI now reverts to pimpleFoam (default) — mismatch.
    with pytest.raises(StlPatchBCError) as exc:
        setup_bc_from_stl_patches(
            case_dir, case_id="stale_simplefoam_override_case"
        )
    assert exc.value.failing_check == "solver_dicts_partial_override"
    err = str(exc.value)
    assert "pimpleFoam" in err  # AI's requested solver
    assert "system/controlDict" in err


def test_solver_name_reports_actual_on_disk_when_controldict_user_owned(tmp_path: Path):
    """V61-111 / Codex R1 P2-1: when controlDict is user-owned and
    skipped by atomic_commit_dicts, the result.solver_name must
    reflect what's actually on disk (what /solve will read), not
    what the caller asked for. This makes the verification field
    reliable for the exact raw-dict workflow it's meant to support.

    Test scenario: AI first authors pimpleFoam; engineer overrides
    fvSchemes + fvSolution + controlDict ALL THREE to a coherent
    custom-tuned pimpleFoam template (full-group override → guard
    steps out per the V61-107.5 R16 contract). Caller then asks for
    simpleFoam — the on-disk controlDict still says pimpleFoam, so
    result.solver_name reports pimpleFoam + a warning."""
    case_dir = tmp_path / "ondisk_truth_case"
    _scaffold_case(case_dir)
    _write_polymesh_axis_aligned_box(
        case_dir,
        [
            ("inlet", 50, 0, "-x"),
            ("outlet", 50, 50, "+x"),
            ("walls", 500, 100, "+z"),
        ],
    )
    # First AI run authors pimpleFoam.
    setup_bc_from_stl_patches(case_dir, case_id="ondisk_truth_case")

    # Engineer fully owns the solver group (all 3 files marked
    # user-overridden) — guard steps out per V61-107.5 R16 contract.
    for rel in ("system/controlDict", "system/fvSchemes", "system/fvSolution"):
        text = (case_dir / rel).read_text()
        mark_user_override(
            case_dir,
            relative_path=rel,
            new_content=text.encode("utf-8"),
            detail={"reason": "full-group pimpleFoam override"},
        )

    # Caller asks for simpleFoam. The atomic_commit_dicts skips the
    # 3 overridden files; on-disk controlDict still says
    # ``application pimpleFoam;``. result.solver_name must reflect
    # that truth, not the requested simpleFoam.
    result = setup_bc_from_stl_patches(
        case_dir, case_id="ondisk_truth_case", solver_name="simpleFoam"
    )
    assert result.solver_name == "pimpleFoam"
    # Warning surfaces the divergence + names the override path so
    # the engineer can act.
    warning_text = " ".join(result.warnings)
    assert "pimpleFoam" in warning_text
    assert "simpleFoam" in warning_text
    assert "controlDict" in warning_text
    # On-disk controlDict still pimpleFoam (was user-overridden).
    on_disk = (case_dir / "system/controlDict").read_text()
    assert "application pimpleFoam;" in on_disk


def test_simplefoam_residual_control_early_exit_treated_as_converged():
    """V61-111 / Codex R1 P1-2: simpleFoam terminates early via
    ``residualControl`` once both p and U initial residuals fall
    below the configured target. ``_is_converged`` must treat this
    as the happy-path indicator for application=simpleFoam, NOT as
    "ran short of endTime" (which would misclassify the normal
    convergence path as ``converged=false``).

    Pre-V61-111 ``_is_converged`` only checked
    end_time_reached >= configured_end_time - 0.5*dt. With simpleFoam
    + residualControl exiting at iteration N < endTime, that gate
    returned False → ``/solve`` reported converged=False on the
    happy path.

    Fix: when application=simpleFoam, accept either ``ran full
    iteration budget`` OR log contains ``SIMPLE solution converged
    in N iterations`` (the OpenFOAM-canonical message).
    """
    from ui.backend.services.case_solve.solver_runner import _is_converged

    # Steady-state run terminated by residualControl at iteration
    # 87 of an endTime=200 budget. continuity error tiny + finite.
    parsed_early = {
        "end_time_reached": 87.0,  # short of 200 endTime
        "continuity": 1e-7,
    }
    log_with_residual_msg = (
        "Time = 87\n"
        "smoothSolver:  Solving for Ux, Initial residual = 1e-05, ...\n"
        "GAMG:  Solving for p, Initial residual = 5e-04, ...\n"
        "SIMPLE solution converged in 87 iterations\n"
        "End\n"
    )
    # WITHOUT the new application+log_text params, default behavior
    # (icoFoam) would reject this as not-yet-reached endTime.
    assert _is_converged(parsed_early, configured_end_time=200, configured_delta_t=1) is False
    # WITH simpleFoam + log_text, residualControl-message detection
    # promotes early-exit to converged=True.
    assert _is_converged(
        parsed_early,
        configured_end_time=200,
        configured_delta_t=1,
        application="simpleFoam",
        log_text=log_with_residual_msg,
    ) is True

    # Sanity: simpleFoam log WITHOUT the converged message must NOT
    # be promoted (ran short of endTime AND no residualControl
    # signal → genuine early stop, e.g. solver crashed).
    log_without_msg = "Time = 87\nFOAM Warning ...\n"
    assert _is_converged(
        parsed_early,
        configured_end_time=200,
        configured_delta_t=1,
        application="simpleFoam",
        log_text=log_without_msg,
    ) is False

    # Sanity: simpleFoam that ran the full iteration budget without
    # residualControl message is converged=True (ran full budget +
    # finite residuals = ok).
    parsed_full = {"end_time_reached": 200.0, "continuity": 1e-7}
    assert _is_converged(
        parsed_full,
        configured_end_time=200,
        configured_delta_t=1,
        application="simpleFoam",
        log_text="Time = 200\nEnd\n",
    ) is True

    # Backward compat: transient solver path unchanged (default
    # application=icoFoam, end_t < endTime → False).
    assert _is_converged(
        parsed_early, configured_end_time=200, configured_delta_t=1
    ) is False
