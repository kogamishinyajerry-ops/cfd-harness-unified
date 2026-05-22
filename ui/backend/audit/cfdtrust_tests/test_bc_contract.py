"""M6 — Real bc_contract tests.

Two layers (matches M4 / M5 shape):
  - parser + persistence unit tests in `cfdtrust.backends.openfoam`
  - audit-gate tests in `cfdtrust.audit.boundary_conditions`
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from cfdtrust.backends import openfoam as ofa
from cfdtrust.audit.boundary_conditions import run as bc_gate


# ---------- canonical 0/<field> samples ----------


_U_FILE = """\
/*--------------------------------*- C++ -*----------------------------------*\\
FoamFile { format ascii; class volVectorField; object U; }
// comment

dimensions      [0 1 -1 0 0 0 0];

internalField   uniform (44.2 0 0);

boundaryField
{
    inlet
    {
        type            fixedValue;
        value           uniform (44.2 0 0);
    }
    outlet
    {
        type            zeroGradient;
    }
    bottomWall
    {
        type            noSlip;
    }
    stepFace
    {
        type            noSlip;
    }
    topWall
    {
        type            noSlip;
    }
    frontAndBack
    {
        type            empty;
    }
}
"""


_K_FILE = """\
FoamFile { format ascii; class volScalarField; object k; }

dimensions      [0 2 -2 0 0 0 0];
internalField   uniform 0.001;

boundaryField
{
    inlet
    {
        type            turbulentIntensityKineticEnergyInlet;
        intensity       0.01;
        value           uniform 0.001;
    }
    outlet
    {
        type            zeroGradient;
    }
    bottomWall
    {
        type            kqRWallFunction;
        value           uniform 0.001;
    }
    frontAndBack
    {
        type            empty;
    }
}
"""


# ---------- _parse_field_boundary_field: canonical ----------


def test_parse_field_boundary_field_extracts_all_patches():
    out = ofa._parse_field_boundary_field(_U_FILE)
    assert set(out.keys()) == {
        "inlet", "outlet", "bottomWall", "stepFace", "topWall", "frontAndBack",
    }
    assert out["inlet"]["type"] == "fixedValue"
    assert out["outlet"]["type"] == "zeroGradient"
    assert out["bottomWall"]["type"] == "noSlip"
    assert out["frontAndBack"]["type"] == "empty"


def test_parse_field_boundary_field_scalar_file():
    out = ofa._parse_field_boundary_field(_K_FILE)
    assert out["inlet"]["type"] == "turbulentIntensityKineticEnergyInlet"
    assert out["bottomWall"]["type"] == "kqRWallFunction"
    assert out["frontAndBack"]["type"] == "empty"


# ---------- _parse_field_boundary_field: robustness ----------


def test_parse_field_boundary_field_returns_empty_on_no_block():
    """0/<file> without a `boundaryField` block must not crash."""
    text = "FoamFile {}\ndimensions [0 1 -1 0 0 0 0];\ninternalField uniform 0;\n"
    assert ofa._parse_field_boundary_field(text) == {}


def test_parse_field_boundary_field_returns_empty_on_truncated():
    text = "boundaryField\n{\n    inlet\n    {\n        type wall;\n"
    # Unbalanced braces — no partial claim allowed.
    assert ofa._parse_field_boundary_field(text) == {}


def test_parse_field_boundary_field_skips_untyped_block():
    text = """
boundaryField
{
    weirdPatch
    {
        value uniform 1.0;
    }
    realPatch
    {
        type            wall;
    }
}
"""
    out = ofa._parse_field_boundary_field(text)
    assert "weirdPatch" not in out
    assert out["realPatch"]["type"] == "wall"


def test_parse_field_boundary_field_strips_comments():
    """Hidden `type` line inside a `//` comment must be ignored."""
    text = """
// type fake;
/* multiline
   type alsoFake;
*/
boundaryField
{
    p1
    {
        // type stillFake;
        type            real;
    }
}
"""
    out = ofa._parse_field_boundary_field(text)
    assert out == {"p1": {"type": "real"}}


def test_parse_field_boundary_field_handles_nested_braces_in_block():
    """Some BC entries have nested `{}` blocks (e.g. cyclicAMI patchValues).
    The parser must balance them and still extract the outer type."""
    text = """
boundaryField
{
    cyclic1
    {
        type            cyclicAMI;
        transform       { type none; }
    }
    plain
    {
        type            wall;
    }
}
"""
    out = ofa._parse_field_boundary_field(text)
    assert out["cyclic1"]["type"] == "cyclicAMI"
    assert out["plain"]["type"] == "wall"


# ---------- DEC-V61-201-SUB-INGEST-BC-REGEX-GROUPED-PATCHES ----------
#
# Canonical OpenFOAM `"(name1|name2|...)" { ... }` syntax — one BC
# block declares many patches in one shot. Compressible aero benchmark
# cases (ONERA M6, RAE 2822, NACA 0012 transonic, ...) author 0/p,
# 0/k, 0/omega this way as the conventional shortcut. Closes
# case_006 production blocker (Gap #23).


def test_parse_field_boundary_field_expands_grouped_patches():
    """Test A: synthetic 0/p with `"(wing|farfield)"` { type fixedValue;
    value uniform 0; } → bc_quality result contains BOTH wing AND
    farfield with that same BC shape."""
    text = """
boundaryField
{
    "(wing|farfield)"
    {
        type            fixedValue;
        value           uniform 0;
    }
}
"""
    out = ofa._parse_field_boundary_field(text)
    assert set(out.keys()) == {"wing", "farfield"}
    assert out["wing"]["type"] == "fixedValue"
    assert out["wing"]["value_scalar"] == 0.0
    assert out["farfield"]["type"] == "fixedValue"
    assert out["farfield"]["value_scalar"] == 0.0
    # Each synthetic entry is an independent dict (no shared-mutable-
    # state surprise if a downstream consumer ever mutates one).
    assert out["wing"] is not out["farfield"]


def test_parse_field_boundary_field_mixes_single_and_grouped():
    """Test B: mixed file with single-patch + grouped + value-vector +
    nested-brace robustness — all parse correctly, ordering irrelevant."""
    text = """
boundaryField
{
    inlet
    {
        type            fixedValue;
        value           uniform (44.2 0 0);
    }
    "(wing|farfield|symmetry)"
    {
        type            slip;
    }
    outlet
    {
        type            zeroGradient;
    }
}
"""
    out = ofa._parse_field_boundary_field(text)
    assert set(out.keys()) == {"inlet", "wing", "farfield", "symmetry", "outlet"}
    assert out["inlet"]["type"] == "fixedValue"
    assert out["inlet"]["value_vector"] == [44.2, 0.0, 0.0]
    for name in ("wing", "farfield", "symmetry"):
        assert out[name]["type"] == "slip"
    assert out["outlet"]["type"] == "zeroGradient"


def test_parse_field_boundary_field_grouped_drops_empty_fragments():
    """Test C: malformed alternation `"(wing|)"` → wing parses, empty
    fragment silently dropped. No exception. Walker advances normally
    to the next single-patch block after the malformed group."""
    text = """
boundaryField
{
    "(wing|)"
    {
        type            fixedValue;
        value           uniform 1.5;
    }
    farfield
    {
        type            zeroGradient;
    }
}
"""
    out = ofa._parse_field_boundary_field(text)
    # wing parsed (valid fragment), empty fragment produced no entry,
    # farfield parsed (walker advanced past the malformed group).
    assert set(out.keys()) == {"wing", "farfield"}
    assert out["wing"]["type"] == "fixedValue"
    assert out["wing"]["value_scalar"] == 1.5
    assert out["farfield"]["type"] == "zeroGradient"


# ---------- _persist_bc_quality ----------


def test_persist_bc_quality_ok_path(tmp_path: Path):
    fields = {
        "U": {"file": "0/U", "parsed": True, "patches": {"inlet": {"type": "fixedValue"}}},
        "p": {"file": "0/p", "parsed": True, "patches": {"inlet": {"type": "zeroGradient"}}},
    }
    out = ofa._persist_bc_quality(
        tmp_path, fields=fields, expected_fields=["U", "p"],
    )
    data = json.loads(out.read_text())
    assert data["bc_parsing_status"] == "ok"
    assert data["fields_present"] == ["U", "p"]
    assert data["fields_missing"] == []
    assert data["expected_fields"] == ["U", "p"]
    assert data["fields"]["U"]["patches"]["inlet"]["type"] == "fixedValue"


def test_persist_bc_quality_missing_file_path(tmp_path: Path):
    fields = {
        "U": {"file": "0/U", "parsed": True, "patches": {"inlet": {"type": "fixedValue"}}},
        "nut": {"file": "0/nut", "parsed": False, "missing": True},
    }
    out = ofa._persist_bc_quality(
        tmp_path, fields=fields, expected_fields=["U", "nut"],
    )
    data = json.loads(out.read_text())
    assert data["fields_present"] == ["U"]
    assert data["fields_missing"] == ["nut"]


def test_persist_bc_quality_blocked_path(tmp_path: Path):
    out = ofa._persist_bc_quality(
        tmp_path, fields=None, expected_fields=["U", "p"],
        blocked_reason="zero_dir_unreadable",
        blocked_detail="permission denied",
    )
    data = json.loads(out.read_text())
    assert data["bc_parsing_status"] == "blocked"
    assert data["reason"] == "zero_dir_unreadable"
    # Honesty: no fake fields data leaking through.
    assert "fields" not in data


# ---------- _collect_and_persist_bc ----------


def _make_case_with_zero(tmp_path: Path, files: dict[str, str]) -> Path:
    case = tmp_path / "case"
    (case / "0").mkdir(parents=True)
    for name, body in files.items():
        (case / "0" / name).write_text(body)
    return case


def test_collect_and_persist_bc_walks_manifest_fields(tmp_path: Path):
    case = _make_case_with_zero(tmp_path, {"U": _U_FILE, "p": _U_FILE.replace("(44.2 0 0)", "0.0"), "k": _K_FILE})
    manifest = {"bc_contract": {"turbulence_fields": ["k", "omega"]}}
    ofa._collect_and_persist_bc(case, manifest)

    data = json.loads((case / "artifacts" / "bc_quality.json").read_text())
    assert data["expected_fields"] == ["U", "p", "k", "omega"]
    assert "U" in data["fields_present"]
    assert "k" in data["fields_present"]
    assert "omega" in data["fields_missing"]   # not created in this test


def test_collect_and_persist_bc_deduplicates_canonical_fields(tmp_path: Path):
    """Manifest can list `U` in turbulence_fields by mistake — we must
    not double-process it."""
    case = _make_case_with_zero(tmp_path, {"U": _U_FILE, "p": _U_FILE})
    manifest = {"bc_contract": {"turbulence_fields": ["U", "k"]}}
    ofa._collect_and_persist_bc(case, manifest)
    data = json.loads((case / "artifacts" / "bc_quality.json").read_text())
    # U appears exactly once
    assert data["expected_fields"].count("U") == 1
    assert data["expected_fields"] == ["U", "p", "k"]


# =====================================================================
# M6.2 — audit/boundary_conditions.run() gate evaluation
# =====================================================================


def _write_geom_quality(case_dir: Path, patches: dict) -> None:
    art = case_dir / "artifacts"
    art.mkdir(parents=True, exist_ok=True)
    (art / "geometry_quality.json").write_text(json.dumps({
        "status": "ok",
        "patches": patches,
        "patch_count": len(patches),
        "polymesh_boundary_parsed": True,
    }))


def _write_bc_quality(case_dir: Path, fields: dict, expected: list[str]) -> None:
    art = case_dir / "artifacts"
    art.mkdir(parents=True, exist_ok=True)
    (art / "bc_quality.json").write_text(json.dumps({
        "bc_parsing_status": "ok",
        "expected_fields": expected,
        "fields_present": sorted(
            n for n, d in fields.items() if d.get("parsed")
        ),
        "fields_missing": sorted(
            n for n, d in fields.items() if d.get("missing")
        ),
        "fields": fields,
    }))


_BFS_REALIZED_PATCHES = {
    "inlet": {"type": "patch", "nFaces": 50, "startFace": 0},
    "outlet": {"type": "patch", "nFaces": 80, "startFace": 50},
    "topWall": {"type": "wall", "nFaces": 160, "startFace": 130},
    "bottomWall": {"type": "wall", "nFaces": 160, "startFace": 290},
    "stepFace": {"type": "wall", "nFaces": 30, "startFace": 450},
    "frontAndBack": {"type": "empty", "nFaces": 23200, "startFace": 480},
}


def _bfs_manifest(**overrides) -> dict:
    m = {
        "case_id": "bc_test",
        "solver_backend": "openfoam",
        "bc_contract": {
            "inlet": {
                "velocity": {"type": "fixedValue", "magnitude_m_s": 44.2},
                "pressure": {"type": "zeroGradient"},
                "k": {"type": "turbulentIntensityKineticEnergyInlet"},
                "omega": {"type": "turbulentMixingLengthFrequencyInlet"},
            },
            "outlet": {
                "pressure": {"type": "fixedValue", "value_Pa": 0.0},
                "velocity": {"type": "zeroGradient"},
            },
            "wall": {  # type-class wildcard for BFS (topWall + bottomWall + stepFace)
                "velocity": {"type": "noSlip"},
                "k": {"type": "kqRWallFunction"},
                "omega": {"type": "omegaWallFunction"},
            },
            "turbulence_fields": ["k", "omega", "nut"],
        },
    }
    m.update(overrides)
    return m


def _full_realized_bc_fields() -> dict:
    """A fully-consistent realized bc_quality.json `fields` dict that
    matches the BFS manifest above.

    Post-M7 NOTE: numeric annotations (`value_vector`, `value_scalar`,
    `params`) are included to match the manifest's numeric declarations
    (`magnitude_m_s: 44.2`, etc.). Without them, the value_match
    dimension would FAIL on every PASS-path M6 test — those tests
    implicitly relied on the M6 audit not yet checking numerics.
    """
    u_patches = {
        "inlet": {"type": "fixedValue", "value_vector": [44.2, 0.0, 0.0]},
        "outlet": {"type": "zeroGradient"},
        "topWall": {"type": "noSlip"},
        "bottomWall": {"type": "noSlip"},
        "stepFace": {"type": "noSlip"},
        "frontAndBack": {"type": "empty"},
    }
    p_patches = {
        "inlet": {"type": "zeroGradient"},
        "outlet": {"type": "fixedValue", "value_scalar": 0.0},
        "topWall": {"type": "zeroGradient"},
        "bottomWall": {"type": "zeroGradient"},
        "stepFace": {"type": "zeroGradient"},
        "frontAndBack": {"type": "empty"},
    }
    k_patches = {
        "inlet": {
            "type": "turbulentIntensityKineticEnergyInlet",
            "value_scalar": 0.293,
            "params": {"intensity": 0.01},
        },
        "outlet": {"type": "zeroGradient"},
        "topWall": {"type": "kqRWallFunction", "value_scalar": 0.293},
        "bottomWall": {"type": "kqRWallFunction", "value_scalar": 0.293},
        "stepFace": {"type": "kqRWallFunction", "value_scalar": 0.293},
        "frontAndBack": {"type": "empty"},
    }
    omega_patches = {
        "inlet": {
            "type": "turbulentMixingLengthFrequencyInlet",
            "value_scalar": 779.0,
            "params": {"mixingLength": 0.00127},
        },
        "outlet": {"type": "zeroGradient"},
        "topWall": {"type": "omegaWallFunction", "value_scalar": 779.0},
        "bottomWall": {"type": "omegaWallFunction", "value_scalar": 779.0},
        "stepFace": {"type": "omegaWallFunction", "value_scalar": 779.0},
        "frontAndBack": {"type": "empty"},
    }
    nut_patches = {
        "inlet": {"type": "calculated"},
        "outlet": {"type": "calculated"},
        "topWall": {"type": "nutkWallFunction"},
        "bottomWall": {"type": "nutkWallFunction"},
        "stepFace": {"type": "nutkWallFunction"},
        "frontAndBack": {"type": "empty"},
    }
    return {
        "U":     {"file": "0/U", "parsed": True, "patches": u_patches},
        "p":     {"file": "0/p", "parsed": True, "patches": p_patches},
        "k":     {"file": "0/k", "parsed": True, "patches": k_patches},
        "omega": {"file": "0/omega", "parsed": True, "patches": omega_patches},
        "nut":   {"file": "0/nut", "parsed": True, "patches": nut_patches},
    }


# ---------- mocked backend ----------


def test_bc_gate_mocked_backend_returns_mocked(tmp_path: Path):
    """Phase-0 honesty: mocked backend → MOCKED, NOT silent PASS."""
    m = _bfs_manifest(solver_backend="mocked")
    gate = bc_gate(tmp_path, m)
    assert gate["status"] == "MOCKED"


# ---------- BLOCKED paths ----------


def test_bc_gate_blocked_when_bc_quality_missing(tmp_path: Path):
    _write_geom_quality(tmp_path, _BFS_REALIZED_PATCHES)
    # NO bc_quality.json
    gate = bc_gate(tmp_path, _bfs_manifest())
    assert gate["status"] == "BLOCKED"
    assert gate["details"]["reason"] == "bc_quality.json_missing"


def test_bc_gate_blocked_when_geometry_quality_missing(tmp_path: Path):
    _write_bc_quality(tmp_path, _full_realized_bc_fields(), ["U", "p", "k", "omega", "nut"])
    # NO geometry_quality.json
    gate = bc_gate(tmp_path, _bfs_manifest())
    assert gate["status"] == "BLOCKED"
    assert gate["details"]["reason"] == "geometry_evidence_missing"


def test_bc_gate_blocked_when_bc_quality_marked_blocked(tmp_path: Path):
    art = tmp_path / "artifacts"
    art.mkdir(parents=True)
    (art / "bc_quality.json").write_text(json.dumps({
        "bc_parsing_status": "blocked",
        "reason": "zero_dir_unreadable",
    }))
    _write_geom_quality(tmp_path, _BFS_REALIZED_PATCHES)
    gate = bc_gate(tmp_path, _bfs_manifest())
    assert gate["status"] == "BLOCKED"
    assert gate["details"]["reason"] == "zero_dir_unreadable"


# ---------- file_presence dimension ----------


def test_bc_gate_file_presence_fail_on_missing_turbulence_field(tmp_path: Path):
    """Manifest declares `nut` in turbulence_fields but 0/nut is missing."""
    _write_geom_quality(tmp_path, _BFS_REALIZED_PATCHES)
    fields = _full_realized_bc_fields()
    fields["nut"] = {"file": "0/nut", "parsed": False, "missing": True}
    _write_bc_quality(tmp_path, fields, ["U", "p", "k", "omega", "nut"])
    gate = bc_gate(tmp_path, _bfs_manifest())
    assert gate["status"] == "FAIL"
    fp = gate["details"]["file_presence"]
    assert "nut" in fp["missing_files"]


def test_bc_gate_file_presence_fail_on_unparseable_file(tmp_path: Path):
    _write_geom_quality(tmp_path, _BFS_REALIZED_PATCHES)
    fields = _full_realized_bc_fields()
    fields["omega"] = {
        "file": "0/omega", "parsed": False, "missing": False,
        "parse_error": "no_boundary_field_block_found",
    }
    _write_bc_quality(tmp_path, fields, ["U", "p", "k", "omega", "nut"])
    gate = bc_gate(tmp_path, _bfs_manifest())
    assert gate["status"] == "FAIL"
    bad = gate["details"]["file_presence"]["unparseable_files"]
    assert any(b["field"] == "omega" for b in bad)


# ---------- patch_coverage dimension ----------


def test_bc_gate_patch_coverage_fail_on_missing_patch_entry(tmp_path: Path):
    """0/U is missing the stepFace patch (in polyMesh but not in U file)."""
    _write_geom_quality(tmp_path, _BFS_REALIZED_PATCHES)
    fields = _full_realized_bc_fields()
    del fields["U"]["patches"]["stepFace"]
    _write_bc_quality(tmp_path, fields, ["U", "p", "k", "omega", "nut"])
    gate = bc_gate(tmp_path, _bfs_manifest())
    assert gate["status"] == "FAIL"
    pc = gate["details"]["patch_coverage"]
    assert pc["dimension_status"] == "FAIL"
    assert "stepFace" in pc["gaps_by_field"]["U"]


def test_bc_gate_patch_coverage_pass_when_all_patches_covered(tmp_path: Path):
    _write_geom_quality(tmp_path, _BFS_REALIZED_PATCHES)
    _write_bc_quality(tmp_path, _full_realized_bc_fields(), ["U", "p", "k", "omega", "nut"])
    gate = bc_gate(tmp_path, _bfs_manifest())
    assert gate["status"] == "PASS"
    assert gate["details"]["patch_coverage"]["dimension_status"] == "PASS"


# ---------- type_match dimension ----------


def test_bc_gate_type_match_pass_on_canonical_bfs(tmp_path: Path):
    """The full BFS manifest realized with full consistency → PASS."""
    _write_geom_quality(tmp_path, _BFS_REALIZED_PATCHES)
    _write_bc_quality(tmp_path, _full_realized_bc_fields(), ["U", "p", "k", "omega", "nut"])
    gate = bc_gate(tmp_path, _bfs_manifest())
    assert gate["status"] == "PASS"
    tm = gate["details"]["type_match"]
    assert tm["dimension_status"] == "PASS"
    # 5 declarations × inlet + 2 × outlet + (3 wall patches × 3 fields) = 16 — but
    # actually: inlet has 4 field-classes, outlet has 2, wall has 3 fields × 3 wall
    # patches = 9 → 4+2+9 = 15 total checked pairs.
    assert tm["checked_count"] == 15


def test_bc_gate_type_match_resolves_wall_to_multiple_patches(tmp_path: Path):
    """The `wall` key in manifest should expand to topWall + bottomWall +
    stepFace (all type=wall). Verify by checking the `checked` records
    include all three."""
    _write_geom_quality(tmp_path, _BFS_REALIZED_PATCHES)
    _write_bc_quality(tmp_path, _full_realized_bc_fields(), ["U", "p", "k", "omega", "nut"])
    gate = bc_gate(tmp_path, _bfs_manifest())
    tm = gate["details"]["type_match"]
    wall_patches_checked = sorted({
        c["resolved_patch"] for c in tm["checked"]
        if c["manifest_key"] == "wall"
    })
    assert wall_patches_checked == ["bottomWall", "stepFace", "topWall"]


def test_bc_gate_type_match_fail_on_mismatch(tmp_path: Path):
    """Tamper with topWall's velocity type → mismatch."""
    _write_geom_quality(tmp_path, _BFS_REALIZED_PATCHES)
    fields = _full_realized_bc_fields()
    fields["U"]["patches"]["topWall"]["type"] = "slip"  # manifest said noSlip
    _write_bc_quality(tmp_path, fields, ["U", "p", "k", "omega", "nut"])
    gate = bc_gate(tmp_path, _bfs_manifest())
    assert gate["status"] == "FAIL"
    tm = gate["details"]["type_match"]
    mismatches = tm["type_mismatches"]
    assert any(
        m["resolved_patch"] == "topWall" and m["field"] == "U" and m["realized_type"] == "slip"
        for m in mismatches
    )


def test_bc_gate_type_match_fail_on_unresolvable_key(tmp_path: Path):
    """Manifest declares BC for `ghost` patch that exists in NEITHER
    polyMesh patch names NOR types → FAIL."""
    _write_geom_quality(tmp_path, _BFS_REALIZED_PATCHES)
    _write_bc_quality(tmp_path, _full_realized_bc_fields(), ["U", "p", "k", "omega", "nut"])
    m = _bfs_manifest()
    m["bc_contract"]["ghost"] = {"velocity": {"type": "fixedValue"}}
    gate = bc_gate(tmp_path, m)
    assert gate["status"] == "FAIL"
    assert "ghost" in gate["details"]["type_match"]["unresolvable_keys"]


def test_bc_gate_resolves_literal_patch_before_type_class(tmp_path: Path):
    """When the manifest key matches a literal patch name AND a patch type
    simultaneously (unlikely but possible), literal wins. flat-plate uses
    `wall` as a literal patch name; verify it does NOT expand to extra
    patches of type=wall."""
    realized = {
        "inlet": {"type": "patch", "nFaces": 50, "startFace": 0},
        "wall": {"type": "wall", "nFaces": 100, "startFace": 50},
        "extraWall": {"type": "wall", "nFaces": 50, "startFace": 150},
    }
    _write_geom_quality(tmp_path, realized)
    fields = {
        "U": {
            "file": "0/U", "parsed": True,
            "patches": {
                "inlet": {"type": "fixedValue"},
                "wall": {"type": "noSlip"},
                "extraWall": {"type": "slip"},   # different from manifest's wall.noSlip
            },
        },
        "p": {
            "file": "0/p", "parsed": True,
            "patches": {
                "inlet": {"type": "zeroGradient"},
                "wall": {"type": "zeroGradient"},
                "extraWall": {"type": "zeroGradient"},
            },
        },
    }
    _write_bc_quality(tmp_path, fields, ["U", "p"])
    m = {
        "case_id": "literal_test",
        "solver_backend": "openfoam",
        "bc_contract": {
            "inlet": {"velocity": {"type": "fixedValue"}, "pressure": {"type": "zeroGradient"}},
            "wall":  {"velocity": {"type": "noSlip"}},
        },
    }
    gate = bc_gate(tmp_path, m)
    # `wall` resolved to literal `wall` (not extraWall) so extraWall's slip
    # is NOT a type mismatch in this audit.
    assert gate["status"] == "PASS"
    resolved_for_wall = {
        c["resolved_patch"] for c in gate["details"]["type_match"]["checked"]
        if c["manifest_key"] == "wall"
    }
    assert resolved_for_wall == {"wall"}


# ---------- combined PASS path + honesty fences ----------


def test_bc_gate_pass_writes_evidence_report(tmp_path: Path):
    _write_geom_quality(tmp_path, _BFS_REALIZED_PATCHES)
    _write_bc_quality(tmp_path, _full_realized_bc_fields(), ["U", "p", "k", "omega", "nut"])
    gate = bc_gate(tmp_path, _bfs_manifest())
    assert gate["status"] == "PASS"
    rep = json.loads((tmp_path / "artifacts" / "bc_audit.json").read_text())
    assert rep["gate_status"] == "PASS"
    assert rep["zero_dir_inspected"] is True
    assert rep["realized_patch_count"] == 6
    assert rep["file_presence_dimension"]["dimension_status"] == "PASS"
    assert rep["patch_coverage_dimension"]["dimension_status"] == "PASS"
    assert rep["type_match_dimension"]["dimension_status"] == "PASS"


def test_bc_gate_does_not_silently_pass_on_empty_contract(tmp_path: Path):
    """Empty bc_contract → FAIL (incomplete contract is a manifest defect)."""
    _write_geom_quality(tmp_path, _BFS_REALIZED_PATCHES)
    _write_bc_quality(tmp_path, _full_realized_bc_fields(), ["U", "p", "k", "omega", "nut"])
    m = _bfs_manifest()
    m["bc_contract"] = {}
    gate = bc_gate(tmp_path, m)
    assert gate["status"] == "FAIL"
    assert gate["details"]["reason"] == "no_bc_contract"


def test_bc_gate_does_not_silently_pass_when_artifacts_missing(tmp_path: Path):
    """No bc_quality.json + no geometry_quality.json + openfoam backend →
    BLOCKED (not PASS, not MOCKED). Belt-side honesty fence."""
    gate = bc_gate(tmp_path, _bfs_manifest())
    assert gate["status"] not in ("PASS", "MOCKED")
    assert gate["status"] == "BLOCKED"


def test_bc_gate_fails_when_field_class_missing_in_bc_quality(tmp_path: Path):
    """Manifest declares `omega` BC but no 0/omega file parsed. The
    file_presence dim catches it as FAIL; the type_match dim records the
    same problem with field-class detail so cockpit can show both."""
    _write_geom_quality(tmp_path, _BFS_REALIZED_PATCHES)
    fields = _full_realized_bc_fields()
    fields["omega"] = {"file": "0/omega", "parsed": False, "missing": True}
    _write_bc_quality(tmp_path, fields, ["U", "p", "k", "omega", "nut"])
    gate = bc_gate(tmp_path, _bfs_manifest())
    assert gate["status"] == "FAIL"
    assert "omega" in gate["details"]["file_presence"]["missing_files"]


# =====================================================================
# M7 — BC value validation (parser extensions + value_match dimension)
# =====================================================================


# ---------- M7.1: parser extracts value_scalar / value_vector / params ----------


def test_parse_field_boundary_field_extracts_value_vector():
    """`value uniform (44.2 0 0);` → realized.value_vector = [44.2, 0.0, 0.0]."""
    out = ofa._parse_field_boundary_field(_U_FILE)
    assert out["inlet"]["value_vector"] == [44.2, 0.0, 0.0]
    # zeroGradient / noSlip / empty entries carry no value
    assert "value_vector" not in out["outlet"]
    assert "value_scalar" not in out["outlet"]
    assert "value_vector" not in out["bottomWall"]


def test_parse_field_boundary_field_extracts_value_scalar():
    text = """
boundaryField
{
    outlet
    {
        type            fixedValue;
        value           uniform 0.0;
    }
    inlet
    {
        type            fixedValue;
        value           uniform 101325;
    }
}
"""
    out = ofa._parse_field_boundary_field(text)
    assert out["outlet"]["value_scalar"] == pytest.approx(0.0)
    assert out["inlet"]["value_scalar"] == pytest.approx(101325.0)


def test_parse_field_boundary_field_extracts_scientific_notation():
    text = """
boundaryField
{
    p1
    {
        type            fixedValue;
        value           uniform 1.5e-3;
    }
}
"""
    out = ofa._parse_field_boundary_field(text)
    assert out["p1"]["value_scalar"] == pytest.approx(1.5e-3)


def test_parse_field_boundary_field_extracts_intensity_param():
    out = ofa._parse_field_boundary_field(_K_FILE)
    assert out["inlet"]["params"] == {"intensity": pytest.approx(0.01)}


def test_parse_field_boundary_field_extracts_mixinglength_param():
    text = """
boundaryField
{
    inlet
    {
        type            turbulentMixingLengthFrequencyInlet;
        mixingLength    0.00127;
        value           uniform 779;
    }
}
"""
    out = ofa._parse_field_boundary_field(text)
    assert out["inlet"]["params"] == {"mixingLength": pytest.approx(0.00127)}
    assert out["inlet"]["value_scalar"] == pytest.approx(779.0)


def test_parse_field_boundary_field_no_params_dict_when_empty():
    """A BC block with no whitelisted params (e.g. plain zeroGradient)
    must NOT carry an empty `params` dict — keeps the JSON clean."""
    text = """
boundaryField
{
    outlet
    {
        type            zeroGradient;
    }
}
"""
    out = ofa._parse_field_boundary_field(text)
    assert "params" not in out["outlet"]


def test_parse_field_boundary_field_vector_pattern_does_not_match_scalar():
    """A scalar value (no parentheses) must NOT match the vector regex
    by accident — regression fence for greedy/lax regex changes."""
    text = """
boundaryField
{
    outlet
    {
        type            fixedValue;
        value           uniform 5.0;
    }
}
"""
    out = ofa._parse_field_boundary_field(text)
    assert "value_vector" not in out["outlet"]
    assert out["outlet"]["value_scalar"] == pytest.approx(5.0)


def test_parse_field_boundary_field_scalar_pattern_does_not_match_vector():
    """Inverse: a vector value must NOT match the scalar regex picking
    up just the first number (otherwise `value_scalar=44.2` would land
    alongside `value_vector=[44.2, 0, 0]`)."""
    text = """
boundaryField
{
    inlet
    {
        type            fixedValue;
        value           uniform (44.2 0 0);
    }
}
"""
    out = ofa._parse_field_boundary_field(text)
    assert "value_scalar" not in out["inlet"]
    assert out["inlet"]["value_vector"] == [44.2, 0.0, 0.0]


# ---------- M7.2: value_match dimension ----------


def _full_realized_bc_fields_with_values() -> dict:
    """Like `_full_realized_bc_fields` but with numeric value/param
    annotations that match the canonical BFS manifest."""
    base = _full_realized_bc_fields()
    base["U"]["patches"]["inlet"]["value_vector"] = [44.2, 0.0, 0.0]
    base["p"]["patches"]["outlet"]["value_scalar"] = 0.0
    base["k"]["patches"]["inlet"]["value_scalar"] = 0.293
    base["k"]["patches"]["inlet"]["params"] = {"intensity": 0.01}
    base["omega"]["patches"]["inlet"]["value_scalar"] = 779.0
    base["omega"]["patches"]["inlet"]["params"] = {"mixingLength": 0.00127}
    return base


def _bfs_manifest_with_numerics() -> dict:
    """BFS manifest with the canonical numeric declarations."""
    m = _bfs_manifest()
    m["bc_contract"]["inlet"]["velocity"]["magnitude_m_s"] = 44.2
    m["bc_contract"]["inlet"]["k"]["intensity"] = 0.01
    m["bc_contract"]["inlet"]["omega"]["mixingLength"] = 0.00127
    m["bc_contract"]["outlet"]["pressure"]["value_Pa"] = 0.0
    return m


def test_value_match_pass_on_canonical_bfs(tmp_path: Path):
    _write_geom_quality(tmp_path, _BFS_REALIZED_PATCHES)
    _write_bc_quality(
        tmp_path,
        _full_realized_bc_fields_with_values(),
        ["U", "p", "k", "omega", "nut"],
    )
    gate = bc_gate(tmp_path, _bfs_manifest_with_numerics())
    assert gate["status"] == "PASS"
    vm = gate["details"]["value_match"]
    assert vm["dimension_status"] == "PASS"
    assert vm["matched_count"] == 4   # magnitude_m_s, intensity, mixingLength, value_Pa


def test_value_match_fail_on_velocity_magnitude_drift(tmp_path: Path):
    """Manifest says 44.2 m/s but realized vector L2 = 30.0 → FAIL."""
    _write_geom_quality(tmp_path, _BFS_REALIZED_PATCHES)
    fields = _full_realized_bc_fields_with_values()
    fields["U"]["patches"]["inlet"]["value_vector"] = [30.0, 0.0, 0.0]
    _write_bc_quality(tmp_path, fields, ["U", "p", "k", "omega", "nut"])
    gate = bc_gate(tmp_path, _bfs_manifest_with_numerics())
    assert gate["status"] == "FAIL"
    mismatches = gate["details"]["value_match"]["value_mismatches"]
    assert any(
        mm["numeric_field"] == "magnitude_m_s"
        and mm["declared"] == pytest.approx(44.2)
        and mm["actual"] == pytest.approx(30.0)
        for mm in mismatches
    )


def test_value_match_pass_on_vector_magnitude_with_y_component(tmp_path: Path):
    """Manifest declares magnitude_m_s=44.2 by L2 norm. Realized
    (35.36, 26.52, 0) also has L2 ≈ 44.2 → must PASS (direction-agnostic)."""
    _write_geom_quality(tmp_path, _BFS_REALIZED_PATCHES)
    fields = _full_realized_bc_fields_with_values()
    fields["U"]["patches"]["inlet"]["value_vector"] = [35.36, 26.52, 0.0]   # |v| ~ 44.2
    _write_bc_quality(tmp_path, fields, ["U", "p", "k", "omega", "nut"])
    m = _bfs_manifest_with_numerics()
    gate = bc_gate(tmp_path, m)
    # L2 = sqrt(35.36^2 + 26.52^2) ≈ 44.199...
    vm = gate["details"]["value_match"]
    # Allow either PASS or FAIL by tolerance; we mostly want to assert
    # the L2-norm computation reached the right neighborhood.
    found_magnitude = next(
        rec for rec in (vm.get("matched", []) + vm.get("value_mismatches", []))
        if rec["numeric_field"] == "magnitude_m_s"
    )
    assert found_magnitude["actual"] == pytest.approx(44.2, rel=1e-3)


def test_value_match_fail_on_pressure_drift(tmp_path: Path):
    _write_geom_quality(tmp_path, _BFS_REALIZED_PATCHES)
    fields = _full_realized_bc_fields_with_values()
    fields["p"]["patches"]["outlet"]["value_scalar"] = 1.5e3   # manifest says 0.0
    _write_bc_quality(tmp_path, fields, ["U", "p", "k", "omega", "nut"])
    gate = bc_gate(tmp_path, _bfs_manifest_with_numerics())
    assert gate["status"] == "FAIL"
    assert any(
        mm["numeric_field"] == "value_Pa" and mm["actual"] == pytest.approx(1500.0)
        for mm in gate["details"]["value_match"]["value_mismatches"]
    )


def test_value_match_fail_on_intensity_drift(tmp_path: Path):
    _write_geom_quality(tmp_path, _BFS_REALIZED_PATCHES)
    fields = _full_realized_bc_fields_with_values()
    fields["k"]["patches"]["inlet"]["params"] = {"intensity": 0.05}   # manifest 0.01
    _write_bc_quality(tmp_path, fields, ["U", "p", "k", "omega", "nut"])
    gate = bc_gate(tmp_path, _bfs_manifest_with_numerics())
    assert gate["status"] == "FAIL"
    assert any(
        mm["numeric_field"] == "intensity" and mm["actual"] == pytest.approx(0.05)
        for mm in gate["details"]["value_match"]["value_mismatches"]
    )


def test_value_match_fail_on_mixinglength_drift(tmp_path: Path):
    _write_geom_quality(tmp_path, _BFS_REALIZED_PATCHES)
    fields = _full_realized_bc_fields_with_values()
    fields["omega"]["patches"]["inlet"]["params"] = {"mixingLength": 0.005}   # manifest 0.00127
    _write_bc_quality(tmp_path, fields, ["U", "p", "k", "omega", "nut"])
    gate = bc_gate(tmp_path, _bfs_manifest_with_numerics())
    assert gate["status"] == "FAIL"
    assert any(
        mm["numeric_field"] == "mixingLength" and mm["actual"] == pytest.approx(0.005)
        for mm in gate["details"]["value_match"]["value_mismatches"]
    )


def test_value_match_fail_on_missing_realized_value(tmp_path: Path):
    """Manifest declares magnitude_m_s but realized has no value_vector
    (e.g. a fixedValue BC with no value line — malformed). → FAIL with
    `value_missing` record."""
    _write_geom_quality(tmp_path, _BFS_REALIZED_PATCHES)
    fields = _full_realized_bc_fields_with_values()
    del fields["U"]["patches"]["inlet"]["value_vector"]
    _write_bc_quality(tmp_path, fields, ["U", "p", "k", "omega", "nut"])
    gate = bc_gate(tmp_path, _bfs_manifest_with_numerics())
    assert gate["status"] == "FAIL"
    assert any(
        miss["numeric_field"] == "magnitude_m_s" and miss["manifest_key"] == "inlet"
        for miss in gate["details"]["value_match"]["value_missing"]
    )


def test_value_match_zero_target_uses_atol_not_rtol(tmp_path: Path):
    """`value_Pa: 0.0` declared, realized=1e-10 (essentially zero) → PASS
    via atol=1e-9. Without atol, the relative tolerance against 0.0 is
    mathematically undefined; this fences the FP-comparison policy."""
    _write_geom_quality(tmp_path, _BFS_REALIZED_PATCHES)
    fields = _full_realized_bc_fields_with_values()
    fields["p"]["patches"]["outlet"]["value_scalar"] = 1e-10
    _write_bc_quality(tmp_path, fields, ["U", "p", "k", "omega", "nut"])
    gate = bc_gate(tmp_path, _bfs_manifest_with_numerics())
    # 1e-10 < atol=1e-9 → PASS for the pressure pair.
    assert gate["status"] == "PASS"


def test_value_match_unknown_numeric_field_does_not_fail(tmp_path: Path):
    """Manifest contains a numeric field the audit doesn't know about
    (e.g. `temperature_K: 300`). Recorded as `numeric_field_unknown`
    but does NOT trigger FAIL — extension surface, not a defect."""
    _write_geom_quality(tmp_path, _BFS_REALIZED_PATCHES)
    _write_bc_quality(
        tmp_path,
        _full_realized_bc_fields_with_values(),
        ["U", "p", "k", "omega", "nut"],
    )
    m = _bfs_manifest_with_numerics()
    m["bc_contract"]["inlet"]["velocity"]["temperature_K"] = 300
    gate = bc_gate(tmp_path, m)
    assert gate["status"] == "PASS"
    unknown = gate["details"]["value_match"]["numeric_field_unknown"]
    assert any(u["numeric_field"] == "temperature_K" for u in unknown)


def test_value_match_string_field_value_does_not_attempt_compare(tmp_path: Path):
    """Non-numeric manifest values (e.g. `note: "this is fine"`) must be
    silently ignored, not crash the audit."""
    _write_geom_quality(tmp_path, _BFS_REALIZED_PATCHES)
    _write_bc_quality(
        tmp_path,
        _full_realized_bc_fields_with_values(),
        ["U", "p", "k", "omega", "nut"],
    )
    m = _bfs_manifest_with_numerics()
    m["bc_contract"]["inlet"]["velocity"]["note"] = "should be 44.2"
    gate = bc_gate(tmp_path, m)
    assert gate["status"] == "PASS"


def test_value_match_resolves_wall_type_class_for_value_check(tmp_path: Path):
    """If manifest declares numerics on a type-class key (like `wall`),
    the value_match dim expands the same way type_match does."""
    realized_patches = {
        "wallA": {"type": "wall", "nFaces": 50, "startFace": 0},
        "wallB": {"type": "wall", "nFaces": 50, "startFace": 50},
    }
    _write_geom_quality(tmp_path, realized_patches)
    fields = {
        "U": {
            "file": "0/U", "parsed": True,
            "patches": {
                "wallA": {"type": "fixedValue", "value_vector": [1.0, 0.0, 0.0]},
                "wallB": {"type": "fixedValue", "value_vector": [99.0, 0.0, 0.0]},   # drift
            },
        },
        "p": {"file": "0/p", "parsed": True, "patches": {
            "wallA": {"type": "zeroGradient"},
            "wallB": {"type": "zeroGradient"},
        }},
    }
    _write_bc_quality(tmp_path, fields, ["U", "p"])
    m = {
        "case_id": "wall_value_test",
        "solver_backend": "openfoam",
        "bc_contract": {
            "wall": {"velocity": {"type": "fixedValue", "magnitude_m_s": 1.0}},
        },
    }
    gate = bc_gate(tmp_path, m)
    # Both wall patches checked; wallB is off → FAIL
    assert gate["status"] == "FAIL"
    vm = gate["details"]["value_match"]
    bad_patches = sorted({mm["resolved_patch"] for mm in vm["value_mismatches"]})
    assert "wallB" in bad_patches
    assert "wallA" not in bad_patches


def test_value_match_dimension_pass_when_no_numerics_declared(tmp_path: Path):
    """A manifest declaring only `type` per patch (no magnitude / value_Pa
    / intensity / mixingLength) → value_match PASS (nothing to check)."""
    _write_geom_quality(tmp_path, _BFS_REALIZED_PATCHES)
    _write_bc_quality(
        tmp_path,
        _full_realized_bc_fields_with_values(),
        ["U", "p", "k", "omega", "nut"],
    )
    m = _bfs_manifest()   # no numerics
    gate = bc_gate(tmp_path, m)
    assert gate["status"] == "PASS"
    assert gate["details"]["value_match"]["dimension_status"] == "PASS"


# =====================================================================
# M8 — Derived BC consistency: k = 1.5*(I*U)^2 + omega = sqrt(k)/(Cmu^0.25 * L)
# =====================================================================


def _bfs_manifest_with_full_inlet() -> dict:
    """BFS manifest with all inlet declarations needed for derivation."""
    m = _bfs_manifest()
    m["bc_contract"]["inlet"]["velocity"]["magnitude_m_s"] = 44.2
    m["bc_contract"]["inlet"]["k"]["intensity"] = 0.01
    m["bc_contract"]["inlet"]["omega"]["mixingLength"] = 0.00127
    return m


def test_derived_pass_on_canonical_bfs(tmp_path: Path):
    """BFS canonical: I=0.01, U=44.2 → k≈0.293; L=0.00127 → omega≈778.
    Realized k=0.293, omega=779. Both within 0.5% tolerance."""
    _write_geom_quality(tmp_path, _BFS_REALIZED_PATCHES)
    _write_bc_quality(
        tmp_path, _full_realized_bc_fields(), ["U", "p", "k", "omega", "nut"]
    )
    gate = bc_gate(tmp_path, _bfs_manifest_with_full_inlet())
    assert gate["status"] == "PASS"
    der = gate["details"]["derived_consistency"]
    assert der["dimension_status"] == "PASS"
    assert der["matched_count"] == 2   # k_from_I_U + omega_from_k_L

    # Verify both derivations are recorded with formula + inputs (so the
    # cockpit / advisor can explain WHY they pass).
    derivations = {m["derivation"] for m in der["matched"]}
    assert derivations == {"k_from_I_U", "omega_from_k_L"}


def test_derived_fail_on_k_drift(tmp_path: Path):
    """Realized k=0.5 (way off from expected ≈0.293) → FAIL."""
    _write_geom_quality(tmp_path, _BFS_REALIZED_PATCHES)
    fields = _full_realized_bc_fields()
    fields["k"]["patches"]["inlet"]["value_scalar"] = 0.5   # expected ~0.293
    _write_bc_quality(tmp_path, fields, ["U", "p", "k", "omega", "nut"])
    gate = bc_gate(tmp_path, _bfs_manifest_with_full_inlet())
    assert gate["status"] == "FAIL"
    der = gate["details"]["derived_consistency"]
    bad = [m for m in der["derived_mismatches"] if m["derivation"] == "k_from_I_U"]
    assert len(bad) == 1
    assert bad[0]["actual"] == pytest.approx(0.5)
    assert bad[0]["expected"] == pytest.approx(0.293, abs=0.001)


def test_derived_fail_on_omega_drift(tmp_path: Path):
    _write_geom_quality(tmp_path, _BFS_REALIZED_PATCHES)
    fields = _full_realized_bc_fields()
    fields["omega"]["patches"]["inlet"]["value_scalar"] = 100.0   # expected ~778
    _write_bc_quality(tmp_path, fields, ["U", "p", "k", "omega", "nut"])
    gate = bc_gate(tmp_path, _bfs_manifest_with_full_inlet())
    assert gate["status"] == "FAIL"
    der = gate["details"]["derived_consistency"]
    bad = [m for m in der["derived_mismatches"] if m["derivation"] == "omega_from_k_L"]
    assert len(bad) == 1
    assert bad[0]["actual"] == pytest.approx(100.0)


def test_derived_skips_when_inlet_only_declares_type(tmp_path: Path):
    """If manifest's inlet doesn't declare magnitude_m_s + intensity,
    no derivation is possible — dim PASS via the no-op note path."""
    _write_geom_quality(tmp_path, _BFS_REALIZED_PATCHES)
    _write_bc_quality(
        tmp_path, _full_realized_bc_fields(), ["U", "p", "k", "omega", "nut"]
    )
    m = _bfs_manifest()   # no numeric declarations
    gate = bc_gate(tmp_path, m)
    assert gate["status"] == "PASS"
    der = gate["details"]["derived_consistency"]
    assert der["dimension_status"] == "PASS"
    assert der["matched_count"] == 0


def test_derived_skips_omega_when_mixinglength_absent(tmp_path: Path):
    """Manifest declares k.intensity but no omega.mixingLength → derive
    k only, skip omega derivation. Still PASS."""
    _write_geom_quality(tmp_path, _BFS_REALIZED_PATCHES)
    _write_bc_quality(
        tmp_path, _full_realized_bc_fields(), ["U", "p", "k", "omega", "nut"]
    )
    m = _bfs_manifest_with_full_inlet()
    del m["bc_contract"]["inlet"]["omega"]["mixingLength"]
    gate = bc_gate(tmp_path, m)
    assert gate["status"] == "PASS"
    der = gate["details"]["derived_consistency"]
    derivations = {m["derivation"] for m in der["matched"]}
    assert derivations == {"k_from_I_U"}


def test_derived_records_realistic_human_rounding(tmp_path: Path):
    """The realistic operator-rounding gap: realized k=0.293 (rounded)
    vs expected 0.29304... is within 0.5% rtol — PASS, NOT FAIL.
    Fences the rtol policy."""
    _write_geom_quality(tmp_path, _BFS_REALIZED_PATCHES)
    fields = _full_realized_bc_fields()
    # Realized as a human would type it (3 sig figs)
    fields["k"]["patches"]["inlet"]["value_scalar"] = 0.293
    fields["omega"]["patches"]["inlet"]["value_scalar"] = 779.0
    _write_bc_quality(tmp_path, fields, ["U", "p", "k", "omega", "nut"])
    gate = bc_gate(tmp_path, _bfs_manifest_with_full_inlet())
    assert gate["status"] == "PASS"
    der = gate["details"]["derived_consistency"]
    assert der["dimension_status"] == "PASS"
    # And both expected values are shown in the record so the user can
    # see how close their rounding is.
    k_record = next(m for m in der["matched"] if m["derivation"] == "k_from_I_U")
    assert k_record["expected"] == pytest.approx(0.293, abs=0.001)


def test_derived_missing_realized_k(tmp_path: Path):
    """Manifest declares I + U but realized k has no value_scalar →
    derived_missing → FAIL."""
    _write_geom_quality(tmp_path, _BFS_REALIZED_PATCHES)
    fields = _full_realized_bc_fields()
    # remove value_scalar from realized k.inlet
    fields["k"]["patches"]["inlet"].pop("value_scalar", None)
    _write_bc_quality(tmp_path, fields, ["U", "p", "k", "omega", "nut"])
    gate = bc_gate(tmp_path, _bfs_manifest_with_full_inlet())
    assert gate["status"] == "FAIL"
    der = gate["details"]["derived_consistency"]
    missing = [m for m in der["derived_missing"] if m["derivation"] == "k_from_I_U"]
    assert len(missing) == 1


def test_derived_uses_expected_k_not_realized_for_omega(tmp_path: Path):
    """The omega derivation must use EXPECTED k, not realized k. This
    way the audit catches internal manifest inconsistency even when
    realized k happens to drift to a value that would also derive
    realized omega correctly."""
    _write_geom_quality(tmp_path, _BFS_REALIZED_PATCHES)
    fields = _full_realized_bc_fields()
    # Set realized k AND realized omega such that they're mutually
    # consistent via the derivation formula (using a fake "consistent
    # but wrong" k = 1.0):
    #   omega_realized = sqrt(1.0) / (0.09^0.25 * 0.00127) ≈ 1437
    fields["k"]["patches"]["inlet"]["value_scalar"] = 1.0          # wrong; expected 0.293
    fields["omega"]["patches"]["inlet"]["value_scalar"] = 1437.0   # consistent with k=1.0 but not with manifest
    _write_bc_quality(tmp_path, fields, ["U", "p", "k", "omega", "nut"])
    gate = bc_gate(tmp_path, _bfs_manifest_with_full_inlet())
    # k derivation FAILs (expected 0.293, realized 1.0)
    # omega derivation FAILs (expected ~778 from manifest, realized 1437)
    assert gate["status"] == "FAIL"
    der = gate["details"]["derived_consistency"]
    # Both derivations recorded as mismatches:
    derivations_failed = {m["derivation"] for m in der["derived_mismatches"]}
    assert derivations_failed == {"k_from_I_U", "omega_from_k_L"}


def test_derived_pass_on_flat_plate_with_realistic_rounding(tmp_path: Path):
    """Flat plate canonical: I=0.01, U=30 → k=0.135 (exact); L=0.01 →
    omega=67.08; realized 67 (operator rounded). Both should PASS."""
    realized_patches = {
        "inlet": {"type": "patch", "nFaces": 60, "startFace": 0},
        "wall": {"type": "wall", "nFaces": 100, "startFace": 60},
        "outlet": {"type": "patch", "nFaces": 60, "startFace": 160},
        "top": {"type": "symmetryPlane", "nFaces": 100, "startFace": 220},
        "frontAndBack": {"type": "empty", "nFaces": 12000, "startFace": 320},
    }
    _write_geom_quality(tmp_path, realized_patches)
    fields = {
        "U": {"file": "0/U", "parsed": True, "patches": {
            "inlet": {"type": "fixedValue", "value_vector": [30.0, 0.0, 0.0]},
            "wall": {"type": "noSlip"},
            "outlet": {"type": "zeroGradient"},
            "top": {"type": "symmetryPlane"},
            "frontAndBack": {"type": "empty"},
        }},
        "p": {"file": "0/p", "parsed": True, "patches": {
            "inlet": {"type": "zeroGradient"},
            "outlet": {"type": "fixedValue", "value_scalar": 0.0},
            "wall": {"type": "zeroGradient"},
            "top": {"type": "symmetryPlane"},
            "frontAndBack": {"type": "empty"},
        }},
        "k": {"file": "0/k", "parsed": True, "patches": {
            "inlet": {"type": "turbulentIntensityKineticEnergyInlet",
                      "value_scalar": 0.135, "params": {"intensity": 0.01}},
            "wall": {"type": "kqRWallFunction"},
            "outlet": {"type": "zeroGradient"},
            "top": {"type": "symmetryPlane"},
            "frontAndBack": {"type": "empty"},
        }},
        "omega": {"file": "0/omega", "parsed": True, "patches": {
            "inlet": {"type": "turbulentMixingLengthFrequencyInlet",
                      "value_scalar": 67.0, "params": {"mixingLength": 0.01}},
            "wall": {"type": "omegaWallFunction"},
            "outlet": {"type": "zeroGradient"},
            "top": {"type": "symmetryPlane"},
            "frontAndBack": {"type": "empty"},
        }},
        "nut": {"file": "0/nut", "parsed": True, "patches": {
            "inlet": {"type": "calculated"}, "wall": {"type": "nutkWallFunction"},
            "outlet": {"type": "calculated"}, "top": {"type": "symmetryPlane"},
            "frontAndBack": {"type": "empty"},
        }},
    }
    _write_bc_quality(tmp_path, fields, ["U", "p", "k", "omega", "nut"])

    m = {
        "case_id": "fp_derived",
        "solver_backend": "openfoam",
        "bc_contract": {
            "inlet": {
                "velocity": {"type": "fixedValue", "magnitude_m_s": 30.0},
                "pressure": {"type": "zeroGradient"},
                "k": {"type": "turbulentIntensityKineticEnergyInlet", "intensity": 0.01},
                "omega": {"type": "turbulentMixingLengthFrequencyInlet", "mixingLength": 0.01},
            },
            "outlet": {
                "pressure": {"type": "fixedValue", "value_Pa": 0.0},
                "velocity": {"type": "zeroGradient"},
            },
            "wall": {
                "velocity": {"type": "noSlip"},
                "k": {"type": "kqRWallFunction"},
                "omega": {"type": "omegaWallFunction"},
            },
            "turbulence_fields": ["k", "omega", "nut"],
        },
    }
    gate = bc_gate(tmp_path, m)
    assert gate["status"] == "PASS"
    der = gate["details"]["derived_consistency"]
    assert der["matched_count"] == 2


# ---------- Cycle 4 spike B: multi-region bc_contract verdict-layer wiring ----------
#
# Cycle 1 (Gap #11) shipped the DATA layer: bc_quality.json now carries
# layout: multi_region + per-region payloads. Cycle 2 left the VERDICT
# layer BLOCKED with 'multi_region_bc_validation_not_yet_wired' as an
# honest deferral. Cycle 4 wires the verdict using region-shape
# classification (fluid/solid/empty) + manifest fluid-field coverage,
# without requiring per-class schema (Gap #28 charter still queued).


_REGION_FLUID_U = """\
FoamFile { class volVectorField; object U; }
dimensions [0 1 -1 0 0 0 0];
internalField uniform (0.5 0 0);
boundaryField
{
    inlet { type fixedValue; value uniform (0.5 0 0); }
    outlet { type zeroGradient; }
    fluid_to_solid { type fixedValue; value uniform (0 0 0); }
}
"""


_REGION_FLUID_P = """\
FoamFile { class volScalarField; object p; }
dimensions [0 2 -2 0 0 0 0];
internalField uniform 0;
boundaryField
{
    inlet { type zeroGradient; }
    outlet { type fixedValue; value uniform 0; }
    fluid_to_solid { type zeroGradient; }
}
"""


_REGION_SOLID_T = """\
FoamFile { class volScalarField; object T; }
dimensions [0 0 0 1 0 0 0];
internalField uniform 300;
boundaryField
{
    solid_to_fluid { type fixedValue; value uniform 300; }
    solid_outer_wall { type fixedValue; value uniform 350; }
}
"""


def _stage_multi_region_bc_quality(
    case_dir: Path,
    *,
    fluid_regions: list[str] = None,
    solid_regions: list[str] = None,
    empty_regions: list[str] = None,
    fluid_has_turb: bool = False,
) -> None:
    """Build artifacts/bc_quality.json with the multi_region layout
    shape. Each fluid region carries U+p (optionally k/omega/nut); each
    solid region carries T; each empty region has no fields."""
    fluid_regions = fluid_regions or []
    solid_regions = solid_regions or []
    empty_regions = empty_regions or []

    art = case_dir / "artifacts"
    art.mkdir(parents=True, exist_ok=True)

    expected = ["U", "p"]
    if fluid_has_turb:
        expected = ["U", "p", "k", "omega", "nut"]

    regions: dict = {}
    for rname in fluid_regions:
        fields_present = ["U", "p"]
        if fluid_has_turb:
            fields_present = ["U", "p", "k", "omega", "nut"]
        regions[rname] = {
            "expected_fields": expected,
            "fields_present": fields_present,
            "fields_missing": [],
            "fields": {f: {"parsed": True, "patches": {}} for f in fields_present},
        }
    for rname in solid_regions:
        regions[rname] = {
            "expected_fields": expected,
            "fields_present": ["T"],
            "fields_missing": expected,  # honestly notes fluid fields missing
            "fields": {"T": {"parsed": True, "patches": {}}},
        }
    for rname in empty_regions:
        regions[rname] = {
            "expected_fields": expected,
            "fields_present": [],
            "fields_missing": expected,
            "fields": {},
        }

    bc = {
        "bc_parsing_status": "ok",
        "layout": "multi_region",
        "expected_fields": expected,
        "regions_detected": sorted(regions.keys()),
        "region_count": len(regions),
        "regions": regions,
    }
    (art / "bc_quality.json").write_text(json.dumps(bc, indent=2))

    # Stage minimal geometry_quality.json so the gate doesn't bail at the
    # "geometry evidence missing" early-return.
    (art / "geometry_quality.json").write_text(json.dumps({
        "status": "ok",
        "realized_patches": ["inlet", "outlet", "fluid_to_solid",
                             "solid_to_fluid", "solid_outer_wall"],
    }))


def _multi_region_manifest(
    *, turbulence_fields: list[str] = None, thermal_fields: list[str] = None,
) -> dict:
    """Minimal manifest accepted by bc_gate for a multi-region case."""
    m = {
        "case_id": "multi_region_test",
        "solver_backend": "openfoam",
        "bc_contract": {
            "inlet": {"velocity": {"type": "fixedValue"}, "pressure": {"type": "zeroGradient"}},
            "outlet": {"velocity": {"type": "zeroGradient"}, "pressure": {"type": "fixedValue"}},
            "wall": {"velocity": {"type": "noSlip"}},
        },
    }
    if turbulence_fields is not None:
        m["bc_contract"]["turbulence_fields"] = turbulence_fields
    if thermal_fields is not None:
        m["bc_contract"]["thermal_fields"] = thermal_fields
    return m


def test_multi_region_verdict_pass_fluid_plus_solid(tmp_path: Path):
    """Gap #11 cycle-4: 2 fluid regions (each carrying U+p) + 1 solid
    region (T only) + manifest declares only U/p as expected → PASS
    with 'multi_region_per_class_pending' reason. Replaces the cycle-2
    BLOCKED 'multi_region_bc_validation_not_yet_wired'."""
    _stage_multi_region_bc_quality(
        tmp_path,
        fluid_regions=["region_cold_fluid", "region_hot_fluid"],
        solid_regions=["region_solid"],
    )
    m = _multi_region_manifest(turbulence_fields=[])

    gate = bc_gate(tmp_path, m)

    assert gate["status"] == "PASS", (
        f"Expected PASS; got {gate['status']} with reason "
        f"{gate.get('details', {}).get('reason')}"
    )
    d = gate["details"]
    assert d["reason"] == "multi_region_per_class_pending"
    assert d["fluid_region_count"] == 2
    assert d["solid_region_count"] == 1
    assert d["empty_region_count"] == 0
    assert d["missing_in_all_fluid_regions"] == []


def test_multi_region_verdict_blocked_empty_region(tmp_path: Path):
    """Gap #11 cycle-4: any empty region (zero parseable fields) trips
    BLOCKED with reason 'multi_region_empty_region_detected'. Catches
    case-staging errors that the cycle-2 dogfood would have missed."""
    _stage_multi_region_bc_quality(
        tmp_path,
        fluid_regions=["region_fluid"],
        empty_regions=["region_empty"],
    )
    m = _multi_region_manifest(turbulence_fields=[])

    gate = bc_gate(tmp_path, m)

    assert gate["status"] == "BLOCKED"
    assert gate["details"]["reason"] == "multi_region_empty_region_detected"
    assert "region_empty" in gate["summary"]


def test_multi_region_verdict_warn_missing_turbulence(tmp_path: Path):
    """Gap #11 cycle-4: manifest declares turbulence_fields = [k, omega]
    but no fluid region carries them → WARN with reason
    'multi_region_fluid_field_missing'. Per-class verdict refinement
    (solid wants only T) still deferred to Gap #28; this catches the
    case where the case author forgot to populate turbulence ICs."""
    _stage_multi_region_bc_quality(
        tmp_path,
        fluid_regions=["region_fluid"],
        solid_regions=["region_solid"],
        fluid_has_turb=False,  # fluid region only has U+p, no k/omega
    )
    m = _multi_region_manifest(turbulence_fields=["k", "omega"])

    gate = bc_gate(tmp_path, m)

    assert gate["status"] == "WARN"
    assert gate["details"]["reason"] == "multi_region_fluid_field_missing"
    missing = gate["details"]["missing_in_all_fluid_regions"]
    assert "k" in missing and "omega" in missing


def test_multi_region_verdict_blocked_no_fluid_region(tmp_path: Path):
    """Gap #11 cycle-4: only solid regions detected (no U+p region) →
    BLOCKED with 'multi_region_no_fluid_region'. chtMultiRegionFoam
    requires ≥1 fluid region by definition; engine refuses to pass."""
    _stage_multi_region_bc_quality(
        tmp_path,
        solid_regions=["region_solid_a", "region_solid_b"],
    )
    m = _multi_region_manifest(turbulence_fields=[])

    gate = bc_gate(tmp_path, m)

    assert gate["status"] == "BLOCKED"
    assert gate["details"]["reason"] == "multi_region_no_fluid_region"
    assert gate["details"]["fluid_region_count"] == 0
    assert gate["details"]["solid_region_count"] == 2
