"""DEC-V61-060 Stage B tests for src.rbc_extractors.

Stage B.1 covers extract_nu_asymmetry only. B.2 (w_max) and B.3
(roll_count) tests land in subsequent commits.

Per intake constraint, all DEC-V61-060 tests live in their own modules
(this file) or in the dedicated TestRBCMultiDim class in
tests/test_foam_agent_adapter.py — no test-class collision with the
parallel V61-058/V61-059 sessions.
"""
from __future__ import annotations

import math

import pytest

from src.rbc_extractors import (
    RBCBoundary,
    RBCFieldSlice,
    extract_nu_asymmetry,
)


def _make_bc(**overrides) -> RBCBoundary:
    """Canonical RBC boundary metadata (Pandey & Schumacher AR=4 setup)."""
    defaults = dict(
        Lx=4.0,
        Ly=1.0,
        H=1.0,
        dT=10.0,
        wall_coord_hot=0.0,    # bottom hot wall at y=0
        wall_coord_cold=1.0,   # top cold wall at y=Ly=1
        T_hot_wall=305.0,
        T_cold_wall=295.0,
        bc_type="fixedValue",
        bc_gradient=None,
    )
    defaults.update(overrides)
    return RBCBoundary(**defaults)


def _linear_conduction_field(nx: int = 8, ny: int = 8) -> RBCFieldSlice:
    """Pure-conduction T(y) = 305 - 10·y, on a uniform nx×ny grid in
    Lx=4 × Ly=1 domain. Symmetric across y → asymmetry should be 0
    (Nu_top == Nu_bottom == 1 for pure conduction)."""
    cxs: list[float] = []
    cys: list[float] = []
    t_vals: list[float] = []
    dx = 4.0 / nx
    dy = 1.0 / ny
    for i in range(nx):
        x = (i + 0.5) * dx
        for j in range(ny):
            y = (j + 0.5) * dy
            cxs.append(x)
            cys.append(y)
            t_vals.append(305.0 - 10.0 * y)
    return RBCFieldSlice(cxs=cxs, cys=cys, t_vals=t_vals)


def _convective_field(nx: int = 8, ny: int = 8) -> RBCFieldSlice:
    """Asymmetric T field where bottom BL is steeper than top BL —
    simulates BL under-resolution. T(y) = 305 - 10·(2y - y²) — gradient
    at y=0 = -20 (steep), gradient at y=Ly=1 = 0 (flat).
    Asymmetry should be large (~1.0)."""
    cxs: list[float] = []
    cys: list[float] = []
    t_vals: list[float] = []
    dx = 4.0 / nx
    dy = 1.0 / ny
    for i in range(nx):
        x = (i + 0.5) * dx
        for j in range(ny):
            y = (j + 0.5) * dy
            cxs.append(x)
            cys.append(y)
            t_vals.append(305.0 - 10.0 * (2 * y - y * y))
    return RBCFieldSlice(cxs=cxs, cys=cys, t_vals=t_vals)


class TestExtractNuAsymmetryB1:
    """DEC-V61-060 Stage B.1 unit tests for extract_nu_asymmetry."""

    def test_pure_conduction_yields_zero_asymmetry(self):
        """Linear T(y) → Nu_top == Nu_bottom == 1 (pure conduction
        baseline) → asymmetry should be exactly 0."""
        slice_ = _linear_conduction_field()
        bc = _make_bc()
        out = extract_nu_asymmetry(slice_, bc)
        assert out, f"Pure conduction returned empty dict: {out}"
        assert out["status"] == "ok"
        assert out["nu_bottom"] == pytest.approx(1.0, abs=0.05), (
            f"Linear T(y) → Nu_bottom should be ~1.0; got {out['nu_bottom']}"
        )
        assert out["nu_top"] == pytest.approx(1.0, abs=0.05), (
            f"Linear T(y) → Nu_top should be ~1.0; got {out['nu_top']}"
        )
        assert out["value"] == pytest.approx(0.0, abs=0.05), (
            f"Symmetric profile must give asymmetry=0; got {out['value']}"
        )

    def test_unbalanced_field_yields_nonzero_asymmetry(self):
        """Quadratic T(y) with steeper BL at bottom → Nu_bottom ≫ Nu_top
        → asymmetry should be large (~1)."""
        slice_ = _convective_field()
        bc = _make_bc()
        out = extract_nu_asymmetry(slice_, bc)
        assert out, f"Convective field returned empty dict: {out}"
        assert out["nu_bottom"] > out["nu_top"], (
            f"Bottom BL steeper than top expected: nu_bottom={out['nu_bottom']}, "
            f"nu_top={out['nu_top']}"
        )
        # Asymmetry should exceed the 5 % gate threshold (intake §3 tolerance)
        # so this synthetic field would FAIL the conservation invariant —
        # exactly what the gate is meant to catch.
        assert out["value"] > 0.05, (
            f"Asymmetric field must exceed 0.05 gate threshold; got {out['value']}"
        )

    def test_empty_slice_returns_empty_dict(self):
        """Fail-closed contract: empty inputs → MISSING_TARGET_QUANTITY."""
        slice_ = RBCFieldSlice(cxs=[], cys=[], t_vals=[])
        bc = _make_bc()
        out = extract_nu_asymmetry(slice_, bc)
        assert out == {}, f"Empty slice must return {{}}; got {out}"

    def test_inconsistent_lengths_returns_empty_dict(self):
        """Fail-closed contract: mismatched array lengths → empty dict."""
        slice_ = RBCFieldSlice(cxs=[0.5], cys=[0.5, 0.7], t_vals=[300.0])
        bc = _make_bc()
        out = extract_nu_asymmetry(slice_, bc)
        assert out == {}, f"Inconsistent lengths must return {{}}; got {out}"

    def test_zero_dt_returns_empty_dict(self):
        """Degenerate BC (dT=0) → empty dict (avoid divide-by-zero)."""
        slice_ = _linear_conduction_field()
        bc = _make_bc(dT=0.0)
        out = extract_nu_asymmetry(slice_, bc)
        assert out == {}, f"Zero dT must return {{}}; got {out}"

    def test_diagnostics_include_column_counts(self):
        """The output must include column counts for both walls so the
        comparator can detect mesh-asymmetry artifacts (e.g. one wall has
        fewer x-columns due to filtering)."""
        slice_ = _linear_conduction_field(nx=8, ny=8)
        bc = _make_bc()
        out = extract_nu_asymmetry(slice_, bc)
        assert "column_count_bottom" in out and "column_count_top" in out
        assert out["column_count_bottom"] == 8
        assert out["column_count_top"] == 8

    def test_canonical_benchmark_metadata_round_trips(self):
        """RBCBoundary should accept the canonical Pandey & Schumacher
        2018 benchmark metadata without raising."""
        bc = RBCBoundary(
            Lx=4.0, Ly=1.0, H=1.0, dT=10.0,
            wall_coord_hot=0.0, wall_coord_cold=1.0,
            T_hot_wall=305.0, T_cold_wall=295.0,
            bc_type="fixedValue",
            bc_gradient=None,
        )
        assert bc.Lx == 4.0
        assert bc.Ly == 1.0
        assert bc.H == 1.0
