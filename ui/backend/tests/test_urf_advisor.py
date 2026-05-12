"""DEC-V61-148 (N4.3) · URF schema + stability advisor tests.

Coverage:
  * URFOverride field validators (charset, range)
  * Empty override → empty hints
  * U relaxation thresholds: safe / warning / critical bands
  * U relaxation laminar relaxed threshold (0.9 vs 0.85)
  * p relaxation thresholds
  * Turbulence equation thresholds (k, omega, epsilon)
  * LES regime info hint when URF is set
  * Hints sort: critical first, then warning, then info
  * V132 contract: advisor module has no mutation surface
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from ui.backend.schemas.urf_override import URFOverride
from ui.backend.services.physics.urf_advisor import (
    derive_stability_hints,
)


def _override(
    *,
    fields: dict | None = None,
    equations: dict | None = None,
) -> URFOverride:
    return URFOverride(
        fields=fields or {},
        equations=equations or {},
        authored_at="2026-05-07T12:00:00Z",
    )


# ────────── URFOverride validators ──────────


def test_urf_factor_must_be_in_open_zero_to_one_inclusive():
    URFOverride(equations={"U": 0.7}, authored_at="2026-05-07T12:00:00Z")
    URFOverride(equations={"U": 1.0}, authored_at="2026-05-07T12:00:00Z")
    with pytest.raises(ValidationError):
        URFOverride(
            equations={"U": 0.0}, authored_at="2026-05-07T12:00:00Z",
        )
    with pytest.raises(ValidationError):
        URFOverride(
            equations={"U": -0.1}, authored_at="2026-05-07T12:00:00Z",
        )
    with pytest.raises(ValidationError):
        URFOverride(
            equations={"U": 1.1}, authored_at="2026-05-07T12:00:00Z",
        )


def test_urf_field_name_alnum():
    URFOverride(
        equations={"U": 0.7, "k": 0.5}, authored_at="2026-05-07T12:00:00Z",
    )
    with pytest.raises(ValidationError):
        URFOverride(
            equations={"my eq": 0.5},
            authored_at="2026-05-07T12:00:00Z",
        )


def test_urf_extra_keys_forbidden():
    with pytest.raises(ValidationError):
        URFOverride(
            authored_at="2026-05-07T12:00:00Z", mystery="oops",
        )


# ────────── Advisor: empty / clean ──────────


def test_advisor_empty_override_yields_no_hints():
    hints = derive_stability_hints(
        urf=_override(), regime="RANS-kOmegaSST",
    )
    assert hints == []


def test_advisor_safe_factors_yield_no_hints():
    hints = derive_stability_hints(
        urf=_override(equations={"U": 0.7, "k": 0.5}, fields={"p": 0.3}),
        regime="RANS-kOmegaSST",
    )
    assert hints == []


# ────────── Advisor: U relaxation ──────────


def test_u_warning_band_for_rans():
    hints = derive_stability_hints(
        urf=_override(equations={"U": 0.8}),
        regime="RANS-kOmegaSST",
    )
    assert len(hints) == 1
    assert hints[0].target == "equations.U"
    assert hints[0].severity == "warning"


def test_u_critical_above_warn_for_rans():
    hints = derive_stability_hints(
        urf=_override(equations={"U": 0.95}),
        regime="RANS-kOmegaSST",
    )
    assert len(hints) == 1
    assert hints[0].severity == "critical"


def test_u_warning_threshold_relaxed_for_laminar():
    """Laminar U warn threshold is 0.9 (not RANS' 0.85). U=0.88
    crosses RANS warn → critical, but for laminar it's still
    warning (since 0.88 > 0.7 safe but ≤ 0.9 laminar warn)."""
    rans = derive_stability_hints(
        urf=_override(equations={"U": 0.88}),
        regime="RANS-kOmegaSST",
    )
    laminar = derive_stability_hints(
        urf=_override(equations={"U": 0.88}),
        regime="laminar",
    )
    assert len(rans) == 1 and rans[0].severity == "critical"
    assert len(laminar) == 1 and laminar[0].severity == "warning"


def test_u_critical_for_laminar_above_0_9():
    hints = derive_stability_hints(
        urf=_override(equations={"U": 0.95}),
        regime="laminar",
    )
    assert hints[0].severity == "critical"


# ────────── Advisor: p relaxation ──────────


def test_p_warning_band():
    hints = derive_stability_hints(
        urf=_override(fields={"p": 0.4}),
        regime="RANS-kOmegaSST",
    )
    assert len(hints) == 1
    assert hints[0].target == "fields.p"
    assert hints[0].severity == "warning"


def test_p_critical_above_warn():
    hints = derive_stability_hints(
        urf=_override(fields={"p": 0.7}),
        regime="RANS-kOmegaSST",
    )
    assert hints[0].severity == "critical"


# ────────── Advisor: turbulence equations ──────────


def test_turbulence_warning_band():
    for eq in ("k", "omega", "epsilon"):
        hints = derive_stability_hints(
            urf=_override(equations={eq: 0.8}),
            regime="RANS-kOmegaSST",
        )
        assert len(hints) == 1
        assert hints[0].severity == "warning"
        assert eq in hints[0].target


def test_turbulence_critical_above_warn():
    for eq in ("k", "omega", "epsilon"):
        hints = derive_stability_hints(
            urf=_override(equations={eq: 0.9}),
            regime="RANS-kOmegaSST",
        )
        assert hints[0].severity == "critical"


# ────────── Advisor: LES regime hint ──────────


def test_les_regime_emits_info_hint_when_urf_present():
    hints = derive_stability_hints(
        urf=_override(equations={"U": 0.7}),  # safe per RANS but LES is special
        regime="LES-stub",
    )
    info_hints = [h for h in hints if h.severity == "info" and h.target == "regime"]
    assert len(info_hints) == 1


def test_les_regime_no_info_hint_when_urf_empty():
    hints = derive_stability_hints(
        urf=_override(),
        regime="LES-stub",
    )
    assert hints == []


# ────────── Advisor: combined + sort order ──────────


def test_combined_hints_sorted_critical_first():
    hints = derive_stability_hints(
        urf=_override(
            equations={"U": 0.95, "k": 0.8},
            fields={"p": 0.4},
        ),
        regime="RANS-kOmegaSST",
    )
    severities = [h.severity for h in hints]
    # critical (U) first, then warning (k, p), no info.
    assert severities[0] == "critical"
    # No "info" before any "warning", no "warning" before any "critical".
    rank = {"critical": 0, "warning": 1, "info": 2}
    for i in range(len(severities) - 1):
        assert rank[severities[i]] <= rank[severities[i + 1]]


def test_warnings_within_same_severity_alpha_sorted_by_target():
    hints = derive_stability_hints(
        urf=_override(
            equations={"U": 0.8, "k": 0.8},
            fields={"p": 0.4},
        ),
        regime="RANS-kOmegaSST",
    )
    warnings = [h for h in hints if h.severity == "warning"]
    targets = [h.target for h in warnings]
    assert targets == sorted(targets)


# ────────── V132 advisory-only contract ──────────


def test_advisor_module_not_in_known_mutation_functions():
    """Stability advisor MUST NOT be a mutator — V130 Principle B."""
    from ui.backend.services.ai_actions.mutating_routes import (
        KNOWN_MUTATION_FUNCTIONS,
    )

    for module, symbol in KNOWN_MUTATION_FUNCTIONS:
        assert symbol != "derive_stability_hints"
        assert "urf_advisor" not in module
