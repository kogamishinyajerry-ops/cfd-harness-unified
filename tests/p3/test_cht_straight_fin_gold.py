"""P3 W3.3a · self-verifying test for the straight-fin CHT gold standard.

The whole point of choosing an analytically-exact benchmark (DEC-V61-226
research, ratified 2026-06-03) is that its reference values are CLOSED-FORM
functions of the inputs — not transcribed numbers that could be wrong or
fabricated (cf. the lid_driven_cavity.yaml Phase-0 fabrication that was only
caught at real-solver time). This test RE-DERIVES eta_f and the tip-temperature
ratio from `case_info.fin_inputs` and fails if the committed reference drifts
from the formula. It is the honesty lock on the benchmark.

Closed form (Incropera & DeWitt, FHMT 7th ed., §3.6 Table 3.4, adiabatic tip):
    m = sqrt(h*P/(k*A_c)),  A_c = w*t,  P = 2*(w+t)
    eta_f             = tanh(mL)/(mL)
    theta_tip/theta_b = 1/cosh(mL)
"""
from __future__ import annotations

import math
from pathlib import Path

import yaml

_GOLD = (
    Path(__file__).resolve().parents[2]
    / "knowledge"
    / "gold_standards"
    / "cht_straight_fin.yaml"
)


def _docs() -> list[dict]:
    return [d for d in yaml.safe_load_all(_GOLD.read_text(encoding="utf-8")) if d]


def _eta_and_tip(fin: dict) -> tuple[float, float]:
    k, h, L, t, w = (
        fin["k_solid"],
        fin["h_conv"],
        fin["L"],
        fin["t"],
        fin["w"],
    )
    a_c = w * t
    perim = 2.0 * (w + t)
    m = math.sqrt(h * perim / (k * a_c))
    m_l = m * L
    return math.tanh(m_l) / m_l, 1.0 / math.cosh(m_l)


def test_fin_efficiency_reference_equals_the_analytical_formula() -> None:
    obs = next(d for d in _docs() if d["quantity"] == "fin_efficiency")
    eta, _ = _eta_and_tip(obs["case_info"]["fin_inputs"])
    committed = obs["reference_values"][0]["value"]
    # the committed reference MUST be the closed-form result of its own inputs
    assert abs(committed - eta) < 5e-4, (committed, eta)


def test_tip_temperature_ratio_reference_equals_the_analytical_formula() -> None:
    obs = next(d for d in _docs() if d["quantity"] == "fin_tip_temperature_ratio")
    _, tip = _eta_and_tip(obs["case_info"]["fin_inputs"])
    committed = obs["reference_values"][0]["value"]
    assert abs(committed - tip) < 5e-4, (committed, tip)


def test_both_observables_present_with_disciplined_tolerance_and_cited_source() -> None:
    docs = _docs()
    assert {d["quantity"] for d in docs} == {
        "fin_efficiency",
        "fin_tip_temperature_ratio",
    }
    for d in docs:
        assert d["tolerance"] == 0.05  # project gold-standard convention
        assert "Incropera" in d["source"]  # cited, analytical
        assert d["reference_values"][0]["value"] > 0


def test_inputs_are_internally_consistent_across_both_observables() -> None:
    # both observables must derive from the SAME fin — guards a copy-paste skew
    fins = [d["case_info"]["fin_inputs"] for d in _docs()]
    keys = ("k_solid", "h_conv", "L", "t", "w")
    assert all(fins[0][k] == f[k] for f in fins for k in keys)
