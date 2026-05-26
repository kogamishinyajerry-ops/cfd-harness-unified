"""DEC-V61-206 · manifest→WorkbenchBasics deriver.

Imported cases have no hand-authored knowledge/workbench_basics/<id>.yaml,
so the workbench used to fall back to fabricated placeholders. The deriver
mirrors the real OpenFOAM case on disk instead. These tests pin the
faithful-mirror contract:
    - patches + per-field BCs come straight from polyMesh/boundary + 0/<f>
    - role is derived from the ACTUAL U BC (a noSlip "periodic_*" → wall)
    - material / solver come from constant/ + system/controlDict
    - a case with no OpenFOAM boundary derives to None (→ endpoint 404,
      UI keeps its honest 待识别) — never a guess
"""
from __future__ import annotations

from pathlib import Path

from ui.backend.services.workbench_basics_deriver import derive_workbench_basics
from ui.backend.services.workbench_basics_deriver.deriver import (
    parse_foam_boundary_field,
)

# A 3-patch turbine-cascade-style case, written exactly like setup-bc would.
_BOUNDARY = """\
FoamFile { version 2.0; format ascii; class polyBoundaryMesh; object boundary; }
3
(
    inlet      { type patch; nFaces 120;  startFace 49234; }
    outlet     { type patch; nFaces 120;  startFace 49354; }
    blade      { type patch; nFaces 1264; startFace 50034; }
)
"""

_U = """\
FoamFile { version 2.0; format ascii; class volVectorField; object U; }
dimensions      [0 1 -1 0 0 0 0];
internalField   uniform (0 0 0);
boundaryField
{
    inlet  { type fixedValue; value uniform (1 -0 -0); }
    outlet { type zeroGradient; }
    blade  { type noSlip; }
}
"""

_P = """\
FoamFile { version 2.0; format ascii; class volScalarField; object p; }
dimensions      [0 2 -2 0 0 0 0];
internalField   uniform 0;
boundaryField
{
    inlet  { type zeroGradient; }
    outlet { type fixedValue; value uniform 0; }
    blade  { type zeroGradient; }
}
"""

_PHYS = "FoamFile { object physicalProperties; }\nnu  nu [0 2 -1 0 0 0 0] 1e-05;\n"
_MOM = "FoamFile { object momentumTransport; }\nsimulationType  laminar;\n"
_CONTROL = "FoamFile { object controlDict; }\napplication     simpleFoam;\nendTime  2000;\n"


def _write_case(root: Path) -> Path:
    case = root / "case_x"
    (case / "constant" / "polyMesh").mkdir(parents=True)
    (case / "0").mkdir()
    (case / "system").mkdir()
    (case / "constant" / "polyMesh" / "boundary").write_text(_BOUNDARY)
    (case / "0" / "U").write_text(_U)
    (case / "0" / "p").write_text(_P)
    (case / "constant" / "physicalProperties").write_text(_PHYS)
    (case / "constant" / "momentumTransport").write_text(_MOM)
    (case / "system" / "controlDict").write_text(_CONTROL)
    return case


def test_parse_foam_boundary_field_vectors_and_scalars():
    parsed = parse_foam_boundary_field(_U)
    assert parsed["inlet"] == {"type": "fixedValue", "value": [1.0, 0.0, 0.0]}
    assert parsed["outlet"] == {"type": "zeroGradient"}
    assert parsed["blade"] == {"type": "noSlip"}
    pp = parse_foam_boundary_field(_P)
    assert pp["outlet"] == {"type": "fixedValue", "value": 0.0}


def test_derive_patches_role_from_actual_u_bc(tmp_path):
    case = _write_case(tmp_path)
    m = derive_workbench_basics("case_x", case_dir=case)
    assert m is not None
    assert m.provenance == "derived"
    roles = {p.id: p.role for p in m.patches}
    assert roles == {"inlet": "inlet", "outlet": "outlet", "blade": "wall"}
    # face count is surfaced in the description, faithfully
    blade = next(p for p in m.patches if p.id == "blade")
    assert "1264 faces" in (blade.description_zh or "")


def test_derive_boundary_conditions_values_and_display(tmp_path):
    case = _write_case(tmp_path)
    m = derive_workbench_basics("case_x", case_dir=case)
    assert m is not None
    by_field = {bc.field: bc for bc in m.boundary_conditions}
    assert set(by_field) == {"U", "p"}
    u = by_field["U"].per_patch
    assert u["inlet"].type == "fixedValue"
    assert u["inlet"].value == [1.0, 0.0, 0.0]
    assert u["inlet"].display_zh == "U=(1, 0, 0)"
    assert u["blade"].type == "noSlip"
    assert u["blade"].display_zh == "U = 0"
    p = by_field["p"].per_patch
    assert p["outlet"].type == "fixedValue"
    assert p["outlet"].value == 0.0


def test_derive_material_and_solver(tmp_path):
    case = _write_case(tmp_path)
    m = derive_workbench_basics("case_x", case_dir=case)
    assert m is not None
    nu = next(
        pr for mat in m.materials for pr in mat.properties if pr.name == "kinematic_viscosity"
    )
    assert nu.value == 1e-05
    assert m.solver is not None
    assert m.solver.name == "simpleFoam"
    assert m.solver.steady_state is True
    assert m.solver.laminar is True


def test_no_openfoam_boundary_derives_to_none(tmp_path):
    # An imported case that has not been through setup-bc yet → no boundary
    # file → None (endpoint 404 → UI shows honest 待识别, never a guess).
    empty = tmp_path / "no_mesh"
    empty.mkdir()
    assert derive_workbench_basics("no_mesh", case_dir=empty) is None


def test_endpoint_returns_derived_basics_for_imported_case(tmp_path, monkeypatch):
    """The route falls back to the deriver when no authored yaml exists,
    returning provenance=derived with the real patches/BCs (not a 404)."""
    from fastapi.testclient import TestClient

    from ui.backend.main import app
    from ui.backend.services.workbench_basics_deriver import deriver as deriver_mod

    imported_root = tmp_path / "imported"
    imported_root.mkdir()
    # _write_case creates <root>/case_x; rename to a route-safe case id dir.
    _write_case(imported_root)
    (imported_root / "derivable_case").mkdir()
    for sub in ("constant", "0", "system"):
        (imported_root / "case_x" / sub).rename(imported_root / "derivable_case" / sub)

    monkeypatch.setattr(deriver_mod, "IMPORTED_DIR", imported_root)
    client = TestClient(app)
    r = client.get("/api/cases/derivable_case/workbench-basics")
    assert r.status_code == 200
    body = r.json()
    assert body["provenance"] == "derived"
    assert {p["id"] for p in body["patches"]} == {"inlet", "outlet", "blade"}
    u = next(bc for bc in body["boundary_conditions"] if bc["field"] == "U")
    assert u["per_patch"]["inlet"]["display_zh"] == "U=(1, 0, 0)"


def test_patch_without_u_bc_derives_to_unknown_role_not_a_name_guess(tmp_path):
    # Codex R0 P1: a patch present in polyMesh/boundary but absent from 0/U
    # has unknowable semantics. The deriver must say role="unknown" and label
    # the patch as having no 0/U — NOT guess "inlet" from the name.
    case = tmp_path / "c"
    (case / "constant" / "polyMesh").mkdir(parents=True)
    (case / "0").mkdir()
    (case / "constant" / "polyMesh" / "boundary").write_text(
        "FoamFile { object boundary; }\n1\n(\n  inlet { type patch; nFaces 5; startFace 1; }\n)\n"
    )
    # 0/U exists but does NOT cover the `inlet` patch.
    (case / "0" / "U").write_text(
        "FoamFile { object U; }\nboundaryField\n{\n  somethingElse { type noSlip; }\n}\n"
    )
    m = derive_workbench_basics("c", case_dir=case)
    assert m is not None
    inlet = next(p for p in m.patches if p.id == "inlet")
    assert inlet.role == "unknown"
    # Codex R1 P2: must not claim the file is absent (this also covers a
    # partial/unreadable 0/U) — only that THIS patch's U BC wasn't identified.
    assert "未识别到该面的 0/U" in (inlet.description_zh or "")
    # dimension is unknowable when 0/U doesn't cover every patch → omitted.
    assert m.dimension is None


def test_solver_without_momentum_transport_does_not_claim_laminar(tmp_path):
    # Codex R0 P1: no constant/momentumTransport → laminar is unknowable, so
    # it must be None and the reasoning must NOT assert laminar.
    case = tmp_path / "c"
    (case / "constant" / "polyMesh").mkdir(parents=True)
    (case / "0").mkdir()
    (case / "system").mkdir()
    (case / "constant" / "polyMesh" / "boundary").write_text(
        "FoamFile { object boundary; }\n1\n(\n  inlet { type patch; nFaces 5; startFace 1; }\n)\n"
    )
    (case / "0" / "U").write_text(
        "FoamFile { object U; }\nboundaryField\n{\n  inlet { type fixedValue; value uniform (1 0 0); }\n}\n"
    )
    (case / "system" / "controlDict").write_text(
        "FoamFile { object controlDict; }\napplication simpleFoam;\n"
    )
    m = derive_workbench_basics("c", case_dir=case)
    assert m is not None and m.solver is not None
    assert m.solver.laminar is None
    assert "laminar" not in m.solver.reasoning_zh
    assert "momentumTransport" not in m.solver.reasoning_zh


def test_dimension_derived_from_empty_patch(tmp_path):
    # Codex R0 P2: dimension must be read from disk. An `empty` U BC marks a
    # 2D case; without one it is 3D.
    case = tmp_path / "c"
    (case / "constant" / "polyMesh").mkdir(parents=True)
    (case / "0").mkdir()
    (case / "constant" / "polyMesh" / "boundary").write_text(
        "FoamFile { object boundary; }\n2\n(\n"
        "  inlet { type patch; nFaces 5; startFace 1; }\n"
        "  frontAndBack { type empty; nFaces 50; startFace 6; }\n)\n"
    )
    (case / "0" / "U").write_text(
        "FoamFile { object U; }\nboundaryField\n{\n"
        "  inlet { type fixedValue; value uniform (1 0 0); }\n"
        "  frontAndBack { type empty; }\n}\n"
    )
    m = derive_workbench_basics("c", case_dir=case)
    assert m is not None
    assert m.dimension == 2


def test_stale_empty_block_in_0U_does_not_force_2d(tmp_path):
    # Codex R2 P1: the 2D/3D decision must scan only boundary-backed patches.
    # A 0/U with an `empty` block for a patch NOT in polyMesh/boundary (stale)
    # must NOT make the case 2D when every real patch is non-empty.
    case = tmp_path / "c"
    (case / "constant" / "polyMesh").mkdir(parents=True)
    (case / "0").mkdir()
    (case / "constant" / "polyMesh" / "boundary").write_text(
        "FoamFile { object boundary; }\n1\n(\n  inlet { type patch; nFaces 5; startFace 1; }\n)\n"
    )
    # 0/U covers the real `inlet` (non-empty) PLUS a stale `frontAndBack` empty
    # block that is not a real mesh patch.
    (case / "0" / "U").write_text(
        "FoamFile { object U; }\nboundaryField\n{\n"
        "  inlet { type fixedValue; value uniform (1 0 0); }\n"
        "  frontAndBack { type empty; }\n}\n"
    )
    m = derive_workbench_basics("c", case_dir=case)
    assert m is not None
    # only `inlet` is boundary-backed and it is non-empty → 3D, not 2D.
    assert m.dimension == 3


def test_legacy_turbulence_properties_cites_correct_filename(tmp_path):
    # Codex R1 P2: a case using the legacy constant/turbulenceProperties must
    # NOT have reasoning_zh claim "constant/momentumTransport".
    case = tmp_path / "c"
    (case / "constant" / "polyMesh").mkdir(parents=True)
    (case / "0").mkdir()
    (case / "system").mkdir()
    (case / "constant" / "polyMesh" / "boundary").write_text(
        "FoamFile { object boundary; }\n1\n(\n  inlet { type patch; nFaces 5; startFace 1; }\n)\n"
    )
    (case / "0" / "U").write_text(
        "FoamFile { object U; }\nboundaryField\n{\n  inlet { type fixedValue; value uniform (1 0 0); }\n}\n"
    )
    (case / "system" / "controlDict").write_text(
        "FoamFile { object controlDict; }\napplication simpleFoam;\n"
    )
    (case / "constant" / "turbulenceProperties").write_text(
        "FoamFile { object turbulenceProperties; }\nsimulationType RAS;\n"
    )
    m = derive_workbench_basics("c", case_dir=case)
    assert m is not None and m.solver is not None
    assert m.solver.laminar is False
    assert "constant/turbulenceProperties" in m.solver.reasoning_zh
    assert "momentumTransport" not in m.solver.reasoning_zh


def test_periodic_patch_written_noslip_derives_to_wall(tmp_path):
    # Faithful-to-disk: a patch NAMED periodic_* but WRITTEN as noSlip ran
    # as a wall — the deriver must say wall, not periodic.
    case = tmp_path / "c"
    (case / "constant" / "polyMesh").mkdir(parents=True)
    (case / "0").mkdir()
    (case / "constant" / "polyMesh" / "boundary").write_text(
        "FoamFile { object boundary; }\n1\n(\n  periodic_lower { type patch; nFaces 280; startFace 1; }\n)\n"
    )
    (case / "0" / "U").write_text(
        "FoamFile { object U; }\nboundaryField\n{\n  periodic_lower { type noSlip; }\n}\n"
    )
    m = derive_workbench_basics("c", case_dir=case)
    assert m is not None
    assert m.patches[0].role == "wall"
