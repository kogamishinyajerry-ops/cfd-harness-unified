"""P3 W3.3b · coverage test for the CHT full two-region conjugate gate.

This is the milestone "coverage flip" test (runnable-coverage 1->2). It drives
the RECORDED live-OF11 conjugate probe outputs
(reports/showcase_aero/_w33b_pipe_probe/postProcessing/) through the QoI
extractor and the cht_conjugate gate, and asserts the gate PASSES — with NO
live Docker / OpenFOAM run. CI reproduces the W3.3b milestone from frozen
artifacts every time.

The artifacts are a converged tail (last 60 rows) of a transient foamMultiRun
solve: fluid[kOmegaSST] + conducting solid, coupledTemperature interface, OF11,
Re=50000 air, restarted from a mapFields-mapped converged field on a resolved
(y+~0.8) mesh. The FLUID flow PRODUCES h; the gate compares the fluid-produced
Nu against the Gnielinski (1976) reference (vs W3.3a, which validated only solid
conduction + an IMPOSED Robin h).

Honesty locks exercised here (complementary to test_cht_pipe_gnielinski_gold.py,
which locks the *reference* against fabrication):
  - the gate is REAL: a wrong wall heat flux flips Nu out of band -> FAIL;
  - energy balance is a HARD gate: a doctored outlet T breaks the
    interface-heat == enthalpy-rise closure -> FAIL even when Nu still matches;
  - Reynolds validity is a HARD gate: a gold whose Re falls outside the
    Gnielinski band fails even when Nu + energy still pass;
  - the extractor MEASURES (does not echo the gold): the extracted Nu differs
    from the committed reference (113.2 vs 104.8) yet lands inside the 10% band;
  - missing artifacts raise rather than fabricate a default.
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

import pytest
import yaml

from src.cht_conjugate_extractor import (
    ConjugateExtractorError,
    extract_conjugate_qois,
    to_key_quantities,
)
from src.cht_conjugate_gate import gate_conjugate_against_gold

_REPO = Path(__file__).resolve().parents[2]
_PROBE = _REPO / "reports" / "showcase_aero" / "_w33b_pipe_probe"
_GOLD = _REPO / "knowledge" / "gold_standards" / "cht_pipe_gnielinski.yaml"

# Recorded live W3.3b probe outcome (converged tail, Re=50000 resolved mesh).
_SIM_NU = 113.2126
_GOLD_NU = 104.7987


def _conjugate_inputs() -> dict:
    docs = [d for d in yaml.safe_load_all(_GOLD.read_text(encoding="utf-8")) if d]
    return docs[0]["case_info"]["conjugate_inputs"]


def _extract_from_probe():
    ci = _conjugate_inputs()
    return extract_conjugate_qois(
        _PROBE,
        D_h=float(ci["D"]),
        fluid_region=str(ci.get("fluid_region", "fluid")),
    )


def _copy_case(tmp_path: Path) -> Path:
    """Copy the full frozen case (postProcessing + constant + system + 0) to tmp.

    The extractor now reads fluid properties from constant/<region>/physicalProperties,
    so doctoring tests must replay a complete case dir, not just postProcessing/."""
    case = tmp_path / "case"
    shutil.copytree(_PROBE, case)
    return case


@pytest.mark.skipif(not _PROBE.is_dir(), reason="recorded W3.3b probe artifacts absent")
def test_extractor_reproduces_recorded_probe_qois() -> None:
    qois = _extract_from_probe()
    # the fluid-produced Nu must match the recorded converged solve
    assert qois.nusselt_number == pytest.approx(_SIM_NU, abs=5e-2), qois
    # raw channels are the integrated solver output, not the dimensionless QoI
    assert qois.q_iface_total_w == pytest.approx(46.0454, abs=0.01)
    assert qois.t_wall_window_k == pytest.approx(349.8190, abs=0.01)
    assert qois.t_bulk_out_k == pytest.approx(319.3955, abs=0.01)
    assert qois.t_in_k == pytest.approx(300.0, abs=0.01)
    assert qois.mdot_kg_s == pytest.approx(2.307500e-3, abs=1e-7)
    # h and driving dT are genuinely assembled (not echoed)
    assert qois.h_w_m2k == pytest.approx(59.55, abs=0.1)
    assert qois.delta_t_window_k == pytest.approx(32.057, abs=0.05)
    # Re is recovered from the SOLVED inlet mass flux + patch area, ~= target 50000
    assert qois.inlet_area_m2 == pytest.approx(1.25e-4, rel=1e-6)
    assert qois.reynolds_solved == pytest.approx(50000.0, rel=1e-4)
    # fluid transport properties are READ FROM THE CASE physicalProperties (Codex R1)
    assert qois.mu_pa_s == pytest.approx(1.846e-5, rel=1e-6)
    assert qois.cp_j_kgk == pytest.approx(1007.0, rel=1e-6)
    assert qois.k_fluid_w_mk == pytest.approx(0.0263, rel=1e-3)
    assert qois.prandtl == pytest.approx(0.70681, rel=1e-4)
    assert qois.rho_kg_m3 == pytest.approx(1.1614, rel=1e-6)


@pytest.mark.skipif(not _PROBE.is_dir(), reason="recorded W3.3b probe artifacts absent")
def test_energy_balance_closes_on_recorded_probe() -> None:
    qois = _extract_from_probe()
    # interface wall-heat integral == fluid enthalpy rise, to well within the 5% gate
    assert qois.energy_balance_residual_w < 0.05 * abs(qois.q_iface_total_w), qois
    # actually closes to ~2% on the resolved mesh
    rel = qois.energy_balance_residual_w / abs(qois.q_iface_total_w)
    assert rel < 0.03, rel


@pytest.mark.skipif(not _PROBE.is_dir(), reason="recorded W3.3b probe artifacts absent")
def test_cht_conjugate_gate_passes_on_recorded_probe() -> None:
    result = gate_conjugate_against_gold(_PROBE, gold_path=_GOLD)
    assert result.passed, result.summary
    assert result.energy_balance_ok, result.summary
    assert result.reynolds_in_band, result.summary
    assert result.reynolds_matches_target, result.summary
    assert result.prandtl_in_band, result.summary
    assert result.fluid_matches_gold, result.summary
    names = {name for name, _ in result.comparisons}
    assert names == {"nusselt_number"}
    for name, cmp in result.comparisons:
        assert cmp.passed, f"{name}: {cmp.summary}"


@pytest.mark.skipif(not _PROBE.is_dir(), reason="recorded W3.3b probe artifacts absent")
def test_extractor_measures_does_not_echo_gold() -> None:
    """The extracted Nu comes from the solver, so it differs from the Gnielinski
    reference (the closed form) — yet lands inside the 10% band. If the extractor
    were echoing the gold this assertion would fail."""
    qois = _extract_from_probe()
    assert qois.nusselt_number != pytest.approx(_GOLD_NU, abs=1e-3)
    # the (real, model-driven) over-prediction is inside the 10% gate
    assert abs(qois.nusselt_number - _GOLD_NU) / _GOLD_NU < 0.10
    # ... and is genuinely non-trivial (kOmegaSST+const-Prt bias), not ~0
    assert abs(qois.nusselt_number - _GOLD_NU) / _GOLD_NU > 0.02


@pytest.mark.skipif(not _PROBE.is_dir(), reason="recorded W3.3b probe artifacts absent")
def test_gate_is_real_doctored_wall_heat_flux_fails(tmp_path: Path) -> None:
    """Genuineness: a wrong wall heat flux must flip Nu out of band -> FAIL.
    Proves the gate compares real solver output against the reference rather than
    rubber-stamping."""
    case = _copy_case(tmp_path)
    bad = case / "postProcessing" / "qWindowAvg" / "0" / "surfaceFieldValue.dat"
    text = bad.read_text(encoding="utf-8")
    # halve the converged window wall heat flux -> h and Nu collapse below the band
    text = text.replace("1.90898605e+03", "9.0000000000e+02")
    bad.write_text(text, encoding="utf-8")

    result = gate_conjugate_against_gold(case, gold_path=_GOLD)
    assert not result.passed, result.summary
    nu = next(cmp for name, cmp in result.comparisons if name == "nusselt_number")
    assert not nu.passed


@pytest.mark.skipif(not _PROBE.is_dir(), reason="recorded W3.3b probe artifacts absent")
def test_energy_balance_is_a_hard_gate_doctored_outlet_T_fails(tmp_path: Path) -> None:
    """A doctored cup-mixing outlet temperature breaks the interface-heat ==
    enthalpy-rise closure and must FAIL the gate even when the Nu observable still
    matches the reference. Locks energy balance as a hard gate, not decoration."""
    case = _copy_case(tmp_path)
    bad = case / "postProcessing" / "TbulkOut" / "0" / "surfaceFieldValue.dat"
    text = bad.read_text(encoding="utf-8")
    # drop the outlet bulk T toward inlet -> enthalpy rise no longer matches Q_iface
    text = text.replace("3.19395515e+02", "3.0800000000e+02")
    bad.write_text(text, encoding="utf-8")

    result = gate_conjugate_against_gold(case, gold_path=_GOLD)
    # the Nu observable still matches the reference (T_out does not enter Nu) ...
    assert all(cmp.passed for _, cmp in result.comparisons), result.summary
    # ... but energy closure is broken, so the gate as a whole FAILS
    assert not result.energy_balance_ok
    assert not result.passed, result.summary


def _gold_with(tmp_path: Path, **ci_overrides) -> Path:
    """Write a copy of the gold with conjugate_inputs overrides (for hard-gate tests)."""
    docs = [d for d in yaml.safe_load_all(_GOLD.read_text(encoding="utf-8")) if d]
    docs[0]["case_info"]["conjugate_inputs"].update(ci_overrides)
    out = tmp_path / "override_gold.yaml"
    out.write_text(
        "\n---\n".join(yaml.safe_dump(d, sort_keys=False) for d in docs),
        encoding="utf-8",
    )
    return out


@pytest.mark.skipif(not _PROBE.is_dir(), reason="recorded W3.3b probe artifacts absent")
def test_reynolds_is_derived_from_case_not_the_yaml(tmp_path: Path) -> None:
    """Codex R0 P2: the Re hard gate must read the SOLVED flow, not the gold's
    claimed Re. Override the gold's Re to a bogus value: the extracted
    reynolds_solved is unchanged (recovered from the inlet mass flux), and the
    gate FAILS because the replayed case no longer matches the gold's target."""
    bad_gold = _gold_with(tmp_path, Re=99999.0)
    result = gate_conjugate_against_gold(_PROBE, gold_path=bad_gold)
    # reynolds_solved comes from the case (~50000), NOT the YAML's 99999 ...
    assert result.qois.reynolds_solved == pytest.approx(50000.0, rel=1e-4)
    assert result.reynolds_in_band  # 50000 is still inside the validity band
    # ... so the replayed run does not match the gold's claimed flow -> FAIL
    assert not result.reynolds_matches_target
    assert not result.passed, result.summary


@pytest.mark.skipif(not _PROBE.is_dir(), reason="recorded W3.3b probe artifacts absent")
def test_reynolds_out_of_validity_band_is_a_hard_gate(tmp_path: Path) -> None:
    """A gold target below the Gnielinski turbulent floor (3000) must FAIL even
    though Nu + energy still pass: applying the correlation out of range is
    dishonest. (The gate's Re-in-band check on the SOLVED Re is wide; this guards
    the gold contract itself from declaring an out-of-band operating point.)"""
    # target Re=2000 < 3000 floor; reynolds_in_band uses SOLVED Re (50000, in band),
    # but the run no longer matches the (now sub-turbulent) target -> FAIL.
    bad_gold = _gold_with(tmp_path, Re=2000.0)
    result = gate_conjugate_against_gold(_PROBE, gold_path=bad_gold)
    assert all(cmp.passed for _, cmp in result.comparisons), result.summary
    assert result.energy_balance_ok
    assert not result.reynolds_matches_target
    assert not result.passed, result.summary


@pytest.mark.skipif(not _PROBE.is_dir(), reason="recorded W3.3b probe artifacts absent")
def test_prandtl_validity_is_a_hard_gate(tmp_path: Path) -> None:
    """Codex R0 P3: Pr (derived from mu*cp/k_fluid) must lie inside the Gnielinski
    domain. A gold/fluid whose Pr is out of range must FAIL even when Nu + energy
    + Re all pass — the reference correlation is outside its declared validity."""
    # raise the Pr floor above the air value (Pr~0.707) -> out of band
    bad_gold = _gold_with(tmp_path, Pr_validity_min=1.0)
    result = gate_conjugate_against_gold(_PROBE, gold_path=bad_gold)
    assert all(cmp.passed for _, cmp in result.comparisons), result.summary
    assert result.energy_balance_ok
    assert result.reynolds_in_band and result.reynolds_matches_target
    assert not result.prandtl_in_band
    assert not result.passed, result.summary


@pytest.mark.skipif(not _PROBE.is_dir(), reason="recorded W3.3b probe artifacts absent")
def test_reynolds_uses_case_viscosity_not_yaml(tmp_path: Path) -> None:
    """Codex R1 P1: the recovered Re must use the CASE viscosity, not the gold's.
    Double mu in the case physicalProperties (gold unchanged): reynolds_solved
    halves to ~25000 — proving it reads the case — and the gate FAILS (the run no
    longer matches the gold's target flow / reference fluid)."""
    case = _copy_case(tmp_path)
    pp = case / "constant" / "fluid" / "physicalProperties"
    pp.write_text(
        pp.read_text(encoding="utf-8").replace("1.846e-5", "3.692e-5"), encoding="utf-8"
    )
    result = gate_conjugate_against_gold(case, gold_path=_GOLD)
    # Re recovered from the CASE mu (doubled) -> ~25000, NOT the gold's 50000
    assert result.qois.reynolds_solved == pytest.approx(25000.0, rel=1e-3)
    assert not result.reynolds_matches_target
    assert not result.fluid_matches_gold
    assert not result.passed, result.summary


@pytest.mark.skipif(not _PROBE.is_dir(), reason="recorded W3.3b probe artifacts absent")
def test_prandtl_uses_case_properties_not_yaml(tmp_path: Path) -> None:
    """Codex R1 P2: Pr is taken from the CASE physicalProperties. Push the case Pr
    out of the Gnielinski band: prandtl_in_band flips False and the gate FAILS,
    even though the gold contract stays in-range."""
    case = _copy_case(tmp_path)
    pp = case / "constant" / "fluid" / "physicalProperties"
    pp.write_text(
        pp.read_text(encoding="utf-8").replace("0.70681", "3000.0"), encoding="utf-8"
    )
    result = gate_conjugate_against_gold(case, gold_path=_GOLD)
    assert result.qois.prandtl == pytest.approx(3000.0, rel=1e-3)
    assert not result.prandtl_in_band  # 3000 > 2000 upper bound
    assert not result.passed, result.summary


@pytest.mark.skipif(not _PROBE.is_dir(), reason="recorded W3.3b probe artifacts absent")
def test_fluid_mismatch_with_gold_is_a_hard_gate(tmp_path: Path) -> None:
    """Codex R1: the CASE fluid must match the gold reference fluid (the reference
    Nu was derived for it). Change the case specific heat: fluid_matches_gold flips
    False and the gate FAILS even though the gold contract is unchanged."""
    case = _copy_case(tmp_path)
    pp = case / "constant" / "fluid" / "physicalProperties"
    txt = re.sub(r"Cv\s+1007\s*;", "Cv 1500;", pp.read_text(encoding="utf-8"))
    pp.write_text(txt, encoding="utf-8")
    result = gate_conjugate_against_gold(case, gold_path=_GOLD)
    assert result.qois.cp_j_kgk == pytest.approx(1500.0, rel=1e-6)
    assert not result.fluid_matches_gold
    assert not result.passed, result.summary


@pytest.mark.skipif(not _PROBE.is_dir(), reason="recorded W3.3b probe artifacts absent")
def test_to_key_quantities_uses_gold_quantity_names() -> None:
    """The comparator looks up gold `quantity` names in key_quantities; the
    extractor's key must match exactly (else the gate silently SKIPs)."""
    kq = to_key_quantities(_extract_from_probe())
    assert set(kq) == {"nusselt_number"}


def test_missing_postprocessing_is_honest_error(tmp_path: Path) -> None:
    """No silent default: an empty case dir raises rather than fabricating QoIs."""
    with pytest.raises((FileNotFoundError, ConjugateExtractorError)):
        extract_conjugate_qois(tmp_path, D_h=0.05)
