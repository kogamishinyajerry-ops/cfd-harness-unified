"""B-ext-4.3 F12 mitigation (DEC-V61-189) regression: setup-bc LDC
executor surfaces a warning when invoked on geometry that's clearly
not the lid-driven cavity tutorial cube.

R7 + curl direct E2E showed icoFoam "converging" residuals on
NACA0012 with LDC defaults (lid_velocity=(1,0,0), nu=1e-3, Re=100,
bbox-derived lid+fixedWalls patches), then producing 1584 NaN U
field entries. The persona had no workbench-side signal that LDC
defaults were wrong for the geometry. Fix: read case_manifest.yaml
ingest_report bbox_extent; if aspect ratio > 3, surface a warning
in the BCSetupResult so the route response carries it back to the
caller.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from ui.backend.services.case_solve.bc_setup import (
    _ldc_geometry_mismatch_warnings,
)


def _write_manifest(case_dir: Path, bbox_extent: list[float]) -> None:
    case_dir.mkdir(parents=True, exist_ok=True)
    (case_dir / "case_manifest.yaml").write_text(
        f"""schema_version: 2
case_id: test_case
source: imported
origin_filename: test.stl
created_at: '2026-05-07T00:00:00Z'
ingest_report_summary:
  bbox_extent: {bbox_extent}
  bbox_min: [0.0, 0.0, 0.0]
  bbox_max: [{bbox_extent[0]}, {bbox_extent[1]}, {bbox_extent[2]}]
  unit_guess: m
  is_watertight: true
  solid_count: 1
  face_count: 12
  is_single_shell: true
  patches: []
  all_default_faces: false
  warnings: []
""",
        encoding="utf-8",
    )


def test_ldc_warning_fires_on_naca0012_aspect_ratio(tmp_path):
    """NACA0012 bbox is roughly [1.0, 0.12, 0.1] — aspect ratio 10×.
    Must trigger ldc_geometry_mismatch warning."""
    case = tmp_path / "case"
    _write_manifest(case, [1.0, 0.12003, 0.1])
    warnings = _ldc_geometry_mismatch_warnings(case)
    assert len(warnings) == 1
    msg = warnings[0]
    assert msg.startswith("ldc_geometry_mismatch:")
    assert "from_stl_patches=1" in msg
    assert "F12" in msg or "DEC-V61" in msg


def test_ldc_warning_silent_on_unit_cube(tmp_path):
    """LDC tutorial cube — no warning."""
    case = tmp_path / "case"
    _write_manifest(case, [1.0, 1.0, 1.0])
    assert _ldc_geometry_mismatch_warnings(case) == ()


def test_ldc_warning_silent_on_near_cube_within_tolerance(tmp_path):
    """1.5× imbalance is within tolerance — no warning."""
    case = tmp_path / "case"
    _write_manifest(case, [1.0, 1.5, 1.2])
    assert _ldc_geometry_mismatch_warnings(case) == ()


def test_ldc_warning_fires_on_pipe_expansion_aspect_ratio(tmp_path):
    """A pipe with 5× aspect ratio fires the warning."""
    case = tmp_path / "case"
    _write_manifest(case, [10.0, 1.0, 1.0])
    warnings = _ldc_geometry_mismatch_warnings(case)
    assert len(warnings) == 1
    assert "ldc_geometry_mismatch" in warnings[0]


def test_ldc_warning_silent_on_missing_manifest(tmp_path):
    """Best-effort: no manifest → no warning, doesn't fail setup-bc."""
    case = tmp_path / "case"
    case.mkdir()
    assert _ldc_geometry_mismatch_warnings(case) == ()


def test_ldc_warning_silent_on_malformed_bbox(tmp_path):
    """Malformed bbox_extent (not a list of 3) → no warning."""
    case = tmp_path / "case"
    case.mkdir()
    (case / "case_manifest.yaml").write_text(
        "schema_version: 2\ncase_id: test\nsource: imported\n"
        "origin_filename: test.stl\ncreated_at: '2026-05-07T00:00:00Z'\n"
        "ingest_report_summary:\n  bbox_extent: not_a_list\n",
        encoding="utf-8",
    )
    assert _ldc_geometry_mismatch_warnings(case) == ()


def test_bc_setup_result_carries_warnings_field():
    """BCSetupResult dataclass must accept warnings tuple."""
    from ui.backend.services.case_solve.bc_setup import BCSetupResult

    r = BCSetupResult(
        case_id="x",
        case_dir=Path("/tmp/x"),
        n_lid_faces=10,
        n_wall_faces=20,
        lid_velocity=(1.0, 0.0, 0.0),
        nu=1e-3,
        reynolds=100.0,
        written_files=("0/U", "0/p"),
        warnings=("foo",),
    )
    assert r.warnings == ("foo",)
    # default
    r2 = BCSetupResult(
        case_id="y",
        case_dir=Path("/tmp/y"),
        n_lid_faces=10,
        n_wall_faces=20,
        lid_velocity=(1.0, 0.0, 0.0),
        nu=1e-3,
        reynolds=100.0,
        written_files=(),
    )
    assert r2.warnings == ()
