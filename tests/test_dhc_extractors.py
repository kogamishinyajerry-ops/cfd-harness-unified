"""Tests for src.dhc_extractors · DEC-V61-057 Batch B.

All tests live under the ``TestDHCMultiDim`` class per DEC-V61-057 §coordination
rule 6 (test-class-name independence across parallel Track-B sessions).

Synthetic field construction notes
----------------------------------
A canonical DHC at Ra=1e6 has thermal BL thickness δ_T/L ≈ 0.032 and a
near-exponential temperature drop across the BL on the hot wall. We don't
need a converged Navier-Stokes solution to test the *extractor* — we only
need fields whose wall gradient is analytically known so we can compare
the extracted Nu against the closed-form ground truth.

The fixtures below build cell-center T-fields with a hand-crafted
y-dependent BL thickness profile so Nu_max occurs at a known y location
and Nu(y_other) is strictly less. We verify both:

  1. The extractor recovers Nu_max within numerical-stencil error.
  2. The y_at_max location matches the seeded peak.
  3. SNR diagnostics behave (noise_floor>0 when there's variation;
     None-snr returned for degenerate flat-Nu inputs).
"""
from __future__ import annotations

import math
from typing import List, Tuple

import pytest

from src.dhc_extractors import (
    DHCBoundary,
    DHCFieldSlice,
    extract_nu_max,
)


# ---------------------------------------------------------------------------
# Synthetic field builders
# ---------------------------------------------------------------------------

def _build_field(
    n_x: int,
    n_y: int,
    L: float,
    *,
    dT: float,
    T_cold: float,
    bl_thickness_at_y: callable,
) -> Tuple[List[float], List[float], List[float]]:
    """Build a uniform-grid DHC T-field with a y-dependent BL thickness.

    Inside the hot-wall BL (x < δ(y)), T drops linearly from T_hot at the
    wall to ~(T_cold + 0.1·dT) at x=δ(y); outside the BL, T relaxes to
    T_cold. The wall gradient at x=0 is then dT_BL/δ(y) where dT_BL =
    0.9·dT, so a thinner BL → larger gradient → larger Nu_local.

    Returns (cxs, cys, t_vals) parallel arrays, one entry per cell-center.
    """
    T_hot = T_cold + dT
    cxs: List[float] = []
    cys: List[float] = []
    t_vals: List[float] = []
    dx = L / n_x
    dy = L / n_y
    for j in range(n_y):
        y = (j + 0.5) * dy
        delta = bl_thickness_at_y(y)
        for i in range(n_x):
            x = (i + 0.5) * dx
            if x < delta:
                # Linear drop across BL: T(0)=T_hot, T(delta)=T_cold + 0.1*dT.
                frac = x / delta
                T = T_hot - frac * (0.9 * dT)
            else:
                T = T_cold + 0.1 * dT * math.exp(-(x - delta) / (0.5 * L))
            cxs.append(x)
            cys.append(y)
            t_vals.append(T)
    return cxs, cys, t_vals


# ---------------------------------------------------------------------------
class TestDHCMultiDim:
    """Multi-dimensional extractor unit tests for DEC-V61-057 Batch B."""

    # ----- B.1 · Nu_max ----------------------------------------------------

    def test_nu_max_recovers_thinnest_bl_layer(self) -> None:
        """Seed a field whose BL is thinnest at y/L=0.05 → Nu_max there."""
        L, dT, T_cold = 1.0, 10.0, 290.0
        # BL thickness profile: minimum 0.025 at y/L=0.05, growing toward
        # mid-cavity. The thinnest BL has wall gradient 0.9*dT/0.025 = 360,
        # so Nu_local = 360 * L/dT = 36.
        def delta(y: float) -> float:
            return 0.025 + 0.10 * abs(y - 0.05)

        cxs, cys, t_vals = _build_field(
            n_x=40, n_y=40, L=L, dT=dT, T_cold=T_cold, bl_thickness_at_y=delta,
        )
        slice_ = DHCFieldSlice(cxs=cxs, cys=cys, t_vals=t_vals)
        bc = DHCBoundary(
            L=L, dT=dT, wall_coord_hot=0.0, T_hot_wall=T_cold + dT,
            bc_type="fixedValue",
        )
        out = extract_nu_max(slice_, bc)
        assert out, "extractor returned empty dict on valid input"
        # Stencil bias on a 40-cell uniform mesh: O(h)=2.5% at minimum-δ
        # layer. Tolerance widened to 12% to absorb (a) discrete-cell
        # alignment of the seed peak and (b) the finite-band over which
        # δ(y) hits its minimum.
        assert out["value"] == pytest.approx(36.0, rel=0.12), (
            f"Nu_max={out['value']}, expected ~36 (analytical)"
        )
        # Peak should land in the bottom 1/4 of the cavity (y/L < 0.25)
        # since the BL minimum is at y/L=0.05.
        assert 0.0 <= out["y_at_max_over_L"] < 0.25, (
            f"y_at_max/L={out['y_at_max_over_L']}, expected in [0, 0.25)"
        )
        assert out["num_layers_used"] == 40
        assert out["source"] == "wall_gradient_stencil_3pt_max"

    def test_nu_max_uniform_bl_gives_uniform_nu(self) -> None:
        """Constant BL thickness → all layers same Nu → noise_floor≈0, SNR=None."""
        L, dT, T_cold = 1.0, 10.0, 290.0
        cxs, cys, t_vals = _build_field(
            n_x=40, n_y=40, L=L, dT=dT, T_cold=T_cold,
            bl_thickness_at_y=lambda y: 0.05,
        )
        slice_ = DHCFieldSlice(cxs=cxs, cys=cys, t_vals=t_vals)
        bc = DHCBoundary(
            L=L, dT=dT, wall_coord_hot=0.0, T_hot_wall=T_cold + dT,
            bc_type="fixedValue",
        )
        out = extract_nu_max(slice_, bc)
        # Uniform δ=0.05: Nu_local = 0.9*dT/0.05 * L/dT = 18.
        assert out["value"] == pytest.approx(18.0, rel=0.10)
        # noise_floor measures interior-layer Nu spread; for a perfectly
        # uniform synthetic, this is at the floating-point noise level.
        # Either snr is None (floor==0) or extremely large (>>1000).
        if out["snr"] is not None:
            assert out["snr"] > 1000.0, (
                f"snr={out['snr']} but uniform field should have ~infinite SNR"
            )

    def test_nu_max_fails_closed_on_empty_input(self) -> None:
        bc = DHCBoundary(
            L=1.0, dT=10.0, wall_coord_hot=0.0, T_hot_wall=300.0,
            bc_type="fixedValue",
        )
        empty_slice = DHCFieldSlice(cxs=[], cys=[], t_vals=[])
        assert extract_nu_max(empty_slice, bc) == {}

    def test_nu_max_fails_closed_on_zero_dT(self) -> None:
        """Degenerate dT=0 would cause divide-by-zero — must return {}."""
        cxs = [0.01, 0.02, 0.01, 0.02]
        cys = [0.10, 0.10, 0.20, 0.20]
        t_vals = [300.0, 300.0, 300.0, 300.0]
        slice_ = DHCFieldSlice(cxs=cxs, cys=cys, t_vals=t_vals)
        bc = DHCBoundary(
            L=1.0, dT=0.0, wall_coord_hot=0.0, T_hot_wall=300.0,
            bc_type="fixedValue",
        )
        assert extract_nu_max(slice_, bc) == {}

    def test_nu_max_y_location_matches_seeded_peak(self) -> None:
        """BL minimum seeded at y/L=0.30 → y_at_max should land near 0.30."""
        L, dT, T_cold = 1.0, 10.0, 290.0
        def delta(y: float) -> float:
            return 0.020 + 0.20 * abs(y - 0.30)

        cxs, cys, t_vals = _build_field(
            n_x=40, n_y=40, L=L, dT=dT, T_cold=T_cold, bl_thickness_at_y=delta,
        )
        slice_ = DHCFieldSlice(cxs=cxs, cys=cys, t_vals=t_vals)
        bc = DHCBoundary(
            L=L, dT=dT, wall_coord_hot=0.0, T_hot_wall=T_cold + dT,
            bc_type="fixedValue",
        )
        out = extract_nu_max(slice_, bc)
        # n_y=40 → dy=0.025, so seeded y=0.30 lands at cell-center 0.2875
        # or 0.3125. y_at_max_over_L should be within one cell of 0.30.
        assert abs(out["y_at_max_over_L"] - 0.30) < 0.04, (
            f"y_at_max_over_L={out['y_at_max_over_L']}, expected within 0.04 of 0.30"
        )
