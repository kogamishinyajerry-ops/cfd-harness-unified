"""DEC-V61-148 (N4.3) · per-equation URF (under-relaxation factor) override.

Captures engineer-set relaxation factors for SIMPLE/PIMPLE solvers.
Lives in `system/fvSolution` under the `relaxationFactors { fields {...}
equations {...} }` block; transient PISO solvers (icoFoam) ignore URF
(no relaxation block written for those — caller skips).

Wire shape:

    URFOverride
      fields: dict[str, float]      # field name → factor in (0, 1]
                                    # (e.g. p: 0.3 — STRONG relaxation
                                    # on pressure for stiff cases)
      equations: dict[str, float]   # equation name → factor in (0, 1]
                                    # (e.g. U: 0.7 — typical RANS U)
      authored_at: str

V132: no mutation surface — schema only. Writer integration lands in
the N4.3 commit route (which IS a V132 mutator) further below.

Stability advisor (separate module `urf_advisor.py`) consumes this
schema + RegimeContract and returns hints when factors look too
aggressive — pure read-only rule engine, V130 advisory-only.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class URFOverride(BaseModel):
    """Engineer-set relaxation factors. Both maps are optional —
    setting either populates the corresponding fvSolution sub-block.
    Empty override = inherit profile YAML defaults.
    """

    model_config = ConfigDict(extra="forbid")

    fields: dict[str, float] = Field(
        default_factory=dict,
        description=(
            "Map from field name (typically 'p', 'rho') to relaxation "
            "factor in (0, 1]. Lower = more relaxed (more stable, "
            "slower convergence). 0.3 is a common pressure under-"
            "relaxation; 1.0 = no relaxation."
        ),
    )
    equations: dict[str, float] = Field(
        default_factory=dict,
        description=(
            "Map from equation name (typically 'U', 'k', 'omega', "
            "'epsilon') to relaxation factor in (0, 1]. 0.7 is a "
            "common RANS momentum default."
        ),
    )
    authored_at: str = Field(
        ...,
        min_length=10,
        max_length=40,
    )

    @field_validator("fields", "equations")
    @classmethod
    def _factors_in_open_zero_to_one_inclusive(
        cls, v: dict[str, float]
    ) -> dict[str, float]:
        for name, factor in v.items():
            if not name.isalnum():
                raise ValueError(
                    f"URF map field name {name!r} must be alnum (e.g. 'U', 'p')"
                )
            if factor <= 0.0 or factor > 1.0:
                raise ValueError(
                    f"URF[{name!r}]={factor} must be in (0, 1] — "
                    "0 stalls the solver, > 1 is unstable"
                )
        return v


__all__ = ["URFOverride"]
