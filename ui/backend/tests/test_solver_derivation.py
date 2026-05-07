"""DEC-V61-143 (N3.4) · solver derivation table tests.

Coverage:
  * Every (RegimeKind, thermal-present) tuple has a derivation row
    (no orphan combos)
  * Every row carries a ``tested_against_case`` regression-fixture ID
    (charter §"missing test = ship-blocker")
  * derive_solver returns the right row for each combo
  * Unknown regime raises (defensive branch)
"""
from __future__ import annotations

import pytest

from ui.backend.schemas.material_contract import (
    FluidProperties,
    MaterialContract,
    ThermalProperties,
)
from ui.backend.schemas.regime_contract import (
    ApplicabilityBounds,
    RegimeContract,
)
from ui.backend.services.physics import (
    SOLVER_DERIVATIONS,
    derive_solver,
)


def _material(*, with_thermal: bool) -> MaterialContract:
    return MaterialContract(
        kind="custom",
        fluid=FluidProperties(
            name="x",
            density=1000.0,
            kinematic_viscosity=1e-6,
            prandtl=7.0 if with_thermal else None,
        ),
        thermal=(
            ThermalProperties(specific_heat=1000.0, thermal_conductivity=1.0)
            if with_thermal
            else None
        ),
        authored_at="2026-05-07T12:00:00Z",
    )


def _regime(kind: str) -> RegimeContract:
    return RegimeContract(
        kind="custom",
        regime=kind,  # type: ignore[arg-type]
        applicability=ApplicabilityBounds(),
        authored_at="2026-05-07T12:00:00Z",
    )


# ────────── table completeness ──────────


_REGIME_KINDS = ("laminar", "RANS-RAS", "RANS-kOmegaSST", "LES-stub")


def test_table_covers_every_regime_kind_and_thermal_combo():
    """Every (RegimeKind × {thermal=False, thermal=True}) pair is in the
    table — 8 rows minimum (we ship exactly 8)."""
    combos = {(r.regime, r.thermal) for r in SOLVER_DERIVATIONS}
    expected = {
        (kind, thermal_present)
        for kind in _REGIME_KINDS
        for thermal_present in (False, True)
    }
    assert combos == expected, (
        f"derivation table missing combos: {expected - combos}; "
        f"unexpected: {combos - expected}"
    )


def test_every_row_has_a_regression_fixture_id():
    """Charter ship-blocker: missing tested_against_case = block N3.4
    from Status=Accepted."""
    for row in SOLVER_DERIVATIONS:
        assert row.tested_against_case, (
            f"row regime={row.regime!r} thermal={row.thermal!r} "
            "has empty tested_against_case (charter ship-blocker)"
        )


def test_every_row_has_non_empty_rationale():
    for row in SOLVER_DERIVATIONS:
        assert len(row.rationale) >= 20, (
            f"row regime={row.regime!r} thermal={row.thermal!r} "
            "has too-short rationale to be useful in the UI"
        )


def test_solver_names_are_valid_openfoam_solvers():
    """Sanity: solver names are spelled correctly."""
    valid = {
        "icoFoam", "simpleFoam", "pimpleFoam",
        "buoyantSimpleFoam", "buoyantPimpleFoam",
    }
    for row in SOLVER_DERIVATIONS:
        assert row.solver in valid, (
            f"row regime={row.regime!r} has invalid solver={row.solver!r}"
        )


# ────────── derive_solver behavior ──────────


def test_derive_laminar_no_thermal_picks_icoFoam():
    row = derive_solver(_regime("laminar"), _material(with_thermal=False))
    assert row.solver == "icoFoam"


def test_derive_laminar_with_thermal_picks_buoyantPimple():
    row = derive_solver(_regime("laminar"), _material(with_thermal=True))
    assert row.solver == "buoyantPimpleFoam"


def test_derive_rans_ras_no_thermal_picks_simpleFoam():
    row = derive_solver(_regime("RANS-RAS"), _material(with_thermal=False))
    assert row.solver == "simpleFoam"


def test_derive_rans_ras_with_thermal_picks_buoyantSimple():
    row = derive_solver(_regime("RANS-RAS"), _material(with_thermal=True))
    assert row.solver == "buoyantSimpleFoam"


def test_derive_rans_komega_sst_no_thermal_picks_simpleFoam():
    row = derive_solver(
        _regime("RANS-kOmegaSST"), _material(with_thermal=False),
    )
    assert row.solver == "simpleFoam"


def test_derive_rans_komega_sst_with_thermal_picks_buoyantSimple():
    row = derive_solver(
        _regime("RANS-kOmegaSST"), _material(with_thermal=True),
    )
    assert row.solver == "buoyantSimpleFoam"


def test_derive_les_stub_no_thermal_picks_pimpleFoam():
    row = derive_solver(_regime("LES-stub"), _material(with_thermal=False))
    assert row.solver == "pimpleFoam"


def test_derive_les_stub_with_thermal_picks_buoyantPimple():
    row = derive_solver(_regime("LES-stub"), _material(with_thermal=True))
    assert row.solver == "buoyantPimpleFoam"


def test_derive_returns_row_with_full_rationale():
    """Returned row is the dataclass — UI can render rationale +
    tested_against_case alongside the solver name."""
    row = derive_solver(_regime("laminar"), _material(with_thermal=False))
    assert row.regime == "laminar"
    assert row.thermal is False
    assert row.tested_against_case == "lid_driven_cavity"
    assert "low-Re" in row.rationale or "incompressible" in row.rationale


# ────────── defensive branches ──────────


def test_derive_unknown_regime_raises_keyerror():
    """If RegimeKind literal grows without the table being updated,
    derive_solver fails loud rather than silently defaulting."""
    class _FakeRegime:
        regime = "future-not-implemented"
    with pytest.raises(KeyError, match="no solver derivation"):
        derive_solver(_FakeRegime(), _material(with_thermal=False))  # type: ignore[arg-type]
