"""M5 — Real geometry_contract tests.

Two layers (same shape as test_mesh_contract.py from M4):
  - parser unit tests: feed canonical / partial / malformed polyMesh/boundary
    text to `_parse_polymesh_boundary` and check it extracts the right
    structured data without ever raising.
  - audit gate tests: write geometry_quality.json fixtures and assert
    audit/geometry.run() PASS / FAIL / BLOCKED / MOCKED correctly.

Backend wiring (`run()` calling the parser after blockMesh) is covered
indirectly by the live verification step in PROGRESS.md; the heavy-lifting
end-to-end is exercised by Docker, which we don't replay in unit tests.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from cfdtrust.backends import openfoam as ofa
from cfdtrust.audit.geometry import run as geometry_gate


# ---------- canonical polyMesh/boundary content ----------


_BFS_BOUNDARY = """\
/*--------------------------------*- C++ -*----------------------------------*\\
  =========                 |
  \\\\      /  F ield         | OpenFOAM 11
\\*---------------------------------------------------------------------------*/
FoamFile
{
    format      ascii;
    class       polyBoundaryMesh;
    location    "constant/polyMesh";
    object      boundary;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

6
(
    inlet
    {
        type            patch;
        nFaces          50;
        startFace       22960;
    }
    outlet
    {
        type            patch;
        nFaces          80;
        startFace       23010;
    }
    topWall
    {
        type            wall;
        inGroups        List<word> 1(wall);
        nFaces          160;
        startFace       23090;
    }
    bottomWall
    {
        type            wall;
        inGroups        List<word> 1(wall);
        nFaces          160;
        startFace       23250;
    }
    stepFace
    {
        type            wall;
        inGroups        List<word> 1(wall);
        nFaces          30;
        startFace       23410;
    }
    frontAndBack
    {
        type            empty;
        inGroups        List<word> 1(empty);
        nFaces          23200;
        startFace       23440;
    }
)
"""


_FLAT_PLATE_BOUNDARY = """\
FoamFile
{
    format      ascii;
}

5
(
    inlet
    {
        type            patch;
        nFaces          50;
        startFace       11500;
    }
    outlet
    {
        type            patch;
        nFaces          50;
        startFace       11550;
    }
    wall
    {
        type            wall;
        nFaces          120;
        startFace       11600;
    }
    top
    {
        type            symmetryPlane;
        nFaces          120;
        startFace       11720;
    }
    frontAndBack
    {
        type            empty;
        nFaces          12000;
        startFace       11840;
    }
)
"""


# ---------- _parse_polymesh_boundary: canonical ----------


def test_parse_polymesh_boundary_bfs_canonical():
    out = ofa._parse_polymesh_boundary(_BFS_BOUNDARY)
    assert set(out.keys()) == {
        "inlet", "outlet", "topWall", "bottomWall", "stepFace", "frontAndBack",
    }
    assert out["inlet"]["type"] == "patch"
    assert out["topWall"]["type"] == "wall"
    assert out["frontAndBack"]["type"] == "empty"
    assert out["bottomWall"]["nFaces"] == 160
    assert out["bottomWall"]["startFace"] == 23250


def test_parse_polymesh_boundary_flat_plate_canonical():
    out = ofa._parse_polymesh_boundary(_FLAT_PLATE_BOUNDARY)
    assert set(out.keys()) == {"inlet", "outlet", "wall", "top", "frontAndBack"}
    assert out["top"]["type"] == "symmetryPlane"
    assert out["wall"]["nFaces"] == 120


# ---------- _parse_polymesh_boundary: robustness ----------


def test_parse_polymesh_boundary_empty_returns_empty_dict():
    assert ofa._parse_polymesh_boundary("") == {}


def test_parse_polymesh_boundary_no_opener_returns_empty():
    """A file with only the FoamFile header (no `N\\n(` list) must NOT raise."""
    text = "FoamFile\n{\n    format ascii;\n}\n"
    assert ofa._parse_polymesh_boundary(text) == {}


def test_parse_polymesh_boundary_skips_untyped_block():
    """A block without `type X;` is malformed; the parser MUST skip it
    rather than crash or invent a default type."""
    text = """
1
(
    weirdPatch
    {
        nFaces 5;
        startFace 0;
    }
)
"""
    assert ofa._parse_polymesh_boundary(text) == {}


def test_parse_polymesh_boundary_strips_comments():
    """`//` and `/* */` comments must not confuse the parser. We hide a
    spurious `type fake;` inside a comment that should be ignored."""
    text = """
// type fake; <-- not a real type line
/* multiline
   type alsoFake;
*/
1
(
    realPatch
    {
        type            wall;
        nFaces          10;
        startFace       0;
    }
)
"""
    out = ofa._parse_polymesh_boundary(text)
    assert out == {"realPatch": {"type": "wall", "nFaces": 10, "startFace": 0}}


def test_parse_polymesh_boundary_handles_inGroups():
    """`inGroups List<word> 1(wall);` must not break field extraction."""
    text = """
1
(
    p1
    {
        type            wall;
        inGroups        List<word> 1(wall);
        nFaces          77;
        startFace       100;
    }
)
"""
    out = ofa._parse_polymesh_boundary(text)
    assert out == {"p1": {"type": "wall", "nFaces": 77, "startFace": 100}}


def test_parse_polymesh_boundary_unbalanced_braces_safe():
    """Truncated input mid-block — must not loop forever or raise."""
    text = """
2
(
    p1
    {
        type wall;
        nFaces 10;
"""
    # No crash; partial recovery acceptable as long as nothing claimed.
    out = ofa._parse_polymesh_boundary(text)
    assert out == {}  # block never closed → don't claim it


def test_parse_polymesh_boundary_partial_fields_safe():
    """Missing nFaces or startFace defaults to 0 (NOT crash)."""
    text = """
1
(
    p1
    {
        type            patch;
    }
)
"""
    out = ofa._parse_polymesh_boundary(text)
    assert out == {"p1": {"type": "patch", "nFaces": 0, "startFace": 0}}


# ---------- _persist_geometry_quality ----------


def test_persist_geometry_quality_ok_path(tmp_path: Path):
    parsed = ofa._parse_polymesh_boundary(_BFS_BOUNDARY)
    out = ofa._persist_geometry_quality(
        tmp_path, patches=parsed,
        boundary_relative="constant/polyMesh/boundary",
    )
    assert out.exists()
    data = json.loads(out.read_text())
    assert data["polymesh_boundary_parsed"] is True
    assert data["status"] == "ok"
    assert data["patch_count"] == 6
    assert "topWall" in data["patches"]
    assert data["boundary_file"] == "constant/polyMesh/boundary"


def test_persist_geometry_quality_blocked_missing_boundary(tmp_path: Path):
    out = ofa._persist_geometry_quality(
        tmp_path, patches=None, boundary_relative=None,
        blocked_reason="boundary_file_missing",
        blocked_detail="/path/to/missing",
    )
    data = json.loads(out.read_text())
    assert data["polymesh_boundary_parsed"] is False
    assert data["status"] == "blocked"
    assert data["reason"] == "boundary_file_missing"
    # Honesty: NO patches dict leaks from a blocked persistence.
    assert "patches" not in data


def test_persist_geometry_quality_empty_patches_path(tmp_path: Path):
    """Parser returned {} (e.g. malformed boundary) → status='empty', not 'ok'."""
    out = ofa._persist_geometry_quality(
        tmp_path, patches={}, boundary_relative="constant/polyMesh/boundary",
    )
    data = json.loads(out.read_text())
    assert data["polymesh_boundary_parsed"] is True
    assert data["status"] == "empty"
    assert data["patch_count"] == 0


# ========================================================================
# M5.2 — audit/geometry.run() gate evaluation
# ========================================================================


def _write_geometry_quality(case_dir: Path, payload: dict) -> None:
    art = case_dir / "artifacts"
    art.mkdir(parents=True, exist_ok=True)
    (art / "geometry_quality.json").write_text(json.dumps(payload, indent=2))


def _bfs_manifest(**overrides) -> dict:
    m = {
        "case_id": "geom_test",
        "solver_backend": "openfoam",
        "geometry_contract": {
            "required_patches": [
                "inlet", "outlet", "topWall", "bottomWall", "stepFace", "frontAndBack",
            ],
            "dimensionality": "2.5D",
            "unit_system": "SI",
        },
    }
    m.update(overrides)
    return m


def _good_bfs_realized() -> dict:
    """The 6-patch realized polyMesh as if blockMesh + parser ran."""
    return ofa._parse_polymesh_boundary(_BFS_BOUNDARY)


# ---------- mocked backend ----------


def test_geometry_gate_mocked_backend_returns_mocked(tmp_path: Path):
    """Phase-0 honesty: solver_backend=mocked → MOCKED (NOT silent PASS)."""
    m = _bfs_manifest(solver_backend="mocked")
    gate = geometry_gate(tmp_path, m)
    assert gate["status"] == "MOCKED"
    rep = json.loads((tmp_path / "artifacts" / "geometry_report.json").read_text())
    assert rep["gate_status"] == "MOCKED"
    assert rep["polymesh_inspected"] is False


# ---------- BLOCKED paths ----------


def test_geometry_gate_blocked_when_quality_json_missing(tmp_path: Path):
    """openfoam backend but no geometry_quality.json → BLOCKED."""
    gate = geometry_gate(tmp_path, _bfs_manifest())
    assert gate["status"] == "BLOCKED"
    assert gate["details"]["reason"] == "geometry_quality_json_missing"


def test_geometry_gate_blocked_when_persistence_was_blocked(tmp_path: Path):
    """M5.1 persisted a blocked state (boundary file missing); gate propagates."""
    _write_geometry_quality(tmp_path, {
        "polymesh_boundary_parsed": False,
        "status": "blocked",
        "reason": "boundary_file_missing",
    })
    gate = geometry_gate(tmp_path, _bfs_manifest())
    assert gate["status"] == "BLOCKED"
    assert gate["details"]["reason"] == "boundary_file_missing"


# ---------- presence dimension ----------


def test_geometry_gate_presence_pass_when_all_required_present(tmp_path: Path):
    _write_geometry_quality(tmp_path, {
        "status": "ok",
        "patches": _good_bfs_realized(),
        "patch_count": 6,
        "polymesh_boundary_parsed": True,
    })
    gate = geometry_gate(tmp_path, _bfs_manifest())
    assert gate["status"] == "PASS"
    assert gate["details"]["presence_dimension"]["dimension_status"] == "PASS"


def test_geometry_gate_presence_fail_when_required_patch_missing(tmp_path: Path):
    """Drop stepFace from realized → manifest expects it → FAIL."""
    realized = _good_bfs_realized()
    del realized["stepFace"]
    _write_geometry_quality(tmp_path, {
        "status": "ok",
        "patches": realized,
        "patch_count": len(realized),
        "polymesh_boundary_parsed": True,
    })
    gate = geometry_gate(tmp_path, _bfs_manifest())
    assert gate["status"] == "FAIL"
    pd = gate["details"]["presence_dimension"]
    assert "stepFace" in pd["missing"]


def test_geometry_gate_presence_records_extras_without_failing(tmp_path: Path):
    """Extras (realized but not required) are informational, NOT a FAIL.
    Cases may legitimately have utility patches that the manifest didn't
    promise — the contract is one-way: manifest declares minimum bar."""
    realized = _good_bfs_realized()
    realized["debugProbe"] = {"type": "patch", "nFaces": 1, "startFace": 0}
    _write_geometry_quality(tmp_path, {
        "status": "ok",
        "patches": realized,
        "patch_count": len(realized),
        "polymesh_boundary_parsed": True,
    })
    gate = geometry_gate(tmp_path, _bfs_manifest())
    assert gate["status"] == "PASS"
    assert "debugProbe" in gate["details"]["presence_dimension"]["extras"]


# ---------- dimensionality dimension ----------


def test_geometry_gate_dimensionality_25d_pass_with_empty_patch(tmp_path: Path):
    _write_geometry_quality(tmp_path, {
        "status": "ok",
        "patches": _good_bfs_realized(),
        "patch_count": 6,
        "polymesh_boundary_parsed": True,
    })
    gate = geometry_gate(tmp_path, _bfs_manifest())
    assert gate["details"]["dimensionality_dimension"]["dimension_status"] == "PASS"


def test_geometry_gate_dimensionality_25d_fail_without_empty_patch(tmp_path: Path):
    """Manifest says 2.5D but realized has zero empty patches → FAIL."""
    realized = _good_bfs_realized()
    # Change frontAndBack from empty to patch (simulates manifest/case drift)
    realized["frontAndBack"] = {"type": "patch", "nFaces": 23200, "startFace": 23440}
    _write_geometry_quality(tmp_path, {
        "status": "ok",
        "patches": realized,
        "patch_count": 6,
        "polymesh_boundary_parsed": True,
    })
    gate = geometry_gate(tmp_path, _bfs_manifest())
    assert gate["status"] == "FAIL"
    dd = gate["details"]["dimensionality_dimension"]
    assert dd["dimension_status"] == "FAIL"
    assert "no empty patch" in dd["reason"]


def test_geometry_gate_dimensionality_3d_fail_with_empty_patch(tmp_path: Path):
    """Manifest says 3D but realized has empty patches → FAIL (front+back
    is reserved for 2D/2.5D OpenFOAM convention)."""
    m = _bfs_manifest()
    m["geometry_contract"]["dimensionality"] = "3D"
    _write_geometry_quality(tmp_path, {
        "status": "ok",
        "patches": _good_bfs_realized(),  # has frontAndBack=empty
        "patch_count": 6,
        "polymesh_boundary_parsed": True,
    })
    gate = geometry_gate(tmp_path, m)
    assert gate["status"] == "FAIL"
    assert gate["details"]["dimensionality_dimension"]["dimension_status"] == "FAIL"


def test_geometry_gate_dimensionality_incomplete_on_unknown_string(tmp_path: Path):
    """Unrecognized dimensionality (e.g. typo '2D5') → INCOMPLETE → FAIL."""
    m = _bfs_manifest()
    m["geometry_contract"]["dimensionality"] = "2D5"   # typo
    _write_geometry_quality(tmp_path, {
        "status": "ok",
        "patches": _good_bfs_realized(),
        "patch_count": 6,
        "polymesh_boundary_parsed": True,
    })
    gate = geometry_gate(tmp_path, m)
    assert gate["status"] == "FAIL"  # incomplete rolls up to FAIL
    dd = gate["details"]["dimensionality_dimension"]
    assert dd["dimension_status"] == "INCOMPLETE"


def test_geometry_gate_dimensionality_absent_does_not_block(tmp_path: Path):
    """Manifest with no dimensionality field → dimensionality dim is PASS
    (nothing to check). Overall gate decided by presence dim alone."""
    m = _bfs_manifest()
    del m["geometry_contract"]["dimensionality"]
    _write_geometry_quality(tmp_path, {
        "status": "ok",
        "patches": _good_bfs_realized(),
        "patch_count": 6,
        "polymesh_boundary_parsed": True,
    })
    gate = geometry_gate(tmp_path, m)
    assert gate["status"] == "PASS"
    assert gate["details"]["dimensionality_dimension"]["dimension_status"] == "PASS"


# ---------- honesty fences ----------


def test_geometry_gate_does_not_silently_pass_when_evidence_missing(tmp_path: Path):
    """openfoam backend + no geometry_quality.json + missing patches in the
    manifest → BLOCKED, never PASS. Belt-side fence on the M5 gate."""
    gate = geometry_gate(tmp_path, _bfs_manifest())
    assert gate["status"] not in ("PASS", "MOCKED")


def test_geometry_gate_fails_on_empty_required_patches(tmp_path: Path):
    """Manifest declares an empty required_patches list → FAIL (contract is
    structurally incomplete; do NOT pass on a no-op contract)."""
    m = _bfs_manifest()
    m["geometry_contract"]["required_patches"] = []
    gate = geometry_gate(tmp_path, m)
    assert gate["status"] == "FAIL"


def test_geometry_gate_pass_with_full_evidence(tmp_path: Path):
    """End-to-end PASS path with mesh_report.json on disk; assert the
    report carries the full evidence chain so the cockpit can render it."""
    _write_geometry_quality(tmp_path, {
        "status": "ok",
        "patches": _good_bfs_realized(),
        "patch_count": 6,
        "polymesh_boundary_parsed": True,
        "boundary_file": "constant/polyMesh/boundary",
    })
    gate = geometry_gate(tmp_path, _bfs_manifest())
    assert gate["status"] == "PASS"

    rep = json.loads((tmp_path / "artifacts" / "geometry_report.json").read_text())
    assert rep["gate_status"] == "PASS"
    assert rep["realized_patch_count"] == 6
    assert rep["presence_dimension"]["dimension_status"] == "PASS"
    assert rep["dimensionality_dimension"]["dimension_status"] == "PASS"
    # Manifest's full required_patches list preserved in the evidence.
    assert sorted(rep["declared_required_patches"]) == sorted(_bfs_manifest()["geometry_contract"]["required_patches"])
