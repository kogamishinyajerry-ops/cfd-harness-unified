"""DEC-V61-144 (N3.5) · tolerance binding tests.

Coverage:
  * Three templates exist (lab_quality / engineering / fast_survey)
  * Each template carries non-empty rationale
  * Tier ordering invariant: lab_quality < engineering < fast_survey
    on every residual target (tighter→looser as you go to faster)
  * Every RegimeKind has a default tier mapping
  * derive_tolerance_for_regime composes correctly
  * Unknown tier / regime raises (defensive)
"""
from __future__ import annotations

import pytest

from ui.backend.services.physics import (
    TOLERANCE_TEMPLATES,
    derive_default_tolerance_tier,
    derive_tolerance_for_regime,
    get_tolerance_template,
)


# ────────── library completeness ──────────


_TIERS = ("lab_quality", "engineering", "fast_survey")


def test_three_tiers_exist():
    assert set(TOLERANCE_TEMPLATES.keys()) == set(_TIERS)


def test_every_template_has_rationale():
    for tier, tmpl in TOLERANCE_TEMPLATES.items():
        assert len(tmpl.rationale) >= 30, (
            f"tier {tier!r} has too-short rationale to be useful"
        )


def test_every_template_residuals_strictly_positive():
    for tmpl in TOLERANCE_TEMPLATES.values():
        assert tmpl.momentum > 0
        assert tmpl.pressure > 0
        assert tmpl.turbulence > 0
        assert tmpl.energy > 0


def test_tier_ordering_invariant():
    """Tighter tiers → smaller residual targets. lab_quality MUST be
    tighter than engineering MUST be tighter than fast_survey on
    every residual."""
    lab = TOLERANCE_TEMPLATES["lab_quality"]
    eng = TOLERANCE_TEMPLATES["engineering"]
    fast = TOLERANCE_TEMPLATES["fast_survey"]
    for field in ("momentum", "pressure", "turbulence", "energy"):
        assert getattr(lab, field) < getattr(eng, field), (
            f"lab_quality.{field} should be tighter than engineering.{field}"
        )
        assert getattr(eng, field) < getattr(fast, field), (
            f"engineering.{field} should be tighter than fast_survey.{field}"
        )


# ────────── regime → default tier mapping ──────────


def test_every_regime_kind_has_default_tier():
    """Same charter ship-blocker pattern as N3.4 — every RegimeKind
    must map to a documented default tier."""
    for kind in ("laminar", "RANS-RAS", "RANS-kOmegaSST", "LES-stub"):
        tier = derive_default_tolerance_tier(kind)  # type: ignore[arg-type]
        assert tier in _TIERS


def test_les_stub_defaults_to_lab_quality():
    """LES turbulent statistics are sensitive to residual control —
    the default tier picks lab_quality so engineers don't accidentally
    run LES with loose residuals."""
    assert derive_default_tolerance_tier("LES-stub") == "lab_quality"


def test_rans_regimes_default_to_engineering():
    """The industrial common case — RANS converges fine at engineering
    residuals; tighter is opt-in."""
    assert derive_default_tolerance_tier("RANS-RAS") == "engineering"
    assert derive_default_tolerance_tier("RANS-kOmegaSST") == "engineering"


def test_laminar_defaults_to_engineering():
    """LDC-style benchmark cases pick lab_quality manually; the
    default for laminar (most often pipe-flow at low-Re) is just
    engineering precision."""
    assert derive_default_tolerance_tier("laminar") == "engineering"


# ────────── derivation composition ──────────


def test_derive_tolerance_for_regime_composes_correctly():
    tmpl = derive_tolerance_for_regime("LES-stub")
    assert tmpl.tier == "lab_quality"
    assert tmpl.momentum == 1e-7

    tmpl = derive_tolerance_for_regime("RANS-kOmegaSST")
    assert tmpl.tier == "engineering"
    assert tmpl.momentum == 1e-5


# ────────── defensive branches ──────────


def test_get_tolerance_template_unknown_tier_raises():
    with pytest.raises(KeyError, match="unknown tolerance tier"):
        get_tolerance_template("ridiculously_tight")  # type: ignore[arg-type]


def test_derive_default_tolerance_tier_unknown_regime_raises():
    """Defensive branch — RegimeKind grew without _REGIME_DEFAULT_TIER
    being updated."""
    with pytest.raises(KeyError, match="no default tolerance tier"):
        derive_default_tolerance_tier("future-not-implemented")  # type: ignore[arg-type]
