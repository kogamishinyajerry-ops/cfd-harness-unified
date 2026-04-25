"""DEC-V61-063 Stage A.1 · tests for src/flat_plate_extractors.py."""
from __future__ import annotations

import math
from typing import List, Tuple

import pytest

from src.flat_plate_extractors import (
    BLASIUS_DELTA99_PREFACTOR,
    BLASIUS_INVARIANT_K,
    BlasiusInvariant,
    FlatPlateExtractorError,
    ProfileSignalMetrics,
    canonicalize_turbulence_model,
    compute_blasius_invariant,
    compute_delta_99_at_x,
    enrich_cf_profile,
    profile_signal_metrics,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _blasius_cf(x: float, U_inf: float = 1.0, nu: float = 1.0 / 50000) -> float:
    """Cf = 0.664 / √Re_x for laminar Blasius."""
    Re_x = U_inf * x / nu
    return BLASIUS_INVARIANT_K / math.sqrt(Re_x)


def _blasius_profile(
    x: float,
    n_points: int = 60,
    H: float = 0.5,
    U_inf: float = 1.0,
    nu: float = 1.0 / 50000,
) -> List[Tuple[float, float]]:
    """Generate a synthetic Blasius-similarity-shaped (y, u_x) profile.

    The actual Blasius f'(η) reaches u/U=0.99 at η_blasius=5, equivalent
    to y/δ_99=1. The synthetic profile here uses tanh(2.65·η) which
    crosses u/U=0.99 at η≈0.99 — close enough that δ_99 extracted from
    this profile is within ~1% of the analytical Blasius δ_99, exercising
    the extractor's ability to recover the reference under realistic
    interpolation.
    """
    delta = BLASIUS_DELTA99_PREFACTOR * math.sqrt(nu * x / U_inf)
    rows: List[Tuple[float, float]] = []
    for i in range(n_points):
        y = H * i / (n_points - 1)
        eta = min(y / delta, 1.5)  # cap at 1.5 to allow free-stream tail
        u_over_U = math.tanh(2.65 * eta)
        u_over_U = min(u_over_U, 1.0)
        rows.append((y, u_over_U * U_inf))
    return rows


# ---------------------------------------------------------------------------
# compute_blasius_invariant
# ---------------------------------------------------------------------------


class TestBlasiusInvariant:
    def test_blasius_profile_recovers_canonical_K(self):
        """Feed Cf = 0.664/√Re_x exactly → mean_K==0.664, std_K==0."""
        U, nu = 1.0, 1.0 / 50000
        cf_pairs = [(x, _blasius_cf(x, U, nu)) for x in (0.25, 0.5, 0.75, 1.0)]
        inv = compute_blasius_invariant(cf_pairs, U_inf=U, nu=nu)
        assert isinstance(inv, BlasiusInvariant)
        assert inv.mean_K == pytest.approx(BLASIUS_INVARIANT_K, abs=1e-9)
        assert inv.std_K == pytest.approx(0.0, abs=1e-9)
        assert inv.rel_spread == pytest.approx(0.0, abs=1e-9)
        assert inv.n_samples == 4
        assert inv.canonical_K == BLASIUS_INVARIANT_K

    def test_invariant_skips_x_below_x_min(self):
        """Default x_min=0.25 drops the inlet-sensitive sample."""
        U, nu = 1.0, 1.0 / 50000
        # 0.10 inside → would be included if x_min weren't applied.
        cf_pairs = [
            (0.10, _blasius_cf(0.10, U, nu) * 1.5),  # inlet drift sample
            (0.50, _blasius_cf(0.50, U, nu)),
            (1.00, _blasius_cf(1.00, U, nu)),
        ]
        inv = compute_blasius_invariant(cf_pairs, U_inf=U, nu=nu)
        assert inv.n_samples == 2  # 0.10 sample skipped
        assert inv.mean_K == pytest.approx(BLASIUS_INVARIANT_K, abs=1e-9)

    def test_invariant_x_min_override_includes_low_x(self):
        """Caller can override x_min=0 to include all samples."""
        U, nu = 1.0, 1.0 / 50000
        cf_pairs = [(x, _blasius_cf(x, U, nu)) for x in (0.05, 0.5, 1.0)]
        inv = compute_blasius_invariant(cf_pairs, U_inf=U, nu=nu, x_min=0.0)
        assert inv.n_samples == 3

    def test_invariant_rejects_empty(self):
        with pytest.raises(FlatPlateExtractorError, match="empty"):
            compute_blasius_invariant([], U_inf=1.0, nu=1e-5)

    def test_invariant_rejects_nonpositive_U_inf(self):
        with pytest.raises(FlatPlateExtractorError, match="U_inf"):
            compute_blasius_invariant(
                [(0.5, 0.004), (1.0, 0.003)], U_inf=0.0, nu=1e-5,
            )

    def test_invariant_rejects_nonpositive_nu(self):
        with pytest.raises(FlatPlateExtractorError, match="nu"):
            compute_blasius_invariant(
                [(0.5, 0.004), (1.0, 0.003)], U_inf=1.0, nu=-1.0,
            )

    def test_invariant_rejects_nonpositive_Cf(self):
        """Cf must be positive (drag, not thrust)."""
        with pytest.raises(FlatPlateExtractorError, match="Cf must be > 0"):
            compute_blasius_invariant(
                [(0.5, -0.004), (1.0, 0.003)], U_inf=1.0, nu=1e-5,
            )

    def test_invariant_rejects_nan(self):
        with pytest.raises(FlatPlateExtractorError, match="finite"):
            compute_blasius_invariant(
                [(0.5, float("nan")), (1.0, 0.003)], U_inf=1.0, nu=1e-5,
            )

    def test_invariant_rejects_too_few_samples(self):
        """Need ≥2 samples after x_min filter to compute std (n-1)."""
        with pytest.raises(FlatPlateExtractorError, match="≥2 samples"):
            compute_blasius_invariant(
                [(0.5, 0.004)], U_inf=1.0, nu=1e-5,
            )

    def test_invariant_reflects_5pct_spread(self):
        """A controlled 5% deviation in Cf yields rel_spread ≈ 0.05."""
        U, nu = 1.0, 1.0 / 50000
        # Three points with deliberate sin-shaped 5% perturbation.
        xs = [0.3, 0.6, 0.9]
        K_true = BLASIUS_INVARIANT_K
        # Perturbations summing roughly to zero around K_true so mean stays near K_true.
        K_perts = [K_true * 1.05, K_true * 1.00, K_true * 0.95]
        cf_pairs = [
            (x, K_pert / math.sqrt(U * x / nu))
            for x, K_pert in zip(xs, K_perts)
        ]
        inv = compute_blasius_invariant(cf_pairs, U_inf=U, nu=nu)
        # mean ≈ K_true; std ≈ K_true * sqrt(0.005) (sample of (.05, 0, -.05))
        # Actual std for n=3 sample from {1.05, 1.00, 0.95}:
        # mean=1.0, var = ((.05)² + 0 + (-.05)²) / 2 = 0.0025 → std=0.05.
        # rel_spread ≈ 0.05.
        assert inv.mean_K == pytest.approx(K_true, abs=1e-9)
        assert inv.rel_spread == pytest.approx(0.05, abs=1e-3)


# ---------------------------------------------------------------------------
# compute_delta_99_at_x
# ---------------------------------------------------------------------------


class TestDelta99:
    def test_synthetic_blasius_profile_recovers_within_tol(self):
        """The tanh(2.65·η) proxy is shaped so u/U=0.99 happens near
        η=1, i.e. y≈δ_99(blasius). Extracted δ_99 should match within
        ~5% of the analytical reference."""
        U, nu = 1.0, 1.0 / 50000
        for x in (0.5, 1.0):
            profile = _blasius_profile(x, n_points=200, U_inf=U, nu=nu)
            d = compute_delta_99_at_x(profile, U_inf=U, x=x, nu=nu)
            blasius = BLASIUS_DELTA99_PREFACTOR * math.sqrt(nu * x / U)
            assert d["delta_99_blasius"] == pytest.approx(blasius, rel=1e-9)
            assert abs(d["rel_error"]) < 0.05, (
                f"x={x}: δ_99={d['delta_99']}, blasius={d['delta_99_blasius']}"
            )

    def test_rejects_too_few_samples(self):
        with pytest.raises(FlatPlateExtractorError, match="≥3"):
            compute_delta_99_at_x(
                [(0.0, 0.0), (0.01, 0.5)], U_inf=1.0, x=0.5, nu=1e-5,
            )

    def test_rejects_profile_never_reaches_99pct(self):
        """Under-resolved profile capped at 0.85·U_∞ → raise, not silently 0."""
        # Profile rises smoothly to 0.85 then plateaus.
        rows = [(y, min(0.85, y * 50)) for y in [0.0, 0.005, 0.01, 0.02, 0.04, 0.08]]
        with pytest.raises(FlatPlateExtractorError, match="never reaches"):
            compute_delta_99_at_x(rows, U_inf=1.0, x=0.5, nu=1e-5)

    def test_rejects_nan_in_profile(self):
        with pytest.raises(FlatPlateExtractorError, match="finite"):
            compute_delta_99_at_x(
                [(0.0, 0.0), (0.01, float("nan")), (0.02, 0.99)],
                U_inf=1.0, x=0.5, nu=1e-5,
            )

    def test_rejects_nonpositive_U_inf(self):
        with pytest.raises(FlatPlateExtractorError, match="U_inf"):
            compute_delta_99_at_x(
                [(0.0, 0.0), (0.01, 0.5), (0.02, 0.99)],
                U_inf=-1.0, x=0.5, nu=1e-5,
            )

    def test_returns_blasius_reference(self):
        """Blasius δ_99(x) = 5·√(ν·x/U). At Re=50000, plate_length=1.0,
        U=1, ν=2e-5: δ_99(x=0.5) = 5·√(1e-5) ≈ 0.01581 m, and
        δ_99(x=1.0) = 5·√(2e-5) ≈ 0.02236 m. (V61-063 intake §1
        secondary_gates table uses these values.)"""
        U, nu = 1.0, 1.0 / 50000
        profile_05 = _blasius_profile(0.5, n_points=200, U_inf=U, nu=nu)
        d_05 = compute_delta_99_at_x(profile_05, U_inf=U, x=0.5, nu=nu)
        assert d_05["x"] == 0.5
        assert d_05["delta_99_blasius"] == pytest.approx(0.01581, abs=1e-4)
        profile_10 = _blasius_profile(1.0, n_points=200, U_inf=U, nu=nu)
        d_10 = compute_delta_99_at_x(profile_10, U_inf=U, x=1.0, nu=nu)
        assert d_10["delta_99_blasius"] == pytest.approx(0.02236, abs=1e-4)


# ---------------------------------------------------------------------------
# profile_signal_metrics
# ---------------------------------------------------------------------------


class TestProfileSignalMetrics:
    def test_blasius_profile_high_snr(self):
        """Cf at x=0.25 (0.00594) vs x=1.0 (0.00297) → ratio 2x; SNR > 1."""
        U, nu = 1.0, 1.0 / 50000
        cf_pairs = [(x, _blasius_cf(x, U, nu)) for x in (0.25, 0.5, 0.75, 1.0)]
        snr = profile_signal_metrics(cf_pairs)
        assert snr.amplitude > 0.0
        assert snr.snr_ratio > 0.5  # 0.00594-0.00297=0.00297; floor=0.00297; ratio=1.0
        assert snr.numerical_floor > 0.0

    def test_uses_max_spacing_floor(self):
        """V61-059 R2 F4: spacing floor uses MAX, not MIN, of Δx."""
        # Three samples with one wide gap and one tight gap.
        cf_pairs = [(0.10, 0.005), (0.11, 0.0049), (1.00, 0.003)]
        snr = profile_signal_metrics(cf_pairs)
        # max(0.01, 0.89) = 0.89 — the wider gap.
        assert snr.sample_spacing_floor == pytest.approx(0.89, abs=1e-9)

    def test_rejects_too_few_samples(self):
        with pytest.raises(FlatPlateExtractorError, match="≥2"):
            profile_signal_metrics([(0.5, 0.004)])

    def test_rejects_nan(self):
        with pytest.raises(FlatPlateExtractorError, match="finite"):
            profile_signal_metrics([(0.5, 0.004), (1.0, float("nan"))])

    def test_flat_profile_low_snr_ratio(self):
        """All Cf identical → amplitude=0 → snr_ratio=0 (advisory signal)."""
        cf_pairs = [(0.25, 0.005), (0.5, 0.005), (1.0, 0.005)]
        snr = profile_signal_metrics(cf_pairs)
        assert snr.amplitude == pytest.approx(0.0)
        assert snr.snr_ratio == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# canonicalize_turbulence_model
# ---------------------------------------------------------------------------


class TestCanonicalizeTurbulence:
    def test_laminar(self):
        assert canonicalize_turbulence_model("laminar") == "laminar"
        assert canonicalize_turbulence_model("Laminar") == "laminar"
        assert canonicalize_turbulence_model("LAMINAR") == "laminar"

    def test_kOmegaSST_camelcase(self):
        assert canonicalize_turbulence_model("kOmegaSST") == "kOmegaSST"

    def test_kOmegaSST_hyphenated(self):
        assert canonicalize_turbulence_model("k-omega SST") == "kOmegaSST"
        assert canonicalize_turbulence_model("k-omega-SST") == "kOmegaSST"
        assert canonicalize_turbulence_model("K-Omega-SST") == "kOmegaSST"

    def test_kOmegaSST_underscored(self):
        assert canonicalize_turbulence_model("k_omega_SST") == "kOmegaSST"

    def test_kEpsilon_variants(self):
        assert canonicalize_turbulence_model("kEpsilon") == "kEpsilon"
        assert canonicalize_turbulence_model("k-epsilon") == "kEpsilon"
        assert canonicalize_turbulence_model("K_Epsilon") == "kEpsilon"

    def test_realizable_ke_variants(self):
        assert canonicalize_turbulence_model("RealizableKE") == "RealizableKE"
        assert canonicalize_turbulence_model("Realizable-K-Epsilon") == "RealizableKE"

    def test_spalart_allmaras(self):
        assert canonicalize_turbulence_model("SpalartAllmaras") == "SpalartAllmaras"
        assert canonicalize_turbulence_model("Spalart-Allmaras") == "SpalartAllmaras"

    def test_unrecognized_returns_none(self):
        assert canonicalize_turbulence_model("LES") is None
        assert canonicalize_turbulence_model("DNS") is None
        assert canonicalize_turbulence_model("nonsense") is None

    def test_none_returns_none(self):
        assert canonicalize_turbulence_model(None) is None
        assert canonicalize_turbulence_model("") is None
        assert canonicalize_turbulence_model("   ") is None

    def test_non_string_returns_none(self):
        # Defensive: malformed task_spec passing a number shouldn't crash.
        assert canonicalize_turbulence_model(42) is None  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# enrich_cf_profile
# ---------------------------------------------------------------------------


class TestEnrichCfProfile:
    def test_full_enrichment_dict_keys(self):
        U, nu = 1.0, 1.0 / 50000
        cf_pairs = [(x, _blasius_cf(x, U, nu)) for x in (0.25, 0.5, 0.75, 1.0)]
        u_lines = {
            0.5: _blasius_profile(0.5, U_inf=U, nu=nu, n_points=200),
            1.0: _blasius_profile(1.0, U_inf=U, nu=nu, n_points=200),
        }
        out = enrich_cf_profile(cf_pairs, u_lines, U_inf=U, nu=nu)
        # Invariant block
        assert "cf_blasius_invariant_mean_K" in out
        assert "cf_blasius_invariant_std_K" in out
        assert "cf_blasius_invariant_rel_spread" in out
        assert "cf_blasius_invariant_per_x_K" in out
        assert "cf_blasius_invariant_n_samples" in out
        # SNR block
        assert "cf_profile_numerical_floor" in out
        assert "cf_profile_amplitude" in out
        assert "cf_profile_snr_ratio" in out
        assert "cf_profile_sample_spacing_floor" in out
        # δ_99 block — keys formatted with 'p' as decimal separator.
        assert "delta_99_at_x_0p5" in out
        assert "delta_99_blasius_at_x_0p5" in out
        assert "delta_99_rel_error_at_x_0p5" in out
        assert "delta_99_at_x_1" in out

    def test_blasius_invariant_recovered_through_enrich(self):
        U, nu = 1.0, 1.0 / 50000
        cf_pairs = [(x, _blasius_cf(x, U, nu)) for x in (0.25, 0.5, 0.75, 1.0)]
        out = enrich_cf_profile(cf_pairs, {}, U_inf=U, nu=nu)
        assert out["cf_blasius_invariant_mean_K"] == pytest.approx(
            BLASIUS_INVARIANT_K, abs=1e-9,
        )
        assert out["cf_blasius_invariant_rel_spread"] == pytest.approx(0.0, abs=1e-9)

    def test_propagates_errors_loudly(self):
        with pytest.raises(FlatPlateExtractorError):
            enrich_cf_profile([], {}, U_inf=1.0, nu=1e-5)
