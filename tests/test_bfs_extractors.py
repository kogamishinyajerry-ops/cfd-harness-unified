"""Unit tests for src.bfs_extractors (DEC-V61-067 A.1).

Tests cover the 3 public extractors:
  - extract_pressure_recovery
  - extract_velocity_profile_at_x
  - extract_cd_mean

plus the shared BfsExtractorError validation surface.

V61-066 testing patterns mirrored:
  - one TestModuleSurface class for constants + error class shape
  - one Test{Function} class per public function with ~6-8 cases
  - inputs include both anchor-perfect data + degenerate-input rejection
"""

from __future__ import annotations

import math

import pytest

from src.bfs_extractors import (
    BfsExtractorError,
    DRIVER_SEEGMILLER_1985_XR_OVER_H_AT_RE_37500,
    LE_MOIN_KIM_1997_CP_DELTA,
    LE_MOIN_KIM_1997_CP_INLET,
    LE_MOIN_KIM_1997_CP_OUTLET,
    LE_MOIN_KIM_1997_XR_OVER_H_AT_RE_5100,
    extract_cd_mean,
    extract_pressure_recovery,
    extract_velocity_profile_at_x,
)


class TestModuleSurface:
    def test_constants_pinned(self):
        assert LE_MOIN_KIM_1997_XR_OVER_H_AT_RE_5100 == pytest.approx(6.28)
        assert DRIVER_SEEGMILLER_1985_XR_OVER_H_AT_RE_37500 == pytest.approx(6.26)
        assert LE_MOIN_KIM_1997_CP_INLET == pytest.approx(-0.90)
        assert LE_MOIN_KIM_1997_CP_OUTLET == pytest.approx(0.10)
        assert LE_MOIN_KIM_1997_CP_DELTA == pytest.approx(1.00)

    def test_error_inherits_value_error(self):
        """Existing code that catches ValueError keeps working."""
        assert issubclass(BfsExtractorError, ValueError)


class TestPressureRecovery:
    def test_le_moin_kim_anchor_round_trip(self):
        """Synthetic p_inlet=-0.45, p_outlet=+0.05, U_bulk=1, ρ=1, p_ref=0
        yields Cp_inlet=-0.9, Cp_outlet=0.10, delta=1.00 (Le/Moin/Kim 1997)."""
        result = extract_pressure_recovery(
            p_inlet=-0.45, p_outlet=0.05,
            U_bulk=1.0, rho=1.0, p_ref=0.0,
        )
        assert result["inlet"] == pytest.approx(LE_MOIN_KIM_1997_CP_INLET, rel=1e-9)
        assert result["outlet"] == pytest.approx(LE_MOIN_KIM_1997_CP_OUTLET, rel=1e-9)
        assert result["delta"] == pytest.approx(LE_MOIN_KIM_1997_CP_DELTA, rel=1e-9)

    def test_default_rho_is_one(self):
        """rho default = 1 matches the normalized adapter run convention."""
        result = extract_pressure_recovery(
            p_inlet=-0.45, p_outlet=0.05, U_bulk=1.0,
        )
        assert result["delta"] == pytest.approx(1.00)

    def test_p_ref_shifts_both_cp_equally(self):
        """Changing p_ref shifts Cp_inlet and Cp_outlet by the same amount;
        delta is invariant."""
        r1 = extract_pressure_recovery(
            p_inlet=-0.45, p_outlet=0.05, U_bulk=1.0, p_ref=0.0,
        )
        r2 = extract_pressure_recovery(
            p_inlet=-0.45, p_outlet=0.05, U_bulk=1.0, p_ref=0.05,
        )
        assert r1["delta"] == pytest.approx(r2["delta"], rel=1e-9)
        assert r1["inlet"] - r2["inlet"] == pytest.approx(
            r1["outlet"] - r2["outlet"], rel=1e-9
        )

    def test_u_bulk_squared_normalization(self):
        """Cp ∝ 1 / U_bulk² — doubling U_bulk quarters the Cp magnitude."""
        r1 = extract_pressure_recovery(p_inlet=-0.45, p_outlet=0.05, U_bulk=1.0)
        r2 = extract_pressure_recovery(p_inlet=-0.45, p_outlet=0.05, U_bulk=2.0)
        assert r2["delta"] == pytest.approx(r1["delta"] / 4.0, rel=1e-9)

    def test_rejects_zero_u_bulk(self):
        with pytest.raises(BfsExtractorError, match="U_bulk"):
            extract_pressure_recovery(p_inlet=-0.45, p_outlet=0.05, U_bulk=0.0)

    def test_rejects_negative_rho(self):
        with pytest.raises(BfsExtractorError, match="rho"):
            extract_pressure_recovery(
                p_inlet=-0.45, p_outlet=0.05, U_bulk=1.0, rho=-1.0,
            )

    def test_rejects_nan_p_inlet(self):
        with pytest.raises(BfsExtractorError, match="p_inlet"):
            extract_pressure_recovery(
                p_inlet=float("nan"), p_outlet=0.05, U_bulk=1.0,
            )

    def test_rejects_inf_p_outlet(self):
        with pytest.raises(BfsExtractorError, match="p_outlet"):
            extract_pressure_recovery(
                p_inlet=-0.45, p_outlet=float("inf"), U_bulk=1.0,
            )


class TestVelocityProfileAtX:
    def _build_le_moin_kim_synthetic(self):
        """Build a single x=6.0 column of cells matching Le/Moin/Kim 1997
        anchor at x/H=6.0: y/H ∈ {0.5, 1.0, 2.0} → u/U_bulk ∈ {0.40, 0.85, 1.05}."""
        cells = []
        # x=6.0 column with 4 y-cells
        for y, u in [(0.5, 0.40), (1.0, 0.85), (2.0, 1.05), (3.0, 1.08)]:
            cells.append((6.0, y, u))
        # Decoy x=5.0 column to verify x-snap picks 6.0
        for y, u in [(0.5, 0.30), (1.0, 0.70), (2.0, 0.95)]:
            cells.append((5.0, y, u))
        # Decoy x=7.0 column
        for y, u in [(0.5, 0.55), (1.0, 0.90), (2.0, 1.08)]:
            cells.append((7.0, y, u))
        return cells

    def test_le_moin_kim_anchor_round_trip(self):
        cells = self._build_le_moin_kim_synthetic()
        result = extract_velocity_profile_at_x(
            cells=cells,
            x_target_physical=6.0,
            y_targets_physical=[0.5, 1.0, 2.0],
            U_bulk=1.0,
            step_height=1.0,
        )
        assert len(result) == 3
        assert result[0]["x_H"] == pytest.approx(6.0)
        assert result[0]["y_H"] == pytest.approx(0.5)
        assert result[0]["u_Ubulk"] == pytest.approx(0.40)
        assert result[1]["y_H"] == pytest.approx(1.0)
        assert result[1]["u_Ubulk"] == pytest.approx(0.85)
        assert result[2]["y_H"] == pytest.approx(2.0)
        assert result[2]["u_Ubulk"] == pytest.approx(1.05)

    def test_x_snap_picks_nearest_unique_column(self):
        """When x_target sits between two columns, the snap picks the
        single nearest column (V61-066 post-R3 #1 lesson)."""
        cells = self._build_le_moin_kim_synthetic()
        # x_target = 6.4 sits between 6.0 and 7.0; nearest is 6.0 (Δ=0.4)
        # vs 7.0 (Δ=0.6).
        result = extract_velocity_profile_at_x(
            cells=cells,
            x_target_physical=6.4,
            y_targets_physical=[0.5],
            U_bulk=1.0,
        )
        assert result[0]["x_H"] == pytest.approx(6.0)
        # Picks u from the 6.0 column, NOT the 7.0 column.
        assert result[0]["u_Ubulk"] == pytest.approx(0.40)

    def test_explicit_x_tol_band_filter(self):
        """When x_tol > 0, picks all cells within the band (legacy compat)."""
        cells = self._build_le_moin_kim_synthetic()
        result = extract_velocity_profile_at_x(
            cells=cells,
            x_target_physical=6.0,
            y_targets_physical=[0.5],
            U_bulk=1.0,
            x_tol=0.5,
        )
        # x_tol=0.5 includes only x=6.0 (|6.0-6.0|=0 ≤ 0.5);
        # x=5.0 is excluded (|5.0-6.0|=1.0 > 0.5).
        assert result[0]["u_Ubulk"] == pytest.approx(0.40)

    def test_step_height_normalizes_x_y(self):
        """With step_height=2, physical x=12 maps to x_H=6.0."""
        cells = [(12.0, 1.0, 0.85)]  # physical x=12, y=1
        result = extract_velocity_profile_at_x(
            cells=cells,
            x_target_physical=12.0,
            y_targets_physical=[1.0],
            U_bulk=1.0,
            step_height=2.0,
        )
        assert result[0]["x_H"] == pytest.approx(6.0)
        assert result[0]["y_H"] == pytest.approx(0.5)

    def test_picks_nearest_y_when_no_exact_match(self):
        """y_target=1.5 with cells at y={0.5, 1.0, 2.0} picks y=1.0
        (Δ=0.5 < Δ=0.5 → tie-break by sort order)."""
        cells = [
            (6.0, 0.5, 0.40),
            (6.0, 1.0, 0.85),
            (6.0, 2.0, 1.05),
        ]
        result = extract_velocity_profile_at_x(
            cells=cells,
            x_target_physical=6.0,
            y_targets_physical=[1.5],
            U_bulk=1.0,
        )
        # min(|0.5-1.5|, |1.0-1.5|, |2.0-1.5|) = 0.5; ties between 1.0 and 2.0;
        # min() with key picks first-encountered → 1.0 (insertion order).
        assert result[0]["y_H"] == pytest.approx(1.0)
        assert result[0]["u_Ubulk"] == pytest.approx(0.85)

    def test_rejects_empty_cells(self):
        with pytest.raises(BfsExtractorError, match="cells is empty"):
            extract_velocity_profile_at_x(
                cells=[], x_target_physical=6.0,
                y_targets_physical=[0.5], U_bulk=1.0,
            )

    def test_rejects_empty_y_targets(self):
        with pytest.raises(BfsExtractorError, match="y_targets_physical"):
            extract_velocity_profile_at_x(
                cells=[(6.0, 0.5, 0.40)],
                x_target_physical=6.0,
                y_targets_physical=[], U_bulk=1.0,
            )

    def test_rejects_zero_u_bulk(self):
        with pytest.raises(BfsExtractorError, match="U_bulk"):
            extract_velocity_profile_at_x(
                cells=[(6.0, 0.5, 0.40)],
                x_target_physical=6.0,
                y_targets_physical=[0.5], U_bulk=0.0,
            )

    def test_rejects_zero_step_height(self):
        with pytest.raises(BfsExtractorError, match="step_height"):
            extract_velocity_profile_at_x(
                cells=[(6.0, 0.5, 0.40)],
                x_target_physical=6.0,
                y_targets_physical=[0.5], U_bulk=1.0,
                step_height=0.0,
            )

    def test_explicit_x_tol_zero_match(self):
        """x_tol > 0 but no cells in band raises."""
        cells = [(6.0, 0.5, 0.40)]
        with pytest.raises(BfsExtractorError, match="no cells found"):
            extract_velocity_profile_at_x(
                cells=cells,
                x_target_physical=20.0,
                y_targets_physical=[0.5],
                U_bulk=1.0,
                x_tol=0.1,
            )


class TestCdMean:
    def test_uniform_tau_x_round_trip(self):
        """Uniform |τ_x| = 0.005 over 5 face samples → cd_mean = 0.005/0.5 = 0.01
        with U_bulk=1, ρ=1."""
        data = [(1.0, 0.005), (2.0, 0.005), (3.0, 0.005), (4.0, 0.005), (5.0, 0.005)]
        cd = extract_cd_mean(data, U_bulk=1.0, rho=1.0)
        assert cd == pytest.approx(0.01, rel=1e-9)

    def test_takes_absolute_value(self):
        """Mixed positive + negative τ_x (recirculation + recovery) — cd_mean
        uses |·| so reverse-flow doesn't cancel forward-flow."""
        data = [(1.0, -0.005), (2.0, 0.005)]  # mean(τ_x)=0 but mean(|τ_x|)=0.005
        cd = extract_cd_mean(data, U_bulk=1.0, rho=1.0)
        assert cd == pytest.approx(0.01, rel=1e-9)

    def test_u_bulk_squared_normalization(self):
        """cd_mean ∝ 1 / U_bulk² — doubling U_bulk quarters cd."""
        data = [(1.0, 0.005), (2.0, 0.005)]
        cd1 = extract_cd_mean(data, U_bulk=1.0)
        cd2 = extract_cd_mean(data, U_bulk=2.0)
        assert cd2 == pytest.approx(cd1 / 4.0, rel=1e-9)

    def test_rho_inverse_normalization(self):
        """cd_mean ∝ 1 / ρ — doubling ρ halves cd."""
        data = [(1.0, 0.005)]
        cd1 = extract_cd_mean(data, U_bulk=1.0, rho=1.0)
        cd2 = extract_cd_mean(data, U_bulk=1.0, rho=2.0)
        assert cd2 == pytest.approx(cd1 / 2.0, rel=1e-9)

    def test_rejects_empty_data(self):
        with pytest.raises(BfsExtractorError, match="empty"):
            extract_cd_mean([], U_bulk=1.0)

    def test_rejects_nan_tau(self):
        data = [(1.0, float("nan"))]
        with pytest.raises(BfsExtractorError, match="tau_x"):
            extract_cd_mean(data, U_bulk=1.0)

    def test_rejects_inf_x(self):
        data = [(float("inf"), 0.005)]
        with pytest.raises(BfsExtractorError, match="x_floor"):
            extract_cd_mean(data, U_bulk=1.0)

    def test_rejects_zero_u_bulk(self):
        data = [(1.0, 0.005)]
        with pytest.raises(BfsExtractorError, match="U_bulk"):
            extract_cd_mean(data, U_bulk=0.0)

    def test_rejects_malformed_entry(self):
        """Each entry must be a 2-tuple."""
        with pytest.raises(BfsExtractorError, match="2-tuples|tuples"):
            extract_cd_mean([(1.0, 0.005, 999.0)], U_bulk=1.0)
