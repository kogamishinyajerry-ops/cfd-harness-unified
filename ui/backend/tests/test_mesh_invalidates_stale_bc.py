"""B-ext-3 F10 (DEC-V61-182): /mesh route must invalidate stale 0/ BC
files when it regenerates polyMesh.

R6 backward_step trace showed persona POSTed /mesh after /setup-bc,
which left 0/p, 0/U, manifest.source=user entries pointing at
patches the regenerated polyMesh no longer had. /solve then failed
deep inside OpenFOAM with cryptic 'Cannot find patchField entry for
patch0'. Fix: clear 0/, 0.orig/, and 0/* manifest entries at end of
mesh_imported_case so the next setup-bc authors fresh files."""
from __future__ import annotations

from pathlib import Path

import pytest

from ui.backend.services.meshing_gmsh.pipeline import (
    _invalidate_stale_bc_after_mesh_regen,
)


def _seed_case(case_dir: Path) -> None:
    case_dir.mkdir(parents=True, exist_ok=True)
    polymesh = case_dir / "constant" / "polyMesh"
    polymesh.mkdir(parents=True)
    (polymesh / "boundary").write_text(
        "FoamFile { object boundary; }\n1\n(\n    patch0 { type patch; nFaces 100; startFace 0; }\n)\n"
    )
    zero = case_dir / "0"
    zero.mkdir()
    (zero / "p").write_text("boundaryField { lid { type zeroGradient; } }")
    (zero / "U").write_text("boundaryField { lid { type fixedValue; } }")
    zero_orig = case_dir / "0.orig"
    zero_orig.mkdir()
    (zero_orig / "p").write_text("boundaryField { lid { type zeroGradient; } }")


def test_invalidate_removes_zero_and_zero_orig(tmp_path):
    case = tmp_path / "case"
    _seed_case(case)
    assert (case / "0").is_dir()
    assert (case / "0.orig").is_dir()

    _invalidate_stale_bc_after_mesh_regen(case)

    assert not (case / "0").exists()
    assert not (case / "0.orig").exists()
    # polyMesh untouched
    assert (case / "constant" / "polyMesh" / "boundary").is_file()


def test_invalidate_idempotent_when_already_clean(tmp_path):
    """Re-runs after /mesh idempotently — no 0/ to remove, no error."""
    case = tmp_path / "case"
    case.mkdir()
    (case / "constant" / "polyMesh").mkdir(parents=True)
    (case / "constant" / "polyMesh" / "boundary").write_text(
        "1\n(\n    patch0 { type patch; nFaces 100; startFace 0; }\n)\n"
    )
    # No 0/ or 0.orig/ at all.
    _invalidate_stale_bc_after_mesh_regen(case)
    assert not (case / "0").exists()


def test_invalidate_clears_zero_prefix_manifest_overrides(tmp_path):
    """case_manifest.yaml override entries for 0/* must be removed so
    the next setup-bc doesn't honor stale source=user marks."""
    case = tmp_path / "case"
    _seed_case(case)
    (case / "case_manifest.yaml").write_text(
        """schema_version: 2
source: imported
case_id: test_case
origin_filename: test.stl
created_at: '2026-05-07T00:00:00Z'
overrides:
  raw_dict_files:
    0/p:
      source: user
      edited_at: null
      etag: null
    0/U:
      source: user
      edited_at: null
      etag: null
    system/controlDict:
      source: user
      edited_at: null
      etag: null
"""
    )

    _invalidate_stale_bc_after_mesh_regen(case)

    import yaml

    raw = yaml.safe_load((case / "case_manifest.yaml").read_text())
    keys = set(raw["overrides"]["raw_dict_files"].keys())
    assert "0/p" not in keys
    assert "0/U" not in keys
    assert "system/controlDict" in keys


def test_invalidate_silently_skips_when_manifest_missing(tmp_path):
    """No manifest → no error; pre-flight check is the load-bearing
    guard, this is just ergonomic cleanup."""
    case = tmp_path / "case"
    _seed_case(case)
    # No case_manifest.yaml.
    _invalidate_stale_bc_after_mesh_regen(case)
    # 0/ still removed; manifest path didn't crash.
    assert not (case / "0").exists()
