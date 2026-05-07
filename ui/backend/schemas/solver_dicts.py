"""DEC-V61-147 (N4.2) · solver dict override schema.

Captures the engineer-tunable knobs of fvSchemes + fvSolution +
controlDict that override the YAML solver-profile defaults
(``services/case_solve/solver_profiles/profiles/*.yaml``). Engineer
fills via the future Step 3 Physics setup workbench (N4.3 wires the
panel).

Scope: only the most commonly-tuned subset. Long-tail knobs continue
to use the raw escape hatch (N4.4 — copy dict to clipboard, edit in
engineer's editor, re-import).

Wire shape:

    SolverDictsOverride
      linear_solvers: dict[str, LinearSolverOverride]
        # field name (U, p, k, omega, ...) → tolerance / solver type
      n_non_orthogonal_correctors: int | None  # 0..5
      div_scheme_default: Literal[...] | None  # divSchemes "default"
      residual_control: dict[str, float] | None
        # field name → residual target (overrides N3.5 default tier)
      authored_at: str

Diff convention: a None field on the override means "don't touch the
derived default". Setting an explicit value means "override this
field". The diff function (`diff_against_defaults`) walks both the
override and the derived baseline and returns a list of changed
fields with (path, baseline, override) tuples.

Out of scope for N4.2 (lands in N4.3 / N4.5 / N4-extend):
  * URF (relaxation factors) — N4.3
  * controlDict timing fields — N4.5
  * Per-corrector residual control (P-only, P-final-only) — N4-extend
  * Custom limited-* gradient + div schemes — N4-extend
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


# Most-commonly-toggled scheme defaults. The full OpenFOAM divSchemes
# surface is much larger; this enum captures what 90% of cases tune.
DivSchemeDefault = Literal[
    "upwind",                    # 1st-order, robust, lossy
    "linear",                    # 2nd-order central, can wiggle
    "linearUpwind",              # 2nd-order with upwind blend (default)
    "limitedLinear",             # blended with limiter — RANS robust default
    "limitedLinearV",            # vector form for U
]

# Linear solver families. PCG/PBiCGStab for symmetric/asymmetric;
# smoothSolver with symGaussSeidel is the U-default workhorse.
LinearSolverFamily = Literal[
    "PCG",          # symmetric (p, k, omega)
    "PBiCGStab",    # asymmetric (rare — swap-in for U on tough cases)
    "smoothSolver", # iterative smoother (U default)
    "GAMG",         # geometric algebraic multigrid (large p)
]


class LinearSolverOverride(BaseModel):
    """Per-field linear solver override. None fields mean "use the
    profile YAML default for this knob".
    """

    model_config = ConfigDict(extra="forbid")

    family: LinearSolverFamily | None = Field(
        default=None,
        description=(
            "Linear solver family (PCG / PBiCGStab / smoothSolver / GAMG). "
            "None = use profile default."
        ),
    )
    tolerance: float | None = Field(
        default=None,
        gt=0.0,
        description=(
            "Absolute residual target. Overrides the field's tolerance "
            "from the N3.5-derived ToleranceTemplate. Strictly positive."
        ),
    )
    rel_tol: float | None = Field(
        default=None,
        ge=0.0,
        description=(
            "Relative tolerance. 0.0 means 'iterate to absolute "
            "tolerance only' — the standard final-corrector value. "
            "0.05 is a common non-final SIMPLE/PISO value."
        ),
    )

    @field_validator("rel_tol")
    @classmethod
    def _rel_tol_under_one(cls, v: float | None) -> float | None:
        if v is not None and v >= 1.0:
            raise ValueError("rel_tol must be < 1.0")
        return v


class SolverDictsOverride(BaseModel):
    """Engineer-tunable overrides on top of the N3.4 derived solver's
    YAML profile defaults. Every field is optional; absent = inherit
    derived default.
    """

    model_config = ConfigDict(extra="forbid")

    linear_solvers: dict[str, LinearSolverOverride] = Field(
        default_factory=dict,
        description=(
            "Map from field name (U, p, k, omega, epsilon, T, ...) to "
            "per-field linear-solver override. Field name MUST match "
            "what the derived solver profile declares — unknown names "
            "are rejected at apply time."
        ),
    )
    n_non_orthogonal_correctors: int | None = Field(
        default=None,
        ge=0,
        le=5,
        description=(
            "Number of non-orthogonal corrector loops in PISO/PIMPLE/"
            "SIMPLE block. Profile default is typically 0-2 depending "
            "on mesh quality (V126 checkMesh max-non-orthogonality "
            "informs this). Cap at 5 — beyond is almost always a "
            "meshing problem, not a corrector problem."
        ),
    )
    div_scheme_default: DivSchemeDefault | None = Field(
        default=None,
        description=(
            "Override the divSchemes 'default' entry. None = inherit "
            "profile YAML's choice (typically 'limitedLinear' for RANS, "
            "'linearUpwind' for icoFoam transient)."
        ),
    )
    residual_control: dict[str, float] | None = Field(
        default=None,
        description=(
            "Map from field name → residualControl threshold. None = "
            "inherit N3.5-derived ToleranceTemplate. When set, every "
            "value MUST be > 0; entries with field names not present "
            "in the derived solver's residual block are rejected at "
            "apply time."
        ),
    )
    authored_at: str = Field(
        ...,
        min_length=10,
        max_length=40,
        description="ISO 8601 timestamp string.",
    )

    @field_validator("residual_control")
    @classmethod
    def _residual_thresholds_positive(
        cls, v: dict[str, float] | None
    ) -> dict[str, float] | None:
        if v is None:
            return v
        for field, threshold in v.items():
            if threshold <= 0.0:
                raise ValueError(
                    f"residual_control[{field!r}] must be > 0; got {threshold}"
                )
        return v

    @field_validator("linear_solvers")
    @classmethod
    def _linear_solver_field_names_charset(
        cls, v: dict[str, LinearSolverOverride]
    ) -> dict[str, LinearSolverOverride]:
        # OpenFOAM field names: alnum + final-suffix is conventional
        # (e.g. p / pFinal / U / UFinal / k / kFinal). We accept alnum
        # only — anything else is suspicious.
        for name in v:
            if not name.isalnum():
                raise ValueError(
                    f"linear_solvers field name {name!r} must be alnum "
                    "(e.g. 'p', 'U', 'pFinal', 'k')"
                )
        return v


__all__ = [
    "DivSchemeDefault",
    "LinearSolverFamily",
    "LinearSolverOverride",
    "SolverDictsOverride",
]
