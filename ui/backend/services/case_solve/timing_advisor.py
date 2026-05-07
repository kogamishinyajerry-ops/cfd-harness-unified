"""DEC-V61-150 (N4.5) · controlDict timing advisor (read-only).

Pure rule-based function consuming `ControlDictTiming` + the
N3.4-derived `SolverName` and emitting :class:`TimingHint` records.

V130 Principle B + V132 contract: this module advises only. Hints
render as informational badges in the timing panel; engineer reads
+ decides. Never auto-tunes. No mutation surface.

Steady-vs-transient solver families (per N3.4 derivation table):

  * Steady family (iterates to residualControl):
      simpleFoam · buoyantSimpleFoam
  * Transient family (advances physical time):
      icoFoam · pimpleFoam · buoyantPimpleFoam

Hints emitted:

  * `info` — engineer set adjust_time_step / max_co / delta_t on a
    steady solver (no error; the solver ignores those fields)
  * `info` — engineer set max_co=N with adjust_time_step=False
    (the value won't take effect; reminder)
  * `warning` — engineer set adjust_time_step=True but no max_co
    set anywhere; the profile default may not match the engineer's
    expectations
  * `info` — write_interval > end_time (case will write only the
    final step; usually a typo)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ui.backend.schemas.control_dict_timing import ControlDictTiming
from ui.backend.services.physics.solver_derivation import SolverName


HintSeverity = Literal["info", "warning"]


@dataclass(frozen=True)
class TimingHint:
    target: str
    severity: HintSeverity
    message: str


_STEADY_SOLVERS: frozenset[SolverName] = frozenset(
    {"simpleFoam", "buoyantSimpleFoam"}
)
_TRANSIENT_SOLVERS: frozenset[SolverName] = frozenset(
    {"icoFoam", "pimpleFoam", "buoyantPimpleFoam"}
)


def derive_timing_hints(
    *,
    timing: ControlDictTiming,
    solver: SolverName,
) -> list[TimingHint]:
    """Return advisory hints for the timing override against the
    derived solver. Empty list when overrides are coherent."""
    out: list[TimingHint] = []
    is_steady = solver in _STEADY_SOLVERS

    # Steady-solver + transient-only fields
    if is_steady:
        if timing.adjust_time_step is not None:
            out.append(
                TimingHint(
                    target="adjust_time_step",
                    severity="info",
                    message=(
                        f"adjust_time_step is set but {solver} is a steady-"
                        "state solver — the field will be written but ignored"
                    ),
                )
            )
        if timing.max_co is not None:
            out.append(
                TimingHint(
                    target="max_co",
                    severity="info",
                    message=(
                        f"max_co is set but {solver} is a steady-state "
                        "solver — the field will be written but ignored"
                    ),
                )
            )
        if timing.delta_t is not None:
            out.append(
                TimingHint(
                    target="delta_t",
                    severity="info",
                    message=(
                        f"delta_t is set but {solver} is a steady-state "
                        "solver — the field is interpreted as outer-loop "
                        "increment only"
                    ),
                )
            )

    # Transient-solver coherence checks
    if not is_steady:
        if timing.max_co is not None and timing.adjust_time_step is False:
            out.append(
                TimingHint(
                    target="max_co",
                    severity="info",
                    message=(
                        "max_co is set but adjust_time_step=False — the "
                        "value won't take effect (fixed Δt is used)"
                    ),
                )
            )
        if (
            timing.adjust_time_step is True
            and timing.max_co is None
        ):
            out.append(
                TimingHint(
                    target="max_co",
                    severity="warning",
                    message=(
                        "adjust_time_step=True but max_co is unset; the "
                        "profile default will be used — confirm it matches "
                        "your scheme tolerance"
                    ),
                )
            )

    # write_interval vs end_time sanity (regime-agnostic)
    if (
        timing.end_time is not None
        and timing.write_interval is not None
        and timing.write_interval > timing.end_time
    ):
        out.append(
            TimingHint(
                target="write_interval",
                severity="info",
                message=(
                    f"write_interval ({timing.write_interval}) > end_time "
                    f"({timing.end_time}) — the case will only write the "
                    "final step; typically a unit-mismatch typo"
                ),
            )
        )

    # Stable sort: warnings before info; alpha by target within.
    return sorted(
        out,
        key=lambda h: (0 if h.severity == "warning" else 1, h.target),
    )


__all__ = ["HintSeverity", "TimingHint", "derive_timing_hints"]
