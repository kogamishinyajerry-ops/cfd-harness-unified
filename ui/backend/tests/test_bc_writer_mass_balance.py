"""DEC-V61-198 A4 · mass-balance pre-flight advisory tests."""
from __future__ import annotations

import pytest

from ui.backend.schemas.bc_contract import (
    BCContract,
    InletOutletBC,
    MassFlowInletBC,
    NoSlipWallBC,
    PressureOutletBC,
    VelocityInletBC,
)
from ui.backend.services.case_bc.writer import check_mass_balance


def test_mass_balance_ok_with_pressure_outlet():
    contract = BCContract(authored_at="2026-05-12T00:00:00Z", patches={
        "inlet": MassFlowInletBC(mass_flow_rate=0.5),
        "outlet": PressureOutletBC(gauge_pressure=0.0),
        "wall": NoSlipWallBC(),
    })
    result = check_mass_balance(contract)
    assert result.status == "ok"
    assert result.total_inlet_kg_s == pytest.approx(0.5)
    assert result.has_relief_outlet is True


def test_mass_balance_ok_with_inlet_outlet_as_relief():
    contract = BCContract(authored_at="2026-05-12T00:00:00Z", patches={
        "inlet": MassFlowInletBC(mass_flow_rate=0.2),
        "farfield": InletOutletBC(gauge_pressure=0.0),
    })
    result = check_mass_balance(contract)
    assert result.status == "ok"
    assert result.has_relief_outlet is True


def test_mass_balance_no_relief_outlet_diverge_risk():
    contract = BCContract(authored_at="2026-05-12T00:00:00Z", patches={
        "inlet_a": MassFlowInletBC(mass_flow_rate=0.3),
        "inlet_b": MassFlowInletBC(mass_flow_rate=0.2),
        "wall": NoSlipWallBC(),
    })
    result = check_mass_balance(contract)
    assert result.status == "no_relief_outlet"
    assert result.total_inlet_kg_s == pytest.approx(0.5)
    assert result.has_relief_outlet is False
    assert "diverge" in result.message


def test_mass_balance_no_mass_flow_pressure_driven():
    contract = BCContract(authored_at="2026-05-12T00:00:00Z", patches={
        "inlet": VelocityInletBC(velocity=(1.0, 0.0, 0.0)),
        "outlet": PressureOutletBC(gauge_pressure=0.0),
    })
    result = check_mass_balance(contract)
    assert result.status == "no_mass_flow"
    assert result.total_inlet_kg_s == 0.0
