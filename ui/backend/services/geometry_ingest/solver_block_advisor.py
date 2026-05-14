"""Density-based solver fvSolution / controlDict pre-flight advisor.

Pre-runtime validation of ``controlDict.adjustTimeStep`` and
``fvSolution.solvers.<field>.preconditioner`` for density-based
compressible solvers (currently rhoCentralFoam · the project's first
density-based-explicit class). Two LANDED rules cover the V27 + V28
failure modes documented on case_006 ONERA M6 transonic (2026-05-08
solver-run history):

R1 (V27) — rhoCentralFoam without ``adjustTimeStep yes``:
    First-iter Co_mean = 674.83, Co_max = 69,440 with ``deltaT 1.0``
    and ``adjustTimeStep no``. rhoCentralFoam uses explicit central-
    upwind flux; CFL stability limit is ``Co = (|U| + a) * dt / dx``.
    A fixed deltaT typically picked from rhoSimpleFoam / rhoPimpleFoam
    intuition is 4-5 orders of magnitude too large. The user-side trap
    is structural similarity to other compressible solvers where fixed
    dt is fine.

R2 (V28) — DILU preconditioner on rhoCentralFoam symmetric matrices:
    rhoCentralFoam wraps U / e / k / omega in a different ``lduMatrix``
    path that maps to the **symmetric** matrix solver registry. DILU
    (Diagonal Incomplete LU) is for asymmetric matrices; symmetric
    matrix path requires DIC, FDIC, GAMG, diagonal, or one of the
    explicit-iteration smoothers (``smoothSolver`` with
    ``symGaussSeidel`` per canonical
    ``tutorials/compressible/rhoCentralFoam/biconic25-55Run35``). The
    case_005 → case_006 fvSolution inheritance (rhoSimpleFoam being
    pressure-based / asymmetric, rhoCentralFoam being density-based /
    symmetric) is the natural-but-wrong inheritance pattern.

Anti-scope (per V130 advisory-only / V132 contract):

- Does NOT mutate any case directory · returns frozen findings only.
- Does NOT check fvSchemes (separate advisor class · future-extension).
- Does NOT runtime-verify Courant number · the engineer-symptom row is
  documentation; the advisor fires pre-runtime on the config pattern.
- Does NOT validate non-density-based solver classes today
  (rhoSimpleFoam / rhoPimpleFoam fvSolution rules belong to a future-
  extension along V53 lines · symmetric-vs-asymmetric class flip when
  ``transonic yes``). Forward-extension is anticipated but out of V64-A
  scope; the advisor returns empty for non-density-based solvers today.

Inputs are a single :class:`SolverBlockSnapshot` instance (frozen
dataclass · all fields explicit). Snapshot mirrors a normalized view of
``system/controlDict`` + ``system/fvSolution`` extracted by the
substrate-input loader. No FreeCAD, no OpenFOAM, no LLM dependency.

References:
- ``industrial_case_solver_findings.md`` V27 + V28 (case_006 v1
  2026-05-08 pre-fix snapshot)
- ``solver_convergence_playbook.md`` S15 (V27 + V28 codified)

LANDED 2026-05-15 under DEC-V64-A-sub-M-V64A-CASE-006-SUBSTRATE-V2.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

# Density-based solver classes whose fvSolution path is symmetric for the
# velocity / energy / turbulence-quantity equations. rhoCentralFoam is the
# only LANDED density-based-explicit solver today; rhoCentralDyMFoam is
# the dynamic-mesh variant with the same matrix structure.
_DENSITY_BASED_SYMMETRIC_SOLVERS: frozenset[str] = frozenset({
    "rhoCentralFoam",
    "rhoCentralDyMFoam",
})

# Preconditioner names whose target matrix class is asymmetric. Flagging
# any of these on the symmetric-matrix path produces V28's runtime error
# (``Unknown symmetric matrix preconditioner type DILU``).
_ASYMMETRIC_ONLY_PRECONDITIONERS: frozenset[str] = frozenset({
    "DILU",
    "FDILU",
})


@dataclass(frozen=True)
class SolverBlockSnapshot:
    """Normalized snapshot of ``system/controlDict`` + ``system/fvSolution``.

    Constructed by the substrate-input loader from a YAML file under
    ``case_*/inputs/solver_block_inputs.yaml``. The snapshot intentionally
    omits scheme blocks (``fvSchemes``) and time-window / write-interval
    controls — those are tracked by separate advisor classes (when LANDED)
    or by the validation-report substrate.

    Fields:

      ``solver`` — OpenFOAM solver application name from ``controlDict``
      (e.g., ``"rhoCentralFoam"``).

      ``adjust_time_step`` — ``controlDict.adjustTimeStep`` flag, parsed
      to ``bool`` if present (``yes`` / ``no`` / ``true`` / ``false`` /
      ``on`` / ``off``); ``None`` if the key is absent (treated as the
      OpenFOAM default ``no`` for V27 dispatch).

      ``delta_t`` — initial ``controlDict.deltaT``; included for
      diagnostic message detail (R1 references the ratio of fixed-dt vs
      the CFL-stable dt for shock cases).

      ``preconditioners`` — mapping of field name (``U`` / ``e`` / ``k``
      / ``omega`` / ``p`` / ``rho`` / ``rhoU`` / ``rhoE`` / ...) to the
      preconditioner string read from
      ``fvSolution.solvers.<field>.preconditioner``. Fields where the
      preconditioner is unspecified (e.g., direct ``diagonal`` solver)
      are absent from the mapping.
    """

    solver: str
    adjust_time_step: bool | None = None
    delta_t: float | None = None
    preconditioners: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class SolverBlockFinding:
    """One advisor finding.

    Mirrors the shape used by D10 / A8 / A10 / D6 (single ``code`` +
    ``severity`` + ``location`` + engineer-readable ``message`` +
    ``detail`` mirroring the upstream convention used by D10).
    """

    severity: str          # "critical" today; ``info``/``warning`` reserved
    code: str              # e.g., "v27_adjusttimestep_required"
    location: str          # e.g., "controlDict" / "fvSolution.solvers.U"
    detail: str            # engineer-readable summary


@dataclass(frozen=True)
class SolverBlockReport:
    """Aggregate output from :func:`check_solver_block`.

    The stack normalizer reads ``findings`` and emits a sequence of
    :class:`advisor_stack.Finding`. Empty when the snapshot describes a
    non-density-based solver, or when both V27 + V28 patterns are absent.
    """

    findings: tuple[SolverBlockFinding, ...]


def check_solver_block(snapshot: SolverBlockSnapshot) -> SolverBlockReport:
    """Inspect ``snapshot`` for V27 + V28 patterns.

    Returns a :class:`SolverBlockReport` with zero or more findings.
    Findings are emitted in deterministic order: V27 first (controlDict
    plane), then V28 in field-name-sorted order (``U``, ``e``, ``k``,
    ``omega``, ...).

    Pure function · no I/O · no logging · no side-effects.
    """
    findings: list[SolverBlockFinding] = []

    if snapshot.solver not in _DENSITY_BASED_SYMMETRIC_SOLVERS:
        return SolverBlockReport(findings=())

    # R1 (V27) — adjust_time_step missing or False on a density-based-
    # explicit solver. Treat absent (None) as False because OpenFOAM's
    # controlDict default is ``adjustTimeStep no`` when the key is omitted.
    if not snapshot.adjust_time_step:
        delta_t_note = (
            f"; deltaT={snapshot.delta_t!r}"
            if snapshot.delta_t is not None
            else ""
        )
        findings.append(
            SolverBlockFinding(
                severity="critical",
                code="v27_adjusttimestep_required",
                location="controlDict.adjustTimeStep",
                detail=(
                    f"{snapshot.solver} requires adjustTimeStep yes "
                    f"(explicit central-upwind flux · CFL-bounded){delta_t_note}; "
                    "fixed deltaT yields catastrophic first-iter Courant "
                    "number (Co > 10^4 observed on case_006 v1 2026-05-08)"
                ),
            )
        )

    # R2 (V28) — DILU / FDILU preconditioner on the symmetric matrix
    # path. Walk the preconditioner mapping deterministically.
    for field_name in sorted(snapshot.preconditioners):
        precond = snapshot.preconditioners[field_name]
        if precond in _ASYMMETRIC_ONLY_PRECONDITIONERS:
            findings.append(
                SolverBlockFinding(
                    severity="critical",
                    code="v28_dilu_on_symmetric",
                    location=f"fvSolution.solvers.{field_name}.preconditioner",
                    detail=(
                        f"{snapshot.solver} routes field '{field_name}' through "
                        f"the symmetric matrix path; preconditioner '{precond}' "
                        "is asymmetric-only (use DIC / FDIC / GAMG / diagonal, "
                        "or smoothSolver+symGaussSeidel per canonical "
                        "rhoCentralFoam tutorial biconic25-55Run35)"
                    ),
                )
            )

    return SolverBlockReport(findings=tuple(findings))
