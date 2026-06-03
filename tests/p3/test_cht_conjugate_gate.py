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
        k_fluid=float(ci["k_fluid"]),
        cp=float(ci["cp"]),
    )


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
    case = tmp_path / "doctored_q"
    shutil.copytree(_PROBE / "postProcessing", case / "postProcessing")
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
    case = tmp_path / "doctored_tout"
    shutil.copytree(_PROBE / "postProcessing", case / "postProcessing")
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


@pytest.mark.skipif(not _PROBE.is_dir(), reason="recorded W3.3b probe artifacts absent")
def test_reynolds_validity_is_a_hard_gate(tmp_path: Path) -> None:
    """A gold whose Re falls outside the Gnielinski validity band must FAIL even
    when Nu + energy still pass. Applying the correlation out of range is
    dishonest; the gate refuses."""
    docs = list(yaml.safe_load_all(_GOLD.read_text(encoding="utf-8")))
    docs = [d for d in docs if d]
    docs[0]["case_info"]["conjugate_inputs"]["Re"] = 1000.0  # below 3000 floor
    bad_gold = tmp_path / "out_of_band_gold.yaml"
    bad_gold.write_text(
        "\n---\n".join(yaml.safe_dump(d, sort_keys=False) for d in docs),
        encoding="utf-8",
    )

    result = gate_conjugate_against_gold(_PROBE, gold_path=bad_gold)
    # Nu + energy are unchanged (same artifacts) ...
    assert all(cmp.passed for _, cmp in result.comparisons), result.summary
    assert result.energy_balance_ok
    # ... but Re is out of band, so the gate as a whole FAILS
    assert not result.reynolds_in_band
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
        extract_conjugate_qois(tmp_path, D_h=0.05, k_fluid=0.0263, cp=1007.0)
