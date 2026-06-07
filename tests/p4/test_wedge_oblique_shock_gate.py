"""P4 V71.A · coverage + anti-cheat test for the supersonic-wedge oblique-shock gate.

Drives a SYNTHETIC offline fixture (reports/showcase_aero/_w71a_wedge_probe_SYNTHETIC/
— NOT a solver run; see its _build_synthetic_fixture.py header) through the QoI
extractor and the wedge_oblique_shock gate, and asserts the gate PASSES — with NO
live Docker / OpenFOAM run.

IMPORTANT — scope of what this proves: these tests exercise the gate's PARSING +
FAIL-CLOSED LOGIC (does a doctored input get caught?). They do NOT validate physics
and do NOT flip runnable-coverage 2->3 — that requires a LIVE rhoCentralFoam solve
(blocked on an ESI image, DEC-V61-224 fork wall, deferred to a separate slice). The
physics REFERENCE is locked separately by the self-verifying gold test
(test_wedge_oblique_shock_gold.py). When the live slice lands, a genuine frozen
rhoCentralFoam probe REPLACES this synthetic fixture.

Honesty locks exercised here:
  - the gate is REAL: a doctored shock-line (wrong density-jump location) flips beta
    out of band -> FAIL;
  - ideal-gas consistency is a HARD gate: a doctored single state probe breaks
    T2/T1 == (p2/p1)/(rho2/rho1) -> FAIL even when that ratio still matches the gold;
  - supersonic-inflow / downstream-supersonic / inflow-matches-target are HARD gates;
  - the extractor MEASURES (does not echo the gold): extracted beta/M2 differ from
    the committed reference yet land inside the 3% band;
  - a flat density field refuses to fabricate a shock angle;
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
_PROBE = _REPO / "reports" / "showcase_aero" / "_w71a_wedge_probe_SYNTHETIC"
_GOLD = _REPO / "knowledge" / "gold_standards" / "wedge_oblique_shock.yaml"
_GOLD_T10 = _REPO / "knowledge" / "gold_standards" / "wedge_oblique_shock_theta10.yaml"
_X_STATION = 0.5  # = wedge_inputs.x_shock_station

# committed gold references (theta=15) — the extractor must DIFFER from these yet pass
_GOLD_BETA = 45.3436
_GOLD_M2 = 1.4457


def _copy_case(tmp_path: Path) -> Path:
    case = tmp_path / "case"
    shutil.copytree(_PROBE, case)
    return case


def _probe_dat(case: Path, probe: str) -> Path:
    """The (single) multi-field surfaceFieldValue.dat under a region-probe dir."""
    return next((case / "postProcessing" / probe).glob("*/surfaceFieldValue.dat"))


_AREA_AVG = re.compile(r"areaAverage\(([^)]+)\)")


def _set_probe_field(case: Path, probe: str, field: str, value: float) -> None:
    """Doctor ONE field's column in a multi-field surfaceFieldValue.dat in place."""
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


def _set_shock_line(case: Path, y_shock: float, rho2: float, rho1: float) -> None:
    """Rewrite the rho(y) sample so the density jump sits at a chosen y_shock."""
    xy = next((case / "postProcessing" / "shockLine").glob("*/*.xy"))
    lines = ["# doctored fixture (test) — distance rho"]
    y = 0.01
    while y < 1.0:
        lines.append(f"{y:.4f}\t{(rho2 if y < y_shock else rho1):.10g}")
        y += 0.02
    xy.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# coverage: the gate passes on the synthetic fixture
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _PROBE.is_dir(), reason="synthetic wedge fixture absent")
def test_extractor_reproduces_synthetic_fixture() -> None:
    q = extract_wedge_qois(_PROBE, x_shock_station=_X_STATION)
    assert q.shock_angle_beta_deg == pytest.approx(45.0, abs=1e-6)
    assert q.mach_downstream == pytest.approx(1.44, abs=1e-9)
    assert q.mach_freestream == pytest.approx(2.0, abs=1e-9)
    assert q.pressure_ratio == pytest.approx(2.1947, abs=1e-3)
    assert q.density_ratio == pytest.approx(1.7289, abs=1e-3)
    assert q.temperature_ratio == pytest.approx(1.2694, abs=1e-3)


@pytest.mark.skipif(not _PROBE.is_dir(), reason="synthetic wedge fixture absent")
def test_gate_passes_on_synthetic_fixture() -> None:
    r = gate_wedge_against_gold(_PROBE, gold_path=_GOLD)
    assert r.passed, r.summary
    assert r.supersonic_inflow_ok
    assert r.inflow_matches_target
    assert r.downstream_supersonic_ok
    assert r.beta_above_mach_angle_ok
    assert r.ideal_gas_consistent_ok
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


@pytest.mark.skipif(not _PROBE.is_dir(), reason="synthetic wedge fixture absent")
def test_extractor_measures_does_not_echo_gold() -> None:
    """Extracted beta/M2 come from the field, so they DIFFER from the committed
    reference — yet land inside the 3% band. If the extractor echoed the gold this
    would fail."""
    q = extract_wedge_qois(_PROBE, x_shock_station=_X_STATION)
    assert q.shock_angle_beta_deg != pytest.approx(_GOLD_BETA, abs=1e-3)
    assert q.mach_downstream != pytest.approx(_GOLD_M2, abs=1e-3)
    assert abs(q.shock_angle_beta_deg - _GOLD_BETA) / _GOLD_BETA < 0.03
    assert abs(q.mach_downstream - _GOLD_M2) / _GOLD_M2 < 0.03


# ---------------------------------------------------------------------------
# anti-cheat: each hard gate independently fails-closed
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _PROBE.is_dir(), reason="synthetic wedge fixture absent")
def test_gate_is_real_doctored_shock_line_wrong_beta_fails(tmp_path: Path) -> None:
    """Move the density jump so the measured beta is wrong -> beta observable out of
    band -> FAIL. Proves beta is measured from the field, not rubber-stamped."""
    case = _copy_case(tmp_path)
    q = extract_wedge_qois(case, x_shock_station=_X_STATION)
    # push the jump far up the line: y_shock=0.85 -> beta=atan2(0.85,0.5)=59.5deg (>>45)
    _set_shock_line(case, y_shock=0.85, rho2=q.rho2, rho1=q.rho1)
    r = gate_wedge_against_gold(case, gold_path=_GOLD)
    assert not r.passed, r.summary
    beta_cmp = next(cmp for name, cmp in r.comparisons if name == "shock_angle_beta_deg")
    assert not beta_cmp.passed


@pytest.mark.skipif(not _PROBE.is_dir(), reason="synthetic wedge fixture absent")
def test_ideal_gas_consistency_is_a_hard_gate_doctored_pressure_fails(tmp_path: Path) -> None:
    """Raise the post-shock pressure by ~2.5%: the pressure_ratio observable still
    passes the 3% comparator, but the independently measured p2/rho2/T2 are no longer
    ideal-gas consistent -> the thermodynamic-consistency hard gate FAILS the gate.
    The shock analogue of the conjugate energy-balance hard gate."""
    case = _copy_case(tmp_path)
    q = extract_wedge_qois(case, x_shock_station=_X_STATION)
    _set_probe_field(case, "postShock", "p", q.p2 * 1.025)
    r = gate_wedge_against_gold(case, gold_path=_GOLD)
    # pressure_ratio still within the 3% comparator band ...
    p_cmp = next(cmp for name, cmp in r.comparisons if name == "pressure_ratio")
    assert p_cmp.passed, r.summary
    # ... but the state is no longer ideal-gas consistent -> hard gate trips -> FAIL
    assert not r.ideal_gas_consistent_ok
    assert not r.passed, r.summary


@pytest.mark.skipif(not _PROBE.is_dir(), reason="synthetic wedge fixture absent")
def test_subsonic_inflow_is_a_hard_gate(tmp_path: Path) -> None:
    """A subsonic freestream Mach cannot host an oblique shock -> FAIL."""
    case = _copy_case(tmp_path)
    _set_probe_field(case, "freestream", "Ma", 0.8)
    r = gate_wedge_against_gold(case, gold_path=_GOLD)
    assert not r.supersonic_inflow_ok
    assert not r.passed, r.summary


@pytest.mark.skipif(not _PROBE.is_dir(), reason="synthetic wedge fixture absent")
def test_inflow_must_match_gold_target_mach(tmp_path: Path) -> None:
    """Still supersonic, but at the WRONG Mach (2.5 vs gold 2.0): the replayed case
    is not the gold's operating point -> inflow_matches_target FAILS."""
    case = _copy_case(tmp_path)
    _set_probe_field(case, "freestream", "Ma", 2.5)
    r = gate_wedge_against_gold(case, gold_path=_GOLD)
    assert r.supersonic_inflow_ok
    assert not r.inflow_matches_target
    assert not r.passed, r.summary


@pytest.mark.skipif(not _PROBE.is_dir(), reason="synthetic wedge fixture absent")
def test_detached_shock_downstream_subsonic_is_a_hard_gate(tmp_path: Path) -> None:
    """A weak oblique shock leaves the flow supersonic; M2<1 (strong/detached root)
    must FAIL even if a ratio matched."""
    case = _copy_case(tmp_path)
    _set_probe_field(case, "postShock", "Ma", 0.8)
    r = gate_wedge_against_gold(case, gold_path=_GOLD)
    assert not r.downstream_supersonic_ok
    assert not r.passed, r.summary


@pytest.mark.skipif(not _PROBE.is_dir(), reason="synthetic wedge fixture absent")
def test_flat_density_field_refuses_to_fabricate_beta(tmp_path: Path) -> None:
    """A flat rho(y) profile (no shock) must RAISE, not invent a shock angle."""
    case = _copy_case(tmp_path)
    q = extract_wedge_qois(case, x_shock_station=_X_STATION)
    _set_shock_line(case, y_shock=2.0, rho2=q.rho1, rho1=q.rho1)  # all rho1 -> flat
    with pytest.raises(WedgeShockExtractorError):
        extract_wedge_qois(case, x_shock_station=_X_STATION)


@pytest.mark.skipif(not _PROBE.is_dir(), reason="synthetic wedge fixture absent")
def test_to_key_quantities_uses_gold_quantity_names() -> None:
    kq = to_key_quantities(extract_wedge_qois(_PROBE, x_shock_station=_X_STATION))
    assert set(kq) == {
        "shock_angle_beta_deg",
        "mach_downstream",
        "pressure_ratio",
        "density_ratio",
        "temperature_ratio",
    }


@pytest.mark.skipif(not _PROBE.is_dir(), reason="synthetic wedge fixture absent")
def test_secondary_theta10_gold_is_parameterised_and_runs(tmp_path: Path) -> None:
    """The gate is gold_path-parameterised: it RUNS against the theta=10 gold. The
    theta=15 fixture does not match the theta=10 references, so it does NOT pass —
    proving the gate discriminates operating points rather than rubber-stamping."""
    r = gate_wedge_against_gold(_PROBE, gold_path=_GOLD_T10)
    assert not r.passed, r.summary  # theta=15 fixture vs theta=10 gold


@pytest.mark.skipif(not _PROBE.is_dir(), reason="synthetic wedge fixture absent")
def test_wall_anchored_line_needs_origin_offset_to_recover_beta(tmp_path: Path) -> None:
    """Codex DEC-V61-232 R0 P1: a shock line sampled from the wedge WALL upward reports
    height ABOVE THE WALL, not above the apex. Without shock_line_origin_y the angle is
    wrong; WITH it (= x*tan(theta)) the absolute beta is recovered."""
    case = _copy_case(tmp_path)
    q = extract_wedge_qois(case, x_shock_station=_X_STATION)  # apex-level, beta=45
    origin = _X_STATION * math.tan(math.radians(15.0))  # wall height at the station
    # re-anchor the SAME absolute shock (y=0.50) on the wall: wall-relative distance = 0.50-origin
    _set_shock_line(case, y_shock=(0.50 - origin), rho2=q.rho2, rho1=q.rho1)
    with_offset = extract_wedge_qois(case, x_shock_station=_X_STATION, shock_line_origin_y=origin)
    without = extract_wedge_qois(case, x_shock_station=_X_STATION, shock_line_origin_y=0.0)
    # the offset recovers ~45 (within sample-step quantisation); omitting it gives the ~36 bug
    assert with_offset.shock_angle_beta_deg == pytest.approx(45.0, abs=1.0)
    assert without.shock_angle_beta_deg < 40.0
    assert with_offset.shock_angle_beta_deg - without.shock_angle_beta_deg > 5.0


@pytest.mark.skipif(not _PROBE.is_dir(), reason="synthetic wedge fixture absent")
def test_extractor_honors_published_probe_names_and_discovers_column_order(tmp_path: Path) -> None:
    """Codex DEC-V61-232 R0 P2: the extractor reads the region probes NAMED in the gold
    contract (freestream / postShock) as multi-field surfaceFieldValue.dat, discovering
    the field column order from the header (not assuming it). A probe name not present
    fails closed."""
    # (a) reordered columns are still read correctly (header-driven, not positional)
    case = _copy_case(tmp_path)
    dat = _probe_dat(case, "postShock")
    cols = _AREA_AVG.findall(
        next(l for l in dat.read_text(encoding="utf-8").splitlines() if "areaAverage" in l)
    )
    assert set(cols) == {"p", "rho", "T", "Ma"}  # the published 4 fields
    q = extract_wedge_qois(case, x_shock_station=_X_STATION)
    assert q.pressure_ratio == pytest.approx(2.1947, abs=1e-3)
    # (b) a probe name that isn't in the bundle fails closed (no fabricated default)
    with pytest.raises(FileNotFoundError):
        extract_wedge_qois(case, x_shock_station=_X_STATION, postshock_probe="does_not_exist")


def _write_shock_line_rows(case: Path, rows: list[tuple[float, float]], fname: str = "line_rho.xy") -> Path:
    """Write an arbitrary (distance, rho) profile to a named .xy under shockLine."""
    d = next((case / "postProcessing" / "shockLine").glob("*"))  # the time dir
    path = d / fname
    path.write_text(
        "# test profile\n" + "\n".join(f"{x:.4f}\t{v:.10g}" for x, v in rows) + "\n",
        encoding="utf-8",
    )
    return path


@pytest.mark.skipif(not _PROBE.is_dir(), reason="synthetic wedge fixture absent")
def test_smeared_shock_is_accepted_and_located(tmp_path: Path) -> None:
    """Codex DEC-V61-232 R1 P1: a numerically SMEARED shock (rise spread over ~6
    cells, so no single step carries 25% of the total variation) must still be
    accepted and located near its centre. The old 25%-single-step guard rejected it;
    the localised-steepening guard does not."""
    case = _copy_case(tmp_path)
    q = extract_wedge_qois(case, x_shock_station=_X_STATION)
    rho2, rho1 = q.rho2, q.rho1
    old_xy = next((case / "postProcessing" / "shockLine").glob("*/*.xy"))
    old_xy.unlink()
    # rho2 below ~0.44, linear smear to rho1 across [0.44, 0.56] (6 cells), rho1 above
    rows: list[tuple[float, float]] = []
    x = 0.02
    while x < 1.0:
        if x <= 0.44:
            v = rho2
        elif x >= 0.56:
            v = rho1
        else:
            frac = (x - 0.44) / 0.12
            v = rho2 + frac * (rho1 - rho2)
        rows.append((x, v))
        x += 0.02
    _write_shock_line_rows(case, rows)
    qs = extract_wedge_qois(case, x_shock_station=_X_STATION)
    # centre of the smear is ~0.50 -> beta ~45, inside the 3% band
    assert qs.shock_angle_beta_deg == pytest.approx(45.0, abs=1.5)
    assert gate_wedge_against_gold(case, gold_path=_GOLD).passed


@pytest.mark.skipif(not _PROBE.is_dir(), reason="synthetic wedge fixture absent")
def test_smooth_full_line_ramp_is_rejected(tmp_path: Path) -> None:
    """A smooth density ramp across the WHOLE line (no localised shock) must fail
    closed — peak slope ~= mean slope, so no shock to fabricate an angle from."""
    case = _copy_case(tmp_path)
    q = extract_wedge_qois(case, x_shock_station=_X_STATION)
    old_xy = next((case / "postProcessing" / "shockLine").glob("*/*.xy"))
    old_xy.unlink()
    rows: list[tuple[float, float]] = []
    x = 0.02
    while x < 1.0:
        frac = (x - 0.02) / (0.98 - 0.02)
        rows.append((x, q.rho2 + frac * (q.rho1 - q.rho2)))  # uniform ramp
        x += 0.02
    _write_shock_line_rows(case, rows)
    with pytest.raises(WedgeShockExtractorError):
        extract_wedge_qois(case, x_shock_station=_X_STATION)


@pytest.mark.skipif(not _PROBE.is_dir(), reason="synthetic wedge fixture absent")
def test_multiple_xy_files_selects_density_not_arbitrary(tmp_path: Path) -> None:
    """Codex DEC-V61-232 R1 P2: when the shockLine set writes several fields (rho, p,
    U) the extractor must select the DENSITY .xy deterministically, not an arbitrary
    file by filesystem order."""
    case = _copy_case(tmp_path)
    q = extract_wedge_qois(case, x_shock_station=_X_STATION)  # rho-only fixture -> beta 45
    # add a pressure profile whose 'shock' sits at a DIFFERENT location (distance 0.80)
    p_rows = [(x, (2.0e5 if x < 0.80 else 1.0e5)) for x in [i * 0.02 + 0.01 for i in range(50)]]
    _write_shock_line_rows(case, p_rows, fname="line_p.xy")
    # density file still drives beta (45), not the pressure file (which would give ~58)
    q2 = extract_wedge_qois(case, x_shock_station=_X_STATION)
    assert q2.shock_angle_beta_deg == pytest.approx(q.shock_angle_beta_deg, abs=1e-6)
    assert q2.shock_angle_beta_deg == pytest.approx(45.0, abs=1e-6)


@pytest.mark.skipif(not _PROBE.is_dir(), reason="synthetic wedge fixture absent")
def test_ambiguous_xy_without_density_match_fails_closed(tmp_path: Path) -> None:
    """If several .xy exist and none unambiguously carries the density field, refuse
    to guess — fail closed rather than measure beta from the wrong signal."""
    case = _copy_case(tmp_path)
    time_dir = next((case / "postProcessing" / "shockLine").glob("*"))
    # rename the rho file so NOTHING matches 'rho', and add a second non-matching file
    (time_dir / "line_rho.xy").rename(time_dir / "line_p.xy")
    (time_dir / "line_U.xy").write_text("# x v\n0.1\t1.0\n0.2\t1.0\n", encoding="utf-8")
    with pytest.raises(WedgeShockExtractorError):
        extract_wedge_qois(case, x_shock_station=_X_STATION)


@pytest.mark.skipif(not _PROBE.is_dir(), reason="synthetic wedge fixture absent")
def test_lone_wrong_field_xy_fails_closed(tmp_path: Path) -> None:
    """Codex DEC-V61-232 R2 P1: if the ONLY sampled-line file is not the density field
    (e.g. a misconfigured set emitted just line_p.xy), the extractor must fail closed
    rather than measure beta from the wrong signal — a lone file is not a free pass."""
    case = _copy_case(tmp_path)
    time_dir = next((case / "postProcessing" / "shockLine").glob("*"))
    (time_dir / "line_rho.xy").rename(time_dir / "line_p.xy")  # only a pressure profile remains
    with pytest.raises(WedgeShockExtractorError):
        extract_wedge_qois(case, x_shock_station=_X_STATION)


def test_missing_postprocessing_is_honest_error(tmp_path: Path) -> None:
    """No silent default: an empty case dir raises rather than fabricating QoIs."""
    with pytest.raises((FileNotFoundError, WedgeShockExtractorError)):
        extract_wedge_qois(tmp_path, x_shock_station=_X_STATION)
