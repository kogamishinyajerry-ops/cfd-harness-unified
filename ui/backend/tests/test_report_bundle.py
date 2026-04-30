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
