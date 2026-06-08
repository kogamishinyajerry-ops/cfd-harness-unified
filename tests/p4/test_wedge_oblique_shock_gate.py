"""P4 V71.A · coverage + anti-cheat test for the supersonic-wedge oblique-shock gate.

Drives the FROZEN LIVE probe (reports/showcase_aero/_w71a_wedge_probe/ — a REAL
rhoCentralFoam solve, NOT authored; see its REPRODUCE.md) through the QoI extractor
and the wedge_oblique_shock gate, and asserts the gate PASSES on genuine solver
output — then proves every hard gate fails-closed by doctoring copies of that probe.

This is the LIVE slice (DEC-V61-233): the live rhoCentralFoam solve LIVE-VALIDATES the
V&V benchmark (it does NOT flip runnable-coverage 2->3 — per Law-1 + DEC-V61-224(b) that
needs the workbench backend wired, deferred; Codex R0 P2-1), replacing the earlier offline
``_w71a_wedge_probe_SYNTHETIC/`` fixture (DEC-V61-232 scaffolding). The tests run
OFFLINE against the frozen artifacts (no Docker needed) yet validate REAL physics:
the measured beta/M2/ratios come from the solver field, not from the gold.

Honesty locks exercised here:
  - the gate PASSES on a real solve: every observable within 0.5% of the analytical
    theta-beta-M reference, all SIX hard gates hold;
  - the gate is REAL: a doctored shock-line (wrong density-jump location) flips beta
    out of band -> FAIL;
  - ideal-gas consistency is a HARD gate: a doctored single state probe breaks
    T2/T1 == (p2/p1)/(rho2/rho1) -> FAIL even when that ratio still matches the gold;
  - shock-locus cross-consistency is a HARD gate: a beta and a p2/p1 each within 3%
    but inconsistent with EACH OTHER on the normal-shock locus -> FAIL (the 6th gate,
    landed with this live slice, that the first five cannot catch);
  - supersonic-inflow / downstream-supersonic / inflow-matches-target are HARD gates;
  - the extractor MEASURES (does not echo the gold): extracted beta/M2 differ from
    the committed reference yet land inside the 3% band;
  - a flat / smoothly-ramped density field refuses to fabricate a shock angle;
  - missing artifacts raise rather than fabricate a default.
"""
from __future__ import annotations

import math
import re
import shutil
from pathlib import Path

import pytest

from src.wedge_oblique_shock_extractor import (
    WedgeShockExtractorError,
    extract_wedge_qois,
    to_key_quantities,
)
from src.wedge_oblique_shock_gate import gate_wedge_against_gold

_REPO = Path(__file__).resolve().parents[2]
_PROBE = _REPO / "reports" / "showcase_aero" / "_w71a_wedge_probe"
_GOLD = _REPO / "knowledge" / "gold_standards" / "wedge_oblique_shock.yaml"
_GOLD_T10 = _REPO / "knowledge" / "gold_standards" / "wedge_oblique_shock_theta10.yaml"

# live sampling geometry — = wedge_inputs.{x_shock_station, shock_line_origin_y}
_X_STATION = 0.12
_ORIGIN_Y = 0.05

# committed gold references (theta=15) — the extractor must DIFFER from these yet pass
_GOLD_BETA = 45.3436
_GOLD_M2 = 1.4457
_GOLD_PRATIO = 2.1947
_GOLD_RRATIO = 1.7289
_GOLD_TRATIO = 1.2694


def _extract(case: Path, **kw):
    """extract_wedge_qois with the live sampling geometry as defaults."""
    kw.setdefault("x_shock_station", _X_STATION)
    kw.setdefault("shock_line_origin_y", _ORIGIN_Y)
    return extract_wedge_qois(case, **kw)


def _copy_case(tmp_path: Path) -> Path:
    case = tmp_path / "case"
    shutil.copytree(_PROBE, case)
    return case


def _probe_dat(case: Path, probe: str) -> Path:
    """The (single) multi-field surfaceFieldValue.dat under a region-probe dir."""
    return next((case / "postProcessing" / probe).glob("*/surfaceFieldValue.dat"))


_AREA_AVG = re.compile(r"areaAverage\(([^)]+)\)")


def _set_probe_field(case: Path, probe: str, field: str, value: float) -> None:
    """Doctor ONE field's column in a multi-field surfaceFieldValue.dat in place
    (every data row, so the last/converged row the extractor reads is changed)."""
    dat = _probe_dat(case, probe)
    lines = dat.read_text(encoding="utf-8").splitlines()
    cols: list[str] = []
    for ln in lines:
        if ln.lstrip().startswith("#"):
            labels = _AREA_AVG.findall(ln)
            if labels:
                cols = labels
    assert field in cols, f"{field} not in {cols}"
    idx = cols.index(field) + 1  # +1 for the leading Time column
    out: list[str] = []
    for ln in lines:
        s = ln.strip()
        if s and not s.startswith("#"):
            parts = s.split()
            parts[idx] = f"{value:.10g}"
            out.append("\t".join(parts))
        else:
            out.append(ln)
    dat.write_text("\n".join(out) + "\n", encoding="utf-8")


def _set_shock_line(case: Path, dist_shock: float, rho2: float, rho1: float) -> None:
    """Rewrite the rho(distance) sample so the density jump sits at a chosen distance
    along the line. Post-shock (high rho2) below the jump (near the wall), freestream
    (rho1) above — matching the live geometry (line runs from y=origin upward).
    beta = atan2(origin_y + dist_shock, x_station)."""
    xy = next((case / "postProcessing" / "shockLine").glob("*/*.xy"))
    lines = ["# doctored fixture (test) — distance rho"]
    d = 0.0
    while d <= 0.25 + 1e-9:
        lines.append(f"{d:.5f}\t{(rho2 if d < dist_shock else rho1):.10g}")
        d += 0.001
    xy.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_shock_line_rows(
    case: Path, rows: list[tuple[float, float]], fname: str = "line_rho.xy"
) -> Path:
    """Write an arbitrary (distance, rho) profile to a named .xy under shockLine."""
    d = next((case / "postProcessing" / "shockLine").glob("*"))  # the time dir
    path = d / fname
    path.write_text(
        "# test profile\n" + "\n".join(f"{x:.5f}\t{v:.10g}" for x, v in rows) + "\n",
        encoding="utf-8",
    )
    return path


# ---------------------------------------------------------------------------
# headline: the gate PASSES on the real frozen rhoCentralFoam probe
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _PROBE.is_dir(), reason="live wedge probe absent")
def test_gate_passes_on_live_probe() -> None:
    """The V&V-validation proof: a REAL rhoCentralFoam solve validates against the
    analytical theta-beta-M gold — every observable + all SIX hard gates PASS. (This
    validates the benchmark; it does not by itself flip runnable-coverage — that needs
    the workbench backend wired, DEC-V61-224(b).)"""
    r = gate_wedge_against_gold(_PROBE, gold_path=_GOLD)
    assert r.passed, r.summary
    assert r.supersonic_inflow_ok
    assert r.inflow_matches_target
    assert r.downstream_supersonic_ok
    assert r.beta_above_mach_angle_ok
    assert r.ideal_gas_consistent_ok
    assert r.shock_locus_consistent_ok
    names = {name for name, _ in r.comparisons}
    assert names == {
        "shock_angle_beta_deg",
        "mach_downstream",
        "pressure_ratio",
        "density_ratio",
        "temperature_ratio",
    }
    for name, cmp in r.comparisons:
        assert cmp.passed, f"{name}: {cmp.summary}"


@pytest.mark.skipif(not _PROBE.is_dir(), reason="live wedge probe absent")
def test_extractor_reproduces_live_probe() -> None:
    """Every measured QoI lands within the 3% tolerance of the analytical gold, and
    the measured freestream Mach is exactly the gold operating point."""
    q = _extract(_PROBE)
    assert q.mach_freestream == pytest.approx(2.0, abs=1e-3)
    assert abs(q.shock_angle_beta_deg - _GOLD_BETA) / _GOLD_BETA < 0.03
    assert abs(q.mach_downstream - _GOLD_M2) / _GOLD_M2 < 0.03
    assert abs(q.pressure_ratio - _GOLD_PRATIO) / _GOLD_PRATIO < 0.03
    assert abs(q.density_ratio - _GOLD_RRATIO) / _GOLD_RRATIO < 0.03
    assert abs(q.temperature_ratio - _GOLD_TRATIO) / _GOLD_TRATIO < 0.03


@pytest.mark.skipif(not _PROBE.is_dir(), reason="live wedge probe absent")
def test_extractor_measures_does_not_echo_gold() -> None:
    """Extracted beta/M2 come from the solver field, so they DIFFER from the committed
    reference — yet land inside the 3% band. If the extractor echoed the gold this
    would fail."""
    q = _extract(_PROBE)
    assert q.shock_angle_beta_deg != pytest.approx(_GOLD_BETA, abs=1e-3)
    assert q.mach_downstream != pytest.approx(_GOLD_M2, abs=1e-3)
    assert abs(q.shock_angle_beta_deg - _GOLD_BETA) / _GOLD_BETA < 0.03
    assert abs(q.mach_downstream - _GOLD_M2) / _GOLD_M2 < 0.03


# ---------------------------------------------------------------------------
# anti-cheat: each hard gate independently fails-closed (doctoring real-probe copies)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _PROBE.is_dir(), reason="live wedge probe absent")
def test_gate_is_real_doctored_shock_line_wrong_beta_fails(tmp_path: Path) -> None:
    """Move the density jump far up the line so the measured beta is grossly wrong ->
    beta observable out of band -> FAIL. Proves beta is measured, not rubber-stamped."""
    case = _copy_case(tmp_path)
    q = _extract(case)
    # dist=0.20 -> beta = atan2(0.05+0.20, 0.12) = atan2(0.25,0.12) ~ 64.3deg (>> 45)
    _set_shock_line(case, dist_shock=0.20, rho2=q.rho2, rho1=q.rho1)
    r = gate_wedge_against_gold(case, gold_path=_GOLD)
    assert not r.passed, r.summary
    beta_cmp = next(cmp for name, cmp in r.comparisons if name == "shock_angle_beta_deg")
    assert not beta_cmp.passed


@pytest.mark.skipif(not _PROBE.is_dir(), reason="live wedge probe absent")
def test_ideal_gas_consistency_is_a_hard_gate_doctored_pressure_fails(tmp_path: Path) -> None:
    """Raise the post-shock pressure by ~2.5%: the pressure_ratio observable still
    passes the 3% comparator, but the independently measured p2/rho2/T2 are no longer
    ideal-gas consistent -> the thermodynamic-consistency hard gate FAILS the gate."""
    case = _copy_case(tmp_path)
    q = _extract(case)
    _set_probe_field(case, "postShock", "p", q.p2 * 1.025)
    r = gate_wedge_against_gold(case, gold_path=_GOLD)
    # pressure_ratio still within the 3% comparator band ...
    p_cmp = next(cmp for name, cmp in r.comparisons if name == "pressure_ratio")
    assert p_cmp.passed, r.summary
    # ... but the state is no longer ideal-gas consistent -> hard gate trips -> FAIL
    assert not r.ideal_gas_consistent_ok
    assert not r.passed, r.summary


@pytest.mark.skipif(not _PROBE.is_dir(), reason="live wedge probe absent")
def test_shock_locus_cross_consistency_is_a_hard_gate(tmp_path: Path) -> None:
    """DEC-V61-232 forward-hardening (landed with the DEC-V61-233 live slice): scale
    the post-shock pressure AND temperature TOGETHER by 2.5%. This keeps each
    observable inside its 3% band AND keeps ideal-gas consistency (T2 and p2 scale
    together), yet shifts the measured p2/p1 OFF the normal-shock locus implied by the
    measured beta -> the shock-locus cross-consistency hard gate FAILS even though the
    first five gates all pass. This is precisely the internally-contradictory tuple the
    independent per-observable checks cannot catch."""
    case = _copy_case(tmp_path)
    q = _extract(case)
    _set_probe_field(case, "postShock", "p", q.p2 * 1.025)
    _set_probe_field(case, "postShock", "T", q.t2 * 1.025)
    r = gate_wedge_against_gold(case, gold_path=_GOLD)
    # every observable still within the 3% comparator band ...
    for name, cmp in r.comparisons:
        assert cmp.passed, f"{name} should still pass the per-observable band: {cmp.summary}"
    # ... and ideal-gas consistency still holds (p2 and T2 scaled together) ...
    assert r.ideal_gas_consistent_ok, r.summary
    # ... but beta and p2/p1 no longer lie on the same shock locus -> 6th gate trips
    assert not r.shock_locus_consistent_ok
    assert not r.passed, r.summary


@pytest.mark.skipif(not _PROBE.is_dir(), reason="live wedge probe absent")
def test_subsonic_inflow_is_a_hard_gate(tmp_path: Path) -> None:
    """A subsonic freestream Mach cannot host an oblique shock -> FAIL."""
    case = _copy_case(tmp_path)
    _set_probe_field(case, "freestream", "Ma", 0.8)
    r = gate_wedge_against_gold(case, gold_path=_GOLD)
    assert not r.supersonic_inflow_ok
    assert not r.passed, r.summary


@pytest.mark.skipif(not _PROBE.is_dir(), reason="live wedge probe absent")
def test_inflow_must_match_gold_target_mach(tmp_path: Path) -> None:
    """Still supersonic, but at the WRONG Mach (2.5 vs gold 2.0): the replayed case
    is not the gold's operating point -> inflow_matches_target FAILS."""
    case = _copy_case(tmp_path)
    _set_probe_field(case, "freestream", "Ma", 2.5)
    r = gate_wedge_against_gold(case, gold_path=_GOLD)
    assert r.supersonic_inflow_ok
    assert not r.inflow_matches_target
    assert not r.passed, r.summary


@pytest.mark.skipif(not _PROBE.is_dir(), reason="live wedge probe absent")
def test_detached_shock_downstream_subsonic_is_a_hard_gate(tmp_path: Path) -> None:
    """A weak oblique shock leaves the flow supersonic; M2<1 (strong/detached root)
    must FAIL even if a ratio matched."""
    case = _copy_case(tmp_path)
    _set_probe_field(case, "postShock", "Ma", 0.8)
    r = gate_wedge_against_gold(case, gold_path=_GOLD)
    assert not r.downstream_supersonic_ok
    assert not r.passed, r.summary


@pytest.mark.skipif(not _PROBE.is_dir(), reason="live wedge probe absent")
def test_flat_density_field_refuses_to_fabricate_beta(tmp_path: Path) -> None:
    """A flat rho(distance) profile (no shock) must RAISE, not invent a shock angle."""
    case = _copy_case(tmp_path)
    q = _extract(case)
    _set_shock_line(case, dist_shock=99.0, rho2=q.rho1, rho1=q.rho1)  # all rho1 -> flat
    with pytest.raises(WedgeShockExtractorError):
        _extract(case)


@pytest.mark.skipif(not _PROBE.is_dir(), reason="live wedge probe absent")
def test_to_key_quantities_uses_gold_quantity_names() -> None:
    kq = to_key_quantities(_extract(_PROBE))
    assert set(kq) == {
        "shock_angle_beta_deg",
        "mach_downstream",
        "pressure_ratio",
        "density_ratio",
        "temperature_ratio",
    }


@pytest.mark.skipif(not _PROBE.is_dir(), reason="live wedge probe absent")
def test_secondary_theta10_gold_discriminates_operating_point() -> None:
    """The gate is gold_path-parameterised: it RUNS against the theta=10 gold. The
    theta=15 live probe does not match the theta=10 references, so it does NOT pass —
    proving the gate discriminates operating points rather than rubber-stamping.

    Codex R1 P2: the theta=10 gold uses the SAME sampling geometry as the live probe
    (x_shock_station=0.12, shock_line_origin_y=0.05), so beta extracts CORRECTLY
    (~45.24, NOT a garbage ~8deg from a geometry mismatch). The gate therefore fails on
    a genuine REFERENCE-VALUE mismatch (45.24 vs the theta=10 reference 39.31), so this
    test would also catch a regression that copied the theta=15 references into the
    theta=10 gold — which a geometry-artifact failure would have masked."""
    r = gate_wedge_against_gold(_PROBE, gold_path=_GOLD_T10)
    assert not r.passed, r.summary  # theta=15 probe vs theta=10 gold
    # beta was extracted with the CORRECT (matching) geometry -> the live ~45.24, not ~8
    assert abs(r.qois.shock_angle_beta_deg - _GOLD_BETA) / _GOLD_BETA < 0.03
    # ...and the failure is a REFERENCE-VALUE mismatch: the beta observable is out of band
    # against the theta=10 reference (45.24 vs 39.31), not a geometry/hard-gate artifact
    beta_cmp = next(cmp for name, cmp in r.comparisons if name == "shock_angle_beta_deg")
    assert not beta_cmp.passed, beta_cmp.summary


@pytest.mark.skipif(not _PROBE.is_dir(), reason="live wedge probe absent")
def test_wall_anchored_line_needs_origin_offset_to_recover_beta() -> None:
    """Codex DEC-V61-232 R0 P1: the live shock line is sampled from y=0.05 (above the
    wedge wall) upward, so it reports height ABOVE that origin, not above the apex.
    WITH shock_line_origin_y=0.05 the absolute beta (~45.34) is recovered; WITHOUT it
    (origin=0) the angle collapses (~31deg) — the exact bug the offset term fixes."""
    with_offset = extract_wedge_qois(
        _PROBE, x_shock_station=_X_STATION, shock_line_origin_y=_ORIGIN_Y
    )
    without = extract_wedge_qois(_PROBE, x_shock_station=_X_STATION, shock_line_origin_y=0.0)
    assert abs(with_offset.shock_angle_beta_deg - _GOLD_BETA) / _GOLD_BETA < 0.03
    assert without.shock_angle_beta_deg < 40.0
    assert with_offset.shock_angle_beta_deg - without.shock_angle_beta_deg > 5.0


@pytest.mark.skipif(not _PROBE.is_dir(), reason="live wedge probe absent")
def test_extractor_honors_published_probe_names_and_discovers_column_order(tmp_path: Path) -> None:
    """Codex DEC-V61-232 R0 P2: the extractor reads the region probes NAMED in the gold
    contract (freestream / postShock) as multi-field surfaceFieldValue.dat, discovering
    the field column order from the header. A probe name not present fails closed."""
    case = _copy_case(tmp_path)
    dat = _probe_dat(case, "postShock")
    cols = _AREA_AVG.findall(
        next(l for l in dat.read_text(encoding="utf-8").splitlines() if "areaAverage" in l)
    )
    assert set(cols) == {"p", "rho", "T", "Ma"}  # the published 4 fields
    q = _extract(case)
    assert abs(q.pressure_ratio - _GOLD_PRATIO) / _GOLD_PRATIO < 0.03
    # a probe name that isn't in the bundle fails closed (no fabricated default)
    with pytest.raises(FileNotFoundError):
        _extract(case, postshock_probe="does_not_exist")


@pytest.mark.skipif(not _PROBE.is_dir(), reason="live wedge probe absent")
def test_smeared_shock_is_accepted_and_located(tmp_path: Path) -> None:
    """Codex DEC-V61-232 R1 P1: a numerically SMEARED shock (rise spread over many
    cells, so no single step carries a large fraction of the total variation) must
    still be accepted and located near its centre, and pass the gate against the real
    post-shock state. The localised-steepening guard admits it; the old 25%-single-step
    guard rejected it."""
    case = _copy_case(tmp_path)
    q = _extract(case)
    rho2, rho1 = q.rho2, q.rho1
    next((case / "postProcessing" / "shockLine").glob("*/*.xy")).unlink()
    # rho2 below 0.0625, linear smear to rho1 across [0.0625, 0.0775] (centre ~0.070),
    # rho1 above -> centre maps to beta = atan2(0.05+0.070, 0.12) = atan2(0.12,0.12) = 45deg
    rows: list[tuple[float, float]] = []
    x = 0.0
    while x <= 0.25 + 1e-9:
        if x <= 0.0625:
            v = rho2
        elif x >= 0.0775:
            v = rho1
        else:
            frac = (x - 0.0625) / 0.015
            v = rho2 + frac * (rho1 - rho2)
        rows.append((x, v))
        x += 0.001
    _write_shock_line_rows(case, rows)
    qs = _extract(case)
    assert qs.shock_angle_beta_deg == pytest.approx(45.0, abs=1.5)
    assert gate_wedge_against_gold(case, gold_path=_GOLD).passed


@pytest.mark.skipif(not _PROBE.is_dir(), reason="live wedge probe absent")
def test_smooth_full_line_ramp_is_rejected(tmp_path: Path) -> None:
    """A smooth density ramp across the WHOLE line (no localised shock) must fail
    closed — peak slope ~= mean slope, so no shock to fabricate an angle from."""
    case = _copy_case(tmp_path)
    q = _extract(case)
    next((case / "postProcessing" / "shockLine").glob("*/*.xy")).unlink()
    rows: list[tuple[float, float]] = []
    x = 0.0
    while x <= 0.25 + 1e-9:
        frac = x / 0.25
        rows.append((x, q.rho2 + frac * (q.rho1 - q.rho2)))  # uniform ramp
        x += 0.001
    _write_shock_line_rows(case, rows)
    with pytest.raises(WedgeShockExtractorError):
        _extract(case)


@pytest.mark.skipif(not _PROBE.is_dir(), reason="live wedge probe absent")
def test_multiple_xy_files_selects_density_not_arbitrary(tmp_path: Path) -> None:
    """Codex DEC-V61-232 R1 P2: when the shockLine set writes several fields (rho, p,
    U) the extractor must select the DENSITY .xy deterministically, not an arbitrary
    file by filesystem order."""
    case = _copy_case(tmp_path)
    q = _extract(case)  # density file -> real beta
    # add a pressure profile whose 'shock' sits at a DIFFERENT distance (0.20)
    p_rows = [(i * 0.005, (2.0e5 if i * 0.005 < 0.20 else 1.0e5)) for i in range(51)]
    _write_shock_line_rows(case, p_rows, fname="line_p.xy")
    # the density file still drives beta, not the pressure file (which would give ~64)
    q2 = _extract(case)
    assert q2.shock_angle_beta_deg == pytest.approx(q.shock_angle_beta_deg, abs=1e-6)


@pytest.mark.skipif(not _PROBE.is_dir(), reason="live wedge probe absent")
def test_ambiguous_xy_without_density_match_fails_closed(tmp_path: Path) -> None:
    """If several .xy exist and none unambiguously carries the density field, refuse
    to guess — fail closed rather than measure beta from the wrong signal."""
    case = _copy_case(tmp_path)
    time_dir = next((case / "postProcessing" / "shockLine").glob("*"))
    # rename the rho file so NOTHING matches 'rho', and add a second non-matching file
    next(time_dir.glob("*rho*.xy")).rename(time_dir / "line_p.xy")
    (time_dir / "line_U.xy").write_text("# x v\n0.1\t1.0\n0.2\t1.0\n", encoding="utf-8")
    with pytest.raises(WedgeShockExtractorError):
        _extract(case)


@pytest.mark.skipif(not _PROBE.is_dir(), reason="live wedge probe absent")
def test_lone_wrong_field_xy_fails_closed(tmp_path: Path) -> None:
    """Codex DEC-V61-232 R2 P1: if the ONLY sampled-line file is not the density field
    (e.g. a misconfigured set emitted just line_p.xy), the extractor must fail closed
    rather than measure beta from the wrong signal — a lone file is not a free pass."""
    case = _copy_case(tmp_path)
    time_dir = next((case / "postProcessing" / "shockLine").glob("*"))
    next(time_dir.glob("*rho*.xy")).rename(time_dir / "line_p.xy")  # only a pressure profile
    with pytest.raises(WedgeShockExtractorError):
        _extract(case)


def test_missing_postprocessing_is_honest_error(tmp_path: Path) -> None:
    """No silent default: an empty case dir raises rather than fabricating QoIs."""
    with pytest.raises((FileNotFoundError, WedgeShockExtractorError)):
        _extract(tmp_path)
