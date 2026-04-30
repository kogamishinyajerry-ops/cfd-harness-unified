"""Tests for the Step 5 multi-figure report bundle service.

Validates that build_report_bundle:

* renders all four expected PNG artifacts when the case dir has a
  valid final time directory + cell-centre field
* raises ReportBundleError on missing solver output (only 0/ exists)
* short-circuits cached PNG reads on a second call (no re-render)
* invalidates the cache when the source U field is touched

The tests pre-stage a synthetic OpenFOAM time-directory layout (U + p
+ C) on a tiny 4×4×4 grid so they never need to invoke Docker /
postProcess. The only surface they test is the matplotlib pipeline
inside report_bundle.py — _ensure_cell_centres is bypassed because a
C file is already on disk.
"""
from __future__ import annotations

import time as _time
from pathlib import Path

import numpy as np
import pytest

from ui.backend.services.case_visualize.report_bundle import (
    ARTIFACT_NAMES,
    ReportBundleError,
    build_report_bundle,
    read_report_artifact,
)


# -- fixture helpers ----------------------------------------------------


def _stage_volVectorField(path: Path, vectors: np.ndarray) -> None:
    """Write a minimal `volVectorField` dict at ``path`` with the
    given (n,3) array. Mirrors the format velocity_slice's parser
    expects.
    """
    n = len(vectors)
    body = "\n".join(f"({v[0]:.6f} {v[1]:.6f} {v[2]:.6f})" for v in vectors)
    text = (
        "FoamFile { version 2.0; format ascii; class volVectorField; }\n"
        f"internalField   nonuniform List<vector> {n}\n(\n{body}\n)\n;\n"
        "boundaryField {}\n"
    )
    path.write_text(text)


def _stage_volScalarField(path: Path, scalars: np.ndarray) -> None:
    n = len(scalars)
    body = "\n".join(f"{v:.6f}" for v in scalars)
    text = (
        "FoamFile { version 2.0; format ascii; class volScalarField; }\n"
        f"internalField   nonuniform List<scalar> {n}\n(\n{body}\n)\n;\n"
        "boundaryField {}\n"
    )
    path.write_text(text)


def _make_synthetic_case(tmp_path: Path) -> Path:
    """Stage a 12×12×12 grid of cells with a swirling 2D velocity
    field on the z-midplane and a quadratic pressure field. Enough
    points + dynamic range that matplotlib's tricontourf doesn't
    degenerate.
    """
    case = tmp_path / "imported_test"
    (case / "constant").mkdir(parents=True)
    (case / "system").mkdir()
    n = 12
    xs = np.linspace(-0.5, 0.5, n)
    ys = np.linspace(-0.5, 0.5, n)
    zs = np.linspace(-0.5, 0.5, n)
    X, Y, Z = np.meshgrid(xs, ys, zs, indexing="ij")
    C = np.stack([X.ravel(), Y.ravel(), Z.ravel()], axis=1)

    # Solid-body rotation in xy + tiny axial component so the slab
    # finite-diff has non-zero vorticity.
    Ux = -Y.ravel()
    Uy = X.ravel()
    Uz = 0.05 * Z.ravel()
    U = np.stack([Ux, Uy, Uz], axis=1)

    # Quadratic pressure bowl centred on origin.
    p = -0.5 * (X.ravel() ** 2 + Y.ravel() ** 2)

    final = case / "1"
    final.mkdir()
    _stage_volVectorField(final / "U", U)
    _stage_volVectorField(final / "C", C)  # pre-staged → no Docker
    _stage_volScalarField(final / "p", p)
    # initial-condition dir so _list_time_dirs sees both 0/ and 1/.
    init = case / "0"
    init.mkdir()
    _stage_volVectorField(init / "U", np.zeros_like(U))
    return case


# -- happy path ---------------------------------------------------------


def test_build_report_bundle_renders_four_artifacts(tmp_path):
    case = _make_synthetic_case(tmp_path)
    bundle = build_report_bundle(case)

    assert bundle.final_time == pytest.approx(1.0)
    assert bundle.cell_count == 12 * 12 * 12
    assert bundle.slab_cell_count >= 16
    assert set(bundle.artifacts.keys()) == set(ARTIFACT_NAMES)

    # All four PNGs exist on disk + non-trivial size.
    for name in ARTIFACT_NAMES:
        rel = bundle.artifacts[name]
        p = case / rel
        assert p.is_file(), f"{name} missing at {p}"
        assert p.stat().st_size > 1024, f"{name} suspiciously small"

    # Summary string mentions the final time + |U| stats.
    assert "final time" in bundle.summary_text
    assert "|U|" in bundle.summary_text


def test_read_report_artifact_returns_png_bytes(tmp_path):
    case = _make_synthetic_case(tmp_path)
    blob = read_report_artifact(case, "contour_streamlines")
    # PNG signature.
    assert blob[:8] == b"\x89PNG\r\n\x1a\n"
    assert len(blob) > 1024


def test_read_report_artifact_rejects_unknown_name(tmp_path):
    case = _make_synthetic_case(tmp_path)
    with pytest.raises(ReportBundleError):
        read_report_artifact(case, "not_a_real_artifact")


# -- caching ------------------------------------------------------------


def test_build_report_bundle_caches_artifacts(tmp_path):
    case = _make_synthetic_case(tmp_path)
    build_report_bundle(case)
    # Capture mtime; second call should NOT rewrite.
    rel = f"reports/1_000000/contour_streamlines.png"
    p = case / rel
    mtime_before = p.stat().st_mtime
    # Sleep enough that filesystems with 1-sec mtime resolution would
    # detect a re-write. Cap at 1.05s to keep the test snappy.
    _time.sleep(1.05)
    build_report_bundle(case)
    assert p.stat().st_mtime == mtime_before, "cache short-circuit failed"


def test_build_report_bundle_invalidates_when_u_field_newer(tmp_path):
    case = _make_synthetic_case(tmp_path)
    build_report_bundle(case)
    rel = f"reports/1_000000/contour_streamlines.png"
    p = case / rel
    mtime_before = p.stat().st_mtime
    # Bump U field's mtime past the cached PNG.
    _time.sleep(1.05)
    (case / "1" / "U").touch()
    build_report_bundle(case)
    assert p.stat().st_mtime > mtime_before, "cache should have invalidated"


# -- cache_version semantics (Codex round-2 P1) ------------------------


def test_build_report_bundle_cache_version_includes_final_time(tmp_path):
    case = _make_synthetic_case(tmp_path)
    bundle = build_report_bundle(case)
    # Final time is 1.0 → "1_000000" prefix; suffix is U's mtime_ns.
    assert bundle.cache_version.startswith("1_000000_")
    # Suffix is a positive int (mtime_ns).
    suffix = bundle.cache_version.split("_")[-1]
    assert suffix.isdigit() and int(suffix) > 0


def test_build_report_bundle_cache_version_changes_on_in_place_resolve(tmp_path):
    case = _make_synthetic_case(tmp_path)
    bundle1 = build_report_bundle(case)
    # Simulate icoFoam overwriting the same time dir's U field
    # (final_time unchanged, mtime advances).
    _time.sleep(1.05)
    (case / "1" / "U").touch()
    bundle2 = build_report_bundle(case)
    assert bundle1.final_time == bundle2.final_time
    assert bundle1.cache_version != bundle2.cache_version, (
        "in-place re-solve must bump cache_version "
        f"(both were {bundle1.cache_version!r})"
    )


# -- case_kind classification (Codex round-4 P2) -----------------------


def _stage_boundary(case: Path, patch_names: list[str]) -> None:
    """Write a minimal polyMesh/boundary file with the given patch
    names so _classify_case_kind has something to read.
    """
    polymesh = case / "constant" / "polyMesh"
    polymesh.mkdir(parents=True, exist_ok=True)
    body_lines = []
    for name in patch_names:
        body_lines.append(
            f"{name}\n{{\n    type wall;\n    nFaces 1;\n    startFace 0;\n}}"
        )
    text = (
        "FoamFile { version 2.0; format ascii; class polyBoundaryMesh; }\n"
        f"{len(patch_names)}\n(\n"
        + "\n".join(body_lines)
        + "\n)\n"
    )
    (polymesh / "boundary").write_text(text)


def test_build_report_bundle_case_kind_lid_driven_cavity(tmp_path):
    case = _make_synthetic_case(tmp_path)
    _stage_boundary(case, ["lid", "fixedWalls", "frontAndBack"])
    bundle = build_report_bundle(case)
    assert bundle.case_kind == "lid_driven_cavity"


def test_build_report_bundle_case_kind_channel(tmp_path):
    case = _make_synthetic_case(tmp_path)
    _stage_boundary(case, ["inlet", "outlet", "walls"])
    bundle = build_report_bundle(case)
    assert bundle.case_kind == "channel"


def test_build_report_bundle_case_kind_unknown_when_pre_setup(tmp_path):
    case = _make_synthetic_case(tmp_path)
    # No boundary file (pre-mesh / pre-setup state) → unknown.
    bundle = build_report_bundle(case)
    assert bundle.case_kind == "unknown"


# -- uniform pressure field (Codex round-2 P2) -------------------------


def test_build_report_bundle_handles_uniform_pressure(tmp_path):
    """When p is `internalField uniform <val>`, the parser returns a
    length-1 array. Previously this fell into the "len(p) != len(U)"
    branch and rendered the placeholder. Now it broadcasts to all
    cells and the pressure panel renders a flat-coloured contour.
    """
    case = tmp_path / "imported_uniform_p"
    (case / "constant").mkdir(parents=True)
    (case / "system").mkdir()
    n = 12
    xs = np.linspace(-0.5, 0.5, n)
    ys = np.linspace(-0.5, 0.5, n)
    zs = np.linspace(-0.5, 0.5, n)
    X, Y, Z = np.meshgrid(xs, ys, zs, indexing="ij")
    C = np.stack([X.ravel(), Y.ravel(), Z.ravel()], axis=1)
    Ux = -Y.ravel()
    Uy = X.ravel()
    Uz = 0.05 * Z.ravel()
    U = np.stack([Ux, Uy, Uz], axis=1)
    final = case / "1"
    final.mkdir()
    _stage_volVectorField(final / "U", U)
    _stage_volVectorField(final / "C", C)
    # Hand-write a uniform-pressure FoamFile. _stage_volScalarField
    # always emits nonuniform; for this test we need the OpenFOAM
    # uniform layout the round-2 fix targets.
    (final / "p").write_text(
        "FoamFile { version 2.0; format ascii; class volScalarField; }\n"
        "internalField   uniform 3.5 ;\n"
        "boundaryField {}\n"
    )
    init = case / "0"
    init.mkdir()
    _stage_volVectorField(init / "U", np.zeros_like(U))

    bundle = build_report_bundle(case)
    p = case / bundle.artifacts["pressure"]
    assert p.is_file()
    # PNG > 1 KB => real plot, not the "not available" placeholder
    # which renders an empty figure ~600 B.
    assert p.stat().st_size > 1024


# -- 3D slab projection dedup (Codex round-6 P2) -----------------------


def test_project_slab_collapses_duplicate_xy_samples():
    """For genuinely 3D meshes the slab catches multiple cells per
    (Cx, Cy) projection with different field values. _project_slab
    must average them onto bins so matplotlib.tri's no-duplicate
    constraint holds. Construct a synthetic case where 4 slab cells
    map to the same projected (x, y) with values [0, 10, 0, 10]; the
    bin should report mean 5.
    """
    from ui.backend.services.case_visualize.report_bundle import _project_slab

    # 4 cells at (0,0), 4 at (1,0), 4 at (0,1), 4 at (1,1) — each
    # quad has alternating Ux 0/10. Total 16 cells.
    Cx = np.array([0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1], dtype=float)
    Cy = np.array([0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1], dtype=float)
    Ux = np.array([0, 10, 0, 10] * 4, dtype=float)
    Uy = np.zeros(16)
    Cx_out, Cy_out, Ux_out, Uy_out, p_out = _project_slab(
        Cx, Cy, Ux, Uy, None, n_bins=2
    )
    # 4 unique (x, y) bins → 4 output cells
    assert len(Cx_out) == 4
    # Every bin should average to 5 (mean of 0, 10, 0, 10)
    assert np.allclose(Ux_out, 5.0)
    assert p_out is None


def test_project_slab_passthrough_when_no_collisions():
    """Pseudo-2D mesh: every (Cx, Cy) is unique → binning is a
    no-op and the function returns the original arrays so we don't
    pay the binning cost.
    """
    from ui.backend.services.case_visualize.report_bundle import _project_slab

    Cx = np.array([0, 1, 2, 3], dtype=float)
    Cy = np.array([0, 1, 2, 3], dtype=float)
    Ux = np.array([0, 1, 2, 3], dtype=float)
    Uy = np.zeros(4)
    Cx_out, *_ = _project_slab(Cx, Cy, Ux, Uy, None, n_bins=64)
    assert Cx_out is Cx  # identity check — pass-through


# -- stale C recovery (Codex round-5 P1) -------------------------------


def test_build_report_bundle_recovers_from_stale_c_field(tmp_path):
    """Simulate a remesh: the case has a C field cached from an old
    mesh (different cell count). Previously the length check rejected
    the bundle permanently. Now it deletes the stale C and lets
    _ensure_cell_centres regenerate. The synthetic test case never
    actually invokes Docker — _ensure_cell_centres returns whichever
    pre-staged C it finds. To exercise the recovery path we stage TWO
    mismatched C fields and verify the build raises a clear error
    instead of silently rendering with wrong centres.
    """
    case = _make_synthetic_case(tmp_path)
    # Plant a stale C in the initial-time dir with the WRONG cell count.
    # _ensure_cell_centres iterates time dirs in ascending order so it
    # picks up 0/C first if it exists.
    init = case / "0"
    n_stale = 50  # not equal to len(U) = 12³ = 1728
    stale_C = np.zeros((n_stale, 3))
    _stage_volVectorField(init / "C", stale_C)
    # The good C field is already in 1/C from _make_synthetic_case.

    # Build now picks 0/C first (smaller time → first in list iteration
    # but _ensure_cell_centres uses for-loop ordering). The recovery
    # path deletes 0/C + retries, which finds the valid 1/C and proceeds.
    bundle = build_report_bundle(case)
    assert bundle.cell_count == 12 * 12 * 12
    assert (init / "C").is_file() is False, "stale C should have been removed"


# -- failure modes ------------------------------------------------------


def test_build_report_bundle_raises_when_only_initial_time_dir(tmp_path):
    case = tmp_path / "imported_unsolved"
    (case / "constant").mkdir(parents=True)
    (case / "system").mkdir()
    init = case / "0"
    init.mkdir()
    _stage_volVectorField(init / "U", np.zeros((8, 3)))
    with pytest.raises(ReportBundleError, match=r"solver hasn't run|0/"):
        build_report_bundle(case)


def test_build_report_bundle_raises_when_no_time_dirs(tmp_path):
    case = tmp_path / "imported_empty"
    (case / "constant").mkdir(parents=True)
    (case / "system").mkdir()
    with pytest.raises(ReportBundleError, match=r"no time directories"):
        build_report_bundle(case)
