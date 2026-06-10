"""V72.A dam_break_collapse gold self-tests (DEC-V61-237).

Re-derives every closed-form quantity the gold/gate rely on (no magic numbers
survive unverified) and PINS the tier-2 honesty state: flipping the anchor to
VERIFIED, filling candidate values, or weakening the meta-gate MUST show up as
a diff in this file (loop-auditor V72.A F2 pin 1).
"""
import math
from pathlib import Path

import yaml

from src.dam_break_gate import derive_sample_time, ritter_bound

REPO = Path(__file__).resolve().parents[2]
GOLD = REPO / "knowledge" / "gold_standards" / "dam_break_collapse.yaml"


def _doc():
    docs = [d for d in yaml.safe_load_all(GOLD.read_text(encoding="utf-8")) if d]
    (doc,) = [d for d in docs if d.get("quantity") == "surge_front_position"]
    return doc


class TestGoldDerivations:
    def test_aspect_ratio_is_exactly_two(self):
        geo = _doc()["case_info"]["geometry"]
        assert math.isclose(
            geo["column_height_m"] / geo["column_width_a_m"], 2.0, rel_tol=1e-9
        ), "n^2=2 is load-bearing: the M&M variables and t(T) conversion assume it"

    def test_sample_times_re_derive(self):
        # t = T*sqrt(a/(2g)); the gold documents 0.086293 / 0.172586 s
        geo = _doc()["case_info"]["geometry"]
        a, g = geo["column_width_a_m"], geo["gravity_m_s2"]
        assert math.isclose(derive_sample_time(1.0, a, g), 0.086293, abs_tol=5e-6)
        assert math.isclose(derive_sample_time(2.0, a, g), 0.172586, abs_tol=5e-6)

    def test_ritter_reduction_is_2T(self):
        # x = 2 t sqrt(g h0) with h0 = n^2 a  =>  Z = 2T for any aspect ratio.
        # Verify numerically at the gold geometry for both sampled T.
        geo = _doc()["case_info"]["geometry"]
        a, g = geo["column_width_a_m"], geo["gravity_m_s2"]
        h0 = geo["column_height_m"]
        for T in (1.0, 2.0):
            t = derive_sample_time(T, a, g)
            z_ritter_physical = 2.0 * t * math.sqrt(g * h0) / a
            assert math.isclose(z_ritter_physical, ritter_bound(T), rel_tol=1e-9)

    def test_sample_T_contains_zero_for_initial_column_gate(self):
        assert 0.0 in _doc()["sample_T"]

    def test_tolerance_is_ten_percent(self):
        assert _doc()["tolerance"] == 0.10


class TestTier2HonestyPins:
    """F2 pin 1: the CURRENT gold must stay DECLARED-NOT-VERIFIED with null
    candidates; upgrading it is a deliberate, diff-visible act (V72.C)."""

    def test_anchor_is_declared_not_verified(self):
        tier2 = _doc()["tier2_anchor"]
        assert tier2["anchor_verification"] == "DECLARED-NOT-VERIFIED"
        assert tier2["provenance"] is None

    def test_candidates_are_null_until_digitized(self):
        for cand in _doc()["tier2_anchor"]["candidates"]:
            assert cand["Z"] is None, (
                "candidate Z filled without flipping this pin — digitize the "
                "primary source, fill provenance, flip anchor_verification, and "
                "update THIS test in the same commit (audit trail)"
            )

    def test_anchor_meta_gate_holds_for_any_filled_candidate(self):
        # Vacuous today (Z null); the assert arms automatically the moment a
        # candidate is filled: Z*(1+tol) must stay strictly under Ritter 2T.
        doc = _doc()
        tol = doc["tolerance"]
        for cand in doc["tier2_anchor"]["candidates"]:
            if cand["Z"] is not None:
                assert cand["Z"] * (1 + tol) < ritter_bound(cand["T"])

    def test_validation_status_is_scaffold(self):
        assert _doc()["case_info"]["validation_status"] == "SCAFFOLD_AUTHORED", (
            "no live run has been gated against this gold; flipping this field "
            "is reserved for the V72.B/C live-evidence slices"
        )
