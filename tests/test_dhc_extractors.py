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
    PSI_CLOSURE_FRACTION_THRESHOLD,
    PSI_MAX_GOLD_NONDIM,
    DHCBoundary,
    DHCFieldSlice,
    extract_nu_max,
    extract_psi_max,
    extract_u_max_vertical,
    extract_v_max_horizontal,
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

    # ----- B.2 · u_max + v_max ---------------------------------------------

    @staticmethod
    def _build_velocity_field(
        n_x: int, n_y: int, L: float,
        u_amplitude: float, v_amplitude: float,
    ) -> Tuple[List[float], List[float], List[Tuple[float, float, float]]]:
        """Build a synthetic 2D buoyant-cell velocity field.

        Seed (NOT a real Navier-Stokes solution — chosen for known peaks):
            u_x(x,y) = -u_amplitude · sin(2πy/L) · sin(πx/L)
            u_y(x,y) =  v_amplitude · sin(πx/L)  · sin(πy/L)

        Properties:
          - At x=L/2 vertical mid-plane: |u_x| = u_amplitude · |sin(2πy/L)| · 1,
            peaks at y=L/4 (and y=3L/4) with magnitude u_amplitude.
          - At y=L/2 horizontal mid-plane: |u_y| = v_amplitude · sin(πx/L) · 1,
            peaks at x=L/2 with magnitude v_amplitude.
          - No-slip on all four walls (sin vanishes at x=0, L and y=0, L).
        """
        cxs: List[float] = []
        cys: List[float] = []
        u_vecs: List[Tuple[float, float, float]] = []
        dx = L / n_x
        dy = L / n_y
        for j in range(n_y):
            y = (j + 0.5) * dy
            for i in range(n_x):
                x = (i + 0.5) * dx
                ux = -u_amplitude * math.sin(2 * math.pi * y / L) * math.sin(math.pi * x / L)
                uy = v_amplitude * math.sin(math.pi * x / L) * math.sin(math.pi * y / L)
                cxs.append(x)
                cys.append(y)
                u_vecs.append((ux, uy, 0.0))
        return cxs, cys, u_vecs

    def test_u_max_vertical_recovers_seeded_amplitude(self) -> None:
        """At x=L/2, |u_x| = u_amplitude · |sin(2πy/L)| · 1 → peaks at y=L/4."""
        L = 1.0
        u_amp, v_amp = 0.001, 0.0  # raw m/s scale
        cxs, cys, u_vecs = self._build_velocity_field(
            n_x=40, n_y=40, L=L, u_amplitude=u_amp, v_amplitude=v_amp,
        )
        slice_ = DHCFieldSlice(cxs=cxs, cys=cys, u_vecs=u_vecs)
        bc = DHCBoundary(
            L=L, dT=10.0, wall_coord_hot=0.0, T_hot_wall=300.0,
            bc_type="fixedValue", alpha=1.408e-5,
        )
        out = extract_u_max_vertical(slice_, bc)
        assert out, "extractor returned empty dict on valid input"
        # At cell-centers nearest x=L/2 (x=0.4875 or 0.5125), sin(πx/L) ≈
        # cos(π·0.0125) = 0.99923. Peak |u_x| at y=L/4 is u_amp·1·0.99923.
        # u_nondim_expected = u_amp · 0.99923 · L / α.
        u_nondim_expected = u_amp * math.cos(math.pi * 0.0125) * L / bc.alpha
        assert out["value"] == pytest.approx(u_nondim_expected, rel=0.05)
        # Peak should be at y/L ∈ {0.25, 0.75} — accept either (symmetry).
        assert (
            abs(out["y_at_max_over_L"] - 0.25) < 0.05
            or abs(out["y_at_max_over_L"] - 0.75) < 0.05
        ), f"y_at_max_over_L={out['y_at_max_over_L']}, expected near 0.25 or 0.75"
        assert out["source"] == "vertical_midplane_sample_max_abs"

    def test_v_max_horizontal_recovers_seeded_amplitude(self) -> None:
        """At y=L/2, |u_y| = v_amplitude · sin(πx/L) · 1 → peaks at x=L/2."""
        L = 1.0
        u_amp, v_amp = 0.0, 0.003
        cxs, cys, u_vecs = self._build_velocity_field(
            n_x=40, n_y=40, L=L, u_amplitude=u_amp, v_amplitude=v_amp,
        )
        slice_ = DHCFieldSlice(cxs=cxs, cys=cys, u_vecs=u_vecs)
        bc = DHCBoundary(
            L=L, dT=10.0, wall_coord_hot=0.0, T_hot_wall=300.0,
            bc_type="fixedValue", alpha=1.408e-5,
        )
        out = extract_v_max_horizontal(slice_, bc)
        assert out, "extractor returned empty dict on valid input"
        # At cell-centers nearest y=L/2 (y=0.4875 or 0.5125), sin(πy/L) ≈
        # sin(π·0.4875) = sin(π·0.5125) = cos(π·0.0125) ≈ 0.9992.
        # At x=L/2: sin(π/2) = 1. So |u_y| at peak ≈ 0.003 · 1 · 0.9992 = 2.998e-3.
        v_nondim_expected = v_amp * 1.0 * math.cos(math.pi * 0.0125) * L / bc.alpha
        assert out["value"] == pytest.approx(v_nondim_expected, rel=0.05)
        assert abs(out["x_at_max_over_L"] - 0.5) < 0.05
        assert out["source"] == "horizontal_midplane_sample_max_abs"

    def test_u_max_fails_closed_when_velocity_missing(self) -> None:
        """No u_vecs → extractor returns {} (MISSING_TARGET_QUANTITY signal)."""
        slice_ = DHCFieldSlice(cxs=[0.5], cys=[0.5], t_vals=[300.0])
        bc = DHCBoundary(
            L=1.0, dT=10.0, wall_coord_hot=0.0, T_hot_wall=300.0,
            bc_type="fixedValue",
        )
        assert extract_u_max_vertical(slice_, bc) == {}
        assert extract_v_max_horizontal(slice_, bc) == {}

    def test_u_max_fails_closed_on_zero_alpha(self) -> None:
        """α=0 → divide-by-zero in nondim → must return {}."""
        slice_ = DHCFieldSlice(
            cxs=[0.5, 0.5], cys=[0.5, 0.6],
            u_vecs=[(0.001, 0.0, 0.0), (0.001, 0.0, 0.0)],
        )
        bc = DHCBoundary(
            L=1.0, dT=10.0, wall_coord_hot=0.0, T_hot_wall=300.0,
            bc_type="fixedValue", alpha=0.0,
        )
        assert extract_u_max_vertical(slice_, bc) == {}

    # ----- B.3 · ψ_max trapezoidal reconstruction --------------------------

    @staticmethod
    def _build_streamfunction_field(
        n_x: int, n_y: int, L: float, A: float,
    ) -> Tuple[List[float], List[float], List[Tuple[float, float, float]]]:
        """Seed an analytically-known ψ = A · sin(πx/L) · sin(πy/L) field.

        Then u_x = ∂ψ/∂y = (Aπ/L) · sin(πx/L) · cos(πy/L)
        and  u_y = -∂ψ/∂x = -(Aπ/L) · cos(πx/L) · sin(πy/L).
        ψ vanishes on all four walls, so the no-slip closure assumption
        used by extract_psi_max is exactly satisfied. ψ_max = A occurs at
        (L/2, L/2). Cumulative trapezoidal integration recovers A within
        the trapezoidal-rule discretization error (~O(dy²) for smooth ψ).
        """
        cxs: List[float] = []
        cys: List[float] = []
        u_vecs: List[Tuple[float, float, float]] = []
        dx = L / n_x
        dy = L / n_y
        coef = A * math.pi / L
        for j in range(n_y):
            y = (j + 0.5) * dy
            for i in range(n_x):
                x = (i + 0.5) * dx
                ux = coef * math.sin(math.pi * x / L) * math.cos(math.pi * y / L)
                uy = -coef * math.cos(math.pi * x / L) * math.sin(math.pi * y / L)
                cxs.append(x)
                cys.append(y)
                u_vecs.append((ux, uy, 0.0))
        return cxs, cys, u_vecs

    def test_psi_max_recovers_analytical_amplitude(self) -> None:
        """Seed ψ=A·sin·sin → extractor recovers A within trapezoidal error."""
        L, A = 1.0, 2.5e-5  # raw m²/s; choose A so A/α ≈ 1.78
        cxs, cys, u_vecs = self._build_streamfunction_field(
            n_x=40, n_y=40, L=L, A=A,
        )
        slice_ = DHCFieldSlice(cxs=cxs, cys=cys, u_vecs=u_vecs)
        bc = DHCBoundary(
            L=L, dT=10.0, wall_coord_hot=0.0, T_hot_wall=300.0,
            bc_type="fixedValue", alpha=1.408e-5,
        )
        out = extract_psi_max(slice_, bc)
        assert out, "extractor returned empty dict on valid input"
        # Discrete trapezoidal recovers ψ_max exactly at the cell-center
        # nearest (L/2, L/2). Tolerance 5% absorbs the cell-snap error.
        expected_nondim = A / bc.alpha
        assert out["value"] == pytest.approx(expected_nondim, rel=0.05)
        # Peak should land near cavity center.
        assert abs(out["x_at_max_over_L"] - 0.5) < 0.05
        assert abs(out["y_at_max_over_L"] - 0.5) < 0.05
        assert out["num_columns_used"] == 40
        assert out["source"] == "trapezoidal_y_integration_of_ux"

    def test_psi_max_passes_snr_for_clean_synthetic(self) -> None:
        """Analytical ψ=0 at top wall → tiny closure residual → HARD_GATED."""
        L, A = 1.0, 2.5e-5
        cxs, cys, u_vecs = self._build_streamfunction_field(
            n_x=80, n_y=80, L=L, A=A,
        )
        slice_ = DHCFieldSlice(cxs=cxs, cys=cys, u_vecs=u_vecs)
        bc = DHCBoundary(
            L=L, dT=10.0, wall_coord_hot=0.0, T_hot_wall=300.0,
            bc_type="fixedValue", alpha=1.408e-5,
        )
        out = extract_psi_max(slice_, bc)
        # Dense mesh + analytically closing field → closure_fraction tiny.
        assert out["closure_fraction_of_gold"] < PSI_CLOSURE_FRACTION_THRESHOLD
        assert out["snr_pass"] is True
        assert out["advisory_status"] == "HARD_GATED"

    def test_psi_max_demotes_when_closure_residual_too_large(self) -> None:
        """Inject an artificial DC offset into u_x → top-wall closure fails."""
        L, A = 1.0, 2.5e-5
        cxs, cys, u_vecs = self._build_streamfunction_field(
            n_x=40, n_y=40, L=L, A=A,
        )
        # DC offset large enough that ∫_0^L offset dy = offset · L blows past
        # 1 % of (PSI_MAX_GOLD_NONDIM · α). The threshold = 0.01·16.75·1.408e-5
        # = 2.36e-6 m²/s. An offset of 5e-6 m/s yields residual 5e-6 m²/s,
        # comfortably above the threshold.
        offset = 5.0e-6
        u_vecs_offset = [(u + offset, v, w) for (u, v, w) in u_vecs]
        slice_ = DHCFieldSlice(cxs=cxs, cys=cys, u_vecs=u_vecs_offset)
        bc = DHCBoundary(
            L=L, dT=10.0, wall_coord_hot=0.0, T_hot_wall=300.0,
            bc_type="fixedValue", alpha=1.408e-5,
        )
        out = extract_psi_max(slice_, bc)
        assert out["closure_fraction_of_gold"] >= PSI_CLOSURE_FRACTION_THRESHOLD
        assert out["snr_pass"] is False
        assert out["advisory_status"] == "PROVISIONAL_ADVISORY"

    def test_psi_max_fails_closed_when_velocity_missing(self) -> None:
        slice_ = DHCFieldSlice(cxs=[0.5], cys=[0.5], t_vals=[300.0])
        bc = DHCBoundary(
            L=1.0, dT=10.0, wall_coord_hot=0.0, T_hot_wall=300.0,
            bc_type="fixedValue",
        )
        assert extract_psi_max(slice_, bc) == {}

    def test_psi_max_constants_match_intake(self) -> None:
        """Guard against drift from intake §B.3 declared values."""
        assert PSI_MAX_GOLD_NONDIM == pytest.approx(16.750)
        assert PSI_CLOSURE_FRACTION_THRESHOLD == pytest.approx(0.01)
