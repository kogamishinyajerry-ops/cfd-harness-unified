"""DEC-V61-148 (N4.3) · URF stability advisor (read-only).

Pure rule-based function consuming :class:`URFOverride` +
:class:`RegimeContract` and emitting :class:`StabilityHint` records.

V130 Principle B + V132 contract: this module advises only. The hints
are rendered as informational text in the URF panel; engineer reads
+ decides. Never auto-tunes. No mutation surface. No V132 entry needed.

Hint thresholds (per RANS / LES industrial practice):

| equation | safe ≤ | warn (>safe, ≤agg) | aggressive > agg |
|---|---|---|---|
| U / equations | 0.7 | 0.85 | 0.85 (likely instability) |
| p / fields | 0.3 | 0.5 | 0.5 (stiff systems may diverge) |
| k / omega / epsilon | 0.7 | 0.85 | 0.85 |

For laminar regimes (no turbulence transport), U > 0.9 is acceptable;
the rule engine relaxes the U threshold. For LES (transient inherent),
URF is typically NOT used — emitting any URF override yields an info
hint reminding the engineer that LES doesn't use SIMPLE/PIMPLE
relaxation in the same way.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ui.backend.schemas.regime_contract import RegimeKind
from ui.backend.schemas.urf_override import URFOverride


HintSeverity = Literal["info", "warning", "critical"]


@dataclass(frozen=True)
class StabilityHint:
    """One advisory record. UI surfaces as a colored badge next to the
    URF slider for the affected field/equation."""

    target: str          # field/equation name OR "regime" for cross-cut hints
    severity: HintSeverity
    message: str
    rationale: str       # why this threshold; cite-ish sentence


# Rule thresholds.
_U_SAFE = 0.7
_U_WARN = 0.85
_U_LAMINAR_RELAXED = 0.9
_P_SAFE = 0.3
_P_WARN = 0.5
_TURB_SAFE = 0.7
_TURB_WARN = 0.85


def derive_stability_hints(
    *,
    urf: URFOverride,
    regime: RegimeKind,
) -> list[StabilityHint]:
    """Return advisory hints for the URF override.

    Empty list when all factors are within safe ranges. Stable-sort
    by (severity-rank descending, target name) so the UI renders
    critical/warning before info."""
    out: list[StabilityHint] = []

    # LES regimes typically don't use SIMPLE/PIMPLE relaxation in the
    # same way — flag any URF as info.
    if regime == "LES-stub" and (urf.fields or urf.equations):
        out.append(
            StabilityHint(
                target="regime",
                severity="info",
                message=(
                    "LES is transient and typically doesn't use "
                    "relaxation factors. Engineer should verify URF "
                    "applies to the chosen sub-grid model."
                ),
                rationale=(
                    "SIMPLE/PIMPLE relaxation is for steady or "
                    "iterative-coupled-corrector cases; LES outer "
                    "loops behave differently."
                ),
            )
        )

    # Equations: U is the common one; relax threshold for laminar.
    u_warn = _U_LAMINAR_RELAXED if regime == "laminar" else _U_WARN
    for name, factor in urf.equations.items():
        if name == "U":
            if factor > u_warn:
                out.append(
                    StabilityHint(
                        target=f"equations.{name}",
                        severity="critical",
                        message=(
                            f"U relaxation = {factor} exceeds "
                            f"{u_warn:.2f} — solver may diverge."
                        ),
                        rationale=(
                            "RANS momentum factors above 0.85 (or 0.9 "
                            "for laminar) routinely cause floating-"
                            "point divergence in SIMPLE/PIMPLE."
                        ),
                    )
                )
            elif factor > _U_SAFE:
                out.append(
                    StabilityHint(
                        target=f"equations.{name}",
                        severity="warning",
                        message=(
                            f"U relaxation = {factor} above 'safe' "
                            f"{_U_SAFE:.2f} — watch residuals."
                        ),
                        rationale=(
                            "RANS U converges fastest at 0.7-0.8; "
                            "above that, residuals can wander."
                        ),
                    )
                )
        elif name in ("k", "omega", "epsilon"):
            if factor > _TURB_WARN:
                out.append(
                    StabilityHint(
                        target=f"equations.{name}",
                        severity="critical",
                        message=(
                            f"turbulence equation {name} relaxation = "
                            f"{factor} exceeds {_TURB_WARN:.2f}."
                        ),
                        rationale=(
                            "Turbulence transport equations diverge "
                            "frequently above 0.85."
                        ),
                    )
                )
            elif factor > _TURB_SAFE:
                out.append(
                    StabilityHint(
                        target=f"equations.{name}",
                        severity="warning",
                        message=(
                            f"turbulence equation {name} relaxation = "
                            f"{factor} above 'safe' {_TURB_SAFE:.2f}."
                        ),
                        rationale=(
                            "Turbulence transport prefers 0.5-0.7."
                        ),
                    )
                )

    # Fields: p typically. Pressure relaxation is the most-common knob.
    for name, factor in urf.fields.items():
        if name == "p":
            if factor > _P_WARN:
                out.append(
                    StabilityHint(
                        target=f"fields.{name}",
                        severity="critical",
                        message=(
                            f"p relaxation = {factor} exceeds "
                            f"{_P_WARN:.2f} — likely divergence on "
                            "stiff systems."
                        ),
                        rationale=(
                            "Pressure relaxation > 0.5 routinely "
                            "diverges in SIMPLE family solvers."
                        ),
                    )
                )
            elif factor > _P_SAFE:
                out.append(
                    StabilityHint(
                        target=f"fields.{name}",
                        severity="warning",
                        message=(
                            f"p relaxation = {factor} above 'safe' "
                            f"{_P_SAFE:.2f}."
                        ),
                        rationale=(
                            "Pressure relaxation tightens convergence "
                            "in SIMPLE; 0.3 is the most-common default."
                        ),
                    )
                )

    return sorted(
        out,
        key=lambda h: (_severity_rank(h.severity), h.target),
    )


def _severity_rank(s: HintSeverity) -> int:
    """Critical first, then warning, then info — for stable UI sort."""
    return {"critical": 0, "warning": 1, "info": 2}[s]


__all__ = [
    "HintSeverity",
    "StabilityHint",
    "derive_stability_hints",
]
