"""DEC-V61-066 A.1: unit tests for src/duct_flow_extractors.py

Test coverage targets:
  extract_friction_factor:        7 cases
  extract_friction_velocity:      4 cases
  extract_bulk_velocity_ratio:    5 cases
  extract_log_law_residual:       9 cases (most complex, most failure modes)
  Constants & module surface:     3 cases
                                 ===
                                  28 cases total

Reference anchors used in tests (Jones 1976 + Hartnett 1962 + Pope 2000):
  - friction_factor anchor:   0.0185 at U_bulk=1, ρ=1, τ_w=0.0185/8 = 0.002313
  - friction_velocity anchor: 0.04811 at τ_w=0.002313, ρ=1
  - u_max/U_bulk anchor:      1.20 (square AR=1 duct, smooth wall)
  - log-law residual anchor:  0.0 on a perfectly-fit synthetic profile
"""

from __future__ import annotations

import math

import pytest

from src.duct_flow_extractors import (
    DuctFlowExtractorError,
    JONES_1976_F_AT_RE_50K,
    LOG_LAW_B,
    LOG_LAW_BAND_Y_PLUS_MAX,
    LOG_LAW_BAND_Y_PLUS_MIN,
    LOG_LAW_KAPPA,
    LogLawResidualResult,
    extract_bulk_velocity_ratio,
    extract_friction_factor,
    extract_friction_velocity,
    extract_log_law_residual,
)


# ============================================================================
# Module-surface tests
# ============================================================================

class TestModuleSurface:
    def test_constants_match_textbook_values(self):
        # Pope 2000 Ch. 7 / Schlichting Ch. 18
        assert LOG_LAW_KAPPA == pytest.approx(0.41)
        assert LOG_LAW_B == pytest.approx(5.0)
        # Default fit band — buffer-layer transition + before wake
        assert LOG_LAW_BAND_Y_PLUS_MIN == 30.0
        assert LOG_LAW_BAND_Y_PLUS_MAX == 200.0

    def test_jones_anchor_matches_gold_yaml(self):
        # ref_value in knowledge/gold_standards/duct_flow.yaml
        assert JONES_1976_F_AT_RE_50K == pytest.approx(0.0185)

    def test_error_class_inherits_value_error(self):
        # Caller code that catches ValueError to fold into audit keys
        # must keep working without a new except clause.
        assert issubclass(DuctFlowExtractorError, ValueError)


# ============================================================================
# extract_friction_factor
# ============================================================================

class TestFrictionFactor:
    def test_jones_anchor_round_trips(self):
        """Jones 1976 anchor: f=0.0185 ⇒ τ_w = ρ·U²·f/8 = 0.0185/8 = 0.0023125"""
        tau_w = JONES_1976_F_AT_RE_50K / 8.0  # ρ=1, U=1
        f = extract_friction_factor(tau_w, U_bulk=1.0, rho=1.0)
        assert f == pytest.approx(JONES_1976_F_AT_RE_50K, rel=1e-12)

    def test_default_rho_is_one(self):
        f1 = extract_friction_factor(0.001, U_bulk=1.0)
        f2 = extract_friction_factor(0.001, U_bulk=1.0, rho=1.0)
        assert f1 == f2

    def test_rho_scales_inversely(self):
        f_rho_1 = extract_friction_factor(0.001, U_bulk=1.0, rho=1.0)
        f_rho_2 = extract_friction_factor(0.001, U_bulk=1.0, rho=2.0)
        assert f_rho_2 == pytest.approx(f_rho_1 / 2.0)

    def test_U_bulk_scales_inversely_squared(self):
        f_U_1 = extract_friction_factor(0.001, U_bulk=1.0, rho=1.0)
        f_U_2 = extract_friction_factor(0.001, U_bulk=2.0, rho=1.0)
        assert f_U_2 == pytest.approx(f_U_1 / 4.0)

    def test_rejects_zero_tau(self):
        with pytest.raises(DuctFlowExtractorError, match="tau_w must be > 0"):
            extract_friction_factor(0.0, U_bulk=1.0)

    def test_rejects_negative_U_bulk(self):
        with pytest.raises(DuctFlowExtractorError, match="U_bulk must be > 0"):
            extract_friction_factor(0.001, U_bulk=-1.0)

    def test_rejects_nan(self):
        with pytest.raises(DuctFlowExtractorError, match="must be finite"):
            extract_friction_factor(math.nan, U_bulk=1.0)


# ============================================================================
# extract_friction_velocity
# ============================================================================

class TestFrictionVelocity:
    def test_jones_anchor_round_trips(self):
        """For Jones at U_bulk=1: u_τ = √(τ_w/ρ) = √(0.0185/8/1) = 0.04811"""
        tau_w = JONES_1976_F_AT_RE_50K / 8.0
        u_tau = extract_friction_velocity(tau_w, rho=1.0)
        # Jones u_τ at Re=50000, U_bulk=1
        assert u_tau == pytest.approx(0.04811, rel=1e-3)

    def test_consistency_with_friction_factor(self):
        """SAME_RUN_CROSS_CHECK: u_τ / U_bulk must equal √(f/8) by algebra.
        This test pins the algebraic identity, NOT the gate verdict —
        the gate is intentionally independent (extractor uses τ_w directly,
        not the just-extracted f).
        """
        tau_w = 0.005
        U_bulk = 1.0
        rho = 1.0
        f = extract_friction_factor(tau_w, U_bulk=U_bulk, rho=rho)
        u_tau = extract_friction_velocity(tau_w, rho=rho)
        # Algebraic identity: u_τ / U_bulk = √(f/8)
        assert u_tau / U_bulk == pytest.approx(math.sqrt(f / 8.0), rel=1e-12)

    def test_rho_scales_inversely_sqrt(self):
        u1 = extract_friction_velocity(0.001, rho=1.0)
        u2 = extract_friction_velocity(0.001, rho=4.0)
        # u_τ ∝ 1/√ρ
        assert u2 == pytest.approx(u1 / 2.0)

    def test_rejects_zero_tau(self):
        with pytest.raises(DuctFlowExtractorError, match="tau_w must be > 0"):
            extract_friction_velocity(0.0)


# ============================================================================
# extract_bulk_velocity_ratio
# ============================================================================

class TestBulkVelocityRatio:
    def test_hartnett_anchor(self):
        """AR=1 smooth duct turbulent: u_max/U_bulk ≈ 1.20"""
        ratio = extract_bulk_velocity_ratio(u_centroid=1.20, U_bulk=1.0)
        assert ratio == pytest.approx(1.20, rel=1e-12)

    def test_unit_ratio(self):
        # Plug flow (degenerate): u_centroid == U_bulk → ratio = 1.0
        assert extract_bulk_velocity_ratio(1.0, 1.0) == pytest.approx(1.0)

    def test_scales_with_U_bulk(self):
        r1 = extract_bulk_velocity_ratio(2.4, 2.0)
        # u_max/U_bulk = 1.2 at any scale
        assert r1 == pytest.approx(1.2)

    def test_rejects_zero_centroid(self):
        with pytest.raises(DuctFlowExtractorError, match="u_centroid must be > 0"):
            extract_bulk_velocity_ratio(0.0, U_bulk=1.0)

    def test_rejects_inf(self):
        with pytest.raises(DuctFlowExtractorError, match="must be finite"):
            extract_bulk_velocity_ratio(math.inf, U_bulk=1.0)


# ============================================================================
# extract_log_law_residual
# ============================================================================

def _log_law_perfect_profile(
    u_tau: float, nu: float, kappa: float = 0.41, B: float = 5.0,
    y_plus_grid: tuple[float, ...] = (40.0, 60.0, 100.0, 150.0),
) -> list[tuple[float, float]]:
    """Build a (y, u_x) profile that EXACTLY satisfies u+ = (1/κ)·ln(y+) + B.

    Used to construct the residual-=-0 test case. y = y+ · ν / u_τ;
    u_x = u_τ · ((1/κ)·ln(y+) + B).
    """
    pts: list[tuple[float, float]] = [(0.0, 0.0)]  # wall sample, will be skipped
    for y_plus in y_plus_grid:
        y = y_plus * nu / u_tau
        u_plus = (1.0 / kappa) * math.log(y_plus) + B
        u = u_plus * u_tau
        pts.append((y, u))
    return pts


class TestLogLawResidual:
    def test_perfect_profile_returns_zero_residual(self):
        u_tau = 0.05
        nu = 1.0 / 50000  # Re=50000 normalized
        u_line = _log_law_perfect_profile(u_tau, nu)
        result = extract_log_law_residual(u_line, u_tau=u_tau, nu=nu)
        assert isinstance(result, LogLawResidualResult)
        assert result.mean_residual == pytest.approx(0.0, abs=1e-12)
        assert result.n_points_in_band == 4  # all 4 in [30, 200]
        assert result.kappa == pytest.approx(LOG_LAW_KAPPA)
        assert result.B == pytest.approx(LOG_LAW_B)

    def test_skips_wall_sample(self):
        """y=0 sample must be silently skipped (log-law undefined at y+=0)."""
        u_tau = 0.05
        nu = 1.0 / 50000
        u_line = _log_law_perfect_profile(u_tau, nu)
        # First entry is the wall (0.0, 0.0). Result already verified perfect.
        # Drop it explicitly and confirm same residual.
        result_no_wall = extract_log_law_residual(u_line[1:], u_tau=u_tau, nu=nu)
        assert result_no_wall.n_points_in_band == 4
        assert result_no_wall.mean_residual == pytest.approx(0.0, abs=1e-12)

    def test_filters_outside_band(self):
        u_tau = 0.05
        nu = 1.0 / 50000
        # y+ values: 5 (buffer), 50 (in band), 150 (in band), 500 (above)
        u_line = _log_law_perfect_profile(
            u_tau, nu, y_plus_grid=(5.0, 50.0, 150.0, 500.0),
        )
        result = extract_log_law_residual(u_line, u_tau=u_tau, nu=nu)
        # Only y+=50 and 150 are in [30, 200]
        assert result.n_points_in_band == 2

    def test_offset_profile_yields_offset_residual(self):
        """A profile shifted by Δu+ in u should give residual ≈ Δu+."""
        u_tau = 0.05
        nu = 1.0 / 50000
        delta = 0.3  # offset in u+ units
        # Build perfect profile then shift each non-wall u by delta·u_τ
        base = _log_law_perfect_profile(u_tau, nu)
        u_line = [(y, u + (delta * u_tau if y > 0 else 0.0)) for y, u in base]
        result = extract_log_law_residual(u_line, u_tau=u_tau, nu=nu)
        # |Δu+| residual should equal delta
        assert result.mean_residual == pytest.approx(delta, rel=1e-9)

    def test_rejects_empty_profile(self):
        with pytest.raises(DuctFlowExtractorError, match="empty"):
            extract_log_law_residual([], u_tau=0.05, nu=1.0 / 50000)

    def test_rejects_no_samples_in_band(self):
        u_tau = 0.05
        nu = 1.0 / 50000
        # All in buffer-layer (y+ < 30) — none qualify
        u_line = _log_law_perfect_profile(
            u_tau, nu, y_plus_grid=(5.0, 10.0, 20.0),
        )
        with pytest.raises(DuctFlowExtractorError, match="need ≥2 samples"):
            extract_log_law_residual(u_line, u_tau=u_tau, nu=nu)

    def test_rejects_bad_band(self):
        with pytest.raises(DuctFlowExtractorError, match="must be > y_plus_min"):
            extract_log_law_residual(
                [(1.0, 1.0), (2.0, 2.0)],
                u_tau=0.05, nu=1.0 / 50000,
                y_plus_min=200.0, y_plus_max=30.0,  # inverted
            )

    def test_rejects_nan_in_line(self):
        with pytest.raises(DuctFlowExtractorError, match="must be finite"):
            extract_log_law_residual(
                [(1.0, math.nan)],
                u_tau=0.05, nu=1.0 / 50000,
            )

    def test_custom_kappa_and_B_propagate_through_result(self):
        u_tau = 0.05
        nu = 1.0 / 50000
        # Build profile against custom (κ, B) and ensure residual stays 0
        u_line = _log_law_perfect_profile(u_tau, nu, kappa=0.40, B=5.5)
        result = extract_log_law_residual(
            u_line, u_tau=u_tau, nu=nu, kappa=0.40, B=5.5,
        )
        assert result.kappa == pytest.approx(0.40)
        assert result.B == pytest.approx(5.5)
        assert result.mean_residual == pytest.approx(0.0, abs=1e-12)
