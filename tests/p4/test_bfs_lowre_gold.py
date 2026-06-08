"""P4 V71.B · structural self-verify of the backward_facing_step_lowre gold.

Reattachment length is an experimental/DNS anchor (NOT a closed form), so unlike
the wedge gold this test cannot re-derive the value — it LOCKS the committed
contract fields + the honesty keys instead: the inherited blended anchor (6.26),
the UNCHANGED 10% tolerance, the dual-reference disclosure, the machine-gated
y+<1 resolved precondition, and the wall-shear reattachment method. If a future
edit silently re-shops the anchor, widens the tolerance, drops the dual-reference
note, or weakens the resolved claim, this test goes red.
"""
from __future__ import annotations

from pathlib import Path

import yaml

_GOLD = (
    Path(__file__).resolve().parents[2]
    / "knowledge"
    / "gold_standards"
    / "backward_facing_step_lowre.yaml"
)


def _load() -> dict:
    docs = [d for d in yaml.safe_load_all(_GOLD.read_text(encoding="utf-8")) if d]
    assert docs, "gold file empty/unparseable"
    for d in docs:
        if d.get("quantity") == "reattachment_length":
            return d
    raise AssertionError("no reattachment_length doc in gold")


def test_gold_parses_and_quantity():
    doc = _load()
    assert doc["quantity"] == "reattachment_length"


def test_anchor_is_inherited_6_26_blended_not_reshopped():
    doc = _load()
    rv = doc["reference_values"][0]
    assert rv["value"] == 6.26, "anchor must stay the inherited blended 6.26 (no per-slice swap to 6.28)"
    assert rv["unit"] == "Xr/H"
    # both brackets disclosed in the reference description (dual-reference honesty)
    desc = rv["description"]
    assert "6.28" in desc and "6.26" in desc, "must disclose BOTH anchor brackets (6.26 + DNS 6.28)"
    assert "5100" in desc, "must name the Le/Moin/Kim DNS regime (Re_H=5100)"


def test_tolerance_unchanged_10pct():
    doc = _load()
    assert doc["tolerance"] == 0.10, "tolerance must stay 0.10 (inherited from high-Re sibling, NOT widened)"


def test_case_info_lowre_identity():
    doc = _load()
    ci = doc["case_info"]
    assert ci["id"] == "backward_facing_step_lowre"
    assert ci["Re"] == 5000
    assert ci["geometry_type"] == "BACKWARD_FACING_STEP"
    assert ci["expansion_ratio"] == 1.125
    assert ci["wall_treatment"] == "resolved"
    assert ci["turbulence_model"] == "kOmegaSST"
    assert ci["validation_status"] == "LIVE_VALIDATED"
    # reattachment is the wall-shear definition, NOT a height-biased U_x proxy
    assert ci["reattachment_method"] == "wall_shear_tau_x_zero_crossing"


def test_yplus_precondition_is_machine_gated_and_disclosed():
    docs = [d for d in yaml.safe_load_all(_GOLD.read_text(encoding="utf-8")) if d]
    pc = next(d for d in docs if "physics_contract" in d)["physics_contract"]
    yp = pc["yplus_precondition"]
    assert yp["status"] == "PASS"
    assert yp["fail_closed"] is True
    assert yp["measured_max_floor_yplus"] < 1.0, "measured resolved-floor y+ must be < 1"
    # the gate clause must reference the shared mask + the < 1 bar
    assert "< 1.0" in yp["gate"] and "bfs_floor_region" in yp["gate"]
    # out-of-claim regions disclosed (step corner singularity + wall-functioned upper wall)
    disc = yp["disclosed_out_of_claim"]
    assert "step_corner" in disc and "upper_wall" in disc
    # "no wall functions" must NOT be claimed (Spalding is a wall function in integrate-to-wall mode)
    assert "no wall function" not in yp["claim_text"].lower()
    assert "integrate-to-wall" in yp["claim_text"]


def test_source_cites_blended_anchor():
    doc = _load()
    src = doc["source"].lower()
    assert "le, moin" in src or "le,moin" in src or "moin" in src
    assert "driver" in src
