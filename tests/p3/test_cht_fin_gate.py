"""P3 W3.3a · coverage test for the CHT straight-fin analytical gate.

This is the "gate-wiring" coverage test: it drives the RECORDED live-OF11 probe
outputs (reports/showcase_aero/_w33a_fin_probe/postProcessing/) through the QoI
extractor and the cht_analytical gate, and asserts the gate PASSES — with NO
live Docker / OpenFOAM run. CI reproduces the W3.3a milestone from frozen
artifacts every time.

Honesty locks exercised here (complementary to test_cht_straight_fin_gold.py,
which locks the *reference* against fabrication):
  - the gate is REAL: a doctored Q_base / T_tip flips it to FAIL (the gate is not
    a constant-true);
  - the extractor MEASURES (does not echo the gold): the extracted eta differs
    from the committed reference at the 4th decimal yet lands inside tolerance;
  - energy closure |Q_base + Q_fin| ~ 0 confirms the adiabatic-tip balance.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from src.cht_fin_extractor import extract_fin_qois, to_key_quantities
from src.cht_fin_gate import gate_fin_against_gold

_REPO = Path(__file__).resolve().parents[2]
_PROBE = _REPO / "reports" / "showcase_aero" / "_w33a_fin_probe"
_GOLD = _REPO / "knowledge" / "gold_standards" / "cht_straight_fin.yaml"

# Live W3.3a probe outcome (see .planning/intel/p3_w33a/fin_probe_evidence.md).
_SIM_ETA = 0.77354
_SIM_TIP = 0.66622
_GOLD_ETA = 0.77402
_GOLD_TIP = 0.66604


def _fin_inputs() -> dict:
    docs = [d for d in yaml.safe_load_all(_GOLD.read_text(encoding="utf-8")) if d]
    return docs[0]["case_info"]["fin_inputs"]


def _extract_from_probe():
    fin = _fin_inputs()
    return extract_fin_qois(
        _PROBE,
        h_conv=float(fin["h_conv"]),
        w=float(fin["w"]),
        t=float(fin["t"]),
        L=float(fin["L"]),
        T_inf=float(fin["T_inf"]),
    )


@pytest.mark.skipif(not _PROBE.is_dir(), reason="recorded W3.3a probe artifacts absent")
def test_extractor_reproduces_recorded_probe_qois() -> None:
    qois = _extract_from_probe()
    # values must match the recorded live probe to 3 decimals
    assert qois.fin_efficiency == pytest.approx(_SIM_ETA, abs=5e-4), qois
    assert qois.fin_tip_temperature_ratio == pytest.approx(_SIM_TIP, abs=5e-4), qois
    # raw channels are the integrated solver output, not the dimensionless QoIs
    assert qois.q_base_w == pytest.approx(775.857, abs=0.01)
    assert qois.t_tip_k == pytest.approx(366.622, abs=0.01)
    assert qois.t_base_k == pytest.approx(400.0, abs=0.01)


@pytest.mark.skipif(not _PROBE.is_dir(), reason="recorded W3.3a probe artifacts absent")
def test_energy_closure_adiabatic_tip() -> None:
    qois = _extract_from_probe()
    # adiabatic tip: all base-injected heat leaves through the fin surface
    assert qois.energy_residual_w < 1e-3 * abs(qois.q_base_w), qois.energy_residual_w


@pytest.mark.skipif(not _PROBE.is_dir(), reason="recorded W3.3a probe artifacts absent")
def test_cht_analytical_gate_passes_on_recorded_probe() -> None:
    result = gate_fin_against_gold(_PROBE, gold_path=_GOLD)
    assert result.passed, result.summary
    names = {name for name, _ in result.comparisons}
    assert names == {"fin_efficiency", "fin_tip_temperature_ratio"}
    for name, cmp in result.comparisons:
        assert cmp.passed, f"{name}: {cmp.summary}"


@pytest.mark.skipif(not _PROBE.is_dir(), reason="recorded W3.3a probe artifacts absent")
def test_extractor_measures_does_not_echo_gold() -> None:
    """The extracted QoIs come from the solver, so they differ from the gold
    reference (which is the exact closed form) — yet land inside tolerance.
    If the extractor were echoing the gold this assertion would fail."""
    qois = _extract_from_probe()
    assert qois.fin_efficiency != pytest.approx(_GOLD_ETA, abs=1e-6)
    assert qois.fin_tip_temperature_ratio != pytest.approx(_GOLD_TIP, abs=1e-6)
    # but the (small) discretisation gap is well inside the 5% gate
    assert abs(qois.fin_efficiency - _GOLD_ETA) / _GOLD_ETA < 0.05
    assert abs(qois.fin_tip_temperature_ratio - _GOLD_TIP) / _GOLD_TIP < 0.05


@pytest.mark.skipif(not _PROBE.is_dir(), reason="recorded W3.3a probe artifacts absent")
def test_gate_is_real_doctored_q_base_fails(tmp_path: Path) -> None:
    """Genuineness: a wrong solver Q_base must flip the gate to FAIL. Proves the
    gate compares real output against the reference rather than rubber-stamping."""
    case = tmp_path / "doctored"
    shutil.copytree(_PROBE / "postProcessing", case / "postProcessing")
    bad = case / "postProcessing" / "basePower" / "0" / "surfaceFieldValue.dat"
    text = bad.read_text(encoding="utf-8")
    # rewrite the converged base power (775.857 W) to a value ~23% off
    text = text.replace("7.7585718688e+02", "6.0000000000e+02")
    bad.write_text(text, encoding="utf-8")

    result = gate_fin_against_gold(case, gold_path=_GOLD)
    assert not result.passed, result.summary
    eff = next(cmp for name, cmp in result.comparisons if name == "fin_efficiency")
    assert not eff.passed


@pytest.mark.skipif(not _PROBE.is_dir(), reason="recorded W3.3a probe artifacts absent")
def test_doctored_tip_temperature_changes_tip_ratio(tmp_path: Path) -> None:
    """The tip-ratio QoI is genuinely a function of the measured T_tip."""
    case = tmp_path / "doctored_tip"
    shutil.copytree(_PROBE / "postProcessing", case / "postProcessing")
    bad = case / "postProcessing" / "tipT" / "0" / "surfaceFieldValue.dat"
    text = bad.read_text(encoding="utf-8")
    text = text.replace("3.6662247153e+02", "3.5000000000e+02")  # cooler tip
    bad.write_text(text, encoding="utf-8")

    fin = _fin_inputs()
    qois = extract_fin_qois(
        case,
        h_conv=float(fin["h_conv"]),
        w=float(fin["w"]),
        t=float(fin["t"]),
        L=float(fin["L"]),
        T_inf=float(fin["T_inf"]),
    )
    # (350 - 300) / (400 - 300) = 0.5
    assert qois.fin_tip_temperature_ratio == pytest.approx(0.5, abs=1e-9)


@pytest.mark.skipif(not _PROBE.is_dir(), reason="recorded W3.3a probe artifacts absent")
def test_to_key_quantities_uses_gold_quantity_names() -> None:
    """The comparator looks up gold `quantity` names in key_quantities; the
    extractor's keys must match exactly (else the gate silently SKIPs)."""
    kq = to_key_quantities(_extract_from_probe())
    assert set(kq) == {"fin_efficiency", "fin_tip_temperature_ratio"}


def test_missing_postprocessing_is_honest_error(tmp_path: Path) -> None:
    """No silent default: an empty case dir raises rather than fabricating QoIs."""
    with pytest.raises(FileNotFoundError):
        extract_fin_qois(tmp_path, h_conv=100.0, w=1.0, t=0.003, L=0.05, T_inf=300.0)
