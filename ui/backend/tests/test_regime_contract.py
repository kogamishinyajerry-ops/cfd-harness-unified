"""DEC-V61-141 (N3.2) · RegimeContract schema + preset library tests.

Coverage:
  * Schema field validators (positivity)
  * Cross-field invariants (kind=preset → preset_id + citation;
    re_max > re_min)
  * Library citation completeness (charter threat-model row 4)
  * Library covers all RegimeKind literals
  * Lookup behavior
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from ui.backend.schemas.regime_contract import (
    ApplicabilityBounds,
    RegimeContract,
)
from ui.backend.services.physics import (
    REGIME_PRESETS,
    get_regime_preset,
    list_regime_preset_ids,
)


# ────────── ApplicabilityBounds ──────────


def test_bounds_all_optional():
    """Every field is optional — bounds are advisory, not mandatory."""
    b = ApplicabilityBounds()
    assert b.re_min is None
    assert b.re_max is None
    assert b.mach_max is None
    assert b.y_plus_target is None


def test_bounds_re_min_non_negative():
    """re_min=0 is allowed (laminar starts at quiescent flow);
    negative is rejected."""
    ApplicabilityBounds(re_min=0.0)  # ok
    with pytest.raises(ValidationError):
        ApplicabilityBounds(re_min=-1.0)


def test_bounds_re_max_strictly_positive():
    with pytest.raises(ValidationError):
        ApplicabilityBounds(re_max=0.0)
    with pytest.raises(ValidationError):
        ApplicabilityBounds(re_max=-1.0)


def test_bounds_mach_max_strictly_positive():
    with pytest.raises(ValidationError):
        ApplicabilityBounds(mach_max=0.0)


def test_bounds_y_plus_strictly_positive():
    with pytest.raises(ValidationError):
        ApplicabilityBounds(y_plus_target=0.0)


def test_bounds_extra_keys_forbidden():
    with pytest.raises(ValidationError):
        ApplicabilityBounds(re_min=1.0, mystery="oops")


# ────────── RegimeContract cross-field ──────────


def _custom_bounds() -> ApplicabilityBounds:
    return ApplicabilityBounds(re_min=1.0, mach_max=0.3)


def test_contract_kind_preset_requires_preset_id():
    with pytest.raises(ValidationError) as exc_info:
        RegimeContract(
            kind="preset",
            preset_id=None,
            regime="laminar",
            citation="https://example.com/cite",  # type: ignore[arg-type]
            authored_at="2026-05-07T12:00:00Z",
        )
    assert "preset_id" in str(exc_info.value)


def test_contract_kind_preset_requires_citation():
    with pytest.raises(ValidationError) as exc_info:
        RegimeContract(
            kind="preset",
            preset_id="laminar_internal_default",
            regime="laminar",
            citation=None,
            authored_at="2026-05-07T12:00:00Z",
        )
    assert "citation" in str(exc_info.value)


def test_contract_kind_custom_must_leave_preset_id_none():
    with pytest.raises(ValidationError) as exc_info:
        RegimeContract(
            kind="custom",
            preset_id="laminar_internal_default",
            regime="laminar",
            authored_at="2026-05-07T12:00:00Z",
        )
    assert "preset_id" in str(exc_info.value)


def test_contract_re_max_must_exceed_re_min_when_both_set():
    with pytest.raises(ValidationError) as exc_info:
        RegimeContract(
            kind="custom",
            regime="laminar",
            applicability=ApplicabilityBounds(re_min=2300.0, re_max=1000.0),
            authored_at="2026-05-07T12:00:00Z",
        )
    assert "re_max" in str(exc_info.value)


def test_contract_re_max_equal_re_min_rejected():
    """A zero-width band signals confused authoring."""
    with pytest.raises(ValidationError):
        RegimeContract(
            kind="custom",
            regime="laminar",
            applicability=ApplicabilityBounds(re_min=2300.0, re_max=2300.0),
            authored_at="2026-05-07T12:00:00Z",
        )


def test_contract_re_min_only_or_re_max_only_ok():
    # One-sided bound is meaningful (e.g. RANS regimes have a lower
    # bound but no documented upper bound).
    RegimeContract(
        kind="custom",
        regime="RANS-kOmegaSST",
        applicability=ApplicabilityBounds(re_min=1000.0),
        authored_at="2026-05-07T12:00:00Z",
    )
    RegimeContract(
        kind="custom",
        regime="laminar",
        applicability=ApplicabilityBounds(re_max=2300.0),
        authored_at="2026-05-07T12:00:00Z",
    )


def test_contract_preset_id_charset():
    with pytest.raises(ValidationError):
        RegimeContract(
            kind="preset",
            preset_id="laminar default",  # space disallowed
            regime="laminar",
            citation="https://example.com/cite",  # type: ignore[arg-type]
            authored_at="2026-05-07T12:00:00Z",
        )


def test_contract_extra_keys_forbidden():
    with pytest.raises(ValidationError):
        RegimeContract(
            kind="custom",
            regime="laminar",
            authored_at="2026-05-07T12:00:00Z",
            mystery="oops",
        )


def test_contract_invalid_regime_literal_rejected():
    with pytest.raises(ValidationError):
        RegimeContract(
            kind="custom",
            regime="dns_full",  # not in RegimeKind literal
            authored_at="2026-05-07T12:00:00Z",
        )


def test_contract_default_applicability_is_empty_bounds():
    """When the engineer doesn't supply applicability, the field
    defaults to all-None bounds rather than rejecting at validation
    time. Bounds are advisory; absence is not an error."""
    c = RegimeContract(
        kind="custom",
        regime="laminar",
        authored_at="2026-05-07T12:00:00Z",
    )
    assert c.applicability.re_min is None
    assert c.applicability.re_max is None
    assert c.applicability.mach_max is None
    assert c.applicability.y_plus_target is None


# ────────── Regime library ──────────


def test_library_covers_every_regime_kind():
    """Every RegimeKind literal has at least one preset entry —
    otherwise the UI dropdown would be missing options the schema
    knows about."""
    regimes_in_library = {p.regime for p in REGIME_PRESETS.values()}
    expected = {"laminar", "RANS-RAS", "RANS-kOmegaSST", "LES-stub"}
    assert expected.issubset(regimes_in_library)


def test_library_preset_ids_unique_and_match_keys():
    for key, preset in REGIME_PRESETS.items():
        assert preset.preset_id == key


def test_library_every_preset_carries_citation():
    """Charter §threat-model row 4: every bundled preset MUST cite a
    public source."""
    for preset_id, preset in REGIME_PRESETS.items():
        assert preset.citation, f"preset {preset_id!r} ships without citation"
        assert preset.citation.startswith(("http://", "https://"))


def test_library_applicability_internally_consistent():
    """Each preset's bounds must satisfy re_max > re_min when both set —
    same invariant the wire schema enforces."""
    for preset_id, preset in REGIME_PRESETS.items():
        ap = preset.applicability
        if ap.re_min is not None and ap.re_max is not None:
            assert ap.re_max > ap.re_min, (
                f"preset {preset_id!r} has re_max <= re_min"
            )


def test_get_regime_preset_unknown_returns_none():
    assert get_regime_preset("turbulent_unobtanium") is None


def test_get_regime_preset_known_returns_match():
    p = get_regime_preset("rans_komegasst_default")
    assert p is not None
    assert p.regime == "RANS-kOmegaSST"


def test_list_regime_preset_ids_stable_order():
    """Ordering matters for the UI dropdown — most common defaults
    (laminar → RANS) appear first."""
    ids = list_regime_preset_ids()
    assert ids[0] == "laminar_internal_default"
    assert "rans_komegasst_default" in ids
    # LES-stub is forward-compat placeholder, ordered after RANS.
    assert ids.index("rans_komegasst_default") < ids.index("les_stub_placeholder")


def test_library_preset_can_populate_a_valid_contract():
    """End-to-end: pick a preset, copy values into a RegimeContract,
    verify it validates. Mirrors what the frontend does in N3.3."""
    preset = REGIME_PRESETS["rans_komegasst_default"]
    contract = RegimeContract(
        kind="preset",
        preset_id=preset.preset_id,
        regime=preset.regime,
        applicability=preset.applicability,
        citation=preset.citation,  # type: ignore[arg-type]
        authored_at="2026-05-07T12:00:00Z",
    )
    assert contract.regime == "RANS-kOmegaSST"
    assert contract.applicability.y_plus_target == 1.0


def test_library_les_stub_carries_low_re_floor():
    """Even though LES is a placeholder, its applicability re_min
    should be high enough that engineers see it doesn't apply to
    laminar / low-Re cases — guards against accidentally selecting
    LES for a 'just see what happens' run."""
    p = REGIME_PRESETS["les_stub_placeholder"]
    assert p.applicability.re_min is not None
    assert p.applicability.re_min >= 1000.0
