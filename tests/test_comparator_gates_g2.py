"""DEC-V61-059 Stage A.1: G2 canonical-band shortcut detector tests.

Closes the DEC-V61-036c G2 territory marker (STATE.md:1313) by adding
a defense-in-depth gate that hard-FAILs plane_channel_flow when the
emitted u+/y+ profile interpolates to within 20% of Moser/Kim DNS
canonical points at BOTH the viscous sublayer (y+≈5) AND the log-law
region (y+≥30) while the run is declared laminar (or no turbulence
model is declared).

Four tests:
    1. laminar emitter that hits canonical band → G2 FIRES
    2. trusted RANS (kOmegaSST) emitting near-canonical → G2 SILENT
    3. missing turbulence_model_used + canonical hit → G2 FIRES
       (untrusted-by-default)
    4. laminar but only viscous-sublayer hit (no log-law) → G2 SILENT
       (insufficient evidence; fall through to comparator)
"""

from __future__ import annotations

from src.comparator_gates import (
    G2_CANONICAL_BAND_TOLERANCE,
    GateViolation,
    _check_g2_canonical_band_shortcut,
    check_all_gates,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _moser_canonical_profile() -> dict:
    """Returns key_quantities containing a u+/y+ profile that lands
    on the Moser canonical points at y+ ∈ {5, 30, 100}.

    This is the SHAPE a unit-mismatch shortcut would produce when the
    extractor accidentally maps cell-center U/u_tau-laminar through
    the u_plus key — values look right, physics doesn't support it.
    """
    return {
        "u_mean_profile_y_plus": [1.0, 5.0, 10.0, 30.0, 100.0],
        "u_mean_profile":         [1.0, 5.4, 11.0, 13.5, 18.3],
    }


def _laminar_poiseuille_uplus_profile() -> dict:
    """A genuinely-laminar emitted profile would NOT match canonical
    DNS at both viscous-sublayer and log-law regions simultaneously.
    Roughly: at Re_b≈100 with h=1, ν=0.01 → u_τ≈0.173, y+_max≈17,
    u+_max ≈ 1.5/0.173 ≈ 8.66. We can sample y+={1, 5, 10, 17}
    against this profile.
    """
    return {
        "u_mean_profile_y_plus": [1.0, 5.0, 10.0, 17.0],
        # Linear-ish ramp typical of low-Re laminar Poiseuille in
        # wall coordinates — saturates at u+≈8.66.
        "u_mean_profile":         [1.0, 5.0, 7.5, 8.66],
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_g2_fires_on_laminar_canonical_band_shortcut():
    """Test 1: laminar declared + canonical-band hit → G2 FAIL."""
    key_qty = _moser_canonical_profile()
    key_qty["turbulence_model_used"] = "laminar"

    violations = _check_g2_canonical_band_shortcut(
        case_id="fully_developed_plane_channel_flow",
        key_quantities=key_qty,
    )

    assert len(violations) == 1, (
        f"expected G2 to fire; got {len(violations)} violations"
    )
    v = violations[0]
    assert v.gate_id == "G2"
    assert v.concern_type == "CANONICAL_BAND_SHORTCUT_LAMINAR_DNS"
    assert "laminar" in v.summary or "laminar" in v.detail
    assert v.evidence["has_viscous"] is True
    assert v.evidence["has_loglaw"] is True
    assert len(v.evidence["hits"]) >= 2

    # Also verify the public check_all_gates() entrypoint surfaces it.
    all_violations = check_all_gates(
        case_id="fully_developed_plane_channel_flow",
        key_quantities=key_qty,
    )
    assert any(av.gate_id == "G2" for av in all_violations)


def test_g2_silent_on_trusted_rans_kOmegaSST():
    """Test 2: trusted RANS turbulence model + canonical-band match
    is HONEST physics — G2 must NOT fire.
    """
    key_qty = _moser_canonical_profile()
    key_qty["turbulence_model_used"] = "kOmegaSST"

    violations = _check_g2_canonical_band_shortcut(
        case_id="fully_developed_plane_channel_flow",
        key_quantities=key_qty,
    )

    assert violations == [], (
        f"G2 falsely fired on legitimate kOmegaSST run: {violations}"
    )

    # Same check via public entrypoint.
    all_violations = check_all_gates(
        case_id="fully_developed_plane_channel_flow",
        key_quantities=key_qty,
    )
    assert not any(av.gate_id == "G2" for av in all_violations)


def test_g2_fires_when_turbulence_model_undeclared():
    """Test 3: turbulence_model_used absent + canonical-band hit →
    treat as untrusted (default-to-laminar pessimistic) and FIRE.

    Rationale: pre-DEC-V61-059 fixtures lack the
    turbulence_model_used key entirely; G2 must close the
    PASS-washing window by failing-closed when the turbulence
    declaration is missing.
    """
    key_qty = _moser_canonical_profile()
    # NO turbulence_model_used key at all.

    violations = _check_g2_canonical_band_shortcut(
        case_id="fully_developed_plane_channel_flow",
        key_quantities=key_qty,
    )

    assert len(violations) == 1
    v = violations[0]
    assert v.gate_id == "G2"
    assert "<not declared>" in v.summary or "not declared" in v.detail
    assert v.evidence["turbulence_model_used"] == "<not declared>"


def test_g2_silent_on_legitimate_laminar_poiseuille():
    """Test 4: laminar emitter producing genuinely-laminar Poiseuille
    profile (saturates at u+≈8.66 at y+_max≈17, never reaches
    log-law region y+≥30) → G2 must NOT fire because there is no
    two-region match.

    This proves the gate doesn't false-positive on every laminar
    plane-channel run — only on those imitating DNS via unit
    mismatch.
    """
    key_qty = _laminar_poiseuille_uplus_profile()
    key_qty["turbulence_model_used"] = "laminar"

    violations = _check_g2_canonical_band_shortcut(
        case_id="fully_developed_plane_channel_flow",
        key_quantities=key_qty,
    )

    assert violations == [], (
        f"G2 false-fired on honest laminar profile: {violations}"
    )


# ---------------------------------------------------------------------------
# Edge-case coverage (not part of the 4 mandated tests, but cheap to add)
# ---------------------------------------------------------------------------

def test_g2_silent_when_case_id_not_plane_channel():
    """G2 is case-scoped — must be silent on cylinder, LDC, NACA, etc."""
    key_qty = _moser_canonical_profile()
    key_qty["turbulence_model_used"] = "laminar"
    for off_case in (
        "lid_driven_cavity_benchmark",
        "naca0012_airfoil",
        "cylinder_crossflow",
        "differential_heated_cavity",
        None,
        "",
    ):
        violations = _check_g2_canonical_band_shortcut(
            case_id=off_case,
            key_quantities=key_qty,
        )
        assert violations == [], (
            f"G2 falsely fired on {off_case!r}: {violations}"
        )


def test_g2_silent_when_key_quantities_missing():
    """G1 covers MISSING_TARGET_QUANTITY; G2 must not double-FAIL."""
    for empty in (None, {}, {"turbulence_model_used": "laminar"}):
        violations = _check_g2_canonical_band_shortcut(
            case_id="fully_developed_plane_channel_flow",
            key_quantities=empty,
        )
        assert violations == [], (
            f"G2 falsely fired on missing profile: {empty!r} → {violations}"
        )


def test_g2_uses_legacy_alias_plane_channel_flow():
    """Both canonical id AND legacy alias must trigger the gate."""
    key_qty = _moser_canonical_profile()
    key_qty["turbulence_model_used"] = "laminar"
    violations = _check_g2_canonical_band_shortcut(
        case_id="plane_channel_flow",
        key_quantities=key_qty,
    )
    assert len(violations) == 1
    assert violations[0].gate_id == "G2"


def test_g2_band_tolerance_constant_is_documented():
    """Sanity: tolerance is wide enough to absorb DNS-vs-RANS structural
    discrepancy yet narrow enough that legitimate misses won't trigger.
    """
    assert 0.05 < G2_CANONICAL_BAND_TOLERANCE < 0.5


def test_g2_silent_when_only_viscous_and_centerline_hit_no_loglaw():
    """Codex round-3 F5 regression: a profile that interpolates to
    canonical values at y+=5 (viscous sublayer) AND y+=100 (centerline)
    but MISSES the actual y+=30 log-law region must NOT trip G2.
    The earlier `has_loglaw = any(yp >= 30.0)` check counted y+=100
    as log-law, producing false hard-fails for profiles whose viscous
    + centerline values happened to land near canonical without
    actually reproducing the (1/0.41)·ln(y+)+5.2 log-law curve.
    """
    # Profile passes through canonical y+=5 (u+=5.4) and y+=100 (u+=18.3)
    # but at y+=30 sits at u+=8.0 — far from the canonical 13.5 (rel_err
    # ≈ 0.41, well outside G2 tolerance 0.20). With the F5 fix the gate
    # only fires if a hit lands in the (10, 60) log-law window.
    key_qty = {
        "u_mean_profile_y_plus": [1.0, 5.0, 30.0, 100.0],
        "u_mean_profile":         [1.0, 5.4, 8.0, 18.3],
        "turbulence_model_used": "laminar",
    }
    violations = _check_g2_canonical_band_shortcut(
        case_id="fully_developed_plane_channel_flow",
        key_quantities=key_qty,
    )
    assert violations == [], (
        f"G2 must not trip on viscous+centerline-only band match: {violations}"
    )


def test_g2_fires_when_actual_loglaw_y_plus_30_is_hit():
    """Companion to the F5 regression above: when the profile DOES hit
    the y+=30 log-law canonical AND a viscous-sublayer point, G2 still
    fires as designed. Prevents F5 from over-tightening the gate.
    """
    key_qty = {
        "u_mean_profile_y_plus": [1.0, 5.0, 30.0, 100.0],
        "u_mean_profile":         [1.0, 5.4, 13.5, 19.0],  # y+=30 hits canonical
        "turbulence_model_used": "laminar",
    }
    violations = _check_g2_canonical_band_shortcut(
        case_id="fully_developed_plane_channel_flow",
        key_quantities=key_qty,
    )
    assert len(violations) == 1
    assert violations[0].gate_id == "G2"


def test_violation_to_audit_concern_dict_uses_dec_v61_059_for_g2():
    """G2 violations must reference DEC-V61-059, not DEC-V61-036b."""
    from src.comparator_gates import violation_to_audit_concern_dict

    v = GateViolation(
        gate_id="G2",
        concern_type="CANONICAL_BAND_SHORTCUT_LAMINAR_DNS",
        summary="x",
        detail="y",
        evidence={},
    )
    d = violation_to_audit_concern_dict(v)
    assert d["decision_refs"] == ["DEC-V61-059"]
