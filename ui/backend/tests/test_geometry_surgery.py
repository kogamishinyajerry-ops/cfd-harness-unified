"""Unit tests for geometry surgery (DEC-V61-198 A3 artifact).

Covers the two pure transforms (decimate / axial_stretch), tier
clamping behavior, and orchestrator dispatch. Decimation backend
is exercised opportunistically — if neither fast_simplification
nor pyfqmr is installed, the decimation tests are skipped (the
small-mesh skip path is still tested unconditionally).
"""
from __future__ import annotations

import importlib.util

import numpy as np
import pytest
import trimesh

from ui.backend.services.geometry_ingest.geometry_surgery import (
    AxialStretchSpec,
    DecimationBackendUnavailable,
    TierSpec,
    apply_surgery,
    axial_stretch,
    decimate_to_tier,
)


_HAS_FAST_SIMPLIFICATION = importlib.util.find_spec("fast_simplification") is not None
_HAS_PYFQMR = importlib.util.find_spec("pyfqmr") is not None
_HAS_DECIMATION_BACKEND = _HAS_FAST_SIMPLIFICATION or _HAS_PYFQMR


def _icosphere(subdivisions: int = 4) -> trimesh.Trimesh:
    """High-face-count mesh for decimation tests (subd=4 → 1280 faces)."""
    return trimesh.creation.icosphere(subdivisions=subdivisions)


def _cube() -> trimesh.Trimesh:
    return trimesh.creation.box([1.0, 1.0, 1.0])


def test_decimate_skips_below_min_to_decimate_threshold():
    cube = _cube()
    assert len(cube.faces) == 12
    tier = TierSpec(keep_ratio=0.1, min_faces=4, max_faces=8, min_to_decimate=20)
    out = decimate_to_tier(cube, tier)
    assert len(out.faces) == 12, "below threshold → returned unchanged"


def test_decimate_returns_input_when_target_exceeds_face_count():
    mesh = _icosphere(subdivisions=2)
    n = len(mesh.faces)
    tier = TierSpec(keep_ratio=2.0, min_faces=1, max_faces=999_999, min_to_decimate=10)
    out = decimate_to_tier(mesh, tier)
    assert len(out.faces) == n, "target > current → returned unchanged"


@pytest.mark.skipif(
    not _HAS_DECIMATION_BACKEND,
    reason="needs fast_simplification or pyfqmr",
)
def test_decimate_clamps_to_min_faces():
    mesh = _icosphere(subdivisions=4)
    n_before = len(mesh.faces)
    assert n_before >= 1000
    tier = TierSpec(keep_ratio=0.001, min_faces=200, max_faces=999_999, min_to_decimate=100)
    out = decimate_to_tier(mesh, tier)
    assert len(out.faces) >= 200 - 50, (
        f"clamped to min_faces≈200, got {len(out.faces)} (some backend slack ok)"
    )
    assert len(out.faces) < n_before, "clamping must still reduce face count"


@pytest.mark.skipif(
    not _HAS_DECIMATION_BACKEND,
    reason="needs fast_simplification or pyfqmr",
)
def test_decimate_clamps_to_max_faces():
    mesh = _icosphere(subdivisions=4)
    n_before = len(mesh.faces)
    tier = TierSpec(keep_ratio=0.99, min_faces=1, max_faces=400, min_to_decimate=100)
    out = decimate_to_tier(mesh, tier)
    assert len(out.faces) <= 400 + 50, f"clamped to max_faces≈400, got {len(out.faces)}"
    assert len(out.faces) < n_before


def test_decimate_raises_helpful_error_when_backend_missing(monkeypatch):
    if _HAS_DECIMATION_BACKEND:
        pytest.skip("decimation backend present; cannot simulate missing-backend path")
    mesh = _icosphere(subdivisions=4)
    tier = TierSpec(keep_ratio=0.1, min_faces=10, max_faces=100, min_to_decimate=100)
    with pytest.raises(DecimationBackendUnavailable) as exc_info:
        decimate_to_tier(mesh, tier)
    assert "fast_simplification" in str(exc_info.value)
    assert "pyfqmr" in str(exc_info.value)


def test_axial_stretch_x_around_origin():
    cube = _cube()
    spec = AxialStretchSpec(axis="x", center=0.0, factor=2.0)
    out = axial_stretch(cube, spec)
    assert out.bounds[0][0] == pytest.approx(-1.0)
    assert out.bounds[1][0] == pytest.approx(1.0)
    assert out.bounds[0][1] == pytest.approx(cube.bounds[0][1])
    assert out.bounds[1][1] == pytest.approx(cube.bounds[1][1])
    assert out.bounds[0][2] == pytest.approx(cube.bounds[0][2])
    assert out.bounds[1][2] == pytest.approx(cube.bounds[1][2])


def test_axial_stretch_y_around_offset_pivot():
    cube = _cube()
    cube.vertices = cube.vertices + np.array([0.0, 5.0, 0.0])
    spec = AxialStretchSpec(axis="y", center=5.0, factor=1.5)
    out = axial_stretch(cube, spec)
    assert out.bounds[0][1] == pytest.approx(5.0 - 0.75)
    assert out.bounds[1][1] == pytest.approx(5.0 + 0.75)
    assert (out.bounds[:, [0, 2]] == cube.bounds[:, [0, 2]]).all()


def test_axial_stretch_factor_one_is_noop():
    cube = _cube()
    spec = AxialStretchSpec(axis="z", center=0.123, factor=1.0)
    out = axial_stretch(cube, spec)
    assert (out.vertices == cube.vertices).all()


def test_axial_stretch_rejects_invalid_axis():
    cube = _cube()
    with pytest.raises(ValueError, match="axis"):
        axial_stretch(cube, AxialStretchSpec(axis="w", center=0.0, factor=1.1))


def test_axial_stretch_rejects_nonpositive_factor():
    cube = _cube()
    with pytest.raises(ValueError, match="factor"):
        axial_stretch(cube, AxialStretchSpec(axis="x", center=0.0, factor=0.0))
    with pytest.raises(ValueError, match="factor"):
        axial_stretch(cube, AxialStretchSpec(axis="x", center=0.0, factor=-1.0))


def test_axial_stretch_preserves_face_topology():
    mesh = _icosphere(subdivisions=2)
    n_faces_before = len(mesh.faces)
    spec = AxialStretchSpec(axis="x", center=0.0, factor=1.5)
    out = axial_stretch(mesh, spec)
    assert len(out.faces) == n_faces_before
    assert (out.faces == mesh.faces).all()


def test_apply_surgery_passes_through_bodies_without_tier():
    cube = _cube()
    sphere = _icosphere(subdivisions=2)
    out = apply_surgery({"a": cube, "b": sphere}, tiers={})
    assert (out["a"].vertices == cube.vertices).all()
    assert (out["b"].vertices == sphere.vertices).all()


def test_apply_surgery_applies_stretch_after_decimate():
    cube = _cube()
    spec = AxialStretchSpec(axis="x", center=0.0, factor=1.2)
    out = apply_surgery(
        {"only_stretch": cube},
        tiers={},
        stretches={"only_stretch": spec},
    )
    assert out["only_stretch"].bounds[0][0] == pytest.approx(-0.6)
    assert out["only_stretch"].bounds[1][0] == pytest.approx(0.6)


def test_apply_surgery_does_not_mutate_inputs():
    cube = _cube()
    original_verts = cube.vertices.copy()
    apply_surgery(
        {"x": cube},
        tiers={},
        stretches={"x": AxialStretchSpec(axis="x", center=0.0, factor=2.0)},
    )
    assert (cube.vertices == original_verts).all(), "input must not be mutated"
