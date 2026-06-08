"""P4 V71.A · self-verifying test for the supersonic-wedge oblique-shock gold.

The whole point of choosing an analytically-exact benchmark (DEC-V61-232) is that
its reference values are CLOSED-FORM functions of the inputs — not transcribed
numbers that could be wrong or fabricated (cf. lid_driven_cavity.yaml Phase-0
fabrication, caught only at real-solver time; and E22's own beta=42deg error,
corrected by this slice). This test RE-DERIVES beta, M2, and the p/rho/T ratios
from `case_info.wedge_inputs` and fails if any committed reference drifts from the
formula. It is the honesty lock on the benchmark and needs NO solver run.

Closed form (Anderson, Modern Compressible Flow 3rd ed., Ch.4; NACA Report 1135):
    theta-beta-M:  tan(theta) = 2 cot(beta) (M1^2 sin^2 beta - 1)
                                 / (M1^2 (gamma + cos 2 beta) + 2)   [weak root]
    M1n = M1 sin(beta)
    p2/p1     = 1 + 2 gamma/(gamma+1) (M1n^2 - 1)
    rho2/rho1 = (gamma+1) M1n^2 / ((gamma-1) M1n^2 + 2)
    T2/T1     = (p2/p1) / (rho2/rho1)
    M2n       = sqrt((1 + (gamma-1)/2 M1n^2) / (gamma M1n^2 - (gamma-1)/2))
    M2        = M2n / sin(beta - theta)
"""
from __future__ import annotations

import math
from pathlib import Path

import pytest
import yaml

_GOLDS = (
    Path(__file__).resolve().parents[2] / "knowledge" / "gold_standards" / "wedge_oblique_shock.yaml",
    Path(__file__).resolve().parents[2]
    / "knowledge"
    / "gold_standards"
    / "wedge_oblique_shock_theta10.yaml",
)


def _docs(path: Path) -> list[dict]:
    return [d for d in yaml.safe_load_all(path.read_text(encoding="utf-8")) if d]


def _solve_oblique_shock(M1: float, theta_deg: float, gamma: float) -> dict[str, float]:
    """Independently re-derive the weak-root oblique-shock state from (M1, theta, gamma).

    Deliberately a SEPARATE implementation from src/wedge_oblique_shock_gate.py so a
    bug shared with the gate would not hide a drifted committed reference.
    """
    if M1 <= 1.0:
        raise ValueError(f"no oblique shock for subsonic M1={M1}")
    theta = math.radians(theta_deg)
    mach_angle = math.asin(1.0 / M1)

    def theta_of_beta(beta: float) -> float:
        num = 2.0 / math.tan(beta) * (M1**2 * math.sin(beta) ** 2 - 1.0)
        den = M1**2 * (gamma + math.cos(2.0 * beta)) + 2.0
        return math.atan(num / den)

    # locate the theta-max beta (boundary between weak and strong roots), then
    # bisect for theta on the WEAK side [mach_angle, beta_thetamax].
    samples = 20001
    betas = [mach_angle + (math.radians(90.0) - mach_angle) * i / (samples - 1) for i in range(samples)]
    thetas = [theta_of_beta(b) for b in betas]
    i_max = max(range(len(thetas)), key=lambda i: thetas[i])
    if theta > thetas[i_max]:
        raise ValueError(f"theta={theta_deg} exceeds detachment theta_max for M1={M1}")
    lo, hi = mach_angle, betas[i_max]
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if theta_of_beta(mid) < theta:
            lo = mid
        else:
            hi = mid
    beta = 0.5 * (lo + hi)

    M1n = M1 * math.sin(beta)
    p2_p1 = 1.0 + 2.0 * gamma / (gamma + 1.0) * (M1n**2 - 1.0)
    rho2_rho1 = (gamma + 1.0) * M1n**2 / ((gamma - 1.0) * M1n**2 + 2.0)
    T2_T1 = p2_p1 / rho2_rho1
    M2n = math.sqrt((1.0 + (gamma - 1.0) / 2.0 * M1n**2) / (gamma * M1n**2 - (gamma - 1.0) / 2.0))
    M2 = M2n / math.sin(beta - theta)
    return {
        "shock_angle_beta_deg": math.degrees(beta),
        "mach_downstream": M2,
        "pressure_ratio": p2_p1,
        "density_ratio": rho2_rho1,
        "temperature_ratio": T2_T1,
    }


_EXPECTED_QUANTITIES = {
    "shock_angle_beta_deg",
    "mach_downstream",
    "pressure_ratio",
    "density_ratio",
    "temperature_ratio",
}


@pytest.mark.parametrize("gold_path", _GOLDS, ids=lambda p: p.stem)
def test_every_reference_equals_the_oblique_shock_formula(gold_path: Path) -> None:
    docs = _docs(gold_path)
    wi = docs[0]["case_info"]["wedge_inputs"]
    derived = _solve_oblique_shock(
        M1=float(wi["M1"]), theta_deg=float(wi["theta_deg"]), gamma=float(wi["gamma"])
    )
    for doc in docs:
        q = doc["quantity"]
        committed = doc["reference_values"][0]["value"]
        # the committed reference MUST be the closed-form result of its own inputs.
        # beta is O(40 deg) so 5e-3 abs is ~1e-4 relative; ratios are O(1-2) so 5e-3
        # abs is a 4-significant-figure lock — tight enough to catch a transcription typo.
        assert abs(committed - derived[q]) < 5e-3, (q, committed, derived[q])


@pytest.mark.parametrize("gold_path", _GOLDS, ids=lambda p: p.stem)
def test_all_five_observables_present_with_disciplined_tolerance_and_cited_source(
    gold_path: Path,
) -> None:
    docs = _docs(gold_path)
    assert {d["quantity"] for d in docs} == _EXPECTED_QUANTITIES
    for d in docs:
        assert d["tolerance"] == 0.03  # P4 analytical-class tolerance (eval E22 signature)
        assert "Anderson" in d["source"]  # cited, analytical (NOT experimental)
        assert d["reference_values"][0]["value"] > 0


@pytest.mark.parametrize("gold_path", _GOLDS, ids=lambda p: p.stem)
def test_inputs_are_internally_consistent_across_all_observables(gold_path: Path) -> None:
    # every observable must derive from the SAME wedge — guards a copy-paste skew
    wedges = [d["case_info"]["wedge_inputs"] for d in _docs(gold_path)]
    keys = ("M1", "theta_deg", "gamma", "x_shock_station", "beta_validity_min_deg")
    assert all(wedges[0][k] == w[k] for w in wedges for k in keys)


@pytest.mark.parametrize("gold_path", _GOLDS, ids=lambda p: p.stem)
def test_solution_is_a_valid_weak_oblique_shock(gold_path: Path) -> None:
    wi = _docs(gold_path)[0]["case_info"]["wedge_inputs"]
    M1 = float(wi["M1"])
    derived = _solve_oblique_shock(M1=M1, theta_deg=float(wi["theta_deg"]), gamma=float(wi["gamma"]))
    mach_angle_deg = math.degrees(math.asin(1.0 / M1))
    # supersonic inflow + beta above the Mach angle + WEAK shock (downstream still supersonic)
    assert M1 > 1.0
    assert derived["shock_angle_beta_deg"] > mach_angle_deg
    assert derived["mach_downstream"] > 1.0
    # the declared Mach-angle floor must equal the real Mach angle for this M1
    assert float(wi["beta_validity_min_deg"]) == pytest.approx(mach_angle_deg, abs=1e-6)


def test_two_angles_give_distinct_references() -> None:
    # the secondary (theta=10) is a genuinely different operating point, not a copy
    primary = _docs(_GOLDS[0])
    secondary = _docs(_GOLDS[1])
    p_beta = next(d for d in primary if d["quantity"] == "shock_angle_beta_deg")
    s_beta = next(d for d in secondary if d["quantity"] == "shock_angle_beta_deg")
    assert p_beta["reference_values"][0]["value"] != s_beta["reference_values"][0]["value"]
    # weaker deflection -> smaller shock angle
    assert s_beta["reference_values"][0]["value"] < p_beta["reference_values"][0]["value"]


# ---------------------------------------------------------------------------
# machine-readable validation_status (DEC-V61-232 forward-hardening, landed with the
# DEC-V61-233 live slice): the run-validation status is a STRUCTURED key, not a YAML
# comment. These tests are its CURRENT consumer (a test-enforced honesty invariant that
# blocks an un-run reference being machine-read as validated); it is also a forward hook
# coverage tooling CAN read (no production consumer reads it yet — Codex R0 P2-2). Named
# validation_status (NOT contract_status) to avoid colliding with the codebase's
# load-bearing physics_contract.contract_status (physics-compatibility axis, read by
# src/report_engine/contract_dashboard.py + src/error_attributor.py).
# ---------------------------------------------------------------------------

_LIVE_VALIDATED = "LIVE_VALIDATED"
_PENDING_STATUSES = {"ANALYTICAL_REFERENCE_AUTHORED"}  # explicitly NOT a validated value


def test_primary_gold_is_machine_readable_live_validated() -> None:
    """The primary (theta=15) gold carries a structured case_info.validation_status =
    LIVE_VALIDATED on every observable doc — the live rhoCentralFoam solve (DEC-V61-233)
    backs it. This test reads the STRUCTURED key (not the header comment); coverage
    tooling CAN read it the same way (no production consumer does yet)."""
    statuses = {d["case_info"]["validation_status"] for d in _docs(_GOLDS[0])}
    assert statuses == {_LIVE_VALIDATED}


def test_secondary_gold_is_not_machine_readable_as_validated() -> None:
    """The theta=10 sensitivity gold has NO live run: its structured validation_status
    must NOT be a validated value, so coverage tooling can never read the un-run
    reference as validated — the exact reason the status was promoted from a comment."""
    statuses = {d["case_info"]["validation_status"] for d in _docs(_GOLDS[1])}
    assert _LIVE_VALIDATED not in statuses
    assert statuses == _PENDING_STATUSES


def test_every_gold_doc_has_a_structured_validation_status() -> None:
    """No doc may silently omit the machine-readable status (a missing key would let
    tooling fall back to guessing). Distinct from physics_contract.contract_status."""
    for gold in _GOLDS:
        for doc in _docs(gold):
            assert "validation_status" in doc["case_info"], (gold.stem, doc["quantity"])
            # must NOT shadow the load-bearing physics-compatibility key name
            assert "contract_status" not in doc["case_info"], (gold.stem, doc["quantity"])
