"""V73.A transonic airfoil extractor unit tests (DEC-V61-238).

Synthetic RAE-2822-like cases exercise the fail-closed contract: every
missing/garbled input raises, never a fabricated QoI. The case builder here
is shared with test_transonic_gate.py (V72.A precedent).
"""
import math
from pathlib import Path

import pytest

from src.transonic_airfoil_extractor import (
    MIN_UPPER_POINTS,
    TransonicExtractionError,
    detect_shock,
    extract_transonic_airfoil,
    integrate_cn_ca,
    order_contour,
    split_surfaces,
)
from src.transonic_airfoil_gate import cp_critical

# --- gold operating point (re-derived freestream, self-consistent) ----------
GAMMA, R_SPEC = 1.4, 287.058
MACH, ALPHA_DEG, RE_C, CHORD = 0.734, 2.79, 6.5e6, 1.0
T_INF = 288.15
SUTH_AS, SUTH_TS = 1.4792e-06, 116.0
MU = SUTH_AS * math.sqrt(T_INF) / (1.0 + SUTH_TS / T_INF)
A_SND = math.sqrt(GAMMA * R_SPEC * T_INF)
UMAG = MACH * A_SND
RHO_INF = RE_C * MU / (UMAG * CHORD)            # so Re comes out exactly 6.5e6
P_INF = RHO_INF * R_SPEC * T_INF
Q_INF = 0.5 * RHO_INF * UMAG * UMAG
UX = UMAG * math.cos(math.radians(ALPHA_DEG))
UZ = UMAG * math.sin(math.radians(ALPHA_DEG))
CP_STAR = cp_critical(MACH, GAMMA)              # ~ -0.647 at M=0.734

N_SIDE = 80


def _interp(knots, x):
    for (x0, y0), (x1, y1) in zip(knots, knots[1:]):
        if x0 <= x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return knots[-1][1]


def cp_upper_default(x):
    """Supersonic plateau + recompression through Cp* near x/c ~ 0.58."""
    return _interp([(0.0, 0.6), (0.05, -1.1), (0.55, -1.1), (0.62, -0.2), (1.0, 0.1)], x)


def cp_lower_default(x):
    """Stagnation Cp ~ 1.12 at the LE, mild subcritical suction aft."""
    return _interp([(0.0, 1.12), (0.02, 0.4), (0.3, -0.3), (0.7, -0.35), (1.0, 0.15)], x)


def _thickness(x):
    """NACA-style 12% thickness (closed-TE polynomial, half-thickness)."""
    return 5 * 0.12 * (
        0.2969 * math.sqrt(x) - 0.1260 * x - 0.3516 * x**2
        + 0.2843 * x**3 - 0.1015 * x**4
    )


def _camber(x):
    """Aft-loaded camber: lower surface crosses z=0 near the TE — the
    z-sign-split failure mode this extractor exists to avoid (F6)."""
    return 0.05 * x**3


def profile_chain(cp_upper=cp_upper_default, cp_lower=cp_lower_default, n=N_SIDE,
                  x_offset=0.0, x_scale=1.0):
    """Closed CCW (x, z, cp) contour: upper TE->LE then lower LE->TE.

    x_offset/x_scale transform ONLY the emitted x coordinate (Cp/z stay tied
    to the untransformed station) — used by the origin-invariance and
    chord-mismatch regressions (Codex R0 P2)."""
    xs = [0.5 * (1.0 - math.cos(math.pi * i / n)) for i in range(n + 1)]
    upper = [(x * x_scale + x_offset, _camber(x) + _thickness(x), cp_upper(x))
             for x in reversed(xs)]
    lower = [(x * x_scale + x_offset, _camber(x) - _thickness(x), cp_lower(x))
             for x in xs[1:]]
    return upper + lower


def _write_probe(case: Path, p=P_INF, t=T_INF, u=(UX, 0.0, UZ), tname="500",
                 extra_rows=()):
    d = case / "postProcessing" / "freestreamProbe" / tname
    d.mkdir(parents=True, exist_ok=True)
    rows = list(extra_rows) + [f"{tname} {p} {t} ({u[0]} {u[1]} {u[2]})"]
    (d / "surfaceFieldValue.dat").write_text(
        "# Region    : sampled upstream plane\n"
        "# Time areaAverage(p) areaAverage(T) areaAverage(U)\n"
        + "\n".join(rows) + "\n"
    )


def _write_declared(case: Path, p=P_INF, t=T_INF, u=(UX, 0.0, UZ)):
    z = case / "0"
    z.mkdir(parents=True, exist_ok=True)
    (z / "p").write_text(f"internalField   uniform {p};\n")
    (z / "T").write_text(f"internalField   uniform {t};\n")
    (z / "U").write_text(f"internalField   uniform ({u[0]} {u[1]} {u[2]});\n")


def _write_transport(case: Path, suth_as=SUTH_AS, suth_ts=SUTH_TS):
    d = case / "constant"
    d.mkdir(parents=True, exist_ok=True)
    (d / "thermophysicalProperties").write_text(
        "thermoType { transport sutherland; }\n"
        f"mixture {{ transport {{ As {suth_as}; Ts {suth_ts}; }} }}\n"
    )


def _write_forces(case: Path, cd, cl, tname="500", rows=None):
    """Default history has a pre-snapshot row AND a post-snapshot junk row:
    only snapshot-time selection (Codex R0 P1) reads the correct values."""
    d = case / "postProcessing" / "forceCoeffs1" / tname
    d.mkdir(parents=True, exist_ok=True)
    if rows is None:
        rows = [
            f"400 {cd} {cl * 0.99} 0.01",
            f"500 {cd} {cl} 0.01",
            f"600 {cd * 5.0} {cl * 1.5} 0.01",   # later junk state: must be ignored
        ]
    (d / "coefficient.dat").write_text(
        "# Force coefficients\n"
        "# Time Cd Cl Cm\n"
        + "\n".join(rows) + "\n"
    )


def _write_surface(case: Path, chain, p_inf=P_INF, q_inf=Q_INF, tname="500"):
    """Raw 'x y z p' rows at both spanwise faces (dedup must collapse them)."""
    d = case / "postProcessing" / "airfoilSurface" / tname
    d.mkdir(parents=True, exist_ok=True)
    lines = ["# x y z p"]
    for x, z, cp in chain:
        p = p_inf + q_inf * cp
        lines.append(f"{x} 0.0005 {z} {p}")
        lines.append(f"{x} -0.0005 {z} {p}")
    (d / "p_aerofoil.raw").write_text("\n".join(lines) + "\n")


def build_case(
    tmp_path: Path,
    cp_upper=cp_upper_default,
    cp_lower=cp_lower_default,
    probe=None,
    declared=None,
    transport=None,
    cl_fc=None,
    cd_fc=0.0168,
    alpha_for_cl=ALPHA_DEG,
    x_offset=0.0,
    x_scale=1.0,
) -> Path:
    """Self-consistent synthetic case. cl_fc defaults to the contour-integrated
    pressure Cl of the SAME synthetic Cp field (so C6 holds by construction);
    doctored cases override individual pieces."""
    case = tmp_path / "case"
    chain = profile_chain(cp_upper, cp_lower, x_offset=x_offset, x_scale=x_scale)
    _write_probe(case, **(probe or {}))
    _write_declared(case, **(declared or {}))
    _write_transport(case, **(transport or {}))
    if cl_fc is None:
        cn, ca = integrate_cn_ca(chain, CHORD)
        a = math.radians(alpha_for_cl)
        cl_fc = cn * math.cos(a) - ca * math.sin(a)
    _write_forces(case, cd_fc, cl_fc)
    _write_surface(case, chain)
    return case


def _extract(case):
    return extract_transonic_airfoil(case, chord=CHORD, gamma=GAMMA, r_specific=R_SPEC)


class TestHappyPath:
    def test_full_extraction(self, tmp_path):
        m = _extract(build_case(tmp_path))
        assert m.measured.mach == pytest.approx(MACH, abs=1e-6)
        assert m.measured.alpha_deg == pytest.approx(ALPHA_DEG, abs=1e-6)
        assert m.declared.mach == pytest.approx(MACH, abs=1e-6)
        assert m.reynolds_declared == pytest.approx(RE_C, rel=1e-9)
        # extraction must reproduce the source Cp field through the
        # p -> Cp roundtrip (LE stagnation point lives at the branch seam)
        exp_max = max(cp for _x, _z, cp in profile_chain())
        assert m.max_cp == pytest.approx(exp_max, abs=1e-9)
        assert 1.0 < m.max_cp < 1.142  # inside the stagnation sanity window
        assert m.min_cp_upper == pytest.approx(-1.1, abs=1e-6)
        assert m.n_upper == N_SIDE + 1 and m.n_lower == N_SIDE + 1
        assert m.shock_decline_reason is None
        assert 0.5 < m.shock_xc < 0.7
        # independent pressure Cl agrees with the (consistently written) FO Cl
        assert m.cl_p == pytest.approx(m.cl_fc, rel=1e-6)
        assert 0.2 < m.cl_p < 0.8  # plausible lifting solution

    def test_aft_loaded_lower_surface_stays_lower(self, tmp_path):
        """F6 regression: with camber 0.05 x^3 the lower surface crosses z=0
        near the TE; a z-sign split would steal those points for the upper
        surface. The contour split must keep them on the lower branch."""
        m = _extract(build_case(tmp_path))
        aft_lower = [x for x, _cp in m.lower_cp if x > 0.95]
        assert aft_lower, "aft lower-surface points (z>0 region) missing from lower branch"
        # both branches span the full chord
        assert min(x for x, _ in m.lower_cp) < 0.01
        assert max(x for x, _ in m.lower_cp) > 0.99
        # and the aft-lower points really do sit at positive z (the trap is real)
        assert _camber(0.97) - _thickness(0.97) > 0


class TestContourGeometry:
    def test_order_contour_rejects_jumping_chain(self, tmp_path):
        pts = [(0.01 * i, 0.0, 0.0) for i in range(20)] + [(10.0, 5.0, 0.0)]
        with pytest.raises(TransonicExtractionError, match="chain jump"):
            order_contour(pts)

    def test_order_contour_too_sparse(self):
        with pytest.raises(TransonicExtractionError, match="too sparse"):
            order_contour([(0.0, 0.0, 0.0)] * 4)

    def test_split_upper_is_higher_mean_z(self):
        chain = order_contour(profile_chain())
        upper, lower = split_surfaces(chain)
        mean_up = sum(z for _x, z, _c in upper) / len(upper)
        mean_lo = sum(z for _x, z, _c in lower) / len(lower)
        assert mean_up > mean_lo

    def test_integrate_constant_cp_is_zero_force(self):
        chain = [(x, z, 0.7) for x, z, _ in profile_chain()]
        cn, ca = integrate_cn_ca(chain, CHORD)
        assert cn == pytest.approx(0.0, abs=1e-9)
        assert ca == pytest.approx(0.0, abs=1e-9)

    def test_integrate_square_known_value(self):
        """Unit square, Cp=+1 bottom / -1 top / linear sides:
        Cn = (1/c) oint Cp dx (CCW) = Cp_low - Cp_up = 2."""
        n = 50
        bottom = [(i / n, 0.0, 1.0) for i in range(n)]
        right = [(1.0, i / n, 1.0 - 2.0 * i / n) for i in range(n)]
        top = [(1.0 - i / n, 1.0, -1.0) for i in range(n)]
        left = [(0.0, 1.0 - i / n, -1.0 + 2.0 * i / n) for i in range(n)]
        cn, ca = integrate_cn_ca(bottom + right + top + left, 1.0)
        assert cn == pytest.approx(2.0, abs=1e-9)
        assert ca == pytest.approx(0.0, abs=1e-9)
        # direction independence: reversed (clockwise) traversal, same answer
        cn_r, ca_r = integrate_cn_ca(list(reversed(bottom + right + top + left)), 1.0)
        assert cn_r == pytest.approx(cn, abs=1e-12)
        assert ca_r == pytest.approx(ca, abs=1e-12)

    def test_integrate_degenerate_contour_raises(self):
        with pytest.raises(TransonicExtractionError, match="zero enclosed area"):
            integrate_cn_ca([(0.0, 0.0, 1.0), (1.0, 0.0, 1.0), (2.0, 0.0, 1.0),
                             (3.0, 0.0, 1.0)], 1.0)


class TestShockDetector:
    def _xs(self, n=40):
        return [i / (n - 1) for i in range(n)]

    def test_sane_profile_locates_shock(self):
        xs = self._xs()
        pts = [(x, cp_upper_default(x)) for x in xs]
        xc, reason = detect_shock(pts, CP_STAR)
        assert reason is None
        assert 0.5 < xc < 0.7

    def test_subcritical_profile_declines(self):
        pts = [(x, -0.5) for x in self._xs()]
        xc, reason = detect_shock(pts, CP_STAR)
        assert xc is None and "no supersonic plateau" in reason

    def test_oscillatory_field_declines(self):
        pts = [(x, CP_STAR + (0.2 if i % 2 else -0.2))
               for i, x in enumerate(self._xs())]
        xc, reason = detect_shock(pts, CP_STAR)
        assert xc is None and "crossings" in reason

    def test_wiggle_recovery_declines(self):
        """Deep spike + shallow plateau inside ONE supersonic excursion (the
        hump between them stays below Cp*, so crossings == 2): the shallow
        recompression jump must not be promoted to a shock (F3)."""
        cps = ([0.5, 0.0, -0.5]                            # descent
               + [-2.0, -2.1, -2.0]                        # deep spike (3 pts < plateau min)
               + [-0.66, -0.67, -0.66]                     # hump: below Cp*, above Cp*-margin
               + [-0.75] * 10                              # shallow plateau (longest run)
               + [-0.63, -0.3, 0.0]                        # weak recovery through Cp*
               + [0.05] * 12)
        xs = [i / (len(cps) - 1) for i in range(len(cps))]
        xc, reason = detect_shock(list(zip(xs, cps)), CP_STAR)
        assert xc is None and "wiggle" in reason

    def test_never_recompresses_declines(self):
        pts = [(x, 0.5 - 3.0 * x) for x in self._xs()]  # dives, never recovers
        xc, reason = detect_shock(pts, CP_STAR)
        assert xc is None and "never recompresses" in reason

    def test_sparse_surface_fails_closed(self):
        pts = [(x / 10, -1.0) for x in range(10)]
        assert len(pts) < MIN_UPPER_POINTS
        with pytest.raises(TransonicExtractionError, match="too sparse"):
            detect_shock(pts, CP_STAR)


class TestFailClosed:
    def test_missing_probe_raises(self, tmp_path):
        case = build_case(tmp_path)
        import shutil
        shutil.rmtree(case / "postProcessing" / "freestreamProbe")
        with pytest.raises(TransonicExtractionError, match="freestream probe"):
            _extract(case)

    def test_probe_header_order_independent(self, tmp_path):
        """Columns located by NAME — vector-before-scalar order must parse."""
        case = build_case(tmp_path)
        dat = (case / "postProcessing" / "freestreamProbe" / "500"
               / "surfaceFieldValue.dat")
        dat.write_text(
            "# Time areaAverage(U) areaAverage(p) areaAverage(T)\n"
            f"500 ({UX} 0.0 {UZ}) {P_INF} {T_INF}\n"
        )
        m = _extract(case)
        assert m.measured.mach == pytest.approx(MACH, abs=1e-6)

    def test_nonuniform_declared_bc_raises(self, tmp_path):
        case = build_case(tmp_path)
        (case / "0" / "p").write_text(
            "internalField   nonuniform List<scalar> 2(1e5 1e5);\n"
        )
        with pytest.raises(TransonicExtractionError, match="uniform"):
            _extract(case)

    def test_missing_transport_raises(self, tmp_path):
        case = build_case(tmp_path)
        (case / "constant" / "thermophysicalProperties").unlink()
        with pytest.raises(TransonicExtractionError, match="thermophysicalProperties"):
            _extract(case)

    def test_gauge_pressure_surface_rejected(self, tmp_path):
        """A gauge-pressure setup (p ~ 0 +/- q Cp) carries non-positive
        absolute pressures — must be rejected, not silently normalized."""
        case = build_case(tmp_path)
        sdir = case / "postProcessing" / "airfoilSurface" / "500"
        rows = []
        for x, z, cp in profile_chain():
            rows.append(f"{x} 0.0005 {z} {Q_INF * cp}")
        (sdir / "p_aerofoil.raw").write_text("# x y z p\n" + "\n".join(rows) + "\n")
        with pytest.raises(TransonicExtractionError, match="absolute pressure"):
            _extract(case)

    def test_garbled_surface_row_raises(self, tmp_path):
        case = build_case(tmp_path)
        raw = (case / "postProcessing" / "airfoilSurface" / "500" / "p_aerofoil.raw")
        raw.write_text("# x y z p\n0.1 0.0\n")
        with pytest.raises(TransonicExtractionError, match="expected 4 columns"):
            _extract(case)

    def test_missing_forcecoeffs_raises(self, tmp_path):
        case = build_case(tmp_path)
        import shutil
        shutil.rmtree(case / "postProcessing" / "forceCoeffs1")
        with pytest.raises(TransonicExtractionError, match="forceCoeffs"):
            _extract(case)

    def test_nonfinite_coefficients_raise(self, tmp_path):
        case = build_case(tmp_path)
        dat = case / "postProcessing" / "forceCoeffs1" / "500" / "coefficient.dat"
        dat.write_text("# Time Cd Cl Cm\n500 nan nan 0\n")
        with pytest.raises(TransonicExtractionError, match="non-finite"):
            _extract(case)

    def test_zero_velocity_probe_raises(self, tmp_path):
        case = build_case(tmp_path, probe={"u": (0.0, 0.0, 0.0)})
        with pytest.raises(TransonicExtractionError, match="zero measured freestream"):
            _extract(case)

    def test_nonphysical_probe_state_raises(self, tmp_path):
        case = build_case(tmp_path, probe={"p": -100.0})
        with pytest.raises(TransonicExtractionError, match="non-physical measured"):
            _extract(case)


class TestSnapshotAlignment:
    """Codex V73.A R0 P1: every judged quantity from ONE solver state."""

    def test_forces_taken_at_snapshot_not_last_row(self, tmp_path):
        # default fixture carries a junk t=600 row after the t=500 snapshot;
        # the matching t=500 row must win (cl_p == cl_fc only holds there)
        m = _extract(build_case(tmp_path))
        assert m.cl_p == pytest.approx(m.cl_fc, rel=1e-6)
        assert m.cd_fc == pytest.approx(0.0168, abs=1e-12)

    def test_no_forces_row_at_snapshot_raises(self, tmp_path):
        case = build_case(tmp_path)
        dat = case / "postProcessing" / "forceCoeffs1" / "500" / "coefficient.dat"
        dat.write_text("# Time Cd Cl Cm\n400 0.0168 0.5 0.01\n450 0.0168 0.5 0.01\n")
        with pytest.raises(TransonicExtractionError, match="mix solver states"):
            _extract(case)

    def test_probe_row_selected_at_snapshot(self, tmp_path):
        # earlier junk probe row (half velocity) must be ignored
        junk = f"400 {P_INF} {T_INF} ({UX * 0.5} 0.0 {UZ * 0.5})"
        case = build_case(tmp_path, probe={"extra_rows": (junk,)})
        m = _extract(case)
        assert m.measured.mach == pytest.approx(MACH, abs=1e-6)

    def test_no_probe_row_at_snapshot_raises(self, tmp_path):
        case = build_case(tmp_path)
        dat = (case / "postProcessing" / "freestreamProbe" / "500"
               / "surfaceFieldValue.dat")
        dat.write_text(
            "# Time areaAverage(p) areaAverage(T) areaAverage(U)\n"
            f"400 {P_INF} {T_INF} ({UX} 0.0 {UZ})\n"
        )
        with pytest.raises(TransonicExtractionError, match="mix solver states"):
            _extract(case)

    def test_duplicate_probe_rows_prefer_post_restart_last(self, tmp_path):
        """Codex R1 P1: a restarted run appends a second row at the SAME
        time; the stale pre-restart row (half velocity) must lose the tie."""
        stale = f"500 {P_INF} {T_INF} ({UX * 0.5} 0.0 {UZ * 0.5})"
        case = build_case(tmp_path, probe={"extra_rows": (stale,)})
        m = _extract(case)
        assert m.measured.mach == pytest.approx(MACH, abs=1e-6)

    def test_duplicate_forces_rows_prefer_post_restart_last(self, tmp_path):
        case = build_case(tmp_path)
        dat = case / "postProcessing" / "forceCoeffs1" / "500" / "coefficient.dat"
        good = dat.read_text()
        # prepend a stale duplicate-time row BEFORE the good t=500 row
        lines = good.splitlines()
        idx = next(i for i, l in enumerate(lines) if l.startswith("500 "))
        lines.insert(idx, "500 0.09 1.9 0.01")  # stale pre-restart junk
        dat.write_text("\n".join(lines) + "\n")
        m = _extract(case)
        assert m.cl_p == pytest.approx(m.cl_fc, rel=1e-6), (
            "the post-restart (last) duplicate row must win"
        )


class TestCoordinateOrigin:
    """Codex V73.A R0 P2: x/c must be LE-anchored, not origin-anchored."""

    def test_translated_geometry_is_invariant(self, tmp_path):
        m0 = _extract(build_case(tmp_path))
        mt = _extract(build_case(tmp_path / "shifted", x_offset=0.37))
        assert mt.shock_xc == pytest.approx(m0.shock_xc, abs=1e-9)
        assert mt.min_cp_upper == pytest.approx(m0.min_cp_upper, abs=1e-9)
        assert mt.cl_p == pytest.approx(m0.cl_p, rel=1e-9)
        # x/c domain stays [0, 1] regardless of where the mesh sits in x
        assert min(x for x, _ in mt.upper_cp) == pytest.approx(0.0, abs=1e-9)
        assert max(x for x, _ in mt.upper_cp) == pytest.approx(1.0, abs=1e-9)

    def test_chord_mismatched_geometry_rejected(self, tmp_path):
        with pytest.raises(TransonicExtractionError, match="declared chord"):
            _extract(build_case(tmp_path, x_scale=1.5))

    def test_face_centre_shrunk_span_accepted(self, tmp_path):
        """Codex R1 P2: raw rows are FACE CENTRES — on a coarse mesh the
        span legitimately falls a few % short of the chord. 5% shrink must
        extract cleanly (LE-anchored x/c just spans [0, 0.95])."""
        m = _extract(build_case(tmp_path / "shrunk", x_scale=0.95))
        assert m.shock_decline_reason is None
        assert max(x for x, _ in m.upper_cp) == pytest.approx(0.95, abs=1e-9)

    def test_partial_surface_still_rejected(self, tmp_path):
        # 15% short is beyond any face-centre effect: partial surface
        with pytest.raises(TransonicExtractionError, match="declared chord"):
            _extract(build_case(tmp_path, x_scale=0.85))

    def test_overlong_span_still_rejected(self, tmp_path):
        # the span can never legitimately EXCEED the chord: tight 2% gate
        with pytest.raises(TransonicExtractionError, match="declared chord"):
            _extract(build_case(tmp_path, x_scale=1.05))
