"""DEC-V61-150 (N4.5) · controlDict timing override schema.

Captures the 4 most-commonly-tuned timing knobs from
`system/controlDict`:

  * endTime           — simulation end time (s)
  * writeInterval     — frequency of field-output dumps
  * adjustTimeStep    — adaptive Δt enable flag (transient solvers)
  * maxCo             — max Courant number cap (transient solvers
                        with adjustTimeStep=on)

Steady solvers (simpleFoam family) ignore Δt / maxCo at runtime —
they iterate to residual convergence, NOT to wall-clock time.
N4.5 schema accepts these fields regardless of regime; the
companion `derive_timing_hints()` helper emits an info hint when
the engineer sets transient-only fields on a steady solver
(charter §threat-model row 7: info hint, NOT blocker per V130
advisory-only).

V132: schema only, no disk write, no V132 entry. Future integration
writer (N4-extend or downstream) adds the mutator route.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ControlDictTiming(BaseModel):
    """Engineer-tunable controlDict timing fields. Every field is
    optional — None means "inherit profile YAML default"."""

    model_config = ConfigDict(extra="forbid")

    end_time: float | None = Field(
        default=None,
        gt=0.0,
        description=(
            "endTime in seconds. Strictly positive. For steady "
            "solvers (simpleFoam family) this is interpreted as a "
            "max iteration count — the solver still terminates on "
            "residualControl convergence."
        ),
    )
    write_interval: float | None = Field(
        default=None,
        gt=0.0,
        description=(
            "writeInterval in seconds for transient OR every-Nth "
            "iteration for steady. Strictly positive."
        ),
    )
    adjust_time_step: bool | None = Field(
        default=None,
        description=(
            "Enable adaptive Δt (transient solvers only). When True, "
            "Δt is recomputed each step against `maxCo`. Steady "
            "solvers ignore this field."
        ),
    )
    max_co: float | None = Field(
        default=None,
        gt=0.0,
        le=10.0,
        description=(
            "Max Courant number when adjust_time_step=True. Bounded "
            "to (0, 10] — values above 10 routinely cause numerical "
            "instability for finite-volume schemes. Default 1.0 for "
            "PIMPLE / 0.5 for explicit schemes is conventional."
        ),
    )
    delta_t: float | None = Field(
        default=None,
        gt=0.0,
        description=(
            "Initial Δt (when adjust_time_step=False, this is the "
            "fixed Δt). Strictly positive. Profile YAML default "
            "varies by solver (icoFoam=0.005, pimpleFoam=0.001)."
        ),
    )
    authored_at: str = Field(
        ...,
        min_length=10,
        max_length=40,
    )

    @field_validator("write_interval")
    @classmethod
    def _write_interval_not_excessive(cls, v: float | None) -> float | None:
        # Defensive: an obscenely large write_interval suggests a
        # missed unit conversion. Cap at 1e6 seconds (~12 days).
        if v is not None and v > 1.0e6:
            raise ValueError(
                f"write_interval {v} > 1e6 — suspicious unit (seconds expected)"
            )
        return v


__all__ = ["ControlDictTiming"]
