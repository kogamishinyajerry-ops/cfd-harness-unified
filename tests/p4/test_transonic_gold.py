"""V73.A gold-standard pins + closed-form re-derivations (DEC-V61-238).

The closed forms in src/transonic_airfoil_gate.py are pinned here against
hand-computed values (independent of the implementation), and the shipped
rae2822_case9.yaml is pinned field-by-field so any silent edit — especially
to the verification-status fields or the tier-2 role skeleton — breaks loudly.
"""
from pathlib import Path

import pytest
import yaml

from src.transonic_airfoil_gate import (
    _ENFORCED_QOI_SET,
    cp_critical,
    cp_stagnation,
    cp_vacuum,
)

REPO = Path(__file__).resolve().parents[2]
GOLD = REPO / "knowledge" / "gold_standards" / "rae2822_case9.yaml"


class TestClosedForms:
    """Hand-derived pins (gamma = 1.4).

    Cp_stag = 2/(g M^2) [(1 + (g-1)/2 M^2)^(g/(g-1)) - 1]
    Cp*     = 2/(g M^2) [((2 + (g-1) M^2)/(g+1))^(g/(g-1)) - 1]
    Cp_vac  = -2/(g M^2)
    """

    def test_cp_stagnation_case9(self):
        # M=0.734: 2/(1.4*0.538756) * ((1.1077512)^3.5 - 1) = 1.1421
        assert cp_stagnation(0.734) == pytest.approx(1.1421, abs=1e-3)

    def test_cp_critical_case9(self):
        # M=0.734: 2.651611 * ((0.9231260)^3.5 - 1) = -0.6475
        assert cp_critical(0.734) == pytest.approx(-0.6475, abs=1e-3)

    def test_cp_critical_nominal_mach(self):
        # M=0.730 — the textbook ~-0.662 value
        assert cp_critical(0.730) == pytest.approx(-0.6621, abs=1e-3)

    def test_cp_vacuum_case9(self):
        # -2/(1.4*0.538756) = -2.6516
        assert cp_vacuum(0.734) == pytest.approx(-2.6516, abs=1e-3)

    def test_cp_critical_is_zero_at_sonic_freestream(self):
        assert cp_critical(1.0) == pytest.approx(0.0, abs=1e-12)

    def test_cp_stagnation_incompressible_limit(self):
        # M -> 0: Cp_stag -> 1 (+ M^2/4 compressibility correction)
        assert cp_stagnation(0.1) == pytest.approx(1.0025, abs=1e-3)
        assert cp_stagnation(0.734) > cp_stagnation(0.3) > 1.0

    def test_vacuum_floor_identity_documented(self):
        """The reason there is NO vacuum-floor tier-1 gate: with the measured
        normalization, p_inf/q_inf == -Cp_vac identically, so Cp >= Cp_vac is
        exactly p_abs >= 0 (enforced in the extractor)."""
        for mach in (0.3, 0.734, 0.9):
            gamma = 1.4
            q_over_p = 0.5 * gamma * mach * mach   # q/p for a perfect gas
            assert 1.0 / q_over_p == pytest.approx(-cp_vacuum(mach, gamma), rel=1e-12)


class TestGoldPins:
    @pytest.fixture(scope="class")
    def doc(self):
        return yaml.safe_load(GOLD.read_text())

    def test_quantity_and_id(self, doc):
        assert doc["quantity"] == "transonic_airfoil_sbli"
        assert doc["case_info"]["id"] == "rae2822_case9"
        assert doc["case_info"]["validation_status"] == "SCAFFOLD_AUTHORED"

    def test_operating_point_corrected_values(self, doc):
        op = doc["operating_point"]
        assert op["mach"] == pytest.approx(0.734)
        assert op["alpha_deg"] == pytest.approx(2.79)
        assert op["reynolds"] == pytest.approx(6.5e6)
        assert op["chord_m"] == pytest.approx(1.0)
        assert op["gamma"] == pytest.approx(1.4)
        assert op["r_specific_J_kgK"] == pytest.approx(287.058)

    def test_operating_point_is_declared_not_verified(self, doc):
        assert doc["operating_point_verification"] == "DECLARED-NOT-VERIFIED"
        dispute = doc["user_adjudication_pending"]
        assert "0.730" in dispute and "0.734" in dispute, (
            "the nominal-vs-corrected dispute must stay visible until adjudicated"
        )

    def test_tier2_anchor_is_null_and_not_verified(self, doc):
        t2 = doc["tier2_anchor"]
        assert t2["anchor_verification"] == "DECLARED-NOT-VERIFIED"
        assert t2["provenance"] is None
        assert all(c["value"] is None for c in t2["candidates"]), (
            "undigitized ballparks must stay prose, never values (fake-anchor lesson)"
        )

    def test_tier2_role_skeleton_matches_code_pin(self, doc):
        roles = {c["qoi"]: c["role"] for c in doc["tier2_anchor"]["candidates"]}
        enforced = {q for q, r in roles.items() if r == "ENFORCED"}
        assert enforced == _ENFORCED_QOI_SET == {"cl", "shock_xc"}
        assert roles["cd"] == "ADVISORY"

    def test_tolerances_pinned(self, doc):
        tol = doc["tolerances"]
        assert tol["mach_atol"] == pytest.approx(0.005)
        assert tol["alpha_atol_deg"] == pytest.approx(0.2)
        assert tol["reynolds_rtol"] == pytest.approx(0.10)
        assert tol["stagnation_margin"] == pytest.approx(0.05)
        assert tol["shock_band"] == [pytest.approx(0.2), pytest.approx(0.9)]
        assert tol["cl_crosscheck_rtol"] == pytest.approx(0.05)

    def test_provenance_prose_present(self, doc):
        info = doc["case_info"]
        assert "AGARD" in info["benchmark"]
        assert "rhoSimpleFoam" in info["solver_plan"]
        assert "rhoCentralFoam" in info["solver_plan"], "fallback solver must stay pinned"
