"""DEC-V61-143 (N3.4) · solver derivation table.

Maps `RegimeContract` × `MaterialContract` thermal-present? → OpenFOAM
solver name. Read-only function — engineer can override in N4 when
the BC + solver workbench lands. The Step Physics panel (N3.3) will
surface the derived solver as informational; the engineer never has
to choose it manually if they accept the default.

V132 contract: this module has NO mutation surface — it returns a
string. The route layer (future N3.5 GET endpoint or N4 solver-dict
editor) consumes the result; nothing here writes disk.

Derivation rules (v0):

| regime          | thermal? | derived solver        |
|-----------------|----------|-----------------------|
| laminar         | no       | icoFoam               |
| laminar         | yes      | buoyantPimpleFoam     |
| RANS-RAS        | no       | simpleFoam            |
| RANS-RAS        | yes      | buoyantSimpleFoam     |
| RANS-kOmegaSST  | no       | simpleFoam            |
| RANS-kOmegaSST  | yes      | buoyantSimpleFoam     |
| LES-stub        | (any)    | pimpleFoam            |

Defaults bias towards steady-state RANS (the most common industrial
case); engineer running transient overrides in N4.

Charter `Status: Accepted` for N3.4 requires every row to have a
``tested_against_case`` regression-suite ID — see
`SOLVER_DERIVATIONS` table below; missing test is a ship-blocker.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ui.backend.schemas.material_contract import MaterialContract
from ui.backend.schemas.regime_contract import RegimeContract, RegimeKind


SolverName = Literal[
    "icoFoam",
    "simpleFoam",
    "pimpleFoam",
    "buoyantSimpleFoam",
    "buoyantPimpleFoam",
]


@dataclass(frozen=True)
class SolverDerivation:
    """One row of the derivation table.

    `rationale` is a short text the UI surfaces next to the derived
    solver name — explains WHY this solver was picked so the engineer
    can decide whether to accept or override.

    `tested_against_case` is a regression-fixture ID
    (`cases/regression/<id>`) that exercises this solver. Charter
    requires every row to have one — missing test = ship-blocker.
    """

    regime: RegimeKind
    thermal: bool
    solver: SolverName
    rationale: str
    tested_against_case: str


SOLVER_DERIVATIONS: tuple[SolverDerivation, ...] = (
    SolverDerivation(
        regime="laminar",
        thermal=False,
        solver="icoFoam",
        rationale=(
            "laminar incompressible — transient solver appropriate for "
            "low-Re internal-flow case (LDC, etc.). Override to "
            "simpleFoam in N4 for steady-state."
        ),
        tested_against_case="lid_driven_cavity",
    ),
    SolverDerivation(
        regime="laminar",
        thermal=True,
        solver="buoyantPimpleFoam",
        rationale=(
            "laminar with energy equation — buoyancy-driven transient. "
            "Override to buoyantSimpleFoam for steady natural convection."
        ),
        tested_against_case="differential_heated_cavity",
    ),
    SolverDerivation(
        regime="RANS-RAS",
        thermal=False,
        solver="simpleFoam",
        rationale=(
            "RANS k-ε steady-state default for fully turbulent "
            "incompressible. Override to pimpleFoam for transient."
        ),
        tested_against_case="elbow_duct",
    ),
    SolverDerivation(
        regime="RANS-RAS",
        thermal=True,
        solver="buoyantSimpleFoam",
        rationale=(
            "RANS k-ε with energy equation — steady buoyant default."
        ),
        tested_against_case="differential_heated_cavity",
    ),
    SolverDerivation(
        regime="RANS-kOmegaSST",
        thermal=False,
        solver="simpleFoam",
        rationale=(
            "RANS k-ω SST steady-state — industrial default for wall-"
            "bounded incompressible RANS. Override to pimpleFoam for "
            "transient."
        ),
        tested_against_case="straight_pipe",
    ),
    SolverDerivation(
        regime="RANS-kOmegaSST",
        thermal=True,
        solver="buoyantSimpleFoam",
        rationale=(
            "RANS k-ω SST with energy equation — steady buoyant default."
        ),
        tested_against_case="differential_heated_cavity",
    ),
    SolverDerivation(
        regime="LES-stub",
        thermal=False,
        solver="pimpleFoam",
        rationale=(
            "LES is inherently transient. Engineer must hand-edit "
            "constant/momentumTransport to choose a sub-grid model "
            "(Smagorinsky / WALE / dynamic) — N3.3 emitted a TODO."
        ),
        tested_against_case="elbow_duct",
    ),
    SolverDerivation(
        regime="LES-stub",
        thermal=True,
        solver="buoyantPimpleFoam",
        rationale=(
            "LES with energy equation — transient buoyant solver. "
            "Engineer must still hand-edit momentumTransport for "
            "sub-grid model."
        ),
        tested_against_case="differential_heated_cavity",
    ),
)


def derive_solver(
    regime: RegimeContract,
    material: MaterialContract,
) -> SolverDerivation:
    """Look up the derivation row for the (regime, thermal-present) tuple.

    Always returns a row — every (RegimeKind, thermal) pair has an
    entry. A `KeyError` here would be a programming bug (RegimeKind
    grew without the table being updated).
    """
    thermal_present = material.thermal is not None
    for row in SOLVER_DERIVATIONS:
        if row.regime == regime.regime and row.thermal == thermal_present:
            return row
    # Defensive: if RegimeKind grew without table update, fail loud
    # rather than silently default. Charter §"missing test = ship-blocker"
    # invariant is enforced by the test suite, but this branch matters
    # if a developer adds a new regime literal in a separate commit.
    raise KeyError(
        f"no solver derivation for regime={regime.regime!r} "
        f"thermal={thermal_present!r} — extend SOLVER_DERIVATIONS"
    )
