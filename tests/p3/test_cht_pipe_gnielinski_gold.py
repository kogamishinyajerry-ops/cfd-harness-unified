"""P3 W3.3b-A · self-verifying test for the Gnielinski conjugate-pipe gold.

The reference Nu is a CLOSED-FORM function of (Re, Pr) — not a transcribed number.
This test RE-DERIVES Nu from `case_info.conjugate_inputs` via the Gnielinski
correlation and fails if the committed value drifts; it also checks the inputs
are internally consistent (nu=mu/rho, Re=U*D/nu, Pr=mu*cp/k). It is the honesty
lock on the benchmark reference (mirrors test_cht_straight_fin_gold.py).

Closed form (Gnielinski 1976; Incropera FHMT 7th ed. Eq. 8.62):
    f  = (0.790 ln(Re) - 1.64)^(-2)
    Nu = (f/8)(Re - 1000) Pr / (1 + 12.7 sqrt(f/8) (Pr^(2/3) - 1))
"""
from __future__ import annotations

import math
from pathlib import Path

import yaml

_GOLD = (
    Path(__file__).resolve().parents[2]
    / "knowledge"
    / "gold_standards"
    / "cht_pipe_gnielinski.yaml"
)


def _docs() -> list[dict]:
    return [d for d in yaml.safe_load_all(_GOLD.read_text(encoding="utf-8")) if d]


def _gnielinski_nu(Re: float, Pr: float) -> float:
    f = (0.790 * math.log(Re) - 1.64) ** -2
    return (f / 8.0) * (Re - 1000.0) * Pr / (
        1.0 + 12.7 * math.sqrt(f / 8.0) * (Pr ** (2.0 / 3.0) - 1.0)
    )


def test_nusselt_reference_equals_the_gnielinski_formula() -> None:
    obs = next(d for d in _docs() if d["quantity"] == "nusselt_number")
    ci = obs["case_info"]["conjugate_inputs"]
    nu_derived = _gnielinski_nu(float(ci["Re"]), float(ci["Pr"]))
    committed = obs["reference_values"][0]["value"]
    # the committed reference MUST be the closed-form result of its own inputs
    assert abs(committed - nu_derived) < 5e-3, (committed, nu_derived)


def test_inputs_are_internally_consistent() -> None:
    ci = next(d for d in _docs() if d["quantity"] == "nusselt_number")["case_info"][
        "conjugate_inputs"
    ]
    rho, mu, cp, k_f, D = (
        float(ci["rho"]),
        float(ci["mu"]),
        float(ci["cp"]),
        float(ci["k_fluid"]),
        float(ci["D"]),
    )
    nu, Re, Pr, U = float(ci["nu"]), float(ci["Re"]), float(ci["Pr"]), float(ci["U_inlet"])
    # properties are reported to ~5 sig figs, so consistency is checked at 1e-4
    # relative (catches typos / gross errors, not last-digit rounding)
    assert math.isclose(nu, mu / rho, rel_tol=1e-4), (nu, mu / rho)          # nu = mu/rho
    assert math.isclose(Pr, mu * cp / k_f, rel_tol=1e-4), (Pr, mu * cp / k_f)  # Pr = mu*cp/k
    assert math.isclose(Re, U * D / nu, rel_tol=2e-4), (Re, U * D / nu)        # Re = U*D/nu


def test_reynolds_and_prandtl_in_gnielinski_validity_band() -> None:
    ci = next(d for d in _docs() if d["quantity"] == "nusselt_number")["case_info"][
        "conjugate_inputs"
    ]
    assert 3000.0 < float(ci["Re"]) < 5.0e6
    assert 0.5 < float(ci["Pr"]) < 2000.0


def test_disciplined_tolerance_is_ten_percent_with_cited_source() -> None:
    obs = next(d for d in _docs() if d["quantity"] == "nusselt_number")
    # 10%, NOT the 5% fin convention — honest band for a +/-20% correlation
    assert obs["tolerance"] == 0.10
    assert "Gnielinski" in obs["source"]
    assert obs["reference_values"][0]["value"] > 0
