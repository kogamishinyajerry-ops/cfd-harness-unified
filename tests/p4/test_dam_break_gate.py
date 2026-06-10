"""V72.A dam-break gate tests (DEC-V61-237).

Synthetic cases exercise every tier-1 sanity gate (each one must BITE — the
doctored-case discipline of test_wedge_oblique_shock_gate.py) and the tier-2
consumption triad (loop-auditor F2: status pin / provenance pin / anchor
meta-gate), all against synthetic golds in tmp_path plus the REAL shipped gold.
"""
from pathlib import Path

import pytest
import yaml

from src.dam_break_extractor import DamBreakExtractionError
from src.dam_break_gate import (
    DamBreakGoldError,
    derive_sample_time,
    gate_dam_break_against_gold,
)
from tests.p4.test_dam_break_extractor import _write_scalar, _write_vector

REPO = Path(__file__).resolve().parents[2]
REAL_GOLD = REPO / "knowledge" / "gold_standards" / "dam_break_collapse.yaml"

A, G = 0.1461, 9.81
BAND = 0.1 * A
T0 = "0"
T1 = f"{derive_sample_time(1.0, A, G):.6f}"   # 0.086293
T2 = f"{derive_sample_time(2.0, A, G):.6f}"   # 0.172586


def _grid(nx=40):
    """One floor row inside the band + one row above; nx cells across 4a."""
    dx = 4.0 * A / nx
    xs = [(i + 0.5) * dx for i in range(nx)]
    return [(x, 0.5 * BAND, 0.0) for x in xs] + [(x, 5.0 * BAND, 0.0) for x in xs]


def _alpha_for_front(z_front: float, height_alpha=0.0, nx=40):
    """Floor row wet (alpha=1) for x/a < z_front, dry beyond; top row constant."""
    dx = 4.0 * A / nx
    floor = [1.0 if (i + 0.5) * dx / A <= z_front else 0.0 for i in range(nx)]
    top = [height_alpha] * nx
    return floor + top


def _build_case(tmp_path, z_by_time: dict, volume_scale_by_time=None, alpha_tweak=None):
    """Synthetic case: same conserving water volume at every time unless scaled."""
    case = tmp_path / "case"
    centres = _grid()
    _write_vector(case / "0" / "C", "C", centres)
    _write_scalar(case / "0" / "V", "V", [1.0e-6] * len(centres))
    base_wet = sum(_alpha_for_front(max(z_by_time.values())))
    for tname, z in z_by_time.items():
        alpha = _alpha_for_front(z)
        # conserve total water: park the deficit in the top row uniformly
        deficit = base_wet - sum(alpha)
        nx = len(alpha) // 2
        scale = (volume_scale_by_time or {}).get(tname, 1.0)
        alpha = [
            v * scale if i < nx else (deficit / nx) * scale
            for i, v in enumerate(alpha)
        ]
        if alpha_tweak:
            alpha = alpha_tweak(tname, alpha)
        _write_scalar(case / tname / "alpha.water", "alpha.water", alpha)
    return case


def _sane_case(tmp_path, **kw):
    """Plausible collapse: Z(0)=1.0 -> 1.4 -> 2.4 (inside all tier-1 gates)."""
    return _build_case(tmp_path, {T0: 1.0, T1: 1.4, T2: 2.4}, **kw)


def _gold(tmp_path, tier2_override=None, **top_override):
    doc = {
        "quantity": "surge_front_position",
        "tolerance": 0.10,
        "sample_T": [0.0, 1.0, 2.0],
        "tier2_anchor": {
            "anchor_verification": "DECLARED-NOT-VERIFIED",
            "provenance": None,
            "candidates": [{"T": 1.0, "Z": None}, {"T": 2.0, "Z": None}],
        },
        "case_info": {
            "id": "dam_break_collapse",
            "validation_status": "SCAFFOLD_AUTHORED",
            "geometry": {
                "column_width_a_m": A,
                "column_height_m": 2 * A,
                "tank_length_m": 4 * A,
                "gravity_m_s2": G,
            },
        },
    }
    if tier2_override is not None:
        doc["tier2_anchor"] = tier2_override
    doc.update(top_override)
    p = tmp_path / "gold.yaml"
    p.write_text(yaml.safe_dump(doc))
    return p


VERIFIED_TIER2 = {
    "anchor_verification": "VERIFIED",
    "provenance": {
        "source": "synthetic-fixture (test only)",
        "digitization": "synthetic points for gate-mode tests",
    },
    "candidates": [{"T": 1.0, "Z": 1.40}, {"T": 2.0, "Z": 2.40}],
}


class TestTier1SanityGates:
    def test_sane_collapse_is_sanity_pass_but_not_coverage_eligible(self, tmp_path):
        r = gate_dam_break_against_gold(_sane_case(tmp_path), _gold(tmp_path))
        assert r.sanity_passed
        assert r.tier2_mode == "PROVISIONAL"
        assert r.tier2_passed is None
        assert not r.coverage_eligible, (
            "tier-1-only verdicts must NEVER be coverage-eligible (F3)"
        )
        assert "SANITY-PASS" in r.summary and "validated" not in r.summary.lower()

    def test_unrun_frozen_case_dies_on_collapse_floor_and_monotone(self, tmp_path):
        case = _build_case(tmp_path, {T0: 1.0, T1: 1.0, T2: 1.0})
        r = gate_dam_break_against_gold(case, _gold(tmp_path))
        assert not r.collapse_floor_ok and not r.monotone_ok
        assert not r.sanity_passed, "Z==1.0 tautology must die (G2+G3)"

    def test_ritter_violation_bites(self, tmp_path):
        # Z(T=1)=2.2 >= 2T=2.0 — faster than the inviscid bound = unphysical
        case = _build_case(tmp_path, {T0: 1.0, T1: 2.2, T2: 2.4})
        r = gate_dam_break_against_gold(case, _gold(tmp_path))
        assert not r.ritter_bound_ok and not r.sanity_passed

    def test_all_flooded_tamper_bites(self, tmp_path):
        # alpha=1 everywhere: Z=4.0 at every time -> G1 (4.0 >= 2.0 at T=1) + G2
        case = _build_case(tmp_path, {T0: 4.0, T1: 4.0, T2: 4.0})
        r = gate_dam_break_against_gold(case, _gold(tmp_path))
        assert not r.sanity_passed
        assert not r.initial_column_ok and not r.ritter_bound_ok

    def test_wrong_initialization_bites_g0(self, tmp_path):
        case = _build_case(tmp_path, {T0: 1.5, T1: 1.7, T2: 2.4})
        r = gate_dam_break_against_gold(case, _gold(tmp_path))
        assert not r.initial_column_ok and not r.sanity_passed

    def test_volume_drift_bites_g4(self, tmp_path):
        case = _sane_case(tmp_path, volume_scale_by_time={T2: 0.95})  # -5% water
        r = gate_dam_break_against_gold(case, _gold(tmp_path))
        assert not r.volume_conservation_ok and not r.sanity_passed

    def test_alpha_overshoot_bites_g5(self, tmp_path):
        def tweak(tname, alpha):
            if tname == T1:
                alpha = list(alpha)
                alpha[0] = 1.02  # 2% overshoot >> 1e-6 tolerance
            return alpha
        case = _sane_case(tmp_path, alpha_tweak=tweak)
        r = gate_dam_break_against_gold(case, _gold(tmp_path))
        assert not r.alpha_bounded_ok and not r.sanity_passed

    def test_missing_time_dir_is_honest_block(self, tmp_path):
        case = _build_case(tmp_path, {T0: 1.0, T1: 1.4})  # no T2 dir
        with pytest.raises(DamBreakExtractionError):
            gate_dam_break_against_gold(case, _gold(tmp_path))


class TestTier2ConsumptionTriad:
    def test_verified_with_provenance_enforces_and_passes(self, tmp_path):
        case = _sane_case(tmp_path)  # measured 1.4 / 2.4 == synthetic anchor
        r = gate_dam_break_against_gold(case, _gold(tmp_path, VERIFIED_TIER2))
        assert r.tier2_mode == "ENFORCED" and r.tier2_passed is True
        assert r.coverage_eligible

    def test_enforced_band_failure_blocks_coverage(self, tmp_path):
        bad = dict(VERIFIED_TIER2)
        bad["candidates"] = [{"T": 1.0, "Z": 1.80}, {"T": 2.0, "Z": 2.40}]
        case = _sane_case(tmp_path)  # measured 1.4 vs 1.80 = -22% > 10%
        r = gate_dam_break_against_gold(case, _gold(tmp_path, bad))
        assert r.tier2_mode == "ENFORCED" and r.tier2_passed is False
        assert not r.coverage_eligible

    def test_verified_without_provenance_is_refused(self, tmp_path):
        bad = dict(VERIFIED_TIER2)
        bad["provenance"] = None
        r = gate_dam_break_against_gold(_sane_case(tmp_path), _gold(tmp_path, bad))
        assert r.tier2_mode == "PROVISIONAL" and not r.coverage_eligible

    def test_unknown_status_value_fails_closed(self, tmp_path):
        bad = dict(VERIFIED_TIER2)
        bad["anchor_verification"] = "verified"  # wrong case = not the enum value
        r = gate_dam_break_against_gold(_sane_case(tmp_path), _gold(tmp_path, bad))
        assert r.tier2_mode == "PROVISIONAL" and not r.coverage_eligible

    def test_anchor_violating_meta_gate_is_rejected(self, tmp_path):
        bad = dict(VERIFIED_TIER2)
        # Z=1.9@T=1: 1.9*1.1=2.09 >= 2.0 -> band crosses the Ritter bound
        bad["candidates"] = [{"T": 1.0, "Z": 1.90}, {"T": 2.0, "Z": 2.40}]
        r = gate_dam_break_against_gold(_sane_case(tmp_path), _gold(tmp_path, bad))
        assert r.tier2_mode == "REJECTED_ANCHOR" and not r.coverage_eligible

    def test_null_candidates_stay_provisional(self, tmp_path):
        bad = dict(VERIFIED_TIER2)
        bad["candidates"] = [{"T": 1.0, "Z": None}]
        r = gate_dam_break_against_gold(_sane_case(tmp_path), _gold(tmp_path, bad))
        assert r.tier2_mode == "PROVISIONAL" and not r.coverage_eligible


class TestGoldFailClosed:
    def test_wrong_aspect_ratio_gold_is_rejected(self, tmp_path):
        gold = _gold(tmp_path)
        doc = yaml.safe_load(gold.read_text())
        doc["case_info"]["geometry"]["column_height_m"] = 3 * A  # n^2=3 != 2
        gold.write_text(yaml.safe_dump(doc))
        with pytest.raises(DamBreakGoldError, match="aspect ratio"):
            gate_dam_break_against_gold(_sane_case(tmp_path), gold)

    def test_gold_without_t0_sample_is_rejected(self, tmp_path):
        gold = _gold(tmp_path, sample_T=[1.0, 2.0])
        with pytest.raises(DamBreakGoldError, match="T=0.0"):
            gate_dam_break_against_gold(_sane_case(tmp_path), gold)

    def test_real_shipped_gold_runs_in_provisional_mode(self, tmp_path):
        """The REAL gold (DECLARED-NOT-VERIFIED) must gate a sane case as
        SANITY-PASS + PROVISIONAL + coverage_eligible False."""
        r = gate_dam_break_against_gold(_sane_case(tmp_path), REAL_GOLD)
        assert r.sanity_passed
        assert r.tier2_mode == "PROVISIONAL"
        assert not r.coverage_eligible
