"""Tests for src.impinging_jet_extractors · DEC-V61-071 Stage B.

All tests live under ``TestImpingingJetMultiDim`` per the DHC Stage B
class-name independence convention (DEC-V61-057 §coordination rule 6).

Synthetic field construction
----------------------------
Adapter convention: pseudo-2D r-z slab. cxs ∈ [0, 5D] is radial; cys ∈
[z_min, z_max] is jet-axial; plate at cy=z_max. We build cell-center T
fields with a hand-crafted r-dependent boundary-layer thickness profile
so Nu(r) takes a known shape: thin BL at the stagnation point (large
gradient, large Nu_stag), thicker BL outward, with an optional second
local minimum in BL thickness in r/D ∈ [1.5, 2.5] (the "wall-jet
transition" signature) so the secondary-peak detector can be exercised.

We don't need a converged Navier-Stokes solution — the extractor only
needs cells whose wall gradient is analytically known so we can compare
against the closed-form ground truth.
"""
from __future__ import annotations

import math
from typing import Callable, List, Tuple

import pytest

from src.impinging_jet_extractors import (
    DEFAULT_PROFILE_STATIONS_R_OVER_D,
    NU_STAG_UNPHYSICAL_CEILING,
    SECONDARY_PEAK_SEARCH_BAND_R_OVER_D,
    ImpingingJetBoundary,
    ImpingingJetFieldSlice,
    extract_nusselt_at_stagnation,
    extract_profile_at_stations,
    extract_secondary_peak_status,
    extract_y_plus_first_cell,
)


# ---------------------------------------------------------------------------
# Synthetic field builders
# ---------------------------------------------------------------------------

# Adapter geometry constants (must match _generate_impinging_jet defaults).
_D = 0.05
_H = 2.0 * _D
_R_MAX = 5.0 * _D
_Z_MIN = -_D / 2
_Z_MAX = _H + _D / 2          # plate face
_T_INLET = 310.0
_T_PLATE = 290.0
_DT = _T_INLET - _T_PLATE     # +20 K (jet hot, plate cold)


def _build_field(
    n_r: int,
    n_z: int,
    *,
    bl_thickness_at_r: Callable[[float], float],
    plate_at_top: bool = True,
) -> Tuple[List[float], List[float], List[float]]:
    """Build a uniform-grid r-z T-field with an r-dependent BL thickness.

    Inside the wall BL (n < δ(r), where n=z_max-z is the wall-normal
    coordinate), T rises linearly from T_plate at the wall to ~T_inlet at
    n=δ(r). Outside the BL, T relaxes back toward T_inlet via an exponential
    tail. The wall gradient at n=0 is then dT/δ(r) where dT=T_inlet-T_plate
    (positive, since T_inlet > T_plate). A thinner δ(r) → larger gradient
    → larger Nu_local at that r.

    Returns (cxs, cys, t_vals) parallel arrays, one entry per cell-center.
    """
    cxs: List[float] = []
    cys: List[float] = []
    t_vals: List[float] = []
    dr = _R_MAX / n_r
    dz = (_Z_MAX - _Z_MIN) / n_z
    for j in range(n_z):
        z = _Z_MIN + (j + 0.5) * dz
        n_wall = _Z_MAX - z if plate_at_top else z - _Z_MIN
        for i in range(n_r):
            r = (i + 0.5) * dr
            delta = bl_thickness_at_r(r)
            if n_wall < delta:
                # Linear rise across the BL: T(n=0)=T_plate, T(n=δ)=T_inlet.
                frac = n_wall / delta
                T = _T_PLATE + frac * _DT
            else:
                # Exponential relaxation back toward T_inlet (small residual).
                T = _T_INLET - 0.05 * _DT * math.exp(-(n_wall - delta) / (0.3 * _H))
            cxs.append(r)
            cys.append(z)
            t_vals.append(T)
    return cxs, cys, t_vals


def _default_bc() -> ImpingingJetBoundary:
    return ImpingingJetBoundary(
        D_nozzle=_D,
        T_plate=_T_PLATE,
        T_inlet=_T_INLET,
        wall_coord_plate=_Z_MAX,
        bc_type="fixedValue",
        bc_gradient=None,
        nu=2.17e-6,  # adapter Re=23000 default
    )


# ---------------------------------------------------------------------------
class TestImpingingJetMultiDim:
    """Multi-dimensional extractor unit tests for DEC-V61-071 Stage B."""

    # ----- B.1 · Nu_stagnation ------------------------------------------

    def test_stagnation_recovers_thin_bl_at_axis(self) -> None:
        """Seed BL at r=0 → Nu_stag ≈ D/δ_axis (linear ramp inside BL).

        Synthetic field — not the literature 145; testing extractor
        recovery against analytical D/δ_axis, not physics agreement.
        """
        # δ(r=0) = 0.015 m → wall gradient = dT/δ = 20/0.015 = 1333 K/m
        # Nu_stag = D · |grad| / dT = 0.05 · 1333 / 20 = 3.333.
        # Mesh: n_z=80 → dz=0.001875 → ~8 cells inside BL → stencil bias
        # well under 15%.
        def delta(r: float) -> float:
            return 0.015 + 0.10 * r  # thinnest at r=0, thickens outward
        cxs, cys, t_vals = _build_field(n_r=60, n_z=80, bl_thickness_at_r=delta)
        slice_ = ImpingingJetFieldSlice(cxs=cxs, cys=cys, t_vals=t_vals)
        out = extract_nusselt_at_stagnation(slice_, _default_bc())
        assert out, "extractor returned empty dict on valid input"
        assert out["value"] == pytest.approx(3.333, rel=0.15), (
            f"Nu_stag={out['value']:.3f}, expected ~3.333 (analytical D/δ_axis)"
        )
        assert out["r_at_stagnation_over_D"] == pytest.approx(0.0, abs=0.20)
        assert out["unphysical_magnitude"] is False
        assert out["source"] == "wall_gradient_stencil_3pt_stagnation"

    def test_stagnation_returns_empty_on_zero_dt(self) -> None:
        """T_inlet == T_plate → ΔT=0 → Nu undefined → MISSING_TARGET signal."""
        cxs, cys, t_vals = _build_field(
            n_r=20, n_z=20, bl_thickness_at_r=lambda r: 0.005
        )
        slice_ = ImpingingJetFieldSlice(cxs=cxs, cys=cys, t_vals=t_vals)
        bc = ImpingingJetBoundary(
            D_nozzle=_D, T_plate=300.0, T_inlet=300.0,
            wall_coord_plate=_Z_MAX, bc_type="fixedValue",
        )
        assert extract_nusselt_at_stagnation(slice_, bc) == {}

    def test_stagnation_returns_empty_on_length_mismatch(self) -> None:
        """Inconsistent input lengths → fail closed with empty dict."""
        slice_ = ImpingingJetFieldSlice(
            cxs=[0.001, 0.002], cys=[_Z_MAX - 0.005], t_vals=[295.0, 296.0],
        )
        assert extract_nusselt_at_stagnation(slice_, _default_bc()) == {}

    def test_stagnation_flags_unphysical_magnitude(self) -> None:
        """Diverged-solver-style huge gradient → unphysical_magnitude=True.

        Inject a temperature profile that ramps absurdly across the first
        wall cell so the stencil produces |grad| > 200000 → Nu > 500.
        """
        # Two near-wall cells with a 100x dT jump over 0.001 m.
        wall_cy = _Z_MAX
        cxs = [0.0001, 0.0001]
        cys = [wall_cy - 0.0005, wall_cy - 0.0015]
        t_vals = [_T_PLATE + 50_000.0, _T_PLATE + 100_000.0]
        slice_ = ImpingingJetFieldSlice(cxs=cxs, cys=cys, t_vals=t_vals)
        out = extract_nusselt_at_stagnation(slice_, _default_bc())
        assert out, "extractor unexpectedly returned empty"
        assert out["value"] > NU_STAG_UNPHYSICAL_CEILING
        assert out["unphysical_magnitude"] is True

    # ----- B.2 · Profile-at-stations ------------------------------------

    def test_profile_resolves_all_default_stations(self) -> None:
        """Profile extractor finds nearest r-bin for every default station."""
        def delta(r: float) -> float:
            # Monotonically thickening BL → monotonically decaying Nu.
            return 0.0025 + 0.10 * r
        cxs, cys, t_vals = _build_field(n_r=80, n_z=40, bl_thickness_at_r=delta)
        slice_ = ImpingingJetFieldSlice(cxs=cxs, cys=cys, t_vals=t_vals)
        out = extract_profile_at_stations(slice_, _default_bc())
        assert out, "profile extractor returned empty dict"
        assert out["num_stations_resolved"] == len(DEFAULT_PROFILE_STATIONS_R_OVER_D)
        assert out["num_stations_requested"] == len(DEFAULT_PROFILE_STATIONS_R_OVER_D)
        # Mesh has 80 r-bins over r ∈ [0, 5D] → bin width ≈ 0.0625 in r/D.
        # Nearest-bin pick should land within half a bin of every target.
        for s in out["stations"]:
            assert s["abs_residual_r_over_D"] <= 0.10, (
                f"target r/D={s['target_r_over_D']} matched at "
                f"r/D={s['matched_r_over_D']} (residual {s['abs_residual_r_over_D']})"
            )
        # Monotonic-decay diagnostic should fire on this seed.
        assert out["shape_diagnostics"]["is_monotonic_decay_first_segment"] is True

    def test_profile_detects_local_minimum_in_band(self) -> None:
        """δ(r) with a max in r/D ∈ [1.0, 2.0] → Nu has a local min there."""
        def delta(r: float) -> float:
            r_d = r / _D
            # δ peaks at r/D=1.5 (Nu local min there), then thins toward
            # r/D=2 (Nu rises = secondary peak signature).
            base = 0.0025 + 0.04 * r
            bump = 0.015 * math.exp(-((r_d - 1.5) ** 2) / 0.05)
            return base + bump
        cxs, cys, t_vals = _build_field(n_r=80, n_z=40, bl_thickness_at_r=delta)
        slice_ = ImpingingJetFieldSlice(cxs=cxs, cys=cys, t_vals=t_vals)
        out = extract_profile_at_stations(slice_, _default_bc())
        assert out, "profile extractor returned empty dict"
        assert out["shape_diagnostics"]["has_local_minimum_in_band"] is True

    def test_profile_returns_empty_on_missing_t(self) -> None:
        """No t_vals → no profile → empty dict (MISSING_TARGET_QUANTITY)."""
        slice_ = ImpingingJetFieldSlice(cxs=[0.001], cys=[_Z_MAX - 0.005])
        assert extract_profile_at_stations(slice_, _default_bc()) == {}

    # ----- B.3 · Secondary-peak status ----------------------------------

    def test_secondary_peak_present_when_seed_has_bump(self) -> None:
        """δ(r) min in r/D ∈ [1.5, 2.5] → Nu peak there → status PRESENT."""
        def delta(r: float) -> float:
            r_d = r / _D
            base = 0.025 - 0.0035 * min(r_d, 5.0)  # decay toward outer
            # Sharp dip in δ near r/D=2 → spike in Nu (the secondary peak).
            dip = 0.015 * math.exp(-((r_d - 2.0) ** 2) / 0.04)
            return max(0.002, base - dip)
        cxs, cys, t_vals = _build_field(n_r=80, n_z=40, bl_thickness_at_r=delta)
        slice_ = ImpingingJetFieldSlice(cxs=cxs, cys=cys, t_vals=t_vals)
        out = extract_secondary_peak_status(slice_, _default_bc())
        assert out, "secondary_peak extractor returned empty dict"
        assert out["value"] == "PRESENT"
        lo, hi = SECONDARY_PEAK_SEARCH_BAND_R_OVER_D
        assert lo <= out["peak_r_over_D"] <= hi
        assert out["monotonic_in_band"] is False
        assert out["peak_Nu_local"] > 0.0

    def test_secondary_peak_absent_on_monotonic_decay(self) -> None:
        """Strictly monotonic decaying Nu(r) → status ABSENT."""
        def delta(r: float) -> float:
            return 0.0025 + 0.10 * r
        cxs, cys, t_vals = _build_field(n_r=80, n_z=40, bl_thickness_at_r=delta)
        slice_ = ImpingingJetFieldSlice(cxs=cxs, cys=cys, t_vals=t_vals)
        out = extract_secondary_peak_status(slice_, _default_bc())
        assert out, "secondary_peak extractor returned empty dict"
        assert out["value"] == "ABSENT"
        assert out["peak_r_over_D"] is None
        assert out["monotonic_in_band"] is True

    # ----- B.4 · y+ first cell at plate ---------------------------------

    def test_y_plus_advisory_reports_max(self) -> None:
        """Seed a known u_r(n) profile → verify y+ recovery within stencil error."""
        def delta(r: float) -> float:
            return 0.005
        cxs_t, cys_t, t_vals = _build_field(
            n_r=20, n_z=20, bl_thickness_at_r=delta,
        )
        # Velocity: u_r = U·n/δ inside BL (linear), constant outside.
        # → |du_r/dn|_wall = U/δ; u_τ = sqrt(ν·U/δ); y+ = n_first·u_τ/ν.
        U = 1.0
        u_vecs: List[Tuple[float, float, float]] = []
        for cx, cy in zip(cxs_t, cys_t):
            n = _Z_MAX - cy
            if n < delta(cx):
                ur = U * n / delta(cx)
            else:
                ur = U
            u_vecs.append((ur, 0.0, 0.0))
        slice_ = ImpingingJetFieldSlice(
            cxs=cxs_t, cys=cys_t, t_vals=t_vals, u_vecs=u_vecs,
        )
        bc = _default_bc()
        out = extract_y_plus_first_cell(slice_, bc)
        assert out, "y+ extractor returned empty dict"
        assert out["advisory_status"] == "PROVISIONAL_ADVISORY"
        assert out["target_max"] == pytest.approx(5.0)
        assert out["num_radial_bins_used"] > 0
        # Analytical: u_τ = sqrt(ν·U/δ); y+ = n_first·u_τ/ν
        # δ=0.005, U=1, ν=2.17e-6 → u_τ ≈ sqrt(2.17e-6·200) ≈ 0.0208 m/s
        # n_first = first cell offset from wall ≈ dz/2 = (Z_MAX - Z_MIN) / (2·n_z)
        dz = (_Z_MAX - _Z_MIN) / 20
        n_first_expected = dz / 2
        u_tau_expected = math.sqrt(bc.nu * U / delta(0.0))
        y_plus_expected = n_first_expected * u_tau_expected / bc.nu
        assert out["value"] == pytest.approx(y_plus_expected, rel=0.30)

    def test_y_plus_returns_empty_when_u_vecs_missing(self) -> None:
        """No velocity field → y+ undefined → MISSING_TARGET signal."""
        cxs, cys, t_vals = _build_field(
            n_r=20, n_z=20, bl_thickness_at_r=lambda r: 0.005,
        )
        slice_ = ImpingingJetFieldSlice(cxs=cxs, cys=cys, t_vals=t_vals)
        assert extract_y_plus_first_cell(slice_, _default_bc()) == {}

    # ----- Codex R1 regression cases -----------------------------------

    def _make_synthetic_radial_profile_slice(
        self, profile: List[Tuple[float, float]],
    ) -> ImpingingJetFieldSlice:
        """Build a slice whose extracted Nu(r/D) matches the requested profile.

        For each (r/D, Nu_target) the helper emits two cells in one r-column
        with T_plate at n=0 implicit and uniform-spaced T such that the
        wall_gradient stencil yields exactly the requested Nu (under the
        unit-scale BC defined in this helper). Used only by the R1 regression
        tests below — production paths build slices from real OpenFOAM data.
        """
        cxs: List[float] = []
        cys: List[float] = []
        t: List[float] = []
        D = 1.0
        wall_cy = 10.0
        T_plate = 0.0
        for r_over_d, nu in profile:
            r = r_over_d * D
            # Pick T1, T2 at n=1, n=2 so |grad|·D/ΔT = nu under T_plate=0,
            # T_inlet=1 (so ΔT=1, D=1) → grad must equal nu, so T at n=1
            # should be `nu`, T at n=2 should be `2·nu`.
            cxs += [r, r]
            cys += [wall_cy - 1.0, wall_cy - 2.0]
            t += [nu, 2 * nu]
        return ImpingingJetFieldSlice(cxs=cxs, cys=cys, t_vals=t)

    def _make_unit_bc(self) -> ImpingingJetBoundary:
        return ImpingingJetBoundary(
            D_nozzle=1.0, T_plate=0.0, T_inlet=1.0,
            wall_coord_plate=10.0, bc_type="fixedValue",
        )

    def test_codex_r1_f1_sparse_profile_degrades_to_missing(self) -> None:
        """Codex R1 F1-HIGH: sparse mesh (1 bin) must NOT fabricate 6 stations."""
        slice_ = self._make_synthetic_radial_profile_slice([(2.0, 10.0)])
        out = extract_profile_at_stations(
            slice_, self._make_unit_bc(),
            target_r_over_d=DEFAULT_PROFILE_STATIONS_R_OVER_D,
        )
        # Per Codex F1 verbatim_fix: when fewer usable r-bins than targets,
        # return {} so the comparator sees MISSING_TARGET_QUANTITY.
        assert out == {}, (
            f"Sparse slice (1 r-bin) should degrade to empty dict, got: {out}"
        )

    def test_codex_r1_f2_band_edge_peak_recognized_as_present(self) -> None:
        """Codex R1 F2-HIGH: peak landing on band edge r/D=2.5 → PRESENT."""
        # Sample profile from Codex repro: peak at r/D=2.5 with valid right
        # neighbour at r/D=3.0 (outside band). Pre-fix returned ABSENT; post-
        # fix recognises the peak via global-profile context.
        profile = [(1.5, 8.0), (2.0, 9.9), (2.5, 10.0), (3.0, 9.8)]
        slice_ = self._make_synthetic_radial_profile_slice(profile)
        out = extract_secondary_peak_status(slice_, self._make_unit_bc())
        assert out, "secondary_peak extractor returned empty dict"
        assert out["value"] == "PRESENT", (
            f"Band-edge peak at r/D=2.5 should register PRESENT, got: {out}"
        )
        assert out["peak_r_over_D"] == pytest.approx(2.5)

    def test_codex_r1_f3_band_edge_minimum_not_reported_as_valley(self) -> None:
        """Codex R1 F3-MED: band-edge minimum at r/D=1.0 must NOT report a valley."""
        # Sample profile from Codex repro: minimum sits at r/D=1.0 (band edge)
        # with rising then peaking values to the right. No interior minimum
        # exists in r/D ∈ [1.0, 2.0]; pre-fix incorrectly reported True.
        profile = [(0.5, 12.0), (1.0, 10.0), (1.5, 11.0), (2.0, 12.0), (3.0, 8.0), (5.0, 6.0)]
        slice_ = self._make_synthetic_radial_profile_slice(profile)
        out = extract_profile_at_stations(
            slice_, self._make_unit_bc(),
            target_r_over_d=[p[0] for p in profile],
        )
        assert out, "profile extractor returned empty dict"
        assert out["shape_diagnostics"]["has_local_minimum_in_band"] is False, (
            f"Band-edge min at r/D=1.0 should NOT register as a valley, got: "
            f"{out['shape_diagnostics']}"
        )

    def test_codex_r1_f3_true_interior_minimum_still_recognized(self) -> None:
        """Codex R1 F3-MED counter-positive: a real interior min still detected."""
        # Same r/D positions as F3-repro but with the minimum moved to r/D=1.5
        # so an interior valley genuinely exists.
        profile = [(0.5, 12.0), (1.0, 11.0), (1.5, 9.0), (2.0, 11.5), (3.0, 8.0), (5.0, 6.0)]
        slice_ = self._make_synthetic_radial_profile_slice(profile)
        out = extract_profile_at_stations(
            slice_, self._make_unit_bc(),
            target_r_over_d=[p[0] for p in profile],
        )
        assert out, "profile extractor returned empty dict"
        assert out["shape_diagnostics"]["has_local_minimum_in_band"] is True, (
            f"Interior min at r/D=1.5 should register as a valley, got: "
            f"{out['shape_diagnostics']}"
        )

    def test_y_plus_returns_empty_when_nu_missing(self) -> None:
        """bc.nu=None → y+ cannot be computed → empty dict."""
        cxs, cys, t_vals = _build_field(
            n_r=20, n_z=20, bl_thickness_at_r=lambda r: 0.005,
        )
        u_vecs = [(1.0, 0.0, 0.0)] * len(cxs)
        slice_ = ImpingingJetFieldSlice(
            cxs=cxs, cys=cys, t_vals=t_vals, u_vecs=u_vecs,
        )
        bc = ImpingingJetBoundary(
            D_nozzle=_D, T_plate=_T_PLATE, T_inlet=_T_INLET,
            wall_coord_plate=_Z_MAX, bc_type="fixedValue",
            bc_gradient=None, nu=None,
        )
        assert extract_y_plus_first_cell(slice_, bc) == {}
