"""Sub-commit 2d: tests for the QoI extraction + reference comparison stack.

Layer 1: `src/cfdtrust/qoi/flat_plate_cf.py` (pure CSV / interpolation / gate)
Layer 2: `src/cfdtrust/qoi/wall_shear.py` (polyMesh + wallShearStress parser)
Audit:   `src/cfdtrust/audit/qoi.py` (orchestration)
"""
from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from cfdtrust.qoi import flat_plate_cf, wall_shear


# ---------- Layer 1: flat_plate_cf ----------


def test_load_reference_csv_parses_real_nasa_data(repo_root: Path):
    """The CFL3D zone of the NASA TMR Cf file must load with the expected
    shape: 448 on-plate rows, monotonic x, Cf in a physically-reasonable
    band for an SST flat plate (1e-3 .. 2e-2)."""
    p = repo_root / "cases" / "flat_plate_rans_sst" / "reference" / "cf_reference.csv"
    rows = flat_plate_cf.load_reference_csv(p)
    assert len(rows) == 448, (
        f"NASA TMR CFL3D on-plate Cf should have 448 rows; got {len(rows)}. "
        "If the source data is intentionally updated, also bump this number "
        "AND the provenance SHA-256."
    )
    # Sorted, on-plate, physically reasonable.
    xs = [r[0] for r in rows]
    cfs = [r[1] for r in rows]
    assert xs == sorted(xs), "reference CSV must be sorted by x"
    assert xs[0] >= 0.0, "on-plate reference must not include x<0"
    assert max(cfs) < 0.02, "Cf max should be below 0.02 for SST flat plate"
    assert min(cfs) > 1e-3, "Cf min should be above 0.001 in the resolved-turbulence region"


def test_load_reference_csv_raises_on_missing_file(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        flat_plate_cf.load_reference_csv(tmp_path / "nope.csv")


def test_load_reference_csv_raises_on_malformed_row(tmp_path: Path):
    p = tmp_path / "bad.csv"
    p.write_text("x_m,Cf\n1.0,2.0\n3.0,not_a_number\n")
    with pytest.raises(ValueError) as exc:
        flat_plate_cf.load_reference_csv(p)
    assert "cannot parse" in str(exc.value)


def test_linear_interpolate_basics():
    curve = [(0.0, 0.0), (1.0, 10.0), (2.0, 20.0)]
    assert flat_plate_cf.linear_interpolate(curve, 0.5) == 5.0
    assert flat_plate_cf.linear_interpolate(curve, 1.5) == 15.0
    # Boundaries:
    assert flat_plate_cf.linear_interpolate(curve, 0.0) == 0.0
    assert flat_plate_cf.linear_interpolate(curve, 2.0) == 20.0
    # Outside range → None (refuse to extrapolate).
    assert flat_plate_cf.linear_interpolate(curve, -0.5) is None
    assert flat_plate_cf.linear_interpolate(curve, 2.5) is None
    # Empty curve → None.
    assert flat_plate_cf.linear_interpolate([], 1.0) is None


def test_compare_passes_when_measured_matches_reference_within_tolerance():
    # Measured and reference identical → PASS with 0% error.
    curve = [(0.1, 5e-3), (0.5, 4e-3), (1.0, 3e-3), (1.5, 2.8e-3)]
    gate = flat_plate_cf.compare_against_reference(
        curve, curve, tolerance=0.05, x_min_compare=0.01,
    )
    assert gate["status"] == "PASS"
    assert gate["details"]["max_rel_error"] == 0.0
    assert gate["details"]["n_compared"] == 4


def test_compare_fails_when_measured_exceeds_tolerance():
    ref = [(0.1, 5e-3), (0.5, 4e-3), (1.0, 3e-3)]
    # +20% offset on every point.
    measured = [(x, cf * 1.20) for (x, cf) in ref]
    gate = flat_plate_cf.compare_against_reference(
        measured, ref, tolerance=0.05, x_min_compare=0.0,
    )
    assert gate["status"] == "FAIL"
    assert abs(gate["details"]["max_rel_error"] - 0.20) < 1e-9


def test_compare_blocks_on_empty_measured_after_skip_window():
    """Honesty rule: if x_min_compare filter strips all measured points,
    BLOCK rather than declare PASS-by-checking-nothing."""
    measured = [(0.001, 5e-3), (0.005, 4e-3)]  # all below x_min=0.01
    ref = [(0.1, 5e-3), (1.0, 3e-3)]
    gate = flat_plate_cf.compare_against_reference(
        measured, ref, tolerance=0.05, x_min_compare=0.01,
    )
    assert gate["status"] == "BLOCKED"
    assert gate["details"]["reason"] == "no_measured_points_in_compare_window"


def test_compare_blocks_on_invalid_tolerance():
    gate = flat_plate_cf.compare_against_reference(
        [(0.1, 5e-3)], [(0.1, 5e-3)], tolerance=0.0, x_min_compare=0.0,
    )
    assert gate["status"] == "BLOCKED"
    assert gate["details"]["reason"] == "invalid_tolerance"


def test_compare_skips_measured_x_outside_reference_range():
    """Measured points beyond the reference curve's x-range must be
    DROPPED from the comparison (not extrapolated, not assumed pass)."""
    # Reference is piecewise linear: at x=0.5 it interpolates to
    # 5e-3 + 0.5*(3e-3 - 5e-3) = 4e-3, so measured 4e-3 is exact.
    measured = [(0.5, 4e-3), (3.0, 2.0e-3)]  # x=3 is beyond ref range
    ref = [(0.0, 5e-3), (1.0, 3e-3), (2.0, 2.5e-3)]
    gate = flat_plate_cf.compare_against_reference(
        measured, ref, tolerance=0.10, x_min_compare=0.0,
    )
    assert gate["status"] == "PASS"
    assert gate["details"]["n_compared"] == 1  # x=3 was dropped


def test_compare_blocks_when_no_overlapping_x():
    measured = [(5.0, 3e-3), (6.0, 2.5e-3)]
    ref = [(0.0, 5e-3), (1.0, 3e-3)]
    gate = flat_plate_cf.compare_against_reference(
        measured, ref, tolerance=0.10, x_min_compare=0.0,
    )
    assert gate["status"] == "BLOCKED"
    assert gate["details"]["reason"] == "no_overlapping_x_points"


def test_nasa_convention_passes_despite_near_le_deviation():
    """DEC-V61-209 ADDENDUM 3: a measured curve that matches the reference
    in the developed region (so integrated drag + downstream Cf are within
    tolerance) PASSES the NASA-convention gate even though a few near-LE points
    over-predict — those are demoted to informational known_deviations, not a
    fail, and stay visible in the rows."""
    # Reference: smooth Cf decaying with x.
    ref = [(0.0129, 5.3e-3), (0.02, 5.0e-3), (0.05, 4.3e-3),
           (0.2, 3.4e-3), (0.5, 3.0e-3), (0.97008, 2.69e-3), (1.98, 2.44e-3)]
    # Measured: identical EXCEPT a +22% spike at the first near-LE point.
    measured = [(0.0129, 5.3e-3 * 1.22)] + ref[1:]
    gate = flat_plate_cf.evaluate_nasa_convention(
        measured, ref, tolerance=0.10, x_min_compare=0.01,
        verification_station_m=0.97008,
    )
    assert gate["status"] == "PASS", gate["summary"]
    det = gate["details"]
    assert det["gate_mode"] == "nasa_integrated"
    assert det["integrated_drag"]["within_tolerance"] is True
    assert det["verification_station"]["within_tolerance"] is True
    # The near-LE over-prediction is REPORTED, not hidden.
    assert det["n_known_deviations"] == 1
    assert det["known_deviations"][0]["x_m"] == pytest.approx(0.0129)
    # Per-point rows are still present (CSV transparency contract unchanged).
    assert len(det["rows"]) == len(ref)


def test_nasa_convention_fails_when_developed_region_off():
    """If the discrepancy is NOT just near-LE — i.e. the downstream station /
    integrated drag are off — the NASA-convention gate FAILs. It only forgives
    LOCALIZED near-LE deviation, not a global offset."""
    ref = [(0.0129, 5.3e-3), (0.05, 4.3e-3), (0.2, 3.4e-3),
           (0.5, 3.0e-3), (0.97008, 2.69e-3), (1.98, 2.44e-3)]
    # +20% everywhere -> integrated drag and station both ~20% off.
    measured = [(x, cf * 1.20) for (x, cf) in ref]
    gate = flat_plate_cf.evaluate_nasa_convention(
        measured, ref, tolerance=0.10, x_min_compare=0.01,
        verification_station_m=0.97008,
    )
    assert gate["status"] == "FAIL", gate["summary"]
    assert gate["details"]["integrated_drag"]["within_tolerance"] is False
    assert gate["details"]["verification_station"]["within_tolerance"] is False


def test_nasa_convention_blocks_when_station_outside_range():
    """If the verification station is outside the compared x-range, the gate
    BLOCKs (refuses to fabricate a downstream value) rather than passing."""
    ref = [(0.05, 4.3e-3), (0.2, 3.4e-3), (0.5, 3.0e-3)]
    measured = list(ref)
    gate = flat_plate_cf.evaluate_nasa_convention(
        measured, ref, tolerance=0.10, x_min_compare=0.01,
        verification_station_m=0.97008,  # beyond max x=0.5
    )
    assert gate["status"] == "BLOCKED"
    assert gate["details"]["reason"] == "verification_station_unavailable"


def test_write_reference_comparison_csv_shape(tmp_path: Path):
    ref = [(0.5, 3e-3)]
    measured = [(0.5, 3.05e-3)]
    gate = flat_plate_cf.compare_against_reference(
        measured, ref, tolerance=0.10, x_min_compare=0.0,
    )
    out = tmp_path / "artifacts" / "ref.csv"
    flat_plate_cf.write_reference_comparison_csv(gate, "skin_friction_coefficient", out)
    text = out.read_text()
    lines = text.strip().splitlines()
    assert len(lines) == 2  # header + 1 row
    header = lines[0].split(",")
    assert header == ["name", "x_m", "Cf_run", "Cf_ref", "abs_error", "rel_error", "within_tolerance"]
    row = lines[1].split(",")
    assert row[0] == "skin_friction_coefficient"
    assert row[6] == "true"


# ---------- Layer 2: wall_shear ----------


# Minimal polyMesh fixture: 4 points → 1 quad face → wall patch of 1 face.
# Plus a wallShearStress file with the matching 1 vector.

_FIXTURE_POINTS = dedent("""
/*-- FoamFile header --*/
FoamFile { format ascii; class vectorField; object points; }

4
(
(0 0 0)
(1 0 0)
(1 0 0.05)
(0 0 0.05)
)
""").strip()

_FIXTURE_FACES = dedent("""
FoamFile { format ascii; class faceList; object faces; }

1
(
4(0 1 2 3)
)
""").strip()

_FIXTURE_BOUNDARY = dedent("""
FoamFile { format ascii; class polyBoundaryMesh; object boundary; }

1
(
    wall
    {
        type            wall;
        inGroups        List<word> 1(wall);
        nFaces          1;
        startFace       0;
    }
)
""").strip()

_FIXTURE_WSS = dedent("""
FoamFile { format ascii; class volVectorField; object wallShearStress; }

dimensions      [0 2 -2 0 0 0 0];
internalField   uniform (0 0 0);

boundaryField
{
    wall
    {
        type            calculated;
        value           nonuniform List<vector>
1
(
(-0.5 0 0)
)
;
    }
}
""").strip()


def test_parse_polymesh_boundary_extracts_patch_metadata():
    bm = wall_shear.parse_polymesh_boundary(_FIXTURE_BOUNDARY)
    assert "wall" in bm
    assert bm["wall"]["startFace"] == 0
    assert bm["wall"]["nFaces"] == 1


def test_parse_polymesh_points_returns_xyz_tuples():
    pts = wall_shear.parse_polymesh_points(_FIXTURE_POINTS)
    assert len(pts) == 4
    assert pts[0] == (0.0, 0.0, 0.0)
    assert pts[1] == (1.0, 0.0, 0.0)


def test_parse_polymesh_faces_returns_vertex_indices():
    faces = wall_shear.parse_polymesh_faces(_FIXTURE_FACES)
    assert len(faces) == 1
    assert faces[0] == [0, 1, 2, 3]


def test_parse_polymesh_points_count_mismatch_raises():
    bad = _FIXTURE_POINTS.replace("4", "5", 1)  # declare 5 but provide 4
    with pytest.raises(ValueError) as exc:
        wall_shear.parse_polymesh_points(bad)
    assert "5" in str(exc.value)


def test_parse_boundary_field_vectors_extracts_wall_vector():
    vecs = wall_shear.parse_boundary_field_vectors(_FIXTURE_WSS, "wall")
    assert vecs == [(-0.5, 0.0, 0.0)]


def test_parse_boundary_field_vectors_raises_on_uniform_value():
    """If the FO didn't actually fire, the value is `uniform (0 0 0)` —
    must BLOCK, not return zeros that would pass the comparison."""
    uni = _FIXTURE_WSS.replace(
        "value           nonuniform List<vector>\n1\n(\n(-0.5 0 0)\n)\n;",
        "value           uniform (0 0 0);",
    )
    with pytest.raises(ValueError) as exc:
        wall_shear.parse_boundary_field_vectors(uni, "wall")
    assert "uniform" in str(exc.value)


def test_parse_boundary_field_vectors_raises_on_missing_patch():
    with pytest.raises(ValueError) as exc:
        wall_shear.parse_boundary_field_vectors(_FIXTURE_WSS, "doesNotExist")
    assert "doesNotExist" in str(exc.value)


def test_face_centers_computed_correctly():
    pts = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 0.0, 0.05), (0.0, 0.0, 0.05)]
    faces = [[0, 1, 2, 3]]
    centers = wall_shear.face_centers(pts, faces, start=0, count=1)
    assert centers == [(0.5, 0.0, 0.025)]


def test_extract_wall_cf_end_to_end_synthetic(tmp_path: Path):
    """End-to-end on a synthetic case dir with our fixtures."""
    case = tmp_path / "case"
    (case / "constant" / "polyMesh").mkdir(parents=True)
    (case / "constant" / "polyMesh" / "points").write_text(_FIXTURE_POINTS)
    (case / "constant" / "polyMesh" / "faces").write_text(_FIXTURE_FACES)
    (case / "constant" / "polyMesh" / "boundary").write_text(_FIXTURE_BOUNDARY)
    (case / "159").mkdir()
    (case / "159" / "wallShearStress").write_text(_FIXTURE_WSS)

    rows = wall_shear.extract_wall_cf(case, "159", patch="wall", u_inf_m_s=10.0)
    # 1 wall face, center at x=0.5, |tau|=0.5, U=10 → Cf = 0.5 / (0.5*100) = 0.01
    assert len(rows) == 1
    assert rows[0][0] == 0.5
    assert abs(rows[0][1] - 0.01) < 1e-12


def test_extract_wall_cf_raises_when_files_missing(tmp_path: Path):
    case = tmp_path / "empty_case"
    case.mkdir()
    with pytest.raises(FileNotFoundError) as exc:
        wall_shear.extract_wall_cf(case, "100", patch="wall", u_inf_m_s=30.0)
    assert "polyMesh" in str(exc.value) or "wallShearStress" in str(exc.value)


def test_extract_wall_cf_rejects_zero_u_inf(tmp_path: Path):
    case = tmp_path / "case"
    case.mkdir()
    with pytest.raises(ValueError):
        wall_shear.extract_wall_cf(case, "100", patch="wall", u_inf_m_s=0.0)


def test_extract_wall_cf_raises_on_face_count_mismatch(tmp_path: Path):
    """Defense-in-depth: boundary says 1 face but wallShearStress block has
    2 vectors → refuse to proceed (could mean stale file or post-mortem
    edit)."""
    case = tmp_path / "case"
    (case / "constant" / "polyMesh").mkdir(parents=True)
    (case / "constant" / "polyMesh" / "points").write_text(_FIXTURE_POINTS)
    (case / "constant" / "polyMesh" / "faces").write_text(_FIXTURE_FACES)
    (case / "constant" / "polyMesh" / "boundary").write_text(_FIXTURE_BOUNDARY)
    bad_wss = _FIXTURE_WSS.replace(
        "1\n(\n(-0.5 0 0)\n)",
        "2\n(\n(-0.5 0 0)\n(-0.3 0 0)\n)",
    )
    (case / "159").mkdir()
    (case / "159" / "wallShearStress").write_text(bad_wss)
    with pytest.raises(ValueError) as exc:
        wall_shear.extract_wall_cf(case, "159", patch="wall", u_inf_m_s=10.0)
    assert "boundary declared 1" in str(exc.value) or "wallShearStress has 2" in str(exc.value)


# ---------- Audit-layer orchestration ----------


def test_audit_qoi_real_path_runs_against_live_case_dir(monkeypatch, tmp_path: Path, repo_root: Path):
    """Build a tmp case dir with:
      - the source manifest flipped to solver_backend=openfoam
      - the polyMesh and a wallShearStress fixture matching the manifest's
        wall patch
    and assert the audit-layer reference_gate is the real one (PASS or FAIL
    or BLOCKED — anything but MOCKED).
    """
    import shutil
    import yaml as _yaml
    from cfdtrust.audit import qoi as qoi_audit

    case_src = repo_root / "cases" / "flat_plate_rans_sst"
    case = tmp_path / "live_like_case"
    shutil.copytree(case_src, case)
    # Flip to openfoam backend.
    m_path = case / "case_manifest.yaml"
    m_text = m_path.read_text().replace("solver_backend: mocked", "solver_backend: openfoam")
    m_path.write_text(m_text)

    # Plant a minimal polyMesh + wallShearStress so the extractor finds data.
    pm = case / "constant" / "polyMesh"
    # Remove the .gitkeep so writes don't conflict.
    (pm / ".gitkeep").unlink(missing_ok=True)
    pm.mkdir(parents=True, exist_ok=True)
    (pm / "points").write_text(_FIXTURE_POINTS)
    (pm / "faces").write_text(_FIXTURE_FACES)
    (pm / "boundary").write_text(_FIXTURE_BOUNDARY)
    (case / "159").mkdir()
    (case / "159" / "wallShearStress").write_text(_FIXTURE_WSS)

    manifest = _yaml.safe_load(m_path.read_text())
    result = qoi_audit.run(case, manifest)

    ref_gate = result["reference_gate"]
    assert ref_gate["details"].get("real_comparison_performed") is True, (
        f"audit should have taken the REAL comparison path; got {ref_gate!r}"
    )
    # qoi.csv should now have per-x rows.
    qoi_csv = (case / "artifacts" / "qoi.csv").read_text()
    assert "openfoam_wallShearStress" in qoi_csv
    # reference_comparison.csv should have the new schema.
    ref_csv = (case / "artifacts" / "reference_comparison.csv").read_text()
    assert ref_csv.startswith("name,x_m,Cf_run,Cf_ref,abs_error,rel_error,within_tolerance")


def test_audit_qoi_mocked_path_still_runs_when_solver_is_mocked(repo_root: Path, tmp_path: Path):
    """Back-compat: a `solver_backend: mocked` case continues to land on
    the Phase 0 placeholder rows. Round-15 honesty rule says mocked must
    remain visibly mocked."""
    import shutil
    import yaml as _yaml
    from cfdtrust.audit import qoi as qoi_audit

    case_src = repo_root / "cases" / "flat_plate_rans_sst"
    case = tmp_path / "mocked_case"
    shutil.copytree(case_src, case)
    manifest = _yaml.safe_load((case / "case_manifest.yaml").read_text())

    result = qoi_audit.run(case, manifest)
    ref_gate = result["reference_gate"]
    assert ref_gate["details"]["real_comparison_performed"] is False
    assert ref_gate["status"] == "MOCKED"


# ---------- Real-OpenFOAM-11 fixture tests (sub-commit 2d live-run capture) ----------


def test_extract_wall_cf_against_real_openfoam_11_fixture(tmp_path: Path, repo_root: Path):
    """End-to-end against the CAPTURED live-run polyMesh + wallShearStress
    from `flat_plate_rans_sst` at iteration 159 (manifest U=30 m/s).

    Synthetic fixtures can't catch every OpenFOAM-format quirk; this test
    burns the project's actual file format into the parser contract. If
    a future OpenFOAM version changes the layout, this test breaks
    immediately."""
    import shutil
    case = tmp_path / "live_replay"
    (case / "constant" / "polyMesh").mkdir(parents=True)
    fixture_dir = repo_root / "cfdtrust_tests" / "fixtures" / "openfoam_logs" / "live_polymesh"
    for name in ("boundary", "faces", "points"):
        shutil.copy(fixture_dir / name, case / "constant" / "polyMesh" / name)
    (case / "159").mkdir()
    shutil.copy(fixture_dir / "wallShearStress_159", case / "159" / "wallShearStress")

    rows = wall_shear.extract_wall_cf(case, "159", patch="wall", u_inf_m_s=30.0)
    # Wall has 100 faces, so we expect 100 Cf samples.
    assert len(rows) == 100, f"expected 100 wall samples, got {len(rows)}"
    # Sorted by x.
    xs = [r[0] for r in rows]
    assert xs == sorted(xs)
    # Wall spans 0..2 m (the plate length from blockMeshDict).
    assert xs[0] >= 0.0
    assert xs[-1] <= 2.0
    # Cf values are physically reasonable (1e-4 .. 1e-2 for a flat plate
    # turbulent BL).
    cfs = [r[1] for r in rows]
    assert max(cfs) < 0.02
    assert min(cfs) > 1e-4


def test_real_openfoam_cf_compared_against_nasa_reference_lands_on_fail(
    tmp_path: Path, repo_root: Path,
):
    """End-to-end: live OF11 Cf vs NASA TMR CFL3D Cf at the project's
    manifest tolerance (10%) → FAIL. Documents the known y+ ~52 vs
    target 0.5-5 mismatch (R14-F-03) carrying through as a real,
    quantified gate failure rather than a hand-wave.

    If a future mesh refinement closes the y+ gap, this test will need
    to be UPDATED (likely to expect PASS) — NOT just deleted."""
    import shutil
    case = tmp_path / "live_replay"
    (case / "constant" / "polyMesh").mkdir(parents=True)
    fixture_dir = repo_root / "cfdtrust_tests" / "fixtures" / "openfoam_logs" / "live_polymesh"
    for name in ("boundary", "faces", "points"):
        shutil.copy(fixture_dir / name, case / "constant" / "polyMesh" / name)
    (case / "159").mkdir()
    shutil.copy(fixture_dir / "wallShearStress_159", case / "159" / "wallShearStress")

    measured = wall_shear.extract_wall_cf(case, "159", patch="wall", u_inf_m_s=30.0)
    reference = flat_plate_cf.load_reference_csv(
        repo_root / "cases" / "flat_plate_rans_sst" / "reference" / "cf_reference.csv"
    )
    gate = flat_plate_cf.compare_against_reference(
        measured, reference, tolerance=0.10, x_min_compare=0.01,
    )
    assert gate["status"] == "FAIL"
    # Max relative error should be in the ~50%+ range (LE region is most off).
    assert gate["details"]["max_rel_error"] > 0.30, (
        f"expected >30% max relative error against NASA TMR; got "
        f"{gate['details']['max_rel_error']:.4f}. If a mesh refinement "
        f"actually CLOSED the y+ gap, update this assertion."
    )


# ---------- Round-16 γ fixes: R16-F-01..F-08 ----------


def test_r16_f01_sha_mismatch_blocks_reference_load(tmp_path: Path, repo_root: Path):
    """R16-F-01 (MED): the audit layer must verify the on-disk reference
    CSV's SHA-256 against the manifest's `reference_csv_sha256` and BLOCK
    on mismatch. Pre-fix, a tampered reference (e.g. a curve designed to
    make our run silently PASS) would not be detected — the manifest's
    `source_sha256` covered only the ORIGINAL upstream file, not the
    derived in-repo CSV that the gate actually reads."""
    import shutil
    import yaml as _yaml
    from cfdtrust.audit import qoi as qoi_audit

    case = tmp_path / "tampered_case"
    shutil.copytree(repo_root / "cases" / "flat_plate_rans_sst", case)
    (case / "case_manifest.yaml").write_text(
        (case / "case_manifest.yaml").read_text().replace(
            "solver_backend: mocked", "solver_backend: openfoam"
        )
    )

    # Plant a synthetic "live run" so the comparison path is reached.
    pm = case / "constant" / "polyMesh"
    pm.mkdir(parents=True, exist_ok=True)
    (pm / "boundary").write_text(_FIXTURE_BOUNDARY)
    (pm / "faces").write_text(_FIXTURE_FACES)
    (pm / "points").write_text(_FIXTURE_POINTS)
    (case / "159").mkdir()
    (case / "159" / "wallShearStress").write_text(_FIXTURE_WSS)

    # TAMPER: overwrite the reference CSV with a fake curve. The manifest's
    # `reference_csv_sha256` still points to the genuine hash.
    (case / "reference" / "cf_reference.csv").write_text("x_m,Cf\n0.0,0.0001\n2.0,0.0001\n")

    manifest = _yaml.safe_load((case / "case_manifest.yaml").read_text())
    result = qoi_audit.run(case, manifest)

    ref_gate = result["reference_gate"]
    assert ref_gate["status"] == "BLOCKED"
    assert ref_gate["details"]["reason"] == "reference_csv_sha_mismatch"
    # Both SHAs are reported so the user can see the drift.
    assert "expected_sha256" in ref_gate["details"]
    assert "actual_sha256" in ref_gate["details"]


def test_r16_f01_correct_sha_lets_real_comparison_run(tmp_path: Path, repo_root: Path):
    """R16-F-01 positive: with the manifest's SHA matching the on-disk
    file, the real-comparison path proceeds. Fences the regression where
    a future code change inverts the SHA check."""
    import shutil
    import yaml as _yaml
    from cfdtrust.audit import qoi as qoi_audit

    case = tmp_path / "honest_case"
    shutil.copytree(repo_root / "cases" / "flat_plate_rans_sst", case)
    (case / "case_manifest.yaml").write_text(
        (case / "case_manifest.yaml").read_text().replace(
            "solver_backend: mocked", "solver_backend: openfoam"
        )
    )
    pm = case / "constant" / "polyMesh"
    pm.mkdir(parents=True, exist_ok=True)
    (pm / "boundary").write_text(_FIXTURE_BOUNDARY)
    (pm / "faces").write_text(_FIXTURE_FACES)
    (pm / "points").write_text(_FIXTURE_POINTS)
    (case / "159").mkdir()
    (case / "159" / "wallShearStress").write_text(_FIXTURE_WSS)

    manifest = _yaml.safe_load((case / "case_manifest.yaml").read_text())
    result = qoi_audit.run(case, manifest)

    # The real comparison should run (status BLOCKED or FAIL is fine — we
    # only care that the SHA check didn't reject it).
    ref_gate = result["reference_gate"]
    assert ref_gate["details"].get("reason") != "reference_csv_sha_mismatch", (
        f"valid SHA should not BLOCK; got {ref_gate!r}"
    )


def test_r16_f02_binary_format_polymesh_blocks_explicitly():
    """R16-F-02 (LOW): polyMesh parsers must raise a structured error when
    the FoamFile header declares `format binary`. Pre-fix, the parser
    would attempt to parse the binary payload and emit a confusing
    "expected '<int> (' block; first 200 chars: ..." error."""
    from cfdtrust.qoi import wall_shear as ws

    binary_header = dedent("""
    FoamFile { format binary; class polyBoundaryMesh; object boundary; }

    1
    (
        wall { type wall; nFaces 1; startFace 0; }
    )
    """).strip()
    with pytest.raises(ValueError) as exc:
        ws.parse_polymesh_boundary(binary_header)
    assert "binary" in str(exc.value).lower()
    assert "ascii" in str(exc.value).lower()


def test_r16_f03_blocks_symlinked_time_dir(tmp_path: Path, repo_root: Path):
    """R16-F-03 (LOW): the audit-layer real-comparison path must refuse
    to read a time-step directory that is a symlink. Defense-in-depth
    against a malicious case_dir that symlinks `159/` to `/etc/`.
    """
    import shutil
    import yaml as _yaml
    from cfdtrust.audit import qoi as qoi_audit

    case = tmp_path / "symlinked_case"
    shutil.copytree(repo_root / "cases" / "flat_plate_rans_sst", case)
    (case / "case_manifest.yaml").write_text(
        (case / "case_manifest.yaml").read_text().replace(
            "solver_backend: mocked", "solver_backend: openfoam"
        )
    )
    # Plant a REAL target time-step dir elsewhere then symlink it in.
    real_dir = tmp_path / "evil_target"
    real_dir.mkdir()
    (real_dir / "wallShearStress").write_text(_FIXTURE_WSS)
    (case / "159").symlink_to(real_dir)

    manifest = _yaml.safe_load((case / "case_manifest.yaml").read_text())
    result = qoi_audit.run(case, manifest)
    ref_gate = result["reference_gate"]
    assert ref_gate["status"] == "BLOCKED"
    assert ref_gate["details"]["reason"] == "time_dir_is_symlink"


def test_r16_f05_absolute_reference_csv_path_blocks(tmp_path: Path, repo_root: Path):
    """R16-F-05 (MED): a manifest with `reference_csv: /etc/passwd`
    (absolute) must BLOCK with `reference_csv_path_unsafe`. Pre-fix the
    audit layer would happily open the absolute path because
    `Path(case_dir) / Path("/etc/passwd")` returns `/etc/passwd`."""
    import shutil
    import yaml as _yaml
    from cfdtrust.audit import qoi as qoi_audit

    case = tmp_path / "evil_manifest_case"
    shutil.copytree(repo_root / "cases" / "flat_plate_rans_sst", case)
    # Flip backend AND inject the absolute path.
    text = (case / "case_manifest.yaml").read_text()
    text = text.replace("solver_backend: mocked", "solver_backend: openfoam")
    text = text.replace(
        "reference_csv: reference/cf_reference.csv",
        "reference_csv: /etc/passwd",
    )
    (case / "case_manifest.yaml").write_text(text)

    # Plant fake polyMesh + WSS so we reach the comparison path.
    pm = case / "constant" / "polyMesh"
    pm.mkdir(parents=True, exist_ok=True)
    (pm / "boundary").write_text(_FIXTURE_BOUNDARY)
    (pm / "faces").write_text(_FIXTURE_FACES)
    (pm / "points").write_text(_FIXTURE_POINTS)
    (case / "159").mkdir()
    (case / "159" / "wallShearStress").write_text(_FIXTURE_WSS)

    manifest = _yaml.safe_load((case / "case_manifest.yaml").read_text())
    result = qoi_audit.run(case, manifest)
    ref_gate = result["reference_gate"]
    assert ref_gate["status"] == "BLOCKED"
    assert ref_gate["details"]["reason"] == "reference_csv_path_unsafe"


def test_r16_f05_traversal_reference_csv_path_blocks(tmp_path: Path, repo_root: Path):
    """R16-F-05 sibling: a manifest with `reference_csv: ../../etc/passwd`
    must BLOCK — even though it's technically a relative path, it
    resolves outside `case_dir`."""
    import shutil
    import yaml as _yaml
    from cfdtrust.audit import qoi as qoi_audit

    case = tmp_path / "traversal_case"
    shutil.copytree(repo_root / "cases" / "flat_plate_rans_sst", case)
    text = (case / "case_manifest.yaml").read_text()
    text = text.replace("solver_backend: mocked", "solver_backend: openfoam")
    text = text.replace(
        "reference_csv: reference/cf_reference.csv",
        "reference_csv: ../../etc/hosts",
    )
    (case / "case_manifest.yaml").write_text(text)
    pm = case / "constant" / "polyMesh"
    pm.mkdir(parents=True, exist_ok=True)
    (pm / "boundary").write_text(_FIXTURE_BOUNDARY)
    (pm / "faces").write_text(_FIXTURE_FACES)
    (pm / "points").write_text(_FIXTURE_POINTS)
    (case / "159").mkdir()
    (case / "159" / "wallShearStress").write_text(_FIXTURE_WSS)

    manifest = _yaml.safe_load((case / "case_manifest.yaml").read_text())
    result = qoi_audit.run(case, manifest)
    ref_gate = result["reference_gate"]
    assert ref_gate["status"] == "BLOCKED"
    assert ref_gate["details"]["reason"] == "reference_csv_path_unsafe"
    assert "outside case_dir" in ref_gate["details"]["detail"]


def test_r16_f06_schema_rejects_negative_x_min_compare(repo_root: Path):
    """R16-F-06 (LOW): `x_min_compare_m` must be >= 0."""
    import json as _json
    from jsonschema import Draft7Validator

    schema = _json.loads(
        (repo_root / "cfdtrust" / "schemas" / "case_manifest.schema.json").read_text()
    )
    sub = schema["properties"]["reference_comparison"]["properties"]["x_min_compare_m"]
    validator = Draft7Validator(sub)
    assert list(validator.iter_errors(-0.01)), "schema must reject negative x_min_compare_m"
    assert not list(validator.iter_errors(0.0))
    assert not list(validator.iter_errors(0.5))


def test_r16_f06_schema_rejects_zero_tolerance(repo_root: Path):
    """Tolerance must be strictly positive — zero or negative is a typo."""
    import json as _json
    from jsonschema import Draft7Validator

    schema = _json.loads(
        (repo_root / "cfdtrust" / "schemas" / "case_manifest.schema.json").read_text()
    )
    sub = schema["properties"]["reference_comparison"]["properties"]["tolerance"]
    validator = Draft7Validator(sub)
    assert list(validator.iter_errors(0.0))
    assert list(validator.iter_errors(-0.05))
    assert not list(validator.iter_errors(0.10))


def test_r16_f06_schema_rejects_absolute_reference_csv(repo_root: Path):
    """`reference_csv` regex disallows leading `/` so absolute paths fail
    schema validation BEFORE hitting the runtime check (defense in depth)."""
    import json as _json
    from jsonschema import Draft7Validator

    schema = _json.loads(
        (repo_root / "cfdtrust" / "schemas" / "case_manifest.schema.json").read_text()
    )
    sub = schema["properties"]["reference_comparison"]["properties"]["reference_csv"]
    validator = Draft7Validator(sub)
    assert list(validator.iter_errors("/etc/passwd"))
    assert not list(validator.iter_errors("reference/cf_reference.csv"))


def test_r16_f07_trust_report_schema_rejects_validated_with_failed_reference(
    repo_root: Path,
):
    """R16-F-07 (LOW): trust_report.json schema must reject a document
    where `validation_status: validated` but `reference_comparison.status`
    is anything other than PASS. Defense-in-depth against an aggregator
    regression that bypasses the audit-layer logic."""
    import json as _json
    from jsonschema import Draft7Validator

    schema = _json.loads(
        (repo_root / "cfdtrust" / "schemas" / "trust_report.schema.json").read_text()
    )
    validator = Draft7Validator(schema)

    base = {
        "case_id": "x",
        "generated_at": "2026-05-21T00:00:00Z",
        "overall_status": "PASS",
        "solver_execution": "real",
        "validation_status": "validated",
        "gates": {
            "geometry_contract": {"status": "PASS", "summary": "ok"},
            "mesh_contract": {"status": "PASS", "summary": "ok"},
            "bc_contract": {"status": "PASS", "summary": "ok"},
            "solver_execution": {"status": "PASS", "summary": "ok"},
            "qoi_extraction": {"status": "PASS", "summary": "ok"},
            "reference_comparison": {"status": "FAIL", "summary": "did not match"},
        },
        "artifacts": {},
        "limitations": [],
        "next_actions": [],
    }
    errors = list(validator.iter_errors(base))
    assert errors, (
        "schema must reject `validation_status=validated` with reference_comparison.status=FAIL"
    )

    # Flip reference to PASS → schema should now accept.
    base["gates"]["reference_comparison"] = {"status": "PASS", "summary": "matched"}
    errors2 = list(validator.iter_errors(base))
    assert not errors2, f"schema must accept validated+ref-PASS; errors: {errors2}"


def test_r16_f08_qoi_csv_header_is_consistent_across_modes(tmp_path: Path, repo_root: Path):
    """R16-F-08 (LOW): qoi.csv columns must be the SAME 5-column layout
    in both mocked and real modes, so downstream consumers don't break
    when the case flips from `solver_backend: mocked` to `openfoam`.
    """
    import shutil
    import yaml as _yaml
    from cfdtrust.audit import qoi as qoi_audit

    expected_header = "name,x_m,value,units,source"

    # Mocked case.
    case_mocked = tmp_path / "mocked"
    shutil.copytree(repo_root / "cases" / "flat_plate_rans_sst", case_mocked)
    manifest_mocked = _yaml.safe_load((case_mocked / "case_manifest.yaml").read_text())
    qoi_audit.run(case_mocked, manifest_mocked)
    mocked_header = (case_mocked / "artifacts" / "qoi.csv").read_text().splitlines()[0]
    assert mocked_header == expected_header

    # Real case (synthetic fixture data).
    case_real = tmp_path / "real"
    shutil.copytree(repo_root / "cases" / "flat_plate_rans_sst", case_real)
    (case_real / "case_manifest.yaml").write_text(
        (case_real / "case_manifest.yaml").read_text().replace(
            "solver_backend: mocked", "solver_backend: openfoam"
        )
    )
    pm = case_real / "constant" / "polyMesh"
    pm.mkdir(parents=True, exist_ok=True)
    (pm / "boundary").write_text(_FIXTURE_BOUNDARY)
    (pm / "faces").write_text(_FIXTURE_FACES)
    (pm / "points").write_text(_FIXTURE_POINTS)
    (case_real / "159").mkdir()
    (case_real / "159" / "wallShearStress").write_text(_FIXTURE_WSS)
    manifest_real = _yaml.safe_load((case_real / "case_manifest.yaml").read_text())
    qoi_audit.run(case_real, manifest_real)
    real_header = (case_real / "artifacts" / "qoi.csv").read_text().splitlines()[0]
    assert real_header == expected_header
