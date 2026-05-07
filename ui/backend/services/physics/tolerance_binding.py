"""DEC-V61-144 (N3.5) · regime → default tolerance template binding.

Maps `RegimeKind` to a `ToleranceTemplate` carrying per-equation
residual targets. The Step Physics panel surfaces the default
template as informational; engineer overrides in N4.2 (solver dict
editor with diff against derived defaults).

Three templates v0:

  * `lab_quality`    — tight residuals for V&V (1e-7 momentum,
                       1e-7 pressure, 1e-7 turbulence). Slow
                       convergence; good for grid-convergence studies.
  * `engineering`    — industrial defaults (1e-5 / 1e-5 / 1e-5).
                       Most cases. The "good enough" target.
  * `fast_survey`    — loose targets (1e-3 / 1e-3 / 1e-3) for
                       sweep / morph runs where qualitative answers
                       are sufficient.

Charter §"existing CaseProfile machinery" — N3.5 is the FIRST sub-DEC
to introduce a structured tolerance contract; N4.2 (solver dict
editor) consumes it as the default-with-override starting point.
The "case profile" name space is reserved for the broader concept
(regime + material + solver + tolerance + run-control bundle) the
M3-extend / M4 milestones will flesh out.

V132: pure read-only function; no mutation surface; no registry entry.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ui.backend.schemas.regime_contract import RegimeKind


ToleranceTier = Literal["lab_quality", "engineering", "fast_survey"]


@dataclass(frozen=True)
class ToleranceTemplate:
    """Per-equation residual targets used by SIMPLE/PIMPLE residual
    control + linear-solver tolerances.

    All values are absolute residuals (the OpenFOAM linear-solver
    `tolerance` field). The relative-tolerance (`relTol`) field of
    each linear solver remains 0 in our profiles — running residuals
    are checked against absolute targets only.
    """

    tier: ToleranceTier
    momentum: float          # U-equation residual target
    pressure: float          # p-equation residual target
    turbulence: float        # k / ω / ε residual target
    energy: float            # T-equation residual target
    rationale: str


_LAB = ToleranceTemplate(
    tier="lab_quality",
    momentum=1e-7,
    pressure=1e-7,
    turbulence=1e-7,
    energy=1e-7,
    rationale=(
        "V&V tight residuals — appropriate for grid-convergence "
        "studies and benchmark reproduction. Solver runs longer; "
        "engineer trades wall-clock for confidence in the field "
        "values' digits beyond engineering precision."
    ),
)

_ENG = ToleranceTemplate(
    tier="engineering",
    momentum=1e-5,
    pressure=1e-5,
    turbulence=1e-5,
    energy=1e-5,
    rationale=(
        "Industrial default — converges quickly to engineering "
        "precision (3-4 sig figs on integral quantities). Most "
        "cases ship with this tier."
    ),
)

_FAST = ToleranceTemplate(
    tier="fast_survey",
    momentum=1e-3,
    pressure=1e-3,
    turbulence=1e-3,
    energy=1e-3,
    rationale=(
        "Loose — for parameter sweeps / shape-morphing runs where "
        "the engineer only needs qualitative trend, not a converged "
        "field. Do NOT use for production answers."
    ),
)


TOLERANCE_TEMPLATES: dict[ToleranceTier, ToleranceTemplate] = {
    "lab_quality": _LAB,
    "engineering": _ENG,
    "fast_survey": _FAST,
}


# Regime → default tier mapping. Engineering is the most common
# default; LES gets lab_quality because LES turbulent statistics are
# sensitive to residual control. Laminar gets engineering since lab-
# quality is opt-in for LDC-style benchmark reproduction.
_REGIME_DEFAULT_TIER: dict[RegimeKind, ToleranceTier] = {
    "laminar": "engineering",
    "RANS-RAS": "engineering",
    "RANS-kOmegaSST": "engineering",
    "LES-stub": "lab_quality",
}


def derive_default_tolerance_tier(regime: RegimeKind) -> ToleranceTier:
    """Return the default tier for a regime. Engineer can pick a
    different tier in N4.2 — this is just the starting point."""
    if regime not in _REGIME_DEFAULT_TIER:
        raise KeyError(
            f"no default tolerance tier for regime={regime!r} — "
            "extend _REGIME_DEFAULT_TIER"
        )
    return _REGIME_DEFAULT_TIER[regime]


def get_tolerance_template(tier: ToleranceTier) -> ToleranceTemplate:
    """Look up template by tier. Raises KeyError on unknown tier."""
    if tier not in TOLERANCE_TEMPLATES:
        raise KeyError(f"unknown tolerance tier {tier!r}")
    return TOLERANCE_TEMPLATES[tier]


def derive_tolerance_for_regime(regime: RegimeKind) -> ToleranceTemplate:
    """Convenience: regime → default-tier → template in one call."""
    return get_tolerance_template(derive_default_tolerance_tier(regime))
