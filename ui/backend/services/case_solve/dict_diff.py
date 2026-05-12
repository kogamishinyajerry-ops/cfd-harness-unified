"""DEC-V61-147 (N4.2) · solver-dict diff utility.

Computes a structured diff between (a) the N3.4-derived defaults
(solver YAML profile + N3.5 ToleranceTemplate) and (b) the engineer's
:class:`SolverDictsOverride`. The result is a list of changed-field
records the UI surfaces in the "diff against derived defaults" panel.

This module is **read-only**: takes two structured inputs, produces
a structured output. No disk write, no V132 surface.

Diff record shape:

    DiffEntry
      path: str                  # canonical dotted path
      baseline: float | str | int | None
      override: float | str | int | None
      reason: str                # human-readable explanation

Output is a list of DiffEntry, sorted by `path` for stable rendering.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ui.backend.schemas.regime_contract import RegimeKind
from ui.backend.schemas.solver_dicts import (
    LinearSolverOverride,
    SolverDictsOverride,
)
from ui.backend.services.physics.solver_derivation import SolverName
from ui.backend.services.physics.tolerance_binding import (
    ToleranceTemplate,
)


@dataclass(frozen=True)
class DiffEntry:
    path: str
    baseline: Any
    override: Any
    reason: str


# Canonical field → which tolerance-template tier-residual it inherits
# from when the override leaves it None. icoFoam (transient PISO) has
# no residualControl block — N3.5 thresholds apply only to SIMPLE/
# PIMPLE which is consumed at the route layer (caller skips the diff
# branch for icoFoam).
_FIELD_TO_TIER_KEY: dict[str, str] = {
    "U": "momentum",
    "UFinal": "momentum",
    "p": "pressure",
    "pFinal": "pressure",
    "k": "turbulence",
    "kFinal": "turbulence",
    "omega": "turbulence",
    "omegaFinal": "turbulence",
    "epsilon": "turbulence",
    "epsilonFinal": "turbulence",
    "T": "energy",
    "TFinal": "energy",
}


def _baseline_tolerance_for_field(
    field: str, template: ToleranceTemplate
) -> float | None:
    """Return the residual target the N3.5 template assigns to this
    field, or None if the field doesn't fit the standard tier
    mapping (e.g. exotic transport equations)."""
    tier_key = _FIELD_TO_TIER_KEY.get(field)
    if tier_key is None:
        return None
    return getattr(template, tier_key)


def diff_against_defaults(
    *,
    solver: SolverName,
    regime: RegimeKind,
    tolerance_template: ToleranceTemplate,
    override: SolverDictsOverride,
) -> list[DiffEntry]:
    """Compute the override-vs-baseline diff.

    Parameters
    ----------
    solver
        N3.4-derived solver name (informs which YAML profile is the
        baseline; this function uses it for context strings only —
        full profile-loading happens at the future writer layer).
    regime
        N3.2 regime literal (informs the human-readable reason
        strings).
    tolerance_template
        N3.5-derived template providing the per-tier baseline
        residuals.
    override
        Engineer-supplied :class:`SolverDictsOverride`.
    """
    out: list[DiffEntry] = []

    # Linear solvers — per-field tolerance overrides
    for field, lso in sorted(override.linear_solvers.items()):
        out.extend(_diff_linear_solver(field, lso, tolerance_template, regime))

    # Non-orthogonal correctors
    if override.n_non_orthogonal_correctors is not None:
        out.append(
            DiffEntry(
                path="n_non_orthogonal_correctors",
                baseline=_default_n_non_ortho(solver),
                override=override.n_non_orthogonal_correctors,
                reason=(
                    f"engineer overrode the {solver} profile's default "
                    "non-orthogonal corrector count (typical reason: "
                    "high checkMesh max-non-orthogonality)"
                ),
            )
        )

    # divSchemes default
    if override.div_scheme_default is not None:
        out.append(
            DiffEntry(
                path="div_scheme_default",
                baseline=_default_div_scheme(solver),
                override=override.div_scheme_default,
                reason=(
                    f"engineer overrode divSchemes default for {solver}; "
                    "typical reasons: switch to limitedLinear for RANS "
                    "robustness, or upwind for first-order survey runs"
                ),
            )
        )

    # residualControl thresholds
    if override.residual_control is not None:
        for field, threshold in sorted(override.residual_control.items()):
            baseline = _baseline_tolerance_for_field(field, tolerance_template)
            out.append(
                DiffEntry(
                    path=f"residual_control.{field}",
                    baseline=baseline,
                    override=threshold,
                    reason=(
                        f"engineer tightened/loosened residualControl on "
                        f"{field} relative to {tolerance_template.tier} "
                        "tier baseline"
                    ),
                )
            )

    return sorted(out, key=lambda e: e.path)


def _diff_linear_solver(
    field: str,
    lso: LinearSolverOverride,
    template: ToleranceTemplate,
    regime: RegimeKind,
) -> list[DiffEntry]:
    out: list[DiffEntry] = []
    if lso.family is not None:
        out.append(
            DiffEntry(
                path=f"linear_solvers.{field}.family",
                baseline=_default_linear_solver_family(field),
                override=lso.family,
                reason=(
                    f"engineer overrode {field} linear-solver family; "
                    "typical reason: GAMG for very large p, PBiCGStab "
                    "for tough U convergence"
                ),
            )
        )
    if lso.tolerance is not None:
        out.append(
            DiffEntry(
                path=f"linear_solvers.{field}.tolerance",
                baseline=_baseline_tolerance_for_field(field, template),
                override=lso.tolerance,
                reason=(
                    f"engineer overrode {field} linear-solver absolute "
                    f"tolerance relative to {template.tier} tier baseline"
                ),
            )
        )
    if lso.rel_tol is not None:
        out.append(
            DiffEntry(
                path=f"linear_solvers.{field}.rel_tol",
                baseline=_default_rel_tol(field),
                override=lso.rel_tol,
                reason=(
                    f"engineer overrode {field} relTol; typical: 0.05 "
                    "for non-final iterations, 0 for final-corrector"
                ),
            )
        )
    return out


# ────────── Default lookup helpers ──────────
#
# These mirror the YAML profile contents at a coarse level. For the
# diff renderer's purposes we only need to know what the solver's
# default WOULD be — the actual final-rendered dict comes from the
# solver_profiles module at the route layer.


def _default_n_non_ortho(solver: SolverName) -> int:
    # icoFoam profile uses 2; SIMPLE/PIMPLE solvers default to 0-1.
    return 2 if solver == "icoFoam" else 0


def _default_div_scheme(solver: SolverName) -> str:
    # Mirrors the YAML profile choices: linearUpwind for icoFoam,
    # limitedLinear for RANS / SIMPLE family.
    if solver == "icoFoam":
        return "linearUpwind"
    return "limitedLinear"


def _default_linear_solver_family(field: str) -> str:
    """Most cases: PCG for symmetric (p, k, omega), smoothSolver for
    U / asymmetric. Diff renderer uses this as a "what would have
    been used" hint; the actual choice is in the YAML profile."""
    if field.startswith("p") or field.startswith("k") or field.startswith("omega") or field.startswith("epsilon"):
        return "PCG"
    return "smoothSolver"


def _default_rel_tol(field: str) -> float:
    """Final-corrector iterations get relTol=0; other iterations 0.05.
    Heuristic: name ends with 'Final' → 0, else 0.05."""
    return 0.0 if field.endswith("Final") else 0.05


__all__ = [
    "DiffEntry",
    "diff_against_defaults",
]
