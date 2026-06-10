"""V73.A transonic airfoil gate tests (DEC-V61-238).

Doctored-case discipline: every tier-1 sanity gate must BITE on a case built
to violate exactly it (loop-auditor F7), plus the tier-2 consumption triad
(status pin / provenance pin / anchor meta-gate), the role completeness pin,
and the breadth-anchor coverage honesty (NO coverage_eligible field).
"""
import math
from pathlib import Path

import pytest
import yaml

from src.transonic_airfoil_extractor import integrate_cn_ca
from src.transonic_airfoil_gate import (
    TransonicGoldError,
    gate_transonic_airfoil_against_gold,
)
from tests.p4.test_transonic_extractor import (
    ALPHA_DEG,
    SUTH_AS,
    UMAG,
    UX,
    UZ,
    _interp,
    build_case,
    profile_chain,
)

REPO = Path(__file__).resolve().parents[2]
REAL_GOLD = REPO / "knowledge" / "gold_standards" / "rae2822_case9.yaml"

NULL_TIER2 = {
    "anchor_verification": "DECLARED-NOT-VERIFIED",
    "provenance": None,
    "candidates": [
        {"qoi": "cl", "role": "ENFORCED", "value": None, "rel_tol": 0.05},
        {"qoi": "shock_xc", "role": "ENFORCED", "value": None, "atol": 0.05},
        {"qoi": "cd", "role": "ADVISORY", "value": None, "rel_tol": 0.15},
    ],
}


def _gold(tmp_path, tier2_override=None, **top_override):
    doc = {
        "quantity": "transonic_airfoil_sbli",
        "operating_point": {
            "mach": 0.734, "alpha_deg": 2.79, "reynolds": 6.5e6,
            "chord_m": 1.0, "gamma": 1.4, "r_specific_J_kgK": 287.058,
        },
        "operating_point_verification": "DECLARED-NOT-VERIFIED",
        "tolerances": {
            "mach_atol": 0.005, "alpha_atol_deg": 0.2, "reynolds_rtol": 0.10,
            "stagnation_margin": 0.05, "shock_band": [0.2, 0.9],
            "cl_range": [0.0, 2.0], "cd_range": [0.0, 0.1],
            "cl_crosscheck_rtol": 0.05,
        },
        "tier2_anchor": tier2_override if tier2_override is not None else NULL_TIER2,
        "case_info": {"id": "rae2822_case9", "validation_status": "SCAFFOLD_AUTHORED"},
    }
    doc.update(top_override)
    p = tmp_path / "gold.yaml"
    p.write_text(yaml.safe_dump(doc))
    return p


def _gate(case, gold):
    return gate_transonic_airfoil_against_gold(case, gold)


def _rotated(deg):
    a = math.radians(deg)
    return (UMAG * math.cos(a), 0.0, UMAG * math.sin(a))


class TestTier1SanityGates:
    def test_sane_case_is_sanity_pass_not_validated(self, tmp_path):
        r = _gate(build_case(tmp_path), _gold(tmp_path))
        assert r.sanity_passed
        assert r.tier2_mode == "PROVISIONAL"
        assert r.tier2_passed is None
        assert "SANITY-PASS" in r.summary
        assert "validated" not in r.summary.lower(), (
            "tier-1-only verdicts must never claim validation (F3 inheritance)"
        )

    def test_breadth_anchor_has_no_coverage_eligible_field(self, tmp_path):
        """V73 is depth on an already-covered cell: nothing downstream may
        flip runnable-coverage off this verdict."""
        r = _gate(build_case(tmp_path), _gold(tmp_path))
        assert not hasattr(r, "coverage_eligible")
        assert "stays 3" in r.coverage_impact
        assert "stays 3" in r.summary

    def test_frozen_uniform_field_dies_everywhere(self, tmp_path):
        """Anti-tautology: an unrun case (p == p_inf everywhere, Cp == 0)
        must fail stagnation, pocket, shock AND force-range gates."""
        case = build_case(tmp_path, cp_upper=lambda x: 0.0, cp_lower=lambda x: 0.0)
        r = _gate(case, _gold(tmp_path))
        assert not r.stagnation_ok
        assert not r.supersonic_pocket_ok
        assert not r.shock_ok
        assert not r.ranges_ok
        assert not r.cl_crosscheck_ok
        assert not r.sanity_passed

    def test_c0a_declared_freestream_mismatch_bites(self, tmp_path):
        # 0/U doctored +5%: measured (probe) still matches gold, but the
        # declared BC no longer matches the measured field
        case = build_case(
            tmp_path, declared={"u": (UX * 1.05, 0.0, UZ * 1.05)}
        )
        r = _gate(case, _gold(tmp_path))
        assert not r.freestream_mach_ok
        assert r.reynolds_ok, "5% velocity is inside the 10% rough Re gate"
        assert not r.sanity_passed

    def test_c0a_probe_mach_off_gold_bites(self, tmp_path):
        case = build_case(tmp_path, probe={"u": (UX * 0.9, 0.0, UZ * 0.9)})
        r = _gate(case, _gold(tmp_path))
        assert not r.freestream_mach_ok
        assert not r.sanity_passed

    def test_c0a_declared_gold_leg_bites_with_measured_in_between(self, tmp_path):
        """Codex R0 P2: measured M=0.738 sits within atol of BOTH declared
        (0.742) and gold (0.734) — only the declared-gold leg catches the
        2x drift of the declared operating point."""
        f_meas, f_decl = 0.738 / 0.734, 0.742 / 0.734
        case = build_case(
            tmp_path,
            probe={"u": (UX * f_meas, 0.0, UZ * f_meas)},
            declared={"u": (UX * f_decl, 0.0, UZ * f_decl)},
        )
        r = _gate(case, _gold(tmp_path))
        assert not r.freestream_mach_ok
        assert not r.sanity_passed

    def test_c0b_declared_gold_leg_bites_with_measured_in_between(self, tmp_path):
        # alpha_meas = gold + 0.15 (inside both measured legs), alpha_decl =
        # gold + 0.30 (outside the declared-gold leg)
        case = build_case(
            tmp_path,
            probe={"u": _rotated(ALPHA_DEG + 0.15)},
            declared={"u": _rotated(ALPHA_DEG + 0.30)},
        )
        r = _gate(case, _gold(tmp_path))
        assert r.freestream_mach_ok, "|U| unchanged on both sides"
        assert not r.alpha_ok
        assert not r.sanity_passed

    def test_c0b_wrong_incidence_bites(self, tmp_path):
        u = _rotated(ALPHA_DEG + 1.2)
        case = build_case(tmp_path, probe={"u": u}, declared={"u": u})
        r = _gate(case, _gold(tmp_path))
        assert r.freestream_mach_ok, "|U| unchanged — Mach gate must stay green"
        assert not r.alpha_ok
        assert not r.sanity_passed

    def test_c0c_wrong_viscosity_bites(self, tmp_path):
        # halved Sutherland As -> mu halves -> declared Re doubles
        case = build_case(tmp_path, transport={"suth_as": SUTH_AS / 2.0})
        r = _gate(case, _gold(tmp_path))
        assert not r.reynolds_ok
        assert r.freestream_mach_ok and r.alpha_ok
        assert not r.sanity_passed

    def test_c1_overshooting_stagnation_bites(self, tmp_path):
        # max Cp 1.30 > Cp_stag(0.734) + 0.05 ~ 1.192 — non-isentropic junk
        case = build_case(
            tmp_path,
            cp_lower=lambda x: _interp(
                [(0.0, 1.30), (0.02, 0.4), (0.3, -0.3), (0.7, -0.35), (1.0, 0.15)], x
            ),
        )
        r = _gate(case, _gold(tmp_path))
        assert not r.stagnation_ok
        assert not r.sanity_passed

    def test_c3_c4_subcritical_flow_bites(self, tmp_path):
        """The capability-matrix gap#2 failure mode: an attached solution
        BELOW shock-formation threshold must not pass a transonic-SBLI gate."""
        case = build_case(
            tmp_path,
            cp_upper=lambda x: _interp(
                [(0.0, 0.6), (0.05, -0.5), (0.55, -0.5), (0.62, -0.2), (1.0, 0.1)], x
            ),
        )
        r = _gate(case, _gold(tmp_path))
        assert not r.supersonic_pocket_ok
        assert not r.shock_ok
        assert "no supersonic plateau" in r.metrics.shock_decline_reason
        assert not r.sanity_passed

    def test_c4_shock_outside_band_bites(self, tmp_path):
        # recompression pushed to x/c ~ 0.93 > band hi 0.9
        case = build_case(
            tmp_path,
            cp_upper=lambda x: _interp(
                [(0.0, 0.6), (0.05, -1.1), (0.91, -1.1), (0.96, -0.2), (1.0, 0.1)], x
            ),
        )
        r = _gate(case, _gold(tmp_path))
        assert r.supersonic_pocket_ok
        assert r.metrics.shock_xc is not None and r.metrics.shock_xc > 0.9
        assert not r.shock_ok
        assert not r.sanity_passed

    def test_c5_drag_out_of_range_bites(self, tmp_path):
        case = build_case(tmp_path, cd_fc=0.15)
        r = _gate(case, _gold(tmp_path))
        assert not r.ranges_ok
        assert not r.sanity_passed

    def test_c6_forcecoeffs_disagreeing_with_pressure_cl_bites(self, tmp_path):
        """The solver FO claims a lift the surface pressures don't support."""
        chain = profile_chain()
        cn, ca = integrate_cn_ca(chain, 1.0)
        a = math.radians(ALPHA_DEG)
        cl_p = cn * math.cos(a) - ca * math.sin(a)
        case = build_case(tmp_path, cl_fc=1.5 * cl_p)
        r = _gate(case, _gold(tmp_path))
        assert r.ranges_ok, "1.5x Cl is still inside (0, 2) — only C6 may bite"
        assert not r.cl_crosscheck_ok
        assert not r.sanity_passed


def _verified_tier2(metrics, cl=None, shock=None, cd=0.0168,
                    cl_roles=("ENFORCED", "ENFORCED", "ADVISORY")):
    return {
        "anchor_verification": "VERIFIED",
        "provenance": {
            "source": "synthetic fixture (test only)",
            "digitization": "values pinned from a prior measured run",
        },
        "candidates": [
            {"qoi": "cl", "role": cl_roles[0],
             "value": float(cl if cl is not None else metrics.cl_fc), "rel_tol": 0.05},
            {"qoi": "shock_xc", "role": cl_roles[1],
             "value": float(shock if shock is not None else metrics.shock_xc), "atol": 0.05},
            {"qoi": "cd", "role": cl_roles[2], "value": float(cd), "rel_tol": 0.15},
        ],
    }


class TestTier2ConsumptionTriad:
    @pytest.fixture()
    def measured(self, tmp_path):
        """Two-phase: gate once in PROVISIONAL mode to obtain the measured
        QoIs, then pin VERIFIED fixtures around them."""
        case = build_case(tmp_path)
        r0 = _gate(case, _gold(tmp_path))
        assert r0.tier2_mode == "PROVISIONAL"
        return case, r0.metrics

    def test_verified_with_provenance_enforces_and_passes(self, tmp_path, measured):
        case, m = measured
        r = _gate(case, _gold(tmp_path, _verified_tier2(m)))
        assert r.tier2_mode == "ENFORCED"
        assert r.tier2_passed is True
        assert not hasattr(r, "coverage_eligible"), (
            "even a full tier-2 pass must not expose a coverage flip handle"
        )

    def test_enforced_band_failure(self, tmp_path, measured):
        case, m = measured
        r = _gate(case, _gold(tmp_path, _verified_tier2(m, cl=m.cl_fc * 1.2)))
        assert r.tier2_mode == "ENFORCED"
        assert r.tier2_passed is False

    def test_advisory_cd_failure_does_not_gate(self, tmp_path, measured):
        case, m = measured
        # cd anchor 3x off (fails its 15% band) but role is ADVISORY
        r = _gate(case, _gold(tmp_path, _verified_tier2(m, cd=m.cd_fc * 3.0)))
        assert r.tier2_mode == "ENFORCED"
        assert r.tier2_passed is True
        assert "ADVISORY — not judged" in r.summary

    def test_verified_without_provenance_is_refused(self, tmp_path, measured):
        case, m = measured
        bad = _verified_tier2(m)
        bad["provenance"] = None
        r = _gate(case, _gold(tmp_path, bad))
        assert r.tier2_mode == "PROVISIONAL" and r.tier2_passed is None

    def test_unknown_status_value_fails_closed(self, tmp_path, measured):
        case, m = measured
        bad = _verified_tier2(m)
        bad["anchor_verification"] = "verified"  # wrong case != enum value
        r = _gate(case, _gold(tmp_path, bad))
        assert r.tier2_mode == "PROVISIONAL"

    def test_null_enforced_value_stays_provisional(self, tmp_path, measured):
        case, m = measured
        bad = _verified_tier2(m)
        bad["candidates"][0]["value"] = None
        r = _gate(case, _gold(tmp_path, bad))
        assert r.tier2_mode == "PROVISIONAL"

    def test_missing_tolerance_stays_provisional(self, tmp_path, measured):
        case, m = measured
        bad = _verified_tier2(m)
        del bad["candidates"][0]["rel_tol"]
        r = _gate(case, _gold(tmp_path, bad))
        assert r.tier2_mode == "PROVISIONAL"

    def test_anchor_band_escaping_sanity_range_is_rejected(self, tmp_path, measured):
        case, m = measured
        # shock 0.88 +/- 0.05 -> band [0.83, 0.93] crosses the 0.9 sanity edge
        r = _gate(case, _gold(tmp_path, _verified_tier2(m, shock=0.88)))
        assert r.tier2_mode == "REJECTED_ANCHOR"
        assert r.tier2_passed is None

    def test_role_pin_rejects_promoted_cd(self, tmp_path, measured):
        case, m = measured
        with pytest.raises(TransonicGoldError, match="role set"):
            _gate(case, _gold(tmp_path, _verified_tier2(
                m, cl_roles=("ENFORCED", "ENFORCED", "ENFORCED"))))

    def test_role_pin_rejects_demoted_shock(self, tmp_path, measured):
        case, m = measured
        with pytest.raises(TransonicGoldError, match="role set"):
            _gate(case, _gold(tmp_path, _verified_tier2(
                m, cl_roles=("ENFORCED", "ADVISORY", "ADVISORY"))))


class TestGoldFailClosed:
    def test_wrong_quantity_doc_rejected(self, tmp_path):
        gold = _gold(tmp_path, quantity="surge_front_position")
        with pytest.raises(TransonicGoldError, match="transonic_airfoil_sbli"):
            _gate(build_case(tmp_path), gold)

    def test_missing_tolerance_key_rejected(self, tmp_path):
        gold = _gold(tmp_path)
        doc = yaml.safe_load(gold.read_text())
        del doc["tolerances"]["mach_atol"]
        gold.write_text(yaml.safe_dump(doc))
        with pytest.raises(TransonicGoldError, match="tolerances malformed"):
            _gate(build_case(tmp_path), gold)

    def test_missing_operating_point_key_rejected(self, tmp_path):
        gold = _gold(tmp_path)
        doc = yaml.safe_load(gold.read_text())
        del doc["operating_point"]["mach"]
        gold.write_text(yaml.safe_dump(doc))
        with pytest.raises(TransonicGoldError, match="operating_point malformed"):
            _gate(build_case(tmp_path), gold)

    def test_degenerate_shock_band_rejected(self, tmp_path):
        gold = _gold(tmp_path)
        doc = yaml.safe_load(gold.read_text())
        doc["tolerances"]["shock_band"] = [0.9, 0.2]
        gold.write_text(yaml.safe_dump(doc))
        with pytest.raises(TransonicGoldError, match="shock_band"):
            _gate(build_case(tmp_path), gold)

    def test_real_shipped_gold_runs_provisional(self, tmp_path):
        """The REAL gold (null candidates, DECLARED-NOT-VERIFIED) must gate a
        sane case as SANITY-PASS + PROVISIONAL, with the breadth-anchor
        coverage note intact."""
        r = _gate(build_case(tmp_path), REAL_GOLD)
        assert r.sanity_passed
        assert r.tier2_mode == "PROVISIONAL"
        assert r.tier2_passed is None
        assert "stays 3" in r.coverage_impact
