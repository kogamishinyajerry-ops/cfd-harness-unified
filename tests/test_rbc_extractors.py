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
    """Canonical RBC boundary metadata (Pandey & Schumacher AR=4 setup).

    DEC-V61-060 R3 F2-MED: g and beta are now REQUIRED on RBCBoundary
    (no defaults — Stage C must plumb case-derived physics or the
    extractors fail-closed). The helper supplies the canonical Pr=10
    AR=4 Ra=1e6 values so tests stay readable.
    """
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
        g=3.0e-4,              # canonical AR=4 Pr=10 Ra=1e6 per Codex R2 probe
        beta=1.0 / 300.0,      # Boussinesq, T_mean ≈ 300 K
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


from src.rbc_extractors import extract_w_max


def _two_roll_velocity_field(nx: int = 16, ny: int = 16) -> RBCFieldSlice:
    """Synthetic 2-roll u_y(x,y) = U_pk · cos(2πx/Lx) · sin(πy/Ly).

    Mirrors Pandey & Schumacher Fig 4b: hot plumes rising at sidewalls
    (u_y > 0 near x=0 and x=Lx), descending plume at center (u_y < 0
    near x=Lx/2). Sign changes at x=Lx/4 (+ → −) and x=3Lx/4 (− → +)
    → 2 sign changes → 2 rolls.
    """
    cxs: list[float] = []
    cys: list[float] = []
    t_vals: list[float] = []
    u_vecs: list[tuple[float, float, float]] = []
    Lx, Ly = 4.0, 1.0
    U_pk = 0.005
    dx = Lx / nx
    dy = Ly / ny
    for i in range(nx):
        x = (i + 0.5) * dx
        for j in range(ny):
            y = (j + 0.5) * dy
            cxs.append(x)
            cys.append(y)
            t_vals.append(305.0 - 10.0 * y)
            uy = U_pk * math.cos(2 * math.pi * x / Lx) * math.sin(math.pi * y / Ly)
            u_vecs.append((0.0, uy, 0.0))
    return RBCFieldSlice(cxs=cxs, cys=cys, t_vals=t_vals, u_vecs=u_vecs)


class TestExtractWMaxB2:
    """DEC-V61-060 Stage B.2 unit tests for extract_w_max."""

    def test_two_roll_field_returns_positive_w_max(self):
        slice_ = _two_roll_velocity_field()
        bc = _make_bc()
        out = extract_w_max(slice_, bc)
        assert out, f"Two-roll field returned empty dict: {out}"
        assert out["status"] == "ok"
        # raw peak ≈ U_pk = 0.005 (after wall trim), should be close
        assert out["raw_w_max"] == pytest.approx(0.005, rel=0.15), (
            f"Peak should be ~0.005 m/s; got {out['raw_w_max']}"
        )
        # Nondim by U_ff = sqrt(g·β·dT·H) with defaults g=3e-4 β=1/300
        # → U_ff = sqrt(3e-4 / 300 * 10 * 1) = sqrt(1e-5) ≈ 0.00316
        # → w_max_nondim ≈ 0.005 / 0.00316 ≈ 1.58
        assert out["value"] > 1.0, f"Nondim w_max should be O(1); got {out['value']}"
        assert "U_ff" in out and out["U_ff"] > 0
        assert out["interior_cell_count"] > 0

    def test_no_velocity_field_returns_empty_dict(self):
        slice_ = RBCFieldSlice(cxs=[0.5], cys=[0.5], t_vals=[300.0], u_vecs=None)
        bc = _make_bc()
        out = extract_w_max(slice_, bc)
        assert out == {}, f"Missing u_vecs must return {{}}; got {out}"

    def test_zero_buoyancy_returns_empty_dict(self):
        """Degenerate U_ff=0 → fail closed."""
        slice_ = _two_roll_velocity_field()
        bc = _make_bc(g=0.0)
        out = extract_w_max(slice_, bc)
        assert out == {}, f"Zero gravity (U_ff=0) must return {{}}; got {out}"

    def test_wall_layer_excluded_from_max(self):
        """The trim must exclude wall-layer cells (where no-slip would
        give u_y=0). Build a field where ONLY wall cells have nonzero u_y;
        the extractor must NOT pick them up."""
        cxs: list[float] = []
        cys: list[float] = []
        t_vals: list[float] = []
        u_vecs: list[tuple[float, float, float]] = []
        # Cells inside the trim zone (within H/20 = 0.05 of walls):
        # y=0.025, y=0.975 → trim threshold y_lo=0.05, y_hi=0.95
        for x in (1.0, 2.0, 3.0):
            for y in (0.025, 0.975):
                cxs.append(x)
                cys.append(y)
                t_vals.append(300.0)
                u_vecs.append((0.0, 99.0, 0.0))  # huge u_y in wall layer
            # Interior cells with small u_y
            for y in (0.5, 0.6):
                cxs.append(x)
                cys.append(y)
                t_vals.append(300.0)
                u_vecs.append((0.0, 0.001, 0.0))
        slice_ = RBCFieldSlice(cxs=cxs, cys=cys, t_vals=t_vals, u_vecs=u_vecs)
        bc = _make_bc()
        out = extract_w_max(slice_, bc)
        assert out, f"Should produce a result; got {out}"
        # Must NOT have picked up the 99.0 wall-layer noise
        assert out["raw_w_max"] == pytest.approx(0.001, abs=1e-9), (
            f"Wall layer trim failed: raw_w_max={out['raw_w_max']} (expected 0.001)"
        )


from src.rbc_extractors import extract_roll_count_x


class TestExtractRollCountB3:
    """DEC-V61-060 Stage B.3 unit tests for extract_roll_count_x."""

    def test_two_roll_field_returns_2(self):
        """Canonical 2-roll u_y(x) ≈ U_pk·sin(2πx/Lx)·sin(πy/Ly) at
        y=H/2: positive near x=Lx/4, negative at x=Lx/2 (descending plume),
        positive near x=3Lx/4 → 2 sign changes → 2 rolls."""
        slice_ = _two_roll_velocity_field(nx=32, ny=32)
        bc = _make_bc()
        out = extract_roll_count_x(slice_, bc)
        assert out, f"Two-roll field returned empty dict: {out}"
        assert out["status"] == "ok"
        assert out["value"] == 2, (
            f"Two-roll field must give roll_count=2; got {out['value']} "
            f"(sign_changes={out.get('sign_changes')})"
        )
        assert out["sign_changes"] == 2
        assert out["y_layer_used"] == pytest.approx(0.5, abs=0.05)

    def test_no_velocity_field_returns_empty_dict(self):
        slice_ = RBCFieldSlice(cxs=[0.5], cys=[0.5], t_vals=[300.0], u_vecs=None)
        bc = _make_bc()
        out = extract_roll_count_x(slice_, bc)
        assert out == {}, f"Missing u_vecs must return {{}}; got {out}"

    def test_single_roll_field_returns_1(self):
        """Single-cell roll: u_y(x) = U_pk·sin(πx/Lx) at y=H/2 — positive
        across the full interior → 0 sign changes → roll_count = 1."""
        nx, ny = 32, 32
        Lx, Ly = 4.0, 1.0
        U_pk = 0.005
        cxs, cys, t_vals, u_vecs = [], [], [], []
        for i in range(nx):
            x = (i + 0.5) * Lx / nx
            for j in range(ny):
                y = (j + 0.5) * Ly / ny
                cxs.append(x); cys.append(y); t_vals.append(300.0)
                uy = U_pk * math.sin(math.pi * x / Lx) * math.sin(math.pi * y / Ly)
                u_vecs.append((0.0, uy, 0.0))
        slice_ = RBCFieldSlice(cxs=cxs, cys=cys, t_vals=t_vals, u_vecs=u_vecs)
        bc = _make_bc()
        out = extract_roll_count_x(slice_, bc)
        assert out["value"] == 1, (
            f"Single-roll field must give roll_count=1; got {out['value']} "
            f"(sign_changes={out['sign_changes']})"
        )

    def test_side_wall_noise_rejected(self):
        """Add huge noise spike at x=0.05·Lx (within side trim zone);
        extractor must NOT count it as a roll boundary."""
        slice_clean = _two_roll_velocity_field(nx=32, ny=32)
        cxs = list(slice_clean.cxs)
        cys = list(slice_clean.cys)
        t_vals = list(slice_clean.t_vals)
        u_vecs = list(slice_clean.u_vecs)
        # Inject 4 noise spikes within side-wall trim zone (5% of Lx=4 = 0.2)
        for _ in range(4):
            cxs.append(0.1)        # within 0.2 trim
            cys.append(0.5)
            t_vals.append(300.0)
            u_vecs.append((0.0, 999.0, 0.0))
        slice_ = RBCFieldSlice(cxs=cxs, cys=cys, t_vals=t_vals, u_vecs=u_vecs)
        bc = _make_bc()
        out = extract_roll_count_x(slice_, bc)
        # Should still report 2 rolls (noise spikes trimmed)
        assert out["value"] == 2, (
            f"Side-wall trim failed: roll_count={out['value']}, "
            f"sign_changes={out['sign_changes']}"
        )


# ============================================================================
# Stage B-final · Integration tests (all 3 extractors on shared field)
# ============================================================================

class TestStageBFinalIntegration:
    """DEC-V61-060 Stage B-final: integration sweep asserting all 3
    extractors operate coherently on a shared canonical RBC field.
    
    Per intake §7 Batch B atomicity_guard, this is the closing commit
    of Stage B before Codex R3 review.
    """

    def test_canonical_two_roll_field_yields_consistent_observables(self):
        """A single synthetic 2-roll RBC field must produce:
          - nu_asymmetry value ≈ 0 (linear T → conduction baseline,
            both walls give Nu ≈ 1 → asymmetry ≈ 0; passes 5% gate)
          - w_max_nondim positive O(1)
          - roll_count = 2 (canonical 2-roll pattern)
        """
        slice_ = _two_roll_velocity_field(nx=32, ny=32)
        bc = _make_bc()
        nu_out = extract_nu_asymmetry(slice_, bc)
        wmax_out = extract_w_max(slice_, bc)
        rc_out = extract_roll_count_x(slice_, bc)

        # All three extractors must succeed
        assert nu_out and wmax_out and rc_out, (
            f"Extractor failure — nu={nu_out}, w_max={wmax_out}, rc={rc_out}"
        )
        # nu_asymmetry within gate threshold (5%)
        assert nu_out["value"] < 0.05, (
            f"Conservation invariant violated: asymmetry={nu_out['value']}"
        )
        # w_max nondim positive (PROVISIONAL_ADVISORY — value reasonable)
        assert wmax_out["value"] > 0
        # roll count = 2 (PROVISIONAL_ADVISORY — matches benchmark)
        assert rc_out["value"] == 2

    def test_unbalanced_field_fails_only_invariant(self):
        """When the temperature field is asymmetric (BL underresolved at
        top), the conservation invariant FAILs but other extractors are
        unaffected (different physics).
        
        Demonstrates that the NON_TYPE_HARD_INVARIANT fires correctly
        without contaminating PROVISIONAL_ADVISORY observables.
        """
        # Combine convective T (asymmetric) with 2-roll u_y
        nx, ny = 16, 16
        Lx, Ly, U_pk = 4.0, 1.0, 0.005
        cxs, cys, t_vals, u_vecs = [], [], [], []
        for i in range(nx):
            x = (i + 0.5) * Lx / nx
            for j in range(ny):
                y = (j + 0.5) * Ly / ny
                cxs.append(x); cys.append(y)
                t_vals.append(305.0 - 10.0 * (2 * y - y * y))  # asymmetric BL
                u_vecs.append((
                    0.0,
                    U_pk * math.cos(2 * math.pi * x / Lx) * math.sin(math.pi * y / Ly),
                    0.0,
                ))
        slice_ = RBCFieldSlice(cxs=cxs, cys=cys, t_vals=t_vals, u_vecs=u_vecs)
        bc = _make_bc()
        nu_out = extract_nu_asymmetry(slice_, bc)
        wmax_out = extract_w_max(slice_, bc)
        rc_out = extract_roll_count_x(slice_, bc)
        # Invariant FAILs (asymmetry > 5%)
        assert nu_out["value"] > 0.05
        # But other observables are uncontaminated
        assert wmax_out["value"] > 0
        assert rc_out["value"] == 2

    def test_extractor_output_keys_compatible_with_comparator(self):
        """All three extractors emit a 'value' field — the comparator
        consumes this uniform key. Other fields are diagnostic."""
        slice_ = _two_roll_velocity_field()
        bc = _make_bc()
        for fn in (extract_nu_asymmetry, extract_w_max, extract_roll_count_x):
            out = fn(slice_, bc)
            assert "value" in out, (
                f"{fn.__name__} must emit 'value' for comparator; got {out}"
            )
            assert "status" in out, (
                f"{fn.__name__} must emit 'status'; got {out}"
            )


# ============================================================================
# Stage B-final-fix · Codex R3 F1-HIGH/F2-MED regression tests
# ============================================================================

class TestStageBFinalFixR3:
    """DEC-V61-060 Stage B-final-fix tests addressing Codex R3 findings:
      F1-HIGH — fail-closed must hold against malformed u_vecs and
                non-finite (NaN, Inf) inputs (don't crash, don't emit
                'status: ok' with NaN value).
      F2-MED  — RBCBoundary.g and beta now Optional[float] with no
                defaults; extractors fail-closed when caller forgets
                to plumb case-derived physics.
    """

    # --- F1-HIGH: malformed u_vecs (arity violations) ---

    def test_w_max_returns_empty_on_short_uvec_tuple(self):
        """u_vecs entries shorter than 3 elements (arity violation)
        used to raise IndexError. Must now fail-closed."""
        slice_ = RBCFieldSlice(
            cxs=[0.5, 1.5], cys=[0.5, 0.5], t_vals=[300.0, 300.0],
            u_vecs=[(0.0,), (0.0, 0.1)],   # both malformed
        )
        bc = _make_bc()
        out = extract_w_max(slice_, bc)
        assert out == {}, f"Malformed u_vecs must return {{}}; got {out}"

    def test_roll_count_returns_empty_on_short_uvec_tuple(self):
        slice_ = RBCFieldSlice(
            cxs=[0.5, 1.5, 2.5], cys=[0.5, 0.5, 0.5],
            t_vals=[300.0, 300.0, 300.0],
            u_vecs=[(0.0,)] * 3,
        )
        bc = _make_bc()
        out = extract_roll_count_x(slice_, bc)
        assert out == {}, f"Malformed u_vecs must return {{}}; got {out}"

    # --- F1-HIGH: non-finite inputs (NaN, Inf) ---

    def test_nu_asymmetry_returns_empty_on_nan_in_t_vals(self):
        slice_ = RBCFieldSlice(
            cxs=[0.5] * 4, cys=[0.125, 0.375, 0.625, 0.875],
            t_vals=[303.75, float("nan"), 298.75, 296.25],
        )
        bc = _make_bc()
        out = extract_nu_asymmetry(slice_, bc)
        assert out == {}, (
            f"NaN in t_vals must return {{}} (not 'ok'+nan); got {out}"
        )

    def test_nu_asymmetry_returns_empty_on_nan_in_dt(self):
        slice_ = _linear_conduction_field()
        bc = _make_bc(dT=float("nan"))
        out = extract_nu_asymmetry(slice_, bc)
        assert out == {}, f"NaN dT must return {{}}; got {out}"

    def test_w_max_returns_empty_on_nan_in_uy(self):
        slice_ = RBCFieldSlice(
            cxs=[1.0, 2.0, 3.0], cys=[0.2, 0.5, 0.8],
            t_vals=[300.0] * 3,
            u_vecs=[(0.0, 0.1, 0.0), (0.0, float("nan"), 0.0), (0.0, 0.1, 0.0)],
        )
        bc = _make_bc()
        out = extract_w_max(slice_, bc)
        assert out == {}, f"NaN u_y must return {{}}; got {out}"

    def test_w_max_returns_empty_on_inf_g(self):
        slice_ = _two_roll_velocity_field()
        bc = _make_bc(g=float("inf"))
        out = extract_w_max(slice_, bc)
        assert out == {}, f"Inf g must return {{}}; got {out}"

    # --- F2-MED: g/beta now required (no defaults) ---

    def test_rbc_boundary_no_default_g(self):
        """Without explicit g, defaults to None — and any extractor
        that needs g must fail-closed."""
        bc = RBCBoundary(
            Lx=4.0, Ly=1.0, H=1.0, dT=10.0,
            wall_coord_hot=0.0, wall_coord_cold=1.0,
            T_hot_wall=305.0, T_cold_wall=295.0,
            # NOTE: g and beta NOT supplied
        )
        assert bc.g is None
        assert bc.beta is None

    def test_w_max_returns_empty_when_g_missing(self):
        """Stage C wiring contract: forgetting to plumb g must surface
        as MISSING_TARGET_QUANTITY at the comparator, not silent bogus."""
        slice_ = _two_roll_velocity_field()
        bc = RBCBoundary(
            Lx=4.0, Ly=1.0, H=1.0, dT=10.0,
            wall_coord_hot=0.0, wall_coord_cold=1.0,
            T_hot_wall=305.0, T_cold_wall=295.0,
            g=None, beta=None,
        )
        out = extract_w_max(slice_, bc)
        assert out == {}, f"Missing g must return {{}}; got {out}"

    def test_nu_asymmetry_works_without_g_beta(self):
        """nu_asymmetry doesn't need g/beta — must still succeed even
        when those fields are None (only w_max + advisory extractors
        consume g/beta)."""
        slice_ = _linear_conduction_field()
        bc = RBCBoundary(
            Lx=4.0, Ly=1.0, H=1.0, dT=10.0,
            wall_coord_hot=0.0, wall_coord_cold=1.0,
            T_hot_wall=305.0, T_cold_wall=295.0,
            g=None, beta=None,
        )
        out = extract_nu_asymmetry(slice_, bc)
        assert out, f"nu_asymmetry should not require g/beta; got {out}"
        assert out["status"] == "ok"


# ============================================================================
# Stage B-final-fix-v2 · Codex R4 F1-HIGH boundary-metadata fail-closed tests
# ============================================================================

class TestStageBFinalFixR4:
    """DEC-V61-060 Stage B-final-fix-v2 tests addressing Codex R4 F1-HIGH:
    fail-closed must hold for non-finite values in BOUNDARY METADATA
    (wall_coord_hot/cold, T_hot/cold_wall, bc_gradient), not just field
    arrays. R3 closed the field-array path; R4 closes the BC path."""

    def test_w_max_returns_empty_on_nan_wall_coord_hot(self):
        slice_ = _two_roll_velocity_field()
        bc = _make_bc(wall_coord_hot=float("nan"))
        out = extract_w_max(slice_, bc)
        assert out == {}, f"NaN wall_coord_hot must return {{}}; got {out}"

    def test_w_max_returns_empty_on_inf_wall_coord_cold(self):
        slice_ = _two_roll_velocity_field()
        bc = _make_bc(wall_coord_cold=float("inf"))
        out = extract_w_max(slice_, bc)
        assert out == {}, f"Inf wall_coord_cold must return {{}}; got {out}"

    def test_nu_asymmetry_returns_empty_on_nan_wall_coord(self):
        slice_ = _linear_conduction_field()
        bc = _make_bc(wall_coord_hot=float("nan"))
        out = extract_nu_asymmetry(slice_, bc)
        assert out == {}, f"NaN wall_coord_hot must return {{}}; got {out}"

    def test_nu_asymmetry_returns_empty_on_nan_t_hot_wall(self):
        slice_ = _linear_conduction_field()
        bc = _make_bc(T_hot_wall=float("nan"))
        out = extract_nu_asymmetry(slice_, bc)
        assert out == {}, f"NaN T_hot_wall must return {{}}; got {out}"

    def test_nu_asymmetry_returns_empty_on_nan_t_cold_wall(self):
        slice_ = _linear_conduction_field()
        bc = _make_bc(T_cold_wall=float("nan"))
        out = extract_nu_asymmetry(slice_, bc)
        assert out == {}, f"NaN T_cold_wall must return {{}}; got {out}"

    def test_nu_asymmetry_returns_empty_on_nan_bc_gradient(self):
        """fixedGradient bc_type with NaN bc_gradient must fail-closed."""
        slice_ = _linear_conduction_field()
        bc = _make_bc(bc_type="fixedGradient", bc_gradient=float("nan"))
        out = extract_nu_asymmetry(slice_, bc)
        assert out == {}, f"NaN bc_gradient must return {{}}; got {out}"

    def test_nu_asymmetry_returns_empty_on_missing_bc_gradient_for_fixed_gradient(self):
        """bc_type='fixedGradient' with bc_gradient=None (the dataclass
        default) is also non-finite for our purposes — must fail-closed."""
        slice_ = _linear_conduction_field()
        bc = _make_bc(bc_type="fixedGradient", bc_gradient=None)
        out = extract_nu_asymmetry(slice_, bc)
        assert out == {}, (
            f"fixedGradient with None bc_gradient must return {{}}; got {out}"
        )
